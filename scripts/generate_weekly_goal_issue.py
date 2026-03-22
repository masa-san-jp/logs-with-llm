#!/usr/bin/env python3
"""
Build a weekly GitHub issue draft prompt from the repository's documentation.

The output is meant to be passed to an LLM from GitHub Actions. The model is
asked to review the repository documentation as a whole and propose a single,
original, challenging next goal as a GitHub issue draft.
"""

import os
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

ISSUE_DATE = os.environ.get("ISSUE_DATE", "")
DOC_PATTERNS = (
    "README.md",
    "blog/*.md",
    "logs/**/*.md",
    "prompts/**/*.yml",
    "prompts/**/*.yaml",
)
MAX_DOC_FILES = int(os.environ.get("DOC_MAX_FILES", "120"))
MAX_SNIPPET_CHARS = int(os.environ.get("DOC_SNIPPET_CHARS", "220"))
MAX_HEADINGS = int(os.environ.get("DOC_MAX_HEADINGS", "4"))

DATE_RE = re.compile(r"\b(20\d{2})(\d{2})(\d{2})\b")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", re.MULTILINE)


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def run_date() -> date:
    if ISSUE_DATE:
        return date.fromisoformat(ISSUE_DATE)
    return today_utc()


def extract_date_from_path(path: str) -> date | None:
    for match in DATE_RE.finditer(path):
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            continue
    return None


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\x00", " ").split())


def list_document_files() -> list[Path]:
    unique_paths: dict[str, Path] = {}

    for pattern in DOC_PATTERNS:
        for path in REPO_ROOT.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            unique_paths[rel] = path

    files = list(unique_paths.values())
    files.sort(key=document_sort_key)
    return files[:MAX_DOC_FILES]


def document_sort_key(path: Path) -> tuple[int, int, str]:
    rel = path.relative_to(REPO_ROOT).as_posix()
    if rel == "README.md":
        section_rank = 0
    else:
        top_level = rel.split("/", 1)[0]
        section_rank = {"prompts": 1, "blog": 2, "logs": 3}.get(top_level, 9)

    detected_date = extract_date_from_path(rel)
    ordinal = -(detected_date.toordinal()) if detected_date else 0
    return (section_rank, ordinal, rel)


def extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    for match in HEADING_RE.finditer(text):
        heading = normalize_text(match.group(1).strip(" #"))
        if heading and heading not in headings:
            headings.append(heading)
    return headings[:MAX_HEADINGS]


def extract_snippet(text: str) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= MAX_SNIPPET_CHARS:
        return normalized
    return normalized[: MAX_SNIPPET_CHARS - 1].rstrip() + "…"


def build_document_summary(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        content = ""

    headings = extract_headings(content)
    snippet = extract_snippet(content)
    detected_date = extract_date_from_path(rel)

    lines = [f"### {rel}"]
    if detected_date:
        lines.append(f"- date: {detected_date.isoformat()}")
    if headings:
        lines.append(f"- headings: {' | '.join(headings)}")
    if snippet:
        lines.append(f"- excerpt: {snippet}")
    else:
        lines.append("- excerpt: (empty)")
    return "\n".join(lines)


def build_repo_overview(files: list[Path]) -> str:
    counts = Counter()
    dated_files = 0

    for path in files:
        rel = path.relative_to(REPO_ROOT).as_posix()
        key = "README"
        if rel != "README.md":
            key = rel.split("/", 1)[0]
        counts[key] += 1
        if extract_date_from_path(rel):
            dated_files += 1

    lines = [
        f"- total_docs: {len(files)}",
        f"- readme_docs: {counts.get('README', 0)}",
        f"- prompt_docs: {counts.get('prompts', 0)}",
        f"- blog_docs: {counts.get('blog', 0)}",
        f"- log_docs: {counts.get('logs', 0)}",
        f"- dated_docs: {dated_files}",
    ]
    return "\n".join(lines)


def build_prompt(files: list[Path], issue_date: date) -> str:
    doc_summaries = "\n\n".join(build_document_summary(path) for path in files)
    date_str = issue_date.isoformat()

    return f"""あなたはレポジトリ全体の流れを読み解き、次に取り組むべきテーマを提案する技術戦略家です。
今日は {date_str} です。

以下は、このレポジトリの主要ドキュメント（README / prompts / blog / logs）を横断して抽出した目録です。
この目録を俯瞰的に分析し、次に起票すべき GitHub Issue を 1 件だけ提案してください。

## 依頼
- 独創的でチャレンジングな目標を 1 件だけ選ぶこと
- ただの整理・清掃・軽微な改善ではなく、プロダクト性・研究性・運用改善のいずれかで明確な飛躍があること
- ドキュメント全体から見える繰り返しテーマ、未解決課題、最近の流れを踏まえること
- 大きすぎて抽象的すぎる提案ではなく、最初の 1〜3 週間で具体的な前進が見えるスコープにすること
- 既存の README / logs / blog の方向性とつながる理由を明示すること
- 出力は日本語にすること

## 出力形式（厳守）
最初の行を issue title として、必ず次の形式にしてください。

# [Weekly Docs Goal {date_str}] 具体的なタイトル

その後に以下の見出しをこの順番で書いてください。

## Why this goal now
- ドキュメント全体を俯瞰して、なぜ今この目標が自然かを説明する

## Goal
- 目標の要約を 1 段落で説明する

## Why it is original and challenging
- 既存の取り組みをどう一段引き上げるかを書く

## Proposed deliverables
- 3〜5 個の成果物を箇条書きで書く

## First actions
- 着手手順を 3〜5 個の箇条書きで書く

## Source signals from the docs
- 根拠になったドキュメントや流れを 3〜6 個の箇条書きで書く

## Repository overview
{build_repo_overview(files)}

## Document inventory

{doc_summaries}
"""


def main() -> None:
    files = list_document_files()
    print(build_prompt(files, run_date()))


if __name__ == "__main__":
    main()
