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
    DEBUG_PROMPT_DIR  if set, write prompts to this directory for debugging
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
DEBUG_PROMPT_DIR = os.environ.get("DEBUG_PROMPT_DIR", "")

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

KEY_MARKERS = [
    "目的",
    "結論",
    "評価",
    "重要",
    "注意",
    "設計思想",
    "仮説",
    "定義",
    "前提",
    "課題",
    "改善",
    "運用",
    "判断",
    "つまり",
    "一方で",
    "だから",
    "要するに",
    "必要",
    "狙い",
    "方針",
    "比較",
    "リスク",
]


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
# Raw excerpt extraction
# ---------------------------------------------------------------------------

def _split_markdown_blocks(content: str) -> list[str]:
    clean = re.sub(r'```[\s\S]*?```', '', content)
    clean = re.sub(r'~~~[\s\S]*?~~~', '', clean)
    blocks = re.split(r'\n{2,}', clean.strip())
    return [b.strip() for b in blocks if b.strip()]


def _normalize_excerpt_block(block: str) -> str:
    return block.strip()


def _is_excerpt_candidate(block: str) -> bool:
    if not block:
        return False
    # Skip single-line headings
    if re.match(r'^#{1,6}\s', block) and '\n' not in block:
        return False
    # Skip large tables
    table_lines = [line for line in block.splitlines() if '|' in line]
    if len(table_lines) > 5:
        return False
    # Skip very short fragments
    if len(block) < 10:
        return False
    return True


def _score_excerpt_candidate(block: str, index: int, blocks: list[str]) -> int:
    score = 1
    for marker in KEY_MARKERS:
        if marker in block:
            score += 2
    # Boost if the preceding block is a heading
    if index > 0 and re.match(r'^#{1,6}\s', blocks[index - 1]):
        score += 2
    if '**' in block:
        score += 1
    if re.search(r'\d', block):
        score += 1
    # Inline code, camelCase, or snake_case identifiers
    if re.search(r'`[^`]+`|[A-Z][a-z]+[A-Z]|\b[a-z]+_[a-z]+\b', block):
        score += 1
    return score


