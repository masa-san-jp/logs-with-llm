#!/usr/bin/env python3
"""
Weekly blog post generator for decision-logs-with-llm.

Reads logs under `logs/`, selects entries from the past BLOG_DAYS days based on
yyyymmdd tokens in their paths, and generates bilingual blog-style Markdown posts
under `blog/yyyymmdd-weekly.md` and `blog/yyyymmdd-weekly-en.md` using OpenAI,
Anthropic, or Ollama.

Usage:
    # OpenAI mode (default)
    OPENAI_API_KEY=sk-... python scripts/generate_weekly_blog.py

    # Anthropic mode
    LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-... python scripts/generate_weekly_blog.py

    # Ollama mode
    LLM_PROVIDER=ollama python scripts/generate_weekly_blog.py

Environment variables:
    LLM_PROVIDER      openai | anthropic | ollama (default: openai)
    BLOG_DAYS         number of days to look back (default: 7)
    OPENAI_API_KEY    required for openai mode
    OPENAI_BASE_URL   optional; override base URL (default: https://api.openai.com/v1)
    OPENAI_MODEL      model name for openai mode (default: gpt-4o-mini)
    ANTHROPIC_API_KEY required for anthropic mode
    ANTHROPIC_MODEL   model name for anthropic mode (default: claude-sonnet-4-20250514)
    OLLAMA_URL        Ollama endpoint (default: http://localhost:11434)
    OLLAMA_MODEL      model name for ollama mode (default: llama3)
    BLOG_DATE         override output date (YYYY-MM-DD); default: today UTC
    LOGS_DIR          path to logs directory (default: logs)
    BLOG_DIR          path to blog directory (default: blog)
    STATE_FILE        path to state JSON file (default: .blog_state.json)
"""

import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai").lower()
BLOG_DAYS = int(os.environ.get("BLOG_DAYS", "7"))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss:20b")
LOGS_DIR = REPO_ROOT / os.environ.get("LOGS_DIR", "logs")
BLOG_DIR = REPO_ROOT / os.environ.get("BLOG_DIR", "blog")
STATE_FILE = REPO_ROOT / os.environ.get("STATE_FILE", ".blog_state.json")

DATE_RE = re.compile(r"\b(20\d{2})(\d{2})(\d{2})\b")
SUPPORTED_LANGUAGES = ("ja", "en")

_SUMMARIZE_PROMPT_TEMPLATE = (
    'You are a precise technical summarizer.\n'
    'Summarize the following content from "{source_name}".\n'
    'Preserve ALL important elements: events, decisions made, things built or learned, '
    'open questions, concrete numbers, and tool names.\n'
    'Be concise but complete — do not drop key facts. Write in plain prose, no headers needed.\n\n'
    'Content:\n{content}\n'
)


def validate_language(language: str) -> str:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    return language


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def run_date() -> date:
    raw = os.environ.get("BLOG_DATE", "")
    if raw:
        return date.fromisoformat(raw)
    return today_utc()


def extract_date_from_path(path: str) -> Optional[date]:
    """Return the first yyyymmdd date found in a path string, or None."""
    for m in DATE_RE.finditer(path):
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Log selection
# ---------------------------------------------------------------------------

def collect_log_files(window_start: date, window_end: date) -> list[Path]:
    """
    Return all log files whose path contains a yyyymmdd token within
    [window_start, window_end].  Falls back to git-diff strategy when no
    dated paths are found.
    """
    dated_files: list[Path] = []

    for path in sorted(LOGS_DIR.rglob("*")):
        if not path.is_file():
            continue
        d = extract_date_from_path(str(path.relative_to(REPO_ROOT)))
        if d is not None and window_start <= d <= window_end:
            dated_files.append(path)

    if dated_files:
        return dated_files

    # Fallback: git diff against the commit recorded in state file
    print(
        "[generate_weekly_blog] No dated log files found in window; "
        "falling back to git-diff strategy.",
        file=sys.stderr,
    )
    return _git_diff_log_files(window_start)


