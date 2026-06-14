"""Unit tests for generate_weekly_blog.py – date parsing and log selection."""

import json
import os
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
        prompt = gen.build_prompt("some logs", "", "", date(2026, 3, 10), "en")
        assert "2026-03-10" in prompt

    def test_contains_logs(self):
        prompt = gen.build_prompt("MY_SPECIAL_LOG_CONTENT", "", "", date(2026, 3, 10), "en")
        assert "MY_SPECIAL_LOG_CONTENT" in prompt

    def test_includes_source_cards(self):
        prompt = gen.build_prompt("logs", "## Source Card\n\n- source: logs/a.md", "", date(2026, 3, 10), "en")
        assert "logs/a.md" in prompt

    def test_includes_prev_style_capsule(self):
        prompt = gen.build_prompt("logs", "", "## Previous Style Capsule\n\nOld title", date(2026, 3, 10), "en")
        assert "Previous Style Capsule" in prompt
        assert "Old title" in prompt

    def test_no_source_cards_section_when_empty(self):
        prompt = gen.build_prompt("logs", "", "", date(2026, 3, 10), "en")
        assert "Source cards with raw excerpts" not in prompt

    def test_no_prev_style_section_when_empty(self):
        prompt = gen.build_prompt("logs", "", "", date(2026, 3, 10), "en")
        assert "Previous style reference" not in prompt
        assert "Previous blog post" not in prompt

    def test_includes_prompt_guidance_strings(self):
        # JA: narrative accumulation — short prose preface + narrative next-step ending (2026-06-14)
        prompt_ja = gen.build_prompt("logs", "cards", "capsule", date(2026, 3, 10), "ja")
        assert "前書き" in prompt_ja
        assert "ナラティブ" in prompt_ja
        assert "ネクストアクション" in prompt_ja
        # EN leans business-philosophical / thought-leadership
        prompt_en = gen.build_prompt("logs", "cards", "capsule", date(2026, 3, 10), "en")
        assert "Before writing your output, confirm each of the following" in prompt_en
        assert "business-philosophical" in prompt_en

    def test_japanese_prompt_requests_japanese_output(self):
        prompt = gen.build_prompt("logs", "", "", date(2026, 3, 10), "ja")
        assert "「私」に統一" in prompt

    def test_includes_source_cards_section_header(self):
        prompt = gen.build_prompt(
            logs_text="summary text",
            source_cards="## Source Card\n\n- source: logs/a.md",
            prev_style_capsule="",
            post_date=date(2026, 5, 30),
            language="ja",
        )
        assert "Source cards with raw excerpts" in prompt or "Source Card" in prompt
        assert "logs/a.md" in prompt

    def test_includes_coverage_requirements_en(self):
        prompt = gen.build_prompt(
            logs_text="summary text",
            source_cards="## Source Card\n\n- source: logs/a.md",
            prev_style_capsule="",
            post_date=date(2026, 5, 30),
            language="en",
        )
        assert "Coverage requirements" in prompt
        assert "Do not let one source dominate" in prompt

    def test_includes_coverage_requirements_ja(self):
        prompt = gen.build_prompt(
            logs_text="summary text",
            source_cards="",
            prev_style_capsule="",
            post_date=date(2026, 5, 30),
            language="ja",
        )
        assert "カバレッジ要件" in prompt

    def test_includes_previous_style_capsule_content(self):
        prompt = gen.build_prompt(
            logs_text="summary text",
            source_cards="## Source Card\n\n- source: logs/a.md",
            prev_style_capsule="## Previous Style Capsule\n\n### Previous title\nOld",
            post_date=date(2026, 5, 30),
            language="en",
        )
        assert "Previous Style Capsule" in prompt
        assert "Old" in prompt

    def test_final_gate_includes_source_coverage_checks_en(self):
        prompt = gen.build_prompt("logs", "", "", date(2026, 3, 10), "en")
        assert "Multiple Source Cards are concretely reflected" in prompt
        assert "not dominated by a single source" in prompt

    def test_final_gate_includes_source_coverage_checks_ja(self):
        prompt = gen.build_prompt("logs", "", "", date(2026, 3, 10), "ja")
        assert "複数の Source Card が本文に具体的に反映されている" in prompt
        assert "1つの Source だけに記事が偏っていない" in prompt

    def test_vocabulary_injection_removed_en(self):
        prompt = gen.build_prompt("logs", "", "", date(2026, 3, 10), "en")
        # Old forced/optional injection guidance gone
        assert "Vocabulary injection is optional" not in prompt
        assert "5–15" not in prompt
        assert "3–6 instances" not in prompt

    def test_en_prompt_analytical_style(self):
        prompt = gen.build_prompt("logs", "", "", date(2026, 3, 10), "en")
        assert "analytical" in prompt

    def test_en_prompt_no_emotional_persona(self):
        prompt = gen.build_prompt("logs", "", "", date(2026, 3, 10), "en")
        assert "quiet but sustained passion" not in prompt
        assert "humble inquirer" not in prompt

    def test_en_prompt_research_note_task(self):
        prompt = gen.build_prompt("logs", "", "", date(2026, 3, 10), "en")
        assert "research note" in prompt

    def test_en_prompt_final_gate_checks_tone(self):
        prompt = gen.build_prompt("logs", "", "", date(2026, 3, 10), "en")
        assert "analytical and informative" in prompt
        assert "Personal feelings and reactions are absent" in prompt

    def test_prompt_vocab_not_carried_ja(self):
        # 2026-06-14 rework: no vocabulary injection; the prompt must instead tell the
        # model NOT to carry the prompt's own abstract vocabulary into the output.
        prompt = gen.build_prompt("logs", "", "", date(2026, 3, 10), "ja")
        assert "3〜6箇所" not in prompt
        assert "5〜15 箇所を文脈に合わせて使用する" not in prompt
        assert "そのまま持ち込まない" in prompt


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


