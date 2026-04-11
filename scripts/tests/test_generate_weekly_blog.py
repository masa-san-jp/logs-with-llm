"""Unit tests for generate_weekly_blog.py – date parsing and log selection."""

import json
import sys
import types
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Make the script importable without a package structure
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_weekly_blog as gen  # noqa: E402


# ---------------------------------------------------------------------------
# extract_date_from_path
# ---------------------------------------------------------------------------

class TestExtractDateFromPath:
    def test_directory_prefix(self):
        assert gen.extract_date_from_path("logs/20260310-grant-agent/minute.md") == date(2026, 3, 10)

    def test_filename_date(self):
        assert gen.extract_date_from_path("logs/20260219-gemini-open-claw-on-asus-gx10.md") == date(2026, 2, 19)

    def test_no_date(self):
        assert gen.extract_date_from_path("logs/Utilizing-GitHub-projects/readme.md") is None

    def test_first_date_wins(self):
        assert gen.extract_date_from_path("logs/20260101-foo/20260201-bar.md") == date(2026, 1, 1)

    def test_invalid_month_skipped(self):
        # 20261399 – month 13, invalid
        assert gen.extract_date_from_path("logs/20261399-foo/file.md") is None

    def test_century_boundary(self):
        assert gen.extract_date_from_path("logs/20991231-test/file.md") == date(2099, 12, 31)


# ---------------------------------------------------------------------------
# collect_log_files  (filesystem-level, using tmp_path)
# ---------------------------------------------------------------------------

class TestCollectLogFiles:
    def _make_logs(self, tmp_path: Path, entries: list[tuple[str, str]]) -> Path:
        """Create fake log files and return the logs_dir."""
        logs_dir = tmp_path / "logs"
        for rel_path, content in entries:
            p = logs_dir / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        return logs_dir

    def test_selects_files_in_window(self, tmp_path):
        logs_dir = self._make_logs(
            tmp_path,
            [
                ("20260310-project/note.md", "inside"),
                ("20260301-old/note.md", "outside"),
            ],
        )
        with (
            mock.patch.object(gen, "LOGS_DIR", logs_dir),
            mock.patch.object(gen, "REPO_ROOT", tmp_path),
        ):
            files = gen.collect_log_files(date(2026, 3, 7), date(2026, 3, 10))
        assert len(files) == 1
        assert files[0].name == "note.md"
        assert "20260310" in str(files[0])

    def test_includes_boundary_dates(self, tmp_path):
        logs_dir = self._make_logs(
            tmp_path,
            [
                ("20260307-start/note.md", "start"),
                ("20260310-end/note.md", "end"),
                ("20260306-before/note.md", "before"),
                ("20260311-after/note.md", "after"),
            ],
        )
        with (
            mock.patch.object(gen, "LOGS_DIR", logs_dir),
            mock.patch.object(gen, "REPO_ROOT", tmp_path),
        ):
            files = gen.collect_log_files(date(2026, 3, 7), date(2026, 3, 10))
        names = {f.parent.name for f in files}
        assert "20260307-start" in names
        assert "20260310-end" in names
        assert "20260306-before" not in names
        assert "20260311-after" not in names

    def test_no_dated_files_returns_empty_when_no_git(self, tmp_path):
        logs_dir = self._make_logs(
            tmp_path,
            [("Utilizing-GitHub-projects/readme.md", "undated")],
        )
        with (
            mock.patch.object(gen, "LOGS_DIR", logs_dir),
            mock.patch.object(gen, "REPO_ROOT", tmp_path),
            mock.patch.object(gen, "_git_diff_log_files", return_value=[]),
        ):
            files = gen.collect_log_files(date(2026, 3, 7), date(2026, 3, 10))
        assert files == []


# ---------------------------------------------------------------------------
# find_previous_blog / read_previous_blog
# ---------------------------------------------------------------------------

