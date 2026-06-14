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
    OLLAMA_MODEL      fallback model name for ollama mode (default: gpt-oss:20b)
    OLLAMA_SUMMARIZE_MODEL  model for the log-summarize phase (default: OLLAMA_MODEL)
    OLLAMA_COMPOSE_MODEL    model for the article-writing phase (default: gpt-oss:120b)
    OLLAMA_THINK      enable reasoning/thinking mode (default: true)
    OLLAMA_TIMEOUT    per-request timeout seconds for ollama (default: 1800)
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
# Two-model split: a lightweight model condenses raw logs, a heavyweight model writes the article.
OLLAMA_SUMMARIZE_MODEL = os.environ.get("OLLAMA_SUMMARIZE_MODEL", OLLAMA_MODEL)
OLLAMA_COMPOSE_MODEL = os.environ.get("OLLAMA_COMPOSE_MODEL", "gpt-oss:120b")
OLLAMA_THINK = os.environ.get("OLLAMA_THINK", "true").lower() in ("1", "true", "yes", "on")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "1800"))
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
        return generate_blog_content(prompt, ollama_model=OLLAMA_SUMMARIZE_MODEL)
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

    for source_name, content in sorted(log_files_dict.items()):
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
                # Collapse internal newlines so each excerpt stays on one bullet line
                single_line = " ".join(excerpt.split())
                lines.append(f"  - {single_line}")
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
        role_text = f"""あなたは、自分の取り組みの記録をナラティブ（物語）として綴る書き手です。
これはマーケティング記事ではありません。読み手に何かを「与えます」と宣言したり売り込んだりせず、自分の思考と実践の蓄積として書きます。
なぜ自分がそう考えたのか、どう試し、どこでつまずき、どう解決しようとしているのか——その過程を、具体を省かずに地の文で語ります。
誇張はしませんが、思考の筋道と具体のディテールはくっきり描きます。
今日は {date_str} です。"""

        language_guidance = (
            "- 一人称は「私」に統一すること（筆者/僕/俺/わたし は禁止）\n"
            "- 文体は「です・ます」基調\n"
            "- これは「ナラティブの蓄積」。マーケ的な煽り・CTA（「ぜひ試してみてください」「〜が得られます」等）は書かない\n"
            "- 箇条書き・羅列に逃げない。要点も次の一手も、地の文の物語として書く（なぜそう考えたか・どう解決しようとしているかが伝わるように）\n"
            "- 抽象語や借り物の語彙でぼかさない。具体的な対象・固有名・数値・手順・判断をそのまま書く\n"
            "- 【重要】このプロンプト内に出てくる語（例：装置 / 解像度 / 手触り感 / 仮説 / 俯瞰）に引っ張られないこと。これらを出力にそのまま持ち込まない\n"
            "- 専門用語は、初出時に一言で噛み砕いてから使う\n"
            "- 段落は 1〜3 文単位。長いブロックは改行で割る\n"
            "- 具体は雑に省略しない。数値・手順・つまずき・比較・固有名を語りの中にディテールとして織り込む\n"
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
            "- [ ] タイトル直後が短い前書き（地の文）で、マーケ的な見出し（得られること等）になっていない\n"
            "- [ ] 箇条書き・羅列でなく、「なぜそう考えたか／どう解決しようとしているか」が地の文の物語として書かれている\n"
            "- [ ] 具体（数値・手順・つまずき・固有名）が省略されず語りに織り込まれている\n"
            "- [ ] このプロンプトの語彙（装置 / 解像度 / 手触り感 / 仮説 / 俯瞰）を出力にそのまま持ち込んでいない\n"
            "- [ ] 締めが（箇条書きでなく地の文で）取り組みの評価／残課題／次の一手になっている\n"
            "- [ ] マーケ的な煽り・CTA がない\n"
            "- [ ] 複数の Source Card が本文に具体的に反映されている\n"
            "- [ ] 1つの Source だけに記事が偏っていない"
        )

        required_structure = (
            "Required structure:\n"
            "1. `# <タイトル>` — 30 字以内。日付ベースのタイトルは使わない\n"
            "2. タイトル直後: 前書きとして、短い文章（2〜4 文程度の地の文）でこの記録が何についてかを静かに置く。"
            "「得られること」「この記事を読むと」のような見出し付き・マーケ的な価値提示はしない。箇条書きにしない\n"
            "3. 本文: 見出しは、何を調べた・作った・判断したかが具体的に分かるものにする"
            "（抽象概念だけの見出しや固定セクション名 Highlights 等は禁止）\n"
            "4. 本文の書き方: 箇条書き・羅列で済ませない。「なぜそう考えたのか」「どう試し、どう解決しようとしているのか」を"
            "地の文の物語として綴り、具体（数値・手順・つまずき・固有名）はその語りの中に織り込む\n"
            "5. 締め: ポエム的な所感やマーケ的な呼びかけで終えない。自分の取り組みへの評価（うまくいった点／いかなかった点）、"
            "残課題、次にやること（ネクストアクション）を、箇条書きではなく物語の続きとして地の文で書く"
        )

        task_instruction = (
            "Write the entry in Markdown as a narrative record of the work — the accumulation of\n"
            "my thinking and practice. Not a marketing piece, not a dry summary."
        )

    else:
        role_text = (
            "You are writing a weekly essay that frames the week's work in a business-philosophical light.\n"
            "Take a clear point of view on what this work means for how we build, operate, and think — not just the technical details.\n"
            "This is a thought-leadership essay, not a personal log and not a marketing post; connect concrete decisions to broader principles about technology, work, and value.\n"
            "Your style is reflective, analytical, and precise.\n"
            "You focus on patterns, design decisions, and implications rather than emotions or reactions.\n"
            f"Today is {date_str}."
        )

        language_guidance = (
            "- Write in first person, in English (the logs may be in Japanese; translate and interpret)\n"
            "- Maintain analytical distance; avoid emotional or subjective reactions\n"
            "- Prefer clear, declarative sentences over hedged or speculative phrasing\n"
            "- Opening (1–2 sentences): state the week's central finding, question, or area of investigation\n"
            "- Headings: describe what was investigated, built, or decided — prefer concrete subjects over abstract concepts\n"
            "- Paragraphs: 2–4 sentences; informative and precise\n"
            "- No vocabulary injection; use technical terms from the source logs directly\n"
            '- Connectors: prefer "This suggests", "The implication is", "A key finding was", "In contrast", "As a result"\n'
            "- Closing: synthesize the week's findings or implications — what the work points toward technically or conceptually\n"
            "- Forbidden: emotional adjectives, slang intensifiers, emojis, first-person feelings"
            ' (e.g., "I felt", "I was excited", "I enjoyed")\n'
            "- Be specific: mention project names, tools, design decisions, and concrete outcomes\n"
            "- Total length: around 1500–2500 characters"
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
            "- Do not use abstract vocabulary for its own sake; use technical terms from the source logs\n"
            "- Do not fabricate emotions or reactions\n"
            "- Do not increase or decrease the critical intensity toward others' work\n"
            "- Do not introduce new themes not analysed in the source\n"
            "- Do not invent numbers, data, or quotations"
        )

        final_gate = (
            "Before writing your output, confirm each of the following:\n"
            "- [ ] Topics, claims, and proper nouns match the source logs\n"
            "- [ ] The tone is analytical and informative, not personal or emotional\n"
            "- [ ] Personal feelings and reactions are absent from the text\n"
            "- [ ] The closing synthesizes findings or implications without personal reflection\n"
            "- [ ] Technical terms are used precisely, from the source logs\n"
            "- [ ] Multiple Source Cards are concretely reflected in the body\n"
            "- [ ] The article is not dominated by a single source\n"
            "- [ ] The post shows what was investigated, built, compared, or decided, not only an abstract theme"
        )

        required_structure = (
            "Required structure:\n"
            "1. `# <Title>` — concise, descriptive title stating the subject matter; 50 characters or fewer\n"
            "2. Opening (1–2 sentences): state the week's central finding, question, or area of investigation\n"
            "3. Body sections using H2 headings that describe what was investigated, built, or decided.\n"
            "   Do NOT use fixed section names (Highlights / Summary / etc.).\n"
            '   Do NOT use vague abstract headings — prefer concrete subjects'
            ' (e.g., "DB Schema: Event Sourcing Approach", "Agent Aiko: Persistent Persona Design").'
        )

        task_instruction = (
            "Write a research note in Markdown based on the decision logs below.\n"
            "The post should read as a technical research document — analytical, precise, and informative."
        )

    return f"""{role_text}

{task_instruction}

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


def _strip_thinking(text: str) -> str:
    """Remove any inline reasoning block a thinking model may emit in the body."""
    return re.sub(r"<think(?:ing)?>[\s\S]*?</think(?:ing)?>", "", text).strip()


def _call_ollama(prompt: str, model: str) -> str:
    import urllib.request

    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": OLLAMA_THINK,
        }
    ).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
        body = json.loads(resp.read())
    # With think=true Ollama returns reasoning in a separate "thinking" field, so
    # "response" already holds the answer; strip any inline block just in case.
    return _strip_thinking(body.get("response", ""))


def generate_blog_content(prompt: str, ollama_model: Optional[str] = None) -> str:
    if LLM_PROVIDER == "anthropic":
        print(f"[generate_weekly_blog] Using Anthropic (model={ANTHROPIC_MODEL})")
        return _call_anthropic(prompt)
    elif LLM_PROVIDER == "ollama":
        model = ollama_model or OLLAMA_MODEL
        print(
            f"[generate_weekly_blog] Using Ollama ({OLLAMA_URL}, model={model}, "
            f"think={OLLAMA_THINK})"
        )
        return _call_ollama(prompt, model)
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

        # Generate content (heavyweight model for the article itself)
        content = generate_blog_content(prompt, ollama_model=OLLAMA_COMPOSE_MODEL)

        # Write output
        output_path = blog_output_path(post_date, language)
        output_path.write_text(content + "\n", encoding="utf-8")
        print(f"[generate_weekly_blog] Written: {output_path.relative_to(REPO_ROOT)}")

    # Update state
    _save_state(post_date)


if __name__ == "__main__":
    main()
