#!/usr/bin/env python3
"""
Cross-log meta-analysis pipeline for decision-logs-with-llm.

Reads all logs under `logs/`, extracts per-log metadata (date, LLMs referenced,
headings, decision snippets), then calls an LLM to identify recurring decision
patterns and open questions across the full corpus.

Two output files are produced:
  - logs/meta/decision-patterns.md  : structured decision-pattern catalog
  - prompts/session-bootstrap.yml   : session-bootstrap template with injected context

Usage:
    # OpenAI mode (default)
    OPENAI_API_KEY=sk-... python scripts/meta_analysis.py

    # Ollama mode
    META_MODE=ollama python scripts/meta_analysis.py

Environment variables:
    META_MODE           openai | ollama (default: openai)
    META_MAX_LOGS       max log files to include in analysis (default: 120)
    META_MAX_CHARS      max chars per log file to include (default: 2000)
    META_RUN_DATE       override analysis date (YYYY-MM-DD); default: today UTC
    OPENAI_API_KEY      required for openai mode
    OPENAI_BASE_URL     optional; override base URL (default: https://api.openai.com/v1)
    OPENAI_MODEL        model name for openai mode (default: gpt-4o-mini)
    OLLAMA_URL          Ollama endpoint (default: http://localhost:11434)
    OLLAMA_MODEL        model name for ollama mode (default: llama3)
    LOGS_DIR            path to logs directory (default: logs)
    META_OUTPUT_DIR     path for meta output files (default: logs/meta)
    PROMPTS_DIR         path to prompts directory (default: prompts)
"""

import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