# ---------------------------------------------------------------------------
# extract_raw_excerpts
# ---------------------------------------------------------------------------

class TestExtractRawExcerpts:
    def test_returns_important_paragraphs(self):
        content = """
# Test

短い説明。

## 目的

この設計の目的は、個人技ではなく組織運用としてAI活用を定着させることです。

## その他

普通の説明文です。
"""
        excerpts = gen.extract_raw_excerpts(content)
        assert excerpts
        assert any("目的" in e or "組織運用" in e for e in excerpts)

    def test_empty_content_returns_empty_list(self):
        assert gen.extract_raw_excerpts("   ") == []

    def test_skips_code_fences(self):
        content = """
```python
print("important but code")
```

結論として、この運用は安全性を優先する。
"""
        excerpts = gen.extract_raw_excerpts(content)
        assert all("print(" not in e for e in excerpts)
        assert any("結論" in e for e in excerpts)

    def test_respects_max_excerpts(self):
        content = "\n\n".join(
            f"## 目的{i}\n\nこの設計の目的は重要な判断を含む段落{i}です。組織運用として評価します。" for i in range(10)
        )
        excerpts = gen.extract_raw_excerpts(content, max_excerpts=3)
        assert len(excerpts) <= 3

    def test_truncates_long_blocks(self):
        long_text = "目的として、" + "あ" * 400
        content = f"## 目的\n\n{long_text}"
        excerpts = gen.extract_raw_excerpts(content, max_chars=350)
        assert excerpts
        assert all(len(e) <= 360 for e in excerpts)  # allow slight overage for punctuation

    def test_skips_large_tables(self):
        table = "\n".join(f"| col{i} | val{i} |" for i in range(10))
        content = f"## データ\n\n{table}\n\n結論として、この比較は重要な判断材料です。"
        excerpts = gen.extract_raw_excerpts(content)
        # Table rows should not appear as excerpts
        assert not any("|" in e and e.count("|") > 3 for e in excerpts)
        assert any("結論" in e for e in excerpts)

    def test_no_duplicates(self):
        content = "## 目的\n\n同じ段落が複数回あっても、重複排除されるべきです。\n\n同じ段落が複数回あっても、重複排除されるべきです。"
        excerpts = gen.extract_raw_excerpts(content)
        keys = [e[:80] for e in excerpts]
        assert len(keys) == len(set(keys))


# ---------------------------------------------------------------------------
# build_source_cards
# ---------------------------------------------------------------------------