def _git_diff_log_files(window_start: Optional[date] = None) -> list[Path]:
    """Return log files changed since the last recorded commit SHA.

    When no prior SHA is recorded, falls back to ``git log --since`` bounded
    by *window_start* (if provided) rather than the single ``HEAD~1..HEAD``
    diff, so that the full ``BLOG_DAYS`` window is respected.
    """
    state = _load_state()
    base_sha = state.get("last_commit_sha", "")

    cmd: list[str]
    if base_sha:
        cmd = ["git", "-C", str(REPO_ROOT), "diff", "--name-only", base_sha, "HEAD"]
    elif window_start:
        cmd = [
            "git", "-C", str(REPO_ROOT),
            "log", "--name-only", "--format=",
            f"--since={window_start.isoformat()}",
            "HEAD",
        ]
    else:
        cmd = ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "HEAD~1", "HEAD"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        changed = result.stdout.strip().splitlines()
    except subprocess.CalledProcessError:
        return []

    files: list[Path] = []
    for rel in changed:
        if rel.startswith("logs/"):
            p = REPO_ROOT / rel
            if p.is_file():
                files.append(p)
    return files


def extract_pdf_text(path: Path) -> str:
    """Extract plain text from a PDF file using pypdf.

    Returns an empty string if pypdf is not installed or the file cannot be parsed.
    """
    try:
        import pypdf  # type: ignore[import]
    except ImportError:
        print(
            f"[generate_weekly_blog] pypdf not installed; skipping PDF file: {path}",
            file=sys.stderr,
        )
        return ""

    pages: list[str] = []
    try:
        with open(path, "rb") as fh:
            reader = pypdf.PdfReader(fh)
            for page in reader.pages:
                text = page.extract_text() or ""
                pages.append(text)
    except Exception as exc:  # noqa: BLE001
        print(
            f"[generate_weekly_blog] Failed to read PDF {path}: {exc}",
            file=sys.stderr,
        )
        return ""

    return "\n".join(pages)


def read_log_files(files: list[Path]) -> dict[str, str]:
    """Read each file and return a dict mapping relative path to raw content."""
    result: dict[str, str] = {}
    for f in files:
        key = str(f.relative_to(REPO_ROOT))
        try:
            if f.suffix.lower() == ".pdf":
                content = extract_pdf_text(f)
            else:
                content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""
        result[key] = content
    return result


def summarize_content(content: str, source_name: str) -> str:
    """Summarize content with an independent LLM call (no shared context).

    Falls back to the original content if the LLM call fails, so a single
    bad file does not abort the whole run.
    """
    prompt = _SUMMARIZE_PROMPT_TEMPLATE.format(
        source_name=source_name, content=content
    )
    print(f"[generate_weekly_blog] Summarizing: {source_name}")
    try:
        return generate_blog_content(prompt)
    except Exception as exc:
        print(
            f"[generate_weekly_blog] Summarization failed for {source_name}: {exc}; "
            "using original content.",
            file=sys.stderr,
        )
        return content


def summarize_log_files(log_files_dict: dict[str, str]) -> str:
    """Summarize each file independently and aggregate the results."""
    summaries: list[str] = []
    for source_name, content in log_files_dict.items():
        if not content.strip():
            continue
        summary = summarize_content(content, source_name)
        summaries.append(f"### {source_name}\n\n{summary}")
    return "\n\n---\n\n".join(summaries)


def summarize_previous_blog(language: str) -> str:
    """Read the previous blog and summarize it with an independent LLM call."""
    raw = read_previous_blog(language)
    if not raw:
        return ""
    prev_post = find_previous_blog(language)
    source_name = prev_post.name if prev_post else f"previous-{language}-blog"
    return summarize_content(raw, source_name)


# ---------------------------------------------------------------------------
# Previous blog context / output paths
# ---------------------------------------------------------------------------

def blog_output_path(post_date: date, language: str) -> Path:
    language = validate_language(language)
    date_token = post_date.strftime("%Y%m%d")
    if language == "ja":
        filename = f"{date_token}-weekly.md"
    else:
        filename = f"{date_token}-weekly-en.md"
    return BLOG_DIR / filename