META_MODE = os.environ.get("META_MODE", "openai").lower()
META_MAX_LOGS = int(os.environ.get("META_MAX_LOGS", "120"))
META_MAX_CHARS = int(os.environ.get("META_MAX_CHARS", "2000"))
META_RUN_DATE = os.environ.get("META_RUN_DATE", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
LOGS_DIR = REPO_ROOT / os.environ.get("LOGS_DIR", "logs")
META_OUTPUT_DIR = REPO_ROOT / os.environ.get("META_OUTPUT_DIR", "logs/meta")
PROMPTS_DIR = REPO_ROOT / os.environ.get("PROMPTS_DIR", "prompts")

DATE_RE = re.compile(r"\b(20\d{2})(\d{2})(\d{2})\b")
LLM_NAMES = ("claude", "gemini", "grok", "ollama", "chatgpt", "openai", "llama", "mistral")


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def run_date() -> date:
    if META_RUN_DATE:
        return date.fromisoformat(META_RUN_DATE)
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
# LLM-name extraction
# ---------------------------------------------------------------------------

def extract_llm_from_path(path: str) -> list[str]:
    """Return LLM names found in a file path (lowercase)."""
    lower = path.lower()
    found = [name for name in LLM_NAMES if name in lower]
    return list(dict.fromkeys(found))  # deduplicate while preserving order


# ---------------------------------------------------------------------------
# Log collection and reading
# ---------------------------------------------------------------------------

def collect_all_log_files() -> list[Path]:
    """Return all log files under LOGS_DIR, excluding the meta/ subdirectory."""
    files: list[Path] = []
    meta_dir = META_OUTPUT_DIR.resolve()

    for path in sorted(LOGS_DIR.rglob("*")):
        if not path.is_file():
            continue
        # Skip files inside the meta output directory
        try:
            path.resolve().relative_to(meta_dir)
            continue
        except ValueError:
            pass
        if path.suffix.lower() in (".md", ".txt", ".pdf"):
            files.append(path)

    return files[:META_MAX_LOGS]


def _read_file_text(path: Path) -> str:
    """Read text from a file, extracting PDF text if needed."""
    if path.suffix.lower() == ".pdf":
        return _extract_pdf_text(path)
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _extract_pdf_text(path: Path) -> str:
    """Extract plain text from a PDF using pypdf; returns '' on failure."""
    try:
        import pypdf  # type: ignore[import]
    except ImportError:
        print(
            f"[meta_analysis] pypdf not installed; skipping PDF: {path}",
            file=sys.stderr,
        )
        return ""

    pages: list[str] = []
    try:
        with open(path, "rb") as fh:
            reader = pypdf.PdfReader(fh)
            for page in reader.pages:
                pages.append(page.extract_text() or "")
    except Exception as exc:  # noqa: BLE001
        print(f"[meta_analysis] Failed to read PDF {path}: {exc}", file=sys.stderr)
        return ""

    return "\n".join(pages)


def build_log_entry(path: Path) -> str:
    """Return a compact per-log summary string for use in the analysis prompt."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = _read_file_text(path)
    snippet = text[:META_MAX_CHARS].rstrip()
    if len(text) > META_MAX_CHARS:
        snippet += "…"

    detected_date = extract_date_from_path(rel)
    llms = extract_llm_from_path(rel)

    meta_lines = [f"### {rel}"]
    if detected_date:
        meta_lines.append(f"- date: {detected_date.isoformat()}")
    if llms:
        meta_lines.append(f"- llms: {', '.join(llms)}")
    meta_lines.append("")
    meta_lines.append(snippet)

    return "\n".join(meta_lines)


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_analysis_prompt(log_entries: list[str], analysis_date: date) -> str:
    """Build the meta-analysis prompt from summarised log entries."""
    date_str = analysis_date.isoformat()
    corpus = "\n\n---\n\n".join(log_entries)

    return f"""You are a meta-cognitive analyst specialising in decision-making patterns.
Today is {date_str}.

The corpus below contains {len(log_entries)} conversation logs with LLMs (Claude, Gemini, Grok,
Ollama, etc.) covering topics like multi-agent system design, organisational knowledge extraction,
GWS CLI integration, and personal productivity.

Your task is to perform a **cross-log meta-analysis** and produce TWO clearly delimited sections:

## OUTPUT FORMAT — follow this EXACTLY

### SECTION 1: DECISION-PATTERNS CATALOG
Produce a Markdown document (`logs/meta/decision-patterns.md`) with the following structure:

```
# 意思決定パターンカタログ

_最終更新: {date_str} — ログ件数: {len(log_entries)}_

## テーマクラスター

List 3–6 recurring themes found across the logs.  For each theme write:
- **テーマ名**: (name)
- **頻度**: (N件)
- **代表ログ**: (comma-separated list of representative log paths)
- **要約**: (one-sentence summary)

## 意思決定パターン

Identify 5–8 named decision patterns.  For each pattern write:
### パターンN: [パターン名]
- **説明**: (what this pattern looks like)
- **頻度**: (N回)
- **具体例**: (a concrete example from the logs)
- **改善示唆**: (one actionable improvement suggestion)

## 未解決課題リスト

List 5–10 open questions or unresolved issues identified across the logs as numbered items.

## LLM活用パターン

For each LLM that appears in the logs, write one bullet noting its observed strengths and weaknesses.
```

### SECTION 2: SESSION-BOOTSTRAP TEMPLATE
Produce a YAML document (`prompts/session-bootstrap.yml`) with the following structure:

```yaml
# セッション開始メタプロンプト
# auto-generated by scripts/meta_analysis.py
# last_updated: {date_str}

meta:
  last_updated: "{date_str}"
  log_count: {len(log_entries)}

decision_patterns:
  # List the 5-8 patterns as YAML sequence items with keys: name, description, frequency
  - name: ""
    description: ""
    frequency: 0

unresolved_issues:
  # List the 5-10 open questions as plain strings
  - ""

llm_strengths:
  # key: LLM name (lowercase), value: one-sentence strength summary
  claude: ""
  gemini: ""

session_template: |
  # セッション開始コンテキスト
  以下は過去の議論から抽出したメタ情報です。本セッションの議論の質を高めるために参照してください。

  ## 自分の意思決定傾向（主なパターン）
  {{decision_patterns}}

  ## 未解決課題リスト
  {{unresolved_issues}}

  ## 今日のテーマに関連する過去の議論
  {{relevant_past_discussions}}

  ## 今日の議題
  {{today_topic}}
```

---

Now analyse the following corpus and produce both sections:

## LOG CORPUS

{corpus}
"""


# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------

def _call_openai(prompt: str) -> str:
    import urllib.request

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set the environment variable or switch to META_MODE=ollama."
        )

    payload = json.dumps(
        {
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
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
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read())
    return body["choices"][0]["message"]["content"]


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


def generate_analysis(prompt: str) -> str:
    if META_MODE == "ollama":
        print(f"[meta_analysis] Using Ollama ({OLLAMA_URL}, model={OLLAMA_MODEL})")
        return _call_ollama(prompt)
    else:
        print(f"[meta_analysis] Using OpenAI (model={OPENAI_MODEL})")
        return _call_openai(prompt)


# ---------------------------------------------------------------------------
# Output parsing and writing
# ---------------------------------------------------------------------------

_SECTION1_RE = re.compile(
    r"###\s*SECTION\s*1[^\n]*\n(.*?)(?=###\s*SECTION\s*2|\Z)",
    re.DOTALL | re.IGNORECASE,
)
_SECTION2_RE = re.compile(
    r"###\s*SECTION\s*2[^\n]*\n(.*?)$",
    re.DOTALL | re.IGNORECASE,
)

# Pattern that matches a fenced code block (```...```) and captures its content
_FENCED_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


def _unwrap_fenced(text: str) -> str:
    """If *text* is entirely a single fenced block, return the inner content; else return text."""
    stripped = text.strip()
    m = _FENCED_RE.fullmatch(stripped)
    if m:
        return m.group(1)
    # Try extracting the first fenced block if present
    m2 = _FENCED_RE.search(stripped)
    if m2:
        return m2.group(1)
    return stripped


def parse_llm_output(llm_text: str) -> tuple[str, str]:
    """
    Split the LLM response into (decision_patterns_md, session_bootstrap_yml).

    Returns the raw section text; falls back to the full response if delimiters
    are not found.
    """
    m1 = _SECTION1_RE.search(llm_text)
    m2 = _SECTION2_RE.search(llm_text)

    catalog_raw = m1.group(1) if m1 else llm_text
    bootstrap_raw = m2.group(1) if m2 else ""

    catalog = _unwrap_fenced(catalog_raw).strip()
    bootstrap = _unwrap_fenced(bootstrap_raw).strip()

    return catalog, bootstrap


def write_decision_patterns(content: str, analysis_date: date) -> Path:
    """Write the decision-patterns catalog to logs/meta/decision-patterns.md."""
    META_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = META_OUTPUT_DIR / "decision-patterns.md"
    out_path.write_text(content + "\n", encoding="utf-8")
    print(f"[meta_analysis] Written: {out_path.relative_to(REPO_ROOT)}")
    return out_path


def write_session_bootstrap(content: str, analysis_date: date) -> Path:
    """Write the session-bootstrap template to prompts/session-bootstrap.yml."""
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROMPTS_DIR / "session-bootstrap.yml"
    out_path.write_text(content + "\n", encoding="utf-8")
    print(f"[meta_analysis] Written: {out_path.relative_to(REPO_ROOT)}")
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    analysis_date = run_date()
    print(f"[meta_analysis] date={analysis_date}  mode={META_MODE}")

    # Collect all log files
    log_files = collect_all_log_files()
    if not log_files:
        print("[meta_analysis] No log files found. Exiting.", file=sys.stderr)
        sys.exit(1)
    print(f"[meta_analysis] Found {len(log_files)} log file(s).")

    # Build per-log entries
    log_entries = [build_log_entry(f) for f in log_files]

    # Build and run analysis prompt
    prompt = build_analysis_prompt(log_entries, analysis_date)
    llm_output = generate_analysis(prompt)

    # Parse output into two sections
    catalog_md, bootstrap_yml = parse_llm_output(llm_output)

    if not catalog_md:
        print("[meta_analysis] Warning: empty decision-patterns catalog.", file=sys.stderr)
        catalog_md = llm_output  # fallback: write everything to catalog

    # Write outputs
    write_decision_patterns(catalog_md, analysis_date)

    if bootstrap_yml:
        write_session_bootstrap(bootstrap_yml, analysis_date)
    else:
        print(
            "[meta_analysis] Warning: session-bootstrap section not found in LLM output; "
            "skipping prompts/session-bootstrap.yml update.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