class TestBuildSourceCards:
    def test_includes_all_source_paths(self):
        files = {
            "logs/20260524-a.md": "## 目的\n\n重要な本文です。",
            "logs/20260525-b.md": "## 結論\n\n別の重要な本文です。",
        }
        cards = gen.build_source_cards(files)
        assert "logs/20260524-a.md" in cards
        assert "logs/20260525-b.md" in cards

    def test_includes_raw_excerpts(self):
        files = {
            "logs/20260524-a.md": "## 目的\n\nこの設計の目的は、運用改善です。",
        }
        cards = gen.build_source_cards(files)
        assert "raw_excerpts" in cards
        assert "運用改善" in cards

    def test_skips_empty_files(self):
        files = {
            "logs/20260524-a.md": "   ",
            "logs/20260525-b.md": "## 結論\n\n重要な本文です。",
        }
        cards = gen.build_source_cards(files)
        assert "logs/20260524-a.md" not in cards
        assert "logs/20260525-b.md" in cards

    def test_includes_date(self):
        files = {"logs/20260524-project.md": "## 目的\n\n重要な内容です。"}
        cards = gen.build_source_cards(files)
        assert "2026-05-24" in cards

    def test_unknown_date_when_no_date_in_path(self):
        files = {"logs/no-date-project.md": "## 目的\n\n重要な内容です。"}
        cards = gen.build_source_cards(files)
        assert "unknown" in cards

    def test_empty_excerpts_placeholder(self):
        files = {"logs/20260524-a.md": "x" * 5}  # too short to extract
        cards = gen.build_source_cards(files)
        assert "No suitable raw excerpt found" in cards

    def test_empty_dict_returns_empty_string(self):
        assert gen.build_source_cards({}) == ""

    def test_multiple_cards_separated(self):
        files = {
            "logs/20260524-a.md": "## 目的\n\n重要な本文です。",
            "logs/20260525-b.md": "## 結論\n\n別の重要な本文です。",
        }
        cards = gen.build_source_cards(files)
        assert "---" in cards


# ---------------------------------------------------------------------------
# build_previous_style_capsule
# ---------------------------------------------------------------------------

