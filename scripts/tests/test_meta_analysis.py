"""Unit tests for meta_analysis.py."""

import sys
from datetime import date
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Make the script importable without a package structure
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import meta_analysis as ma  # noqa: E402


# ---------------------------------------------------------------------------
# extract_date_from_path
# ---------------------------------------------------------------------------

class TestExtractDateFromPath:
    def test_directory_prefix(self):
        assert ma.extract_date_from_path("logs/20260310-grant-agent/note.md") == date(2026, 3, 10)

    def test_no_date(self):
        assert ma.extract_date_from_path("logs/no-date/readme.md") is None

    def test_invalid_month_skipped(self):
        assert ma.extract_date_from_path("logs/20261399-foo/file.md") is None

    def test_first_date_wins(self):
        assert ma.extract_date_from_path("logs/20260101-foo/20260201-bar.md") == date(2026, 1, 1)


# ---------------------------------------------------------------------------
# extract_llm_from_path
# ---------------------------------------------------------------------------

class TestExtractLlmFromPath:
    def test_claude_in_path(self):
        assert "claude" in ma.extract_llm_from_path("logs/20260218-oolama-agent-teams/claude/meeting.md")

    def test_gemini_in_path(self):
        assert "gemini" in ma.extract_llm_from_path("logs/20260217-gemini-task-manege-on-gws/note.md")

    def test_multiple_llms(self):
        llms = ma.extract_llm_from_path("logs/20260219-claude-gemini-comparison/notes.md")
        assert "claude" in llms
        assert "gemini" in llms

    def test_no_llm_in_path(self):
        assert ma.extract_llm_from_path("logs/20260310-grant-agent/note.md") == []

    def test_case_insensitive(self):
        assert "claude" in ma.extract_llm_from_path("logs/20260218-CLAUDE-notes/file.md")

    def test_deduplication(self):
        # "claude" appears twice but should only be reported once
        llms = ma.extract_llm_from_path("logs/20260218-claude/claude-notes.md")
        assert llms.count("claude") == 1


# ---------------------------------------------------------------------------
# collect_all_log_files
# ---------------------------------------------------------------------------

class TestCollectAllLogFiles:
    def _make_logs(self, tmp_path: Path, entries: list[tuple[str, str]]) -> Path:
        logs_dir = tmp_path / "logs"
        for rel_path, content in entries:
            p = logs_dir / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        return logs_dir

    def test_collects_md_files(self, tmp_path):
        logs_dir = self._make_logs(
            tmp_path,
            [
                ("20260310-project/note.md", "content"),
                ("20260311-other/data.md", "more content"),
            ],
        )
        meta_dir = tmp_path / "logs" / "meta"
        with (
            mock.patch.object(ma, "LOGS_DIR", logs_dir),
            mock.patch.object(ma, "META_OUTPUT_DIR", meta_dir),
            mock.patch.object(ma, "META_MAX_LOGS", 100),
        ):
            files = ma.collect_all_log_files()
        assert len(files) == 2
        assert all(f.suffix == ".md" for f in files)

    def test_excludes_meta_dir(self, tmp_path):
        logs_dir = self._make_logs(
            tmp_path,
            [
                ("20260310-project/note.md", "content"),
                ("meta/decision-patterns.md", "meta content"),
            ],
        )
        meta_dir = logs_dir / "meta"
        with (
            mock.patch.object(ma, "LOGS_DIR", logs_dir),
            mock.patch.object(ma, "META_OUTPUT_DIR", meta_dir),
            mock.patch.object(ma, "META_MAX_LOGS", 100),
        ):
            files = ma.collect_all_log_files()
        assert len(files) == 1
        assert files[0].name == "note.md"
        assert files[0].parent.name == "20260310-project"

    def test_respects_max_logs(self, tmp_path):
        logs_dir = self._make_logs(
            tmp_path,
            [(f"2026031{i}-topic/note.md", f"content {i}") for i in range(5)],
        )
        meta_dir = tmp_path / "logs" / "meta"
        with (
            mock.patch.object(ma, "LOGS_DIR", logs_dir),
            mock.patch.object(ma, "META_OUTPUT_DIR", meta_dir),
            mock.patch.object(ma, "META_MAX_LOGS", 3),
        ):
            files = ma.collect_all_log_files()
        assert len(files) == 3

    def test_includes_txt_and_pdf(self, tmp_path):
        logs_dir = tmp_path / "logs"
        (logs_dir / "20260310-project").mkdir(parents=True)
        (logs_dir / "20260310-project" / "note.txt").write_text("txt content")
        (logs_dir / "20260310-project" / "report.pdf").write_bytes(b"stub")
        meta_dir = tmp_path / "logs" / "meta"
        with (
            mock.patch.object(ma, "LOGS_DIR", logs_dir),
            mock.patch.object(ma, "META_OUTPUT_DIR", meta_dir),
            mock.patch.object(ma, "META_MAX_LOGS", 100),
        ):
            files = ma.collect_all_log_files()
        suffixes = {f.suffix for f in files}
        assert ".txt" in suffixes
        assert ".pdf" in suffixes