def _truncate_excerpt(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_punc = max(
        truncated.rfind('。'),
        truncated.rfind('.'),
        truncated.rfind('！'),
        truncated.rfind('？'),
        truncated.rfind('!'),
        truncated.rfind('?'),
    )
    if last_punc > max_chars // 2:
        return truncated[:last_punc + 1]
    last_space = truncated.rfind(' ')
    if last_space > max_chars // 2:
        return truncated[:last_space].rstrip() + "..."
    return truncated.rstrip() + "..."


def extract_raw_excerpts(
    content: str,
    max_excerpts: int = 4,
    max_chars: int = 350,
) -> list[str]:
    """Extract representative raw excerpts from Markdown content without calling an LLM."""
    blocks = _split_markdown_blocks(content)
    scored: list[tuple[int, int, str]] = []

    for idx, block in enumerate(blocks):
        normalized = _normalize_excerpt_block(block)
        if not _is_excerpt_candidate(normalized):
            continue

        score = _score_excerpt_candidate(normalized, idx, blocks)
        if score <= 0:
            continue

        excerpt = _truncate_excerpt(normalized, max_chars)
        scored.append((score, -idx, excerpt))

    scored.sort(reverse=True)

    result: list[str] = []
    seen: set[str] = set()
    for _, _, excerpt in scored:
        key = excerpt[:80]
        if key in seen:
            continue
        seen.add(key)
        result.append(excerpt)
        if len(result) >= max_excerpts:
            break

    return result


# ---------------------------------------------------------------------------
# Source card construction
# ---------------------------------------------------------------------------

def build_source_cards(log_files_dict: dict[str, str]) -> str:
    """Build a structured block of Source Cards for each non-empty log file."""
    cards: list[str] = []

    for source_name, content in log_files_dict.items():
        if not content.strip():
            continue

        d = extract_date_from_path(source_name)
        date_text = d.isoformat() if d else "unknown"
        excerpts = extract_raw_excerpts(content)

        lines = [
            "## Source Card",
            "",
            f"- source: {source_name}",
            f"- date: {date_text}",
            "- raw_excerpts:",
        ]

        if excerpts:
            for excerpt in excerpts:
                lines.append(f"  - {excerpt}")
        else:
            lines.append("  - (No suitable raw excerpt found.)")

        cards.append("\n".join(lines))

    return "\n\n---\n\n".join(cards)


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
# Previous style capsule
# ---------------------------------------------------------------------------

def _extract_markdown_title(markdown: str) -> str:
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line
    return ""


def _extract_h2_headings(markdown: str) -> list[str]:
    headings: list[str] = []
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("## "):
            headings.append(line[3:].strip())
    return headings


def _extract_opening_paragraphs(markdown: str, max_paragraphs: int = 2) -> str:
    blocks = re.split(r'\n{2,}', markdown.strip())
    result: list[str] = []
    for block in blocks:
        b = block.strip()
        if not b:
            continue
        if re.match(r'^#{1,6}\s', b):
            continue
        result.append(b)
        if len(result) >= max_paragraphs:
            break
    return "\n\n".join(result)


def _extract_closing_paragraphs(markdown: str, max_paragraphs: int = 2) -> str:
    blocks = re.split(r'\n{2,}', markdown.strip())
    result: list[str] = []
    for block in reversed(blocks):
        b = block.strip()
        if not b:
            continue
        if re.match(r'^#{1,6}\s', b):
            continue
        result.insert(0, b)
        if len(result) >= max_paragraphs:
            break
    return "\n\n".join(result)


def build_previous_style_capsule(language: str) -> str:
    """Extract style reference elements from the previous blog post without calling an LLM."""
    raw = read_previous_blog(language)
    if not raw.strip():
        return ""

    title = _extract_markdown_title(raw)
    opening = _extract_opening_paragraphs(raw, max_paragraphs=2)
    headings = _extract_h2_headings(raw)
    closing = _extract_closing_paragraphs(raw, max_paragraphs=2)

    parts = ["## Previous Style Capsule", ""]

    if title:
        parts.extend(["### Previous title", title, ""])
    if opening:
        parts.extend(["### Opening sample", opening, ""])
    if headings:
        parts.append("### Heading pattern")
        parts.extend([f"- {h}" for h in headings])
        parts.append("")
    if closing:
        parts.extend(["### Closing sample", closing, ""])

    return "\n".join(parts).strip()


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_prompt(
    logs_text: str,
    source_cards: str,
    prev_style_capsule: str,
    post_date: date,
    language: str,
) -> str:
    language = validate_language(language)
    date_str = post_date.strftime("%Y-%m-%d")

    source_cards_section = ""
    if source_cards:
        source_cards_section = f"""
## Source cards with raw excerpts

{source_cards}
"""

    prev_style_section = ""
    if prev_style_capsule:
        prev_style_section = f"""
## Previous style reference

{prev_style_capsule}
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
            "- 語彙注入は任意。使う場合も3〜6箇所までに留める\n"
            "- 「装置」「解像度」「手触り感」「仮説」などの抽象語は、具体対象を説明できる場合だけ使う\n"
            "- 同じ抽象語を複数セクションで繰り返さない\n"
            "- 抽象語よりも、ログに含まれる具体的な調査対象・設計判断・比較観点を優先する\n"
            "- 接続語として「〜とすると〜」「一方で〜」「〜のではないだろうか」「つまり〜」「逆に〜」を段落間に散らす\n"
            "- 思考パターン: 抽象を 2〜3 要素に分解、ミクロ↔マクロ往復、対比（デジタル/フィジカル 等）の痕跡を残す\n"
            "- 末尾近くで、自分の制作・実践への接続を 1 段落含める\n"
            "- 末尾は「自分の制作への接続」「普遍化」「読者への静かな挨拶」「公開日の明記」のいずれか（複数可）で締める\n"
            "- 禁止語（出力しないこと）: ヤバい / エモい / 神 / エグい / めちゃくちゃ / 完全に / 絶対に / 必ず / 絵文字（本文内）\n"
            "- プロジェクト名・ツール名・コード識別子は正確に。英語のままで自然な場合は英語を維持する\n"
            "- 文量目安: 3000〜4000 字"
        )

        coverage_requirements = (
            "カバレッジ要件:\n"
            "- Source Card をそれぞれ別個の材料として扱う。\n"
            "- 本文では少なくとも min(4, Source数) 個の異なる Source Card に触れる。\n"
            "- Source が1つしかない場合を除き、1つの Source だけで記事全体を支配しない。\n"
            "- 扱った Source ごとに、プロジェクト名、意思決定、ツール名、比較観点、数値、具体ディテールのいずれかを最低1つ残す。\n"
            "- 複数 Source を共通テーマで統合してよいが、単一の抽象エッセイに潰さない。\n"
            "- 見出しには抽象概念だけでなく、できるだけ具体対象を含める。\n"
            "- カバレッジ計画やチェックリストは出力しない。"
        )

        prohibitions = (
            "制約（必ず守ること）:\n"
            "- 原稿（ログ）にない題材・固有名詞・エピソード・人物を追加しない\n"
            "- 原稿の主張の向き（賛否・立場）を変えない\n"
            "- 語彙注入は任意とし、使用する場合は 3〜6 箇所以内に留める\n"
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
            "- [ ] 語彙注入が自然で過剰でない\n"
            "- [ ] 複数の Source Card が本文に具体的に反映されている\n"
            "- [ ] 1つの Source だけに記事が偏っていない\n"
            "- [ ] 抽象テーマだけでなく、何を調べた・作った・比較したかが見える"
        )

        required_structure = (
            "Required structure:\n"
            "1. `# <タイトル>` — 30 字以内で読者の好奇心・共感を喚起する記事タイトル。日付ベースのタイトルは使わない\n"
            "2. 冒頭段落（1〜3 文）: 事実提示 / 状況設定 / 前日譚のいずれかで始める\n"
            "3. 本文セクション: H2 見出しを「概念：切り口」形式で自由に設定する。\n"
            "   固定セクション名（Highlights / What I Worked On 等）は使わない。\n"
            "   ログの実際のテーマを反映した見出しを選ぶこと。"
        )

    else:
        role_text = (
            "You are a writer with the following persona:\n"
            "An observer and experimenter with quiet but sustained passion.\n"
            "A humble inquirer who presents ideas as hypotheses, not assertions.\n"
            "A creator who always connects insights back to their own practice.\n"
            "A thinker who decomposes and reconnects concepts.\n"
            'Someone who views the world through the lens of "mechanisms" and "systems".\n'
            f"Today is {date_str}."
        )

        language_guidance = (
            "- Write in first person, in English (the logs may be in Japanese; translate and interpret)\n"
            "- Hedging ratio: Use assertive and hedged expressions at roughly 6:4 to 5:5."
            ' Prefer: "I think…", "It seems that…", "One might argue…", "Perhaps…", "I wonder whether…"\n'
            "- Opening: Begin with one of — (a) a concrete fact or observation, (b) a situational setup, (c) a brief backstory\n"
            '- Headings: Use "Concept: Angle" format for all H2 headings. Avoid chronological labels (Step 1 / Next / Finally)\n'
            "- Paragraphs: 1–3 sentences per paragraph. Break long blocks with line breaks\n"
            "- Vocabulary injection is optional. If used, keep it to 3–6 instances.\n"
            "- Abstract words such as mechanism, apparatus, texture, granularity, and hypothesis should be used only when they clarify a concrete source detail.\n"
            "- Do not repeat the same abstract motif across multiple sections.\n"
            "- Prefer concrete project names, tools, design decisions, comparison points, and source-specific details over abstract phrasing.\n"
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

        coverage_requirements = (
            "Coverage requirements:\n"
            "- Treat each Source Card as a distinct source.\n"
            "- Cover at least min(4, number_of_sources) distinct sources in the main body.\n"
            "- Do not let one source dominate the article unless there is only one source.\n"
            "- Each covered source must leave at least one concrete trace: project name, decision, tool name, comparison point, number, or direct detail.\n"
            "- You may synthesize sources under a shared theme, but do not collapse them into a single abstract essay.\n"
            "- Prefer headings that include concrete subjects, not only abstract concepts.\n"
            "- Do not output a checklist or coverage plan."
        )

        prohibitions = (
            "Constraints (strictly follow):\n"
            "- Do not introduce topics, proper nouns, episodes, or people not present in the source logs\n"
            "- Do not alter the stance or position of arguments in the logs\n"
            "- Do not over-inject vocabulary (3–6 instances maximum, optional)\n"
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
            "- [ ] Vocabulary injection feels natural and is not excessive\n"
            "- [ ] Multiple Source Cards are concretely reflected in the body\n"
            "- [ ] The article is not dominated by a single source\n"
            "- [ ] The post shows what was investigated, built, compared, or decided, not only an abstract theme"
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

{coverage_requirements}

{prohibitions}

{final_gate}
{source_cards_section}{prev_style_section}
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
        source_cards = ""
    else:
        print(f"[generate_weekly_blog] Found {len(log_files)} log file(s).")
        # Phase 2: Read file contents (returns dict)
        log_files_dict = read_log_files(log_files)
        # Phase 3: Summarize each file with an independent LLM context
        print("[generate_weekly_blog] Summarizing log files...")
        aggregated_logs_summary = summarize_log_files(log_files_dict)
        # Phase 4: Build source cards (deterministic, no LLM)
        source_cards = build_source_cards(log_files_dict)

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    for language in SUPPORTED_LANGUAGES:
        # Phase 5: Extract previous style capsule (deterministic, no LLM)
        prev_style_capsule = build_previous_style_capsule(language)
        if prev_style_capsule:
            prev_post = find_previous_blog(language)
            print(f"[generate_weekly_blog] Using previous {language} blog for style reference: {prev_post.name}")
        else:
            print(f"[generate_weekly_blog] No previous {language} blog post found.")

        # Phase 6: Build prompt using compressed summaries, source cards, and style capsule
        prompt = build_prompt(
            aggregated_logs_summary,
            source_cards,
            prev_style_capsule,
            post_date,
            language,
        )

        if DEBUG_PROMPT_DIR:
            debug_dir = REPO_ROOT / DEBUG_PROMPT_DIR
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / f"{post_date}-{language}-prompt.md").write_text(prompt, encoding="utf-8")

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
