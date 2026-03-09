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
    def test_returns_most_recent(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        (blog_dir / "2026-02-01.md").write_text("old")
        (blog_dir / "2026-03-01.md").write_text("newer")
        (blog_dir / "2026-01-15.md").write_text("oldest")

        with mock.patch.object(gen, "BLOG_DIR", blog_dir):
            result = gen.find_previous_blog()
        assert result is not None
        assert result.name == "2026-03-01.md"

    def test_returns_none_when_empty(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        with mock.patch.object(gen, "BLOG_DIR", blog_dir):
            assert gen.find_previous_blog() is None

    def test_read_previous_blog_content(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        (blog_dir / "2026-03-01.md").write_text("# Post\nHello world")
        with mock.patch.object(gen, "BLOG_DIR", blog_dir):
            content = gen.read_previous_blog()
        assert "Hello world" in content


# ---------------------------------------------------------------------------
# build_prompt
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_contains_date(self):
        prompt = gen.build_prompt("some logs", "", date(2026, 3, 10))
        assert "2026-03-10" in prompt

    def test_contains_logs(self):
        prompt = gen.build_prompt("MY_SPECIAL_LOG_CONTENT", "", date(2026, 3, 10))
        assert "MY_SPECIAL_LOG_CONTENT" in prompt

    def test_includes_previous_blog(self):
        prompt = gen.build_prompt("logs", "PREV_BLOG_CONTENT", date(2026, 3, 10))
        assert "PREV_BLOG_CONTENT" in prompt

    def test_no_previous_blog(self):
        prompt = gen.build_prompt("logs", "", date(2026, 3, 10))
        assert "Previous blog post" not in prompt

    def test_required_sections_present(self):
        prompt = gen.build_prompt("logs", "prev", date(2026, 3, 10))
        for section in ["Highlights", "What I Worked On", "Decisions", "Progress Since Last Time", "What's Next"]:
            assert section in prompt


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