class TestFindPreviousBlog:
    def test_returns_most_recent_japanese_post(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        (blog_dir / "20260201-weekly.md").write_text("old")
        (blog_dir / "20260301-weekly.md").write_text("newer")
        (blog_dir / "20260115-weekly.md").write_text("oldest")
        (blog_dir / "20260401-weekly-en.md").write_text("english")

        with mock.patch.object(gen, "BLOG_DIR", blog_dir):
            result = gen.find_previous_blog("ja")
        assert result is not None
        assert result.name == "20260301-weekly.md"

    def test_returns_most_recent_english_post(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        (blog_dir / "20260301-weekly.md").write_text("japanese")
        (blog_dir / "20260201-weekly-en.md").write_text("old")
        (blog_dir / "20260315-weekly-en.md").write_text("newer")

        with mock.patch.object(gen, "BLOG_DIR", blog_dir):
            result = gen.find_previous_blog("en")
        assert result is not None
        assert result.name == "20260315-weekly-en.md"

    def test_returns_none_when_empty(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        with mock.patch.object(gen, "BLOG_DIR", blog_dir):
            assert gen.find_previous_blog("ja") is None

    def test_read_previous_blog_content(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        (blog_dir / "20260301-weekly.md").write_text("# Post\nHello world")
        with mock.patch.object(gen, "BLOG_DIR", blog_dir):
            content = gen.read_previous_blog("ja")
        assert "Hello world" in content


class TestBlogOutputPath:
    def test_japanese_filename(self, tmp_path):
        with mock.patch.object(gen, "BLOG_DIR", tmp_path / "blog"):
            assert gen.blog_output_path(date(2026, 3, 10), "ja").name == "20260310-weekly.md"

    def test_english_filename(self, tmp_path):
        with mock.patch.object(gen, "BLOG_DIR", tmp_path / "blog"):
            assert gen.blog_output_path(date(2026, 3, 10), "en").name == "20260310-weekly-en.md"


# ---------------------------------------------------------------------------
# build_prompt
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_contains_date(self):
        prompt = gen.build_prompt("some logs", "", date(2026, 3, 10), "en")
        assert "2026-03-10" in prompt

    def test_contains_logs(self):
        prompt = gen.build_prompt("MY_SPECIAL_LOG_CONTENT", "", date(2026, 3, 10), "en")
        assert "MY_SPECIAL_LOG_CONTENT" in prompt

    def test_includes_previous_blog(self):
        prompt = gen.build_prompt("logs", "PREV_BLOG_CONTENT", date(2026, 3, 10), "en")
        assert "PREV_BLOG_CONTENT" in prompt

    def test_no_previous_blog(self):
        prompt = gen.build_prompt("logs", "", date(2026, 3, 10), "en")
        assert "Previous blog post" not in prompt

    def test_required_sections_present(self):
        prompt = gen.build_prompt("logs", "prev", date(2026, 3, 10), "en")
        for section in ["Highlights", "What I Worked On", "Decisions", "Progress Since Last Time", "What's Next"]:
            assert section in prompt

    def test_japanese_prompt_requests_japanese_output(self):
        prompt = gen.build_prompt("logs", "", date(2026, 3, 10), "ja")
        assert "Write in first person, in Japanese." in prompt


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

class TestStateHelpers:
    def test_load_missing_returns_empty(self, tmp_path):
        with mock.patch.object(gen, "STATE_FILE", tmp_path / ".blog_state.json"):
            assert gen._load_state() == {}

    def test_save_and_load(self, tmp_path):
        state_file = tmp_path / ".blog_state.json"
        with (
            mock.patch.object(gen, "STATE_FILE", state_file),
            mock.patch.object(gen, "REPO_ROOT", tmp_path),
            mock.patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = mock.Mock(stdout="abc123\n", returncode=0)
            gen._save_state(date(2026, 3, 10))
            state = gen._load_state()

        assert state["last_blog_date"] == "2026-03-10"
        assert state["last_commit_sha"] == "abc123"

    def test_load_corrupt_json_returns_empty(self, tmp_path):
        state_file = tmp_path / ".blog_state.json"
        state_file.write_text("{ not valid json }")
        with mock.patch.object(gen, "STATE_FILE", state_file):
            assert gen._load_state() == {}

# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

class TestExtractPdfText:
    def test_returns_empty_string_when_pypdf_missing(self, tmp_path):
        """extract_pdf_text returns "" gracefully if pypdf is not available."""
        dummy_pdf = tmp_path / "dummy.pdf"
        dummy_pdf.write_bytes(b"%PDF-1.4")  # minimal stub – no real pages

        with mock.patch.dict("sys.modules", {"pypdf": None}):
            result = gen.extract_pdf_text(dummy_pdf)
        assert result == ""

    def test_returns_empty_string_for_corrupt_pdf(self, tmp_path):
        """extract_pdf_text returns "" when the file cannot be parsed."""
        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_bytes(b"this is not a pdf")
        result = gen.extract_pdf_text(bad_pdf)
        assert result == ""

    def test_pdf_included_in_read_log_files(self, tmp_path):
        """read_log_files calls extract_pdf_text for .pdf files."""
        pdf_path = tmp_path / "20260310-doc.pdf"
        pdf_path.write_bytes(b"stub")

        with (
            mock.patch.object(gen, "REPO_ROOT", tmp_path),
            mock.patch.object(gen, "extract_pdf_text", return_value="extracted pdf text") as mock_extract,
        ):
            result = gen.read_log_files([pdf_path])

        mock_extract.assert_called_once_with(pdf_path)
        assert any("extracted pdf text" in v for v in result.values())

    def test_pdf_collected_in_window(self, tmp_path):
        """collect_log_files picks up .pdf files whose path contains a date in window."""
        logs_dir = tmp_path / "logs"
        pdf_path = logs_dir / "20260310-doc" / "report.pdf"
        pdf_path.parent.mkdir(parents=True)
        pdf_path.write_bytes(b"stub")

        with (
            mock.patch.object(gen, "LOGS_DIR", logs_dir),
            mock.patch.object(gen, "REPO_ROOT", tmp_path),
        ):
            files = gen.collect_log_files(date(2026, 3, 7), date(2026, 3, 10))

        assert len(files) == 1
        assert files[0].suffix == ".pdf"


# ---------------------------------------------------------------------------
# read_log_files
# ---------------------------------------------------------------------------

class TestReadLogFiles:
    def test_returns_dict_keyed_by_relative_path(self, tmp_path):
        f = tmp_path / "logs" / "20260310-project" / "note.md"
        f.parent.mkdir(parents=True)
        f.write_text("hello")
        with mock.patch.object(gen, "REPO_ROOT", tmp_path):
            result = gen.read_log_files([f])
        assert isinstance(result, dict)
        assert len(result) == 1
        key = list(result.keys())[0]
        assert "20260310" in key
        assert result[key] == "hello"

    def test_oserror_stores_empty_string(self, tmp_path):
        missing = tmp_path / "logs" / "20260310-x" / "ghost.md"
        with mock.patch.object(gen, "REPO_ROOT", tmp_path):
            result = gen.read_log_files([missing])
        assert isinstance(result, dict)
        assert len(result) == 1
        assert list(result.values())[0] == ""

    def test_multiple_files_all_included(self, tmp_path):
        logs_dir = tmp_path / "logs"
        for name in ["20260310-a/note.md", "20260311-b/note.md"]:
            p = logs_dir / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"content of {name}")
        files = list((tmp_path / "logs").rglob("*.md"))
        with mock.patch.object(gen, "REPO_ROOT", tmp_path):
            result = gen.read_log_files(files)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# summarize_content
# ---------------------------------------------------------------------------

class TestSummarizeContent:
    def test_calls_generate_blog_content(self):
        with mock.patch.object(gen, "generate_blog_content", return_value="summary") as mock_gen:
            result = gen.summarize_content("raw text", "source.md")
        mock_gen.assert_called_once()
        assert result == "summary"

    def test_prompt_contains_source_name_and_content(self):
        with mock.patch.object(gen, "generate_blog_content", return_value="ok") as mock_gen:
            gen.summarize_content("my content", "logs/20260310-project/note.md")
        prompt_sent = mock_gen.call_args[0][0]
        assert "logs/20260310-project/note.md" in prompt_sent
        assert "my content" in prompt_sent

    def test_falls_back_to_original_on_failure(self):
        with mock.patch.object(gen, "generate_blog_content", side_effect=RuntimeError("API down")):
            result = gen.summarize_content("raw text", "source.md")
        assert result == "raw text"


# ---------------------------------------------------------------------------
# summarize_log_files
# ---------------------------------------------------------------------------

class TestSummarizeLogFiles:
    def test_calls_summarize_per_file(self):
        files = {"logs/a.md": "content a", "logs/b.md": "content b"}
        with mock.patch.object(gen, "summarize_content", return_value="summary") as mock_sum:
            result = gen.summarize_log_files(files)
        assert mock_sum.call_count == 2
        assert "logs/a.md" in result
        assert "logs/b.md" in result

    def test_skips_empty_files(self):
        files = {"logs/a.md": "content", "logs/empty.md": "   "}
        with mock.patch.object(gen, "summarize_content", return_value="s") as mock_sum:
            gen.summarize_log_files(files)
        assert mock_sum.call_count == 1

    def test_empty_dict_returns_empty_string(self):
        result = gen.summarize_log_files({})
        assert result == ""

    def test_aggregated_output_contains_all_summaries(self):
        files = {"logs/x.md": "aaa", "logs/y.md": "bbb"}
        with mock.patch.object(gen, "summarize_content", side_effect=["sum-x", "sum-y"]):
            result = gen.summarize_log_files(files)
        assert "sum-x" in result
        assert "sum-y" in result


# ---------------------------------------------------------------------------
# summarize_previous_blog
# ---------------------------------------------------------------------------

class TestSummarizePreviousBlog:
    def test_returns_empty_string_when_no_previous_blog(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        with mock.patch.object(gen, "BLOG_DIR", blog_dir):
            result = gen.summarize_previous_blog("ja")
        assert result == ""

    def test_summarizes_previous_blog_content(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        (blog_dir / "20260301-weekly.md").write_text("# Old Post\nSome content")
        with (
            mock.patch.object(gen, "BLOG_DIR", blog_dir),
            mock.patch.object(gen, "summarize_content", return_value="condensed") as mock_sum,
        ):
            result = gen.summarize_previous_blog("ja")
        mock_sum.assert_called_once()
        assert result == "condensed"

    def test_source_name_is_filename(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        (blog_dir / "20260301-weekly-en.md").write_text("# Old EN Post")
        with (
            mock.patch.object(gen, "BLOG_DIR", blog_dir),
            mock.patch.object(gen, "summarize_content", return_value="ok") as mock_sum,
        ):
            gen.summarize_previous_blog("en")
        source_name_used = mock_sum.call_args[0][1]
        assert source_name_used == "20260301-weekly-en.md"