def find_previous_blog(language: str) -> Optional[Path]:
    """Return the most recent blog post file for the requested language, or None."""
    language = validate_language(language)
    pattern = "*-weekly.md" if language == "ja" else "*-weekly-en.md"
    posts = sorted(BLOG_DIR.glob(pattern), reverse=True)
    return posts[0] if posts else None


def read_previous_blog(language: str) -> str:
    post = find_previous_blog(language)
    if post is None:
        return ""
    try:
        return post.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_prompt(logs_text: str, prev_blog: str, post_date: date, language: str) -> str:
    language = validate_language(language)
    date_str = post_date.strftime("%Y-%m-%d")
    prev_section = ""
    if prev_blog:
        prev_section = f"""
## Previous blog post (for context — describe what changed since then)

{prev_blog}
"""

    if language == "ja":
        role_text = f"""あなたは次のような書き手です:
観察者かつ実験者であり、静かな熱量を持ち、謙抑な探究者として仮説形で提示します。
常に自分の制作・実践に接続し、物事を分解と接続によって捉え直します。
そして世界を「装置」として俯瞰します。
今日は {date_str} です。"""

        language_guidance = (
            "- 一人称は「私」に統一すること（筆者/僕/俺/わたし は禁止）\n"
            "- 文体は「です・ます」基調\n"
            "- 断定と仮説の比率を 6:4〜5:5 に保つ。「〜だと私は思う」「〜のではないか」「〜と考えられる」等の言い換えを活用する\n"
            "- 冒頭の 1〜3 文は、事実提示 / 状況設定 / 前日譚のいずれかで始める\n"
            "- 見出しは「概念：切り口」形式（H2 主体、時系列ラベル禁止）\n"
            "- 段落は 1〜3 文単位。長いブロックは改行で割る\n"
            "- 語彙注入: 以下の core リストから 5〜15 箇所を文脈に合わせて使用する\n"
            "  [装置, 偏在, 手触り感, 仮説, 解像度, 再現可能, 身体性, 着想, 閃き, 静かな, 実在感, 手応え, 狙いを定める]\n"
            "- 接続語として「〜とすると〜」「一方で〜」「〜のではないだろうか」「つまり〜」「逆に〜」を段落間に散らす\n"
            "- 思考パターン: 抽象を 2〜3 要素に分解、ミクロ↔マクロ往復、対比（デジタル/フィジカル 等）の痕跡を残す\n"
            "- 末尾近くで、自分の制作・実践への接続を 1 段落含める\n"
            "- 末尾は「自分の制作への接続」「普遍化」「読者への静かな挨拶」「公開日の明記」のいずれか（複数可）で締める\n"
            "- 禁止語（出力しないこと）: ヤバい / エモい / 神 / エグい / めちゃくちゃ / 完全に / 絶対に / 必ず / 絵文字（本文内）\n"
            "- プロジェクト名・ツール名・コード識別子は正確に。英語のままで自然な場合は英語を維持する\n"
            "- 文量目安: 3000〜4000 字"
        )

        prohibitions = (
            "制約（必ず守ること）:\n"
            "- 原稿（ログ）にない題材・固有名詞・エピソード・人物を追加しない\n"
            "- 原稿の主張の向き（賛否・立場）を変えない\n"
            "- 語彙注入は 5〜15 箇所以内に留める\n"
            "- 感情表現を捏造しない\n"
            "- 他者の作品への批判強度を勝手に増減させない\n"
            "- ログが分析していないテーマを新たに読み込まない\n"
            "- 数字・データ・引用を創作しない"
        )

        final_gate = (
            "出力前に以下を自己確認すること:\n"
            "- [ ] 題材・主張・固有名詞が原稿のまま\n"
            "- [ ] 「観察し、分解し、制作に接続する人」として読める\n"
            "- [ ] 断定と推測が適度に混在している\n"
            "- [ ] 具体↔抽象の接続が少なくとも1箇所ある\n"
            "- [ ] 末尾に制作接続 or 普遍化が含まれる\n"
            "- [ ] 語彙注入が自然で過剰でない"
        )

        required_structure = (
            "Required structure:\n"
            "1. `# <タイトル>` — 30 字以内で読者の好奇心・共感を喚起する記事タイトル。日付ベースのタイトルは使わない\n"
            "2. 冒頭段落（2〜3 文）: 事実提示 / 状況設定 / 前日譚のいずれかで始める\n"
            "3. 本文セクション: H2 見出しを「概念：切り口」形式で自由に設定する。\n"
            "   固定セクション名（Highlights / What I Worked On 等）は使わない。\n"
            "   ログの実際のテーマを反映した見出しを選ぶこと。"
        )

    else:
        role_text = f"""You are a writer with the following persona:
An observer and experimenter with quiet but sustained passion.
A humble inquirer who presents ideas as hypotheses, not assertions.
A creator who always connects insights back to their own practice.
A thinker who decomposes and reconnects concepts.
Someone who views the world through the lens of "mechanisms" and "systems".
Today is {date_str}."""

        language_guidance = (
            "- Write in first person, in English (the logs may be in Japanese; translate and interpret)\n"
            "- Hedging ratio: Use assertive and hedged expressions at roughly 6:4 to 5:5."
            ' Prefer: "I think…", "It seems that…", "One might argue…", "Perhaps…", "I wonder whether…"\n'
            "- Opening: Begin with one of — (a) a concrete fact or observation, (b) a situational setup, (c) a brief backstory\n"
            '- Headings: Use "Concept: Angle" format for all H2 headings. Avoid chronological labels (Step 1 / Next / Finally)\n'
            "- Paragraphs: 1–3 sentences per paragraph. Break long blocks with line breaks\n"
            "- Vocabulary injection: Inject 5–15 instances of:"
            " mechanism / apparatus, ubiquity / pervasive, tactility / texture,"
            " granularity / resolution, hypothesis, reproducible, insight, emergent, friction, interplay\n"
            '- Connectors: Scatter: "That said,", "In other words,", "On the other hand,", "If so,", "One might wonder whether", "Conversely,"\n'
            "- Thinking patterns: Leave traces of (a) decomposing abstraction into 2–3 elements,"
            " (b) micro↔macro oscillation, (c) contrast pairs (digital/physical, local/global, explicit/implicit)\n"
            "- Closing: End with connection to own practice, universalization of the theme, a quiet closing remark, or publication date\n"
            '- Forbidden words: Avoid "amazing", "awesome", "literally", "totally", "absolutely", "definitely",'
            ' "it\'s insane that", slang intensifiers, and emojis in body text\n'
            '- Self-reference: Include 1–2 explicit "I think / I believe / I suspect" phrases at section transitions\n'
            "- Be specific: mention project names, tools, and concrete outcomes\n"
            "- Total length: around 2000–3000 characters"
        )

        prohibitions = (
            "Constraints (strictly follow):\n"
            "- Do not introduce topics, proper nouns, episodes, or people not present in the source logs\n"
            "- Do not alter the stance or position of arguments in the logs\n"
            "- Do not over-inject vocabulary (5–15 instances maximum)\n"
            "- Do not fabricate emotions or reactions\n"
            "- Do not increase or decrease the critical intensity toward others' work\n"
            "- Do not introduce new themes not analysed in the source\n"
            "- Do not invent numbers, data, or quotations"
        )

        final_gate = (
            "Before writing your output, confirm each of the following:\n"
            '- [ ] Topics, claims, and proper nouns match the source logs\n'
            '- [ ] The post reads as written by someone who "observes, decomposes, and connects to practice"\n'
            "- [ ] Assertions and hedged expressions are appropriately mixed\n"
            "- [ ] At least one concrete↔abstract connection is present\n"
            "- [ ] The closing connects to own practice or universalises the theme\n"
            "- [ ] Vocabulary injection feels natural and is not excessive"
        )

        required_structure = (
            "Required structure:\n"
            "1. `# <Title>` — a short, catchy, article-style title in 30 characters or fewer"
            " that makes the reader feel curious, excited, or emotionally engaged; do not use a generic date-based title\n"
            "2. An opening paragraph (2–3 sentences) using one of: fact presentation / situational setup / backstory\n"
            "3. Free-form body sections using H2 headings in \"Concept: Angle\" format.\n"
            "   Do NOT use fixed section names (Highlights / What I Worked On / etc.).\n"
            "   Choose headings that reflect the actual themes in the logs."
        )

    return f"""{role_text}

Write an engaging blog post in Markdown based on the decision logs below.
The post should feel like a genuine personal reflection — not a dry summary.

{required_structure}

Guidelines:
{language_guidance}

{prohibitions}

{final_gate}
{prev_section}
## This week's decision logs

{logs_text}
"""


# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------

def _call_openai(prompt: str) -> str:
    import urllib.request

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set the environment variable or switch to LLM_PROVIDER=ollama."
        )

    payload = json.dumps(
        {
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
    ).encode()

    req = urllib.request.Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())
    return body["choices"][0]["message"]["content"]


def _call_anthropic(prompt: str) -> str:
    import urllib.request

    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Set the environment variable or switch to LLM_PROVIDER=openai."
        )

    payload = json.dumps(
        {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())
    return body["content"][0]["text"]


def _call_ollama(prompt: str) -> str:
    import urllib.request

    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }
    ).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.loads(resp.read())
    return body.get("response", "")


def generate_blog_content(prompt: str) -> str:
    if LLM_PROVIDER == "anthropic":
        print(f"[generate_weekly_blog] Using Anthropic (model={ANTHROPIC_MODEL})")
        return _call_anthropic(prompt)
    elif LLM_PROVIDER == "ollama":
        print(f"[generate_weekly_blog] Using Ollama ({OLLAMA_URL}, model={OLLAMA_MODEL})")
        return _call_ollama(prompt)
    else:
        print(f"[generate_weekly_blog] Using OpenAI (model={OPENAI_MODEL})")
        return _call_openai(prompt)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(post_date: date) -> None:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        sha = result.stdout.strip()
    except subprocess.CalledProcessError:
        sha = ""

    state = _load_state()
    state["last_commit_sha"] = sha
    state["last_blog_date"] = post_date.isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    post_date = run_date()
    window_end = post_date
    window_start = window_end - timedelta(days=BLOG_DAYS - 1)

    print(
        f"[generate_weekly_blog] date={post_date}  window={window_start}..{window_end}"
        f"  provider={LLM_PROVIDER}"
    )

    # Phase 1: Collect log files
    log_files = collect_log_files(window_start, window_end)
    if not log_files:
        print(
            "[generate_weekly_blog] No log files found for this period. "
            "Writing a placeholder post.",
            file=sys.stderr,
        )
        aggregated_logs_summary = "(No new log entries found for this period.)"
    else:
        print(f"[generate_weekly_blog] Found {len(log_files)} log file(s).")
        # Phase 2: Read file contents (returns dict)
        log_files_dict = read_log_files(log_files)
        # Phase 3: Summarize each file with an independent LLM context
        print("[generate_weekly_blog] Summarizing log files...")
        aggregated_logs_summary = summarize_log_files(log_files_dict)

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    for language in SUPPORTED_LANGUAGES:
        # Phase 4: Summarize previous blog with an independent LLM context
        print(f"[generate_weekly_blog] Summarizing previous {language} blog...")
        prev_blog_summary = summarize_previous_blog(language)
        if prev_blog_summary:
            prev_post = find_previous_blog(language)
            print(f"[generate_weekly_blog] Using previous {language} blog post: {prev_post.name}")
        else:
            print(f"[generate_weekly_blog] No previous {language} blog post found.")

        # Phase 5: Build prompt using compressed summaries only
        prompt = build_prompt(aggregated_logs_summary, prev_blog_summary, post_date, language)

        # Generate content
        content = generate_blog_content(prompt)

        # Write output
        output_path = blog_output_path(post_date, language)
        output_path.write_text(content + "\n", encoding="utf-8")
        print(f"[generate_weekly_blog] Written: {output_path.relative_to(REPO_ROOT)}")

    # Update state
    _save_state(post_date)


if __name__ == "__main__":
    main()