class TestBuildPreviousStyleCapsule:
    def test_extracts_style_elements(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        (blog_dir / "20260522-weekly.md").write_text(
            "# 前回タイトル\n\n"
            "冒頭段落1です。\n\n"
            "冒頭段落2です。\n\n"
            "## 見出しA\n\n"
            "本文A。\n\n"
            "## 見出しB\n\n"
            "本文B。\n\n"
            "締め段落です。\n",
            encoding="utf-8",
        )
        with mock.patch.object(gen, "BLOG_DIR", blog_dir):
            capsule = gen.build_previous_style_capsule("ja")

        assert "Previous Style Capsule" in capsule
        assert "前回タイトル" in capsule
        assert "冒頭段落1" in capsule
        assert "見出しA" in capsule
        assert "締め段落" in capsule

    def test_empty_when_no_previous_blog(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        with mock.patch.object(gen, "BLOG_DIR", blog_dir):
            assert gen.build_previous_style_capsule("ja") == ""

    def test_includes_h2_headings(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        (blog_dir / "20260522-weekly-en.md").write_text(
            "# Title\n\nOpening.\n\n## Section One\n\nBody.\n\n## Section Two\n\nBody.\n\nClosing.\n",
            encoding="utf-8",
        )
        with mock.patch.object(gen, "BLOG_DIR", blog_dir):
            capsule = gen.build_previous_style_capsule("en")

        assert "Section One" in capsule
        assert "Section Two" in capsule

    def test_does_not_include_full_body(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        body_text = "中間の本文ブロックです。この部分は含まれるべきではありません。"
        (blog_dir / "20260522-weekly.md").write_text(
            "# タイトル\n\n冒頭段落。\n\n## 見出し\n\n"
            + body_text
            + "\n\n## 見出し2\n\n別の本文。\n\n締め段落。\n",
            encoding="utf-8",
        )
        with mock.patch.object(gen, "BLOG_DIR", blog_dir):
            capsule = gen.build_previous_style_capsule("ja")

        # Opening (冒頭段落) and closing (締め段落) should be present
        assert "冒頭段落" in capsule
        assert "締め段落" in capsule


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------

class TestMain:
    def _make_setup(self, tmp_path):
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        log_file = logs_dir / "20260524-test.md"
        log_file.write_text("## 目的\n\nテストログです。")
        return logs_dir, blog_dir, log_file

    def test_build_source_cards_called(self, tmp_path):
        logs_dir, blog_dir, log_file = self._make_setup(tmp_path)
        with (
            mock.patch.object(gen, "LOGS_DIR", logs_dir),
            mock.patch.object(gen, "BLOG_DIR", blog_dir),
            mock.patch.object(gen, "REPO_ROOT", tmp_path),
            mock.patch.object(gen, "STATE_FILE", tmp_path / ".blog_state.json"),
            mock.patch.object(gen, "build_source_cards", return_value="cards") as mock_cards,
            mock.patch.object(gen, "build_previous_style_capsule", return_value=""),
            mock.patch.object(gen, "summarize_log_files", return_value="summary"),
            mock.patch.object(gen, "generate_blog_content", return_value="blog content"),
            mock.patch.object(gen, "_save_state"),
            mock.patch.dict(os.environ, {"BLOG_DATE": "2026-05-24"}),
        ):
            gen.main()
        mock_cards.assert_called_once()

    def test_build_previous_style_capsule_called_per_language(self, tmp_path):
        logs_dir, blog_dir, log_file = self._make_setup(tmp_path)
        with (
            mock.patch.object(gen, "LOGS_DIR", logs_dir),
            mock.patch.object(gen, "BLOG_DIR", blog_dir),
            mock.patch.object(gen, "REPO_ROOT", tmp_path),
            mock.patch.object(gen, "STATE_FILE", tmp_path / ".blog_state.json"),
            mock.patch.object(gen, "build_source_cards", return_value=""),
            mock.patch.object(gen, "build_previous_style_capsule", return_value="") as mock_capsule,
            mock.patch.object(gen, "summarize_log_files", return_value="summary"),
            mock.patch.object(gen, "generate_blog_content", return_value="blog content"),
            mock.patch.object(gen, "_save_state"),
            mock.patch.dict(os.environ, {"BLOG_DATE": "2026-05-24"}),
        ):
            gen.main()
        assert mock_capsule.call_count == len(gen.SUPPORTED_LANGUAGES)

    def test_build_prompt_receives_source_cards(self, tmp_path):
        logs_dir, blog_dir, log_file = self._make_setup(tmp_path)
        captured_prompts: list[tuple] = []

        def fake_build_prompt(logs_text, source_cards, prev_style_capsule, post_date, language):
            captured_prompts.append((source_cards,))
            return "prompt"

        with (
            mock.patch.object(gen, "LOGS_DIR", logs_dir),
            mock.patch.object(gen, "BLOG_DIR", blog_dir),
            mock.patch.object(gen, "REPO_ROOT", tmp_path),
            mock.patch.object(gen, "STATE_FILE", tmp_path / ".blog_state.json"),
            mock.patch.object(gen, "build_source_cards", return_value="MY_SOURCE_CARDS"),
            mock.patch.object(gen, "build_previous_style_capsule", return_value=""),
            mock.patch.object(gen, "summarize_log_files", return_value="summary"),
            mock.patch.object(gen, "build_prompt", side_effect=fake_build_prompt),
            mock.patch.object(gen, "generate_blog_content", return_value="blog content"),
            mock.patch.object(gen, "_save_state"),
            mock.patch.dict(os.environ, {"BLOG_DATE": "2026-05-24"}),
        ):
            gen.main()

        assert all(sc == "MY_SOURCE_CARDS" for sc, in captured_prompts)

    def test_summarize_previous_blog_not_called_from_main(self, tmp_path):
        logs_dir, blog_dir, log_file = self._make_setup(tmp_path)
        with (
            mock.patch.object(gen, "LOGS_DIR", logs_dir),
            mock.patch.object(gen, "BLOG_DIR", blog_dir),
            mock.patch.object(gen, "REPO_ROOT", tmp_path),
            mock.patch.object(gen, "STATE_FILE", tmp_path / ".blog_state.json"),
            mock.patch.object(gen, "build_source_cards", return_value=""),
            mock.patch.object(gen, "build_previous_style_capsule", return_value=""),
            mock.patch.object(gen, "summarize_log_files", return_value="summary"),
            mock.patch.object(gen, "generate_blog_content", return_value="blog content"),
            mock.patch.object(gen, "summarize_previous_blog") as mock_prev_summary,
            mock.patch.object(gen, "_save_state"),
            mock.patch.dict(os.environ, {"BLOG_DATE": "2026-05-24"}),
        ):
            gen.main()
        mock_prev_summary.assert_not_called()