# ---------------------------------------------------------------------------
# build_log_entry
# ---------------------------------------------------------------------------

class TestBuildLogEntry:
    def test_contains_relative_path(self, tmp_path):
        f = tmp_path / "logs" / "20260310-project" / "note.md"
        f.parent.mkdir(parents=True)
        f.write_text("# Title\nContent here")
        with mock.patch.object(ma, "REPO_ROOT", tmp_path):
            entry = ma.build_log_entry(f)
        assert "logs/20260310-project/note.md" in entry

    def test_contains_date_metadata(self, tmp_path):
        f = tmp_path / "logs" / "20260310-project" / "note.md"
        f.parent.mkdir(parents=True)
        f.write_text("content")
        with mock.patch.object(ma, "REPO_ROOT", tmp_path):
            entry = ma.build_log_entry(f)
        assert "2026-03-10" in entry

    def test_contains_llm_metadata(self, tmp_path):
        f = tmp_path / "logs" / "20260218-claude-notes" / "note.md"
        f.parent.mkdir(parents=True)
        f.write_text("content")
        with mock.patch.object(ma, "REPO_ROOT", tmp_path):
            entry = ma.build_log_entry(f)
        assert "claude" in entry

    def test_truncates_long_content(self, tmp_path):
        f = tmp_path / "logs" / "20260310-project" / "note.md"
        f.parent.mkdir(parents=True)
        f.write_text("X" * 5000)
        with (
            mock.patch.object(ma, "REPO_ROOT", tmp_path),
            mock.patch.object(ma, "META_MAX_CHARS", 100),
        ):
            entry = ma.build_log_entry(f)
        assert "…" in entry

    def test_short_content_not_truncated(self, tmp_path):
        f = tmp_path / "logs" / "20260310-project" / "note.md"
        f.parent.mkdir(parents=True)
        f.write_text("Short")
        with (
            mock.patch.object(ma, "REPO_ROOT", tmp_path),
            mock.patch.object(ma, "META_MAX_CHARS", 200),
        ):
            entry = ma.build_log_entry(f)
        assert "…" not in entry


# ---------------------------------------------------------------------------
# build_analysis_prompt
# ---------------------------------------------------------------------------

class TestBuildAnalysisPrompt:
    def test_contains_date(self):
        prompt = ma.build_analysis_prompt(["log entry"], date(2026, 4, 1))
        assert "2026-04-01" in prompt

    def test_contains_log_count(self):
        entries = ["entry1", "entry2", "entry3"]
        prompt = ma.build_analysis_prompt(entries, date(2026, 4, 1))
        assert "3" in prompt

    def test_contains_section_markers(self):
        prompt = ma.build_analysis_prompt(["log"], date(2026, 4, 1))
        assert "SECTION 1" in prompt
        assert "SECTION 2" in prompt

    def test_contains_log_corpus(self):
        prompt = ma.build_analysis_prompt(["MY_UNIQUE_LOG_CONTENT"], date(2026, 4, 1))
        assert "MY_UNIQUE_LOG_CONTENT" in prompt

    def test_contains_output_paths(self):
        prompt = ma.build_analysis_prompt(["log"], date(2026, 4, 1))
        assert "decision-patterns.md" in prompt
        assert "session-bootstrap.yml" in prompt


