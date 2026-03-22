"""Unit tests for generate_weekly_goal_issue.py."""

import sys
from datetime import date
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_weekly_goal_issue as gen  # noqa: E402


class TestListDocumentFiles:
    def test_collects_supported_document_paths(self, tmp_path):
        (tmp_path / "README.md").write_text("# Readme")
        (tmp_path / "logs/20260321-topic/minutes.md").parent.mkdir(parents=True)
        (tmp_path / "logs/20260321-topic/minutes.md").write_text("# Minutes")
        (tmp_path / "blog/20260320-weekly.md").parent.mkdir(parents=True)
        (tmp_path / "blog/20260320-weekly.md").write_text("# Weekly")
        (tmp_path / "prompts/20260120-writer-voice.yml").parent.mkdir(parents=True)
        (tmp_path / "prompts/20260120-writer-voice.yml").write_text("style: reflective")
        (tmp_path / "notes/todo.txt").parent.mkdir(parents=True)
        (tmp_path / "notes/todo.txt").write_text("ignore me")

        with mock.patch.object(gen, "REPO_ROOT", tmp_path):
            files = [path.relative_to(tmp_path).as_posix() for path in gen.list_document_files()]

        assert files == [
            "README.md",
            "prompts/20260120-writer-voice.yml",
            "blog/20260320-weekly.md",
            "logs/20260321-topic/minutes.md",
        ]

    def test_respects_max_doc_files(self, tmp_path):
        for index in range(3):
            path = tmp_path / f"logs/2026032{index}-topic/minutes.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# Topic {index}")

        with (
            mock.patch.object(gen, "REPO_ROOT", tmp_path),
            mock.patch.object(gen, "MAX_DOC_FILES", 2),
        ):
            files = gen.list_document_files()

        assert len(files) == 2


class TestDocumentSummary:
    def test_extract_headings_and_snippet(self):
        content = """# Title

## Highlights

This is a long paragraph with useful details.
"""
        headings = gen.extract_headings(content)
        snippet = gen.extract_snippet(content)

        assert headings == ["Title", "Highlights"]
        assert "This is a long paragraph" in snippet

    def test_build_document_summary_contains_metadata(self, tmp_path):
        path = tmp_path / "logs/20260321-topic/minutes.md"
        path.parent.mkdir(parents=True)
        path.write_text("# Meeting\n\n## Decisions\n\nDetailed content")

        with mock.patch.object(gen, "REPO_ROOT", tmp_path):
            summary = gen.build_document_summary(path)

        assert "### logs/20260321-topic/minutes.md" in summary
        assert "- date: 2026-03-21" in summary
        assert "Meeting | Decisions" in summary


class TestBuildPrompt:
    def test_prompt_contains_required_sections(self, tmp_path):
        path = tmp_path / "README.md"
        path.write_text("# decision-logs-with-llm\n\nRepository overview")

        with mock.patch.object(gen, "REPO_ROOT", tmp_path):
            prompt = gen.build_prompt([path], date(2026, 3, 21))

        assert "[Weekly Docs Goal 2026-03-21]" in prompt
        assert "## Why this goal now" in prompt
        assert "## Source signals from the docs" in prompt
        assert "### README.md" in prompt


# ---------------------------------------------------------------------------
# PDF support
# ---------------------------------------------------------------------------

class TestPdfSupport:
    def test_pdf_pattern_in_doc_patterns(self):
        """logs/**/*.pdf must be in DOC_PATTERNS."""
        assert "logs/**/*.pdf" in gen.DOC_PATTERNS

    def test_extract_pdf_text_missing_pypdf(self, tmp_path):
        """extract_pdf_text returns '' when pypdf is not importable."""
        dummy = tmp_path / "dummy.pdf"
        dummy.write_bytes(b"%PDF-1.4")
        with mock.patch.dict("sys.modules", {"pypdf": None}):
            assert gen.extract_pdf_text(dummy) == ""

    def test_extract_pdf_text_corrupt_file(self, tmp_path):
        """extract_pdf_text returns '' for unreadable files."""
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf")
        assert gen.extract_pdf_text(bad) == ""

    def test_build_document_summary_uses_pdf_extractor(self, tmp_path):
        """build_document_summary delegates to extract_pdf_text for .pdf files."""
        pdf_path = tmp_path / "logs" / "20260310-topic" / "report.pdf"
        pdf_path.parent.mkdir(parents=True)
        pdf_path.write_bytes(b"stub")

        with (
            mock.patch.object(gen, "REPO_ROOT", tmp_path),
            mock.patch.object(gen, "extract_pdf_text", return_value="pdf content here") as mock_extract,
        ):
            summary = gen.build_document_summary(pdf_path)

        mock_extract.assert_called_once_with(pdf_path)
        assert "pdf content here" in summary

    def test_list_document_files_includes_pdf(self, tmp_path):
        """list_document_files collects PDF files from logs/."""
        pdf_path = tmp_path / "logs" / "20260310-topic" / "report.pdf"
        pdf_path.parent.mkdir(parents=True)
        pdf_path.write_bytes(b"stub")

        with mock.patch.object(gen, "REPO_ROOT", tmp_path):
            files = gen.list_document_files()

        assert any(f.suffix == ".pdf" for f in files)
