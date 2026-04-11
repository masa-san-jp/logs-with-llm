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


def read_log_files(files: list[Path]) -> str:
    """Concatenate log file contents into a single string."""
    parts: list[str] = []
    for f in files:
        try:
            if f.suffix.lower() == ".pdf":
                content = extract_pdf_text(f)
            else:
                content = f.read_text(encoding="utf-8", errors="replace")
            parts.append(f"### {f.relative_to(REPO_ROOT)}\n\n{content}")
        except OSError:
            pass
    return "\n\n---\n\n".join(parts)


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
        language_guidance = (
            "- Write in first person, in Japanese.\n"
            "- Keep project names, tool names, and code identifiers accurate; leave them in English where natural.\n"
            "- Keep the tone curious and reflective, not corporate.\n"
            "- Total length: around 3000–4000 characters."
        )
    else:
        language_guidance = (
            "- Write in first person, in English (the logs may be in Japanese; translate and interpret).\n"
            "- Be specific: mention project names, tools, and concrete outcomes.\n"
            "- Keep the tone curious and reflective, not corporate.\n"
            "- Total length: around 2000–3000 characters."
        )

    return f"""You are a blogger who is curious about a wide range of fields and does independent, cross-disciplinary research while building personal projects.
Today is {date_str}.

Write an engaging blog post in Markdown based on the decision logs below.
The post should feel like a genuine personal reflection — not a dry summary.

Required structure:
1. `# <Title>` — a short, catchy, article-style title in 30 characters or fewer that makes the reader feel curious, excited, or emotionally engaged; do not use a generic date-based title
2. A short, suggestive intro paragraph that sparks the reader's curiosity (2–3 sentences, conversational)
3. `## Highlights` — 3–5 bullet points with summaries of the most interesting and worth-exploring topics
4. `## What I Worked On` — narrative paragraphs about the week's work. Write with depth about the overall picture, the themes explored in detail, and what felt novel or interesting
5. `## Decisions & Tradeoffs` — key technical or design decisions made and why
6. `## Progress Since Last Time` — compare with the previous blog post; what moved forward, what evolved, and what is still unresolved
7. `## What's Next` — propose new themes for future work that extend the current progress and open up new areas

Guidelines:
{language_guidance}
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

    # Collect logs
    log_files = collect_log_files(window_start, window_end)
    if not log_files:
        print(
            "[generate_weekly_blog] No log files found for this period. "
            "Writing a placeholder post.",
            file=sys.stderr,
        )
        logs_text = "(No new log entries found for this period.)"
    else:
        print(f"[generate_weekly_blog] Found {len(log_files)} log file(s).")
        logs_text = read_log_files(log_files)

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    for language in SUPPORTED_LANGUAGES:
        prev_blog = read_previous_blog(language)
        if prev_blog:
            prev_post = find_previous_blog(language)
            print(f"[generate_weekly_blog] Using previous {language} blog post: {prev_post.name}")
        else:
            print(f"[generate_weekly_blog] No previous {language} blog post found.")

        prompt = build_prompt(logs_text, prev_blog, post_date, language)

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