# ---------------------------------------------------------------------------
# parse_llm_output
# ---------------------------------------------------------------------------

class TestParseLlmOutput:
    def test_splits_on_section_markers(self):
        llm_output = (
            "### SECTION 1: DECISION-PATTERNS CATALOG\n"
            "# Catalog content\n\n"
            "### SECTION 2: SESSION-BOOTSTRAP TEMPLATE\n"
            "bootstrap: true\n"
        )
        catalog, bootstrap = ma.parse_llm_output(llm_output)
        assert "Catalog content" in catalog
        assert "bootstrap: true" in bootstrap

    def test_fallback_when_no_delimiters(self):
        llm_output = "Some unstructured output"
        catalog, bootstrap = ma.parse_llm_output(llm_output)
        assert "Some unstructured output" in catalog
        assert bootstrap == ""

    def test_unwraps_fenced_code_blocks(self):
        llm_output = (
            "### SECTION 1: DECISION-PATTERNS CATALOG\n"
            "```markdown\n# Catalog\nContent here\n```\n"
            "### SECTION 2: SESSION-BOOTSTRAP TEMPLATE\n"
            "```yaml\nkey: value\n```\n"
        )
        catalog, bootstrap = ma.parse_llm_output(llm_output)
        assert "# Catalog" in catalog
        assert "key: value" in bootstrap

    def test_case_insensitive_section_headers(self):
        llm_output = (
            "### section 1: decision-patterns catalog\n"
            "catalog text\n"
            "### section 2: session-bootstrap template\n"
            "bootstrap text\n"
        )
        catalog, bootstrap = ma.parse_llm_output(llm_output)
        assert "catalog text" in catalog
        assert "bootstrap text" in bootstrap


# ---------------------------------------------------------------------------
# write_decision_patterns / write_session_bootstrap
# ---------------------------------------------------------------------------

class TestWriteOutputFiles:
    def test_write_decision_patterns_creates_file(self, tmp_path):
        meta_dir = tmp_path / "logs" / "meta"
        with (
            mock.patch.object(ma, "META_OUTPUT_DIR", meta_dir),
            mock.patch.object(ma, "REPO_ROOT", tmp_path),
        ):
            out = ma.write_decision_patterns("# Patterns\n", date(2026, 4, 1))
        assert out.exists()
        assert out.read_text(encoding="utf-8").startswith("# Patterns")

    def test_write_session_bootstrap_creates_file(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        with (
            mock.patch.object(ma, "PROMPTS_DIR", prompts_dir),
            mock.patch.object(ma, "REPO_ROOT", tmp_path),
        ):
            out = ma.write_session_bootstrap("key: value\n", date(2026, 4, 1))
        assert out.exists()
        assert "key: value" in out.read_text(encoding="utf-8")

    def test_write_decision_patterns_adds_newline(self, tmp_path):
        meta_dir = tmp_path / "logs" / "meta"
        with (
            mock.patch.object(ma, "META_OUTPUT_DIR", meta_dir),
            mock.patch.object(ma, "REPO_ROOT", tmp_path),
        ):
            out = ma.write_decision_patterns("content", date(2026, 4, 1))
        assert out.read_text(encoding="utf-8").endswith("\n")

    def test_write_session_bootstrap_adds_newline(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        with (
            mock.patch.object(ma, "PROMPTS_DIR", prompts_dir),
            mock.patch.object(ma, "REPO_ROOT", tmp_path),
        ):
            out = ma.write_session_bootstrap("content", date(2026, 4, 1))
        assert out.read_text(encoding="utf-8").endswith("\n")


# ---------------------------------------------------------------------------
# PDF extraction (same guards as in generate_weekly_blog tests)
# ---------------------------------------------------------------------------

class TestExtractPdfText:
    def test_returns_empty_when_pypdf_missing(self, tmp_path):
        dummy = tmp_path / "dummy.pdf"
        dummy.write_bytes(b"%PDF-1.4")
        with mock.patch.dict("sys.modules", {"pypdf": None}):
            assert ma._extract_pdf_text(dummy) == ""

    def test_returns_empty_for_corrupt_pdf(self, tmp_path):
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a real pdf")
        assert ma._extract_pdf_text(bad) == ""
