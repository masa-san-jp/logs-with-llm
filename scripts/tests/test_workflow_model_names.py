"""Workflow regression tests for GitHub Models model IDs."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


class TestWorkflowModelNames:
    def test_weekly_blog_uses_supported_github_models_default(self):
        content = (WORKFLOWS_DIR / "weekly-blog.yml").read_text(encoding="utf-8")

        assert "GITHUB_MODELS_MODEL: claude-sonnet-4" in content
        assert "claude-sonnet-4-5" not in content

    def test_meta_analysis_normalizes_legacy_invalid_model_name(self):
        content = (WORKFLOWS_DIR / "meta-analysis.yml").read_text(encoding="utf-8")

        assert "github_models→claude-sonnet-4" in content
        assert "MODEL=\"${{ inputs.model || 'claude-sonnet-4' }}\"" in content
        assert 'if [[ "$MODEL" == "claude-sonnet-4-5" ]]; then' in content
        assert 'MODEL="claude-sonnet-4"' in content

    def test_weekly_goal_issue_normalizes_legacy_invalid_model_name(self):
        content = (WORKFLOWS_DIR / "weekly-doc-goal-issue.yml").read_text(encoding="utf-8")

        assert "MODEL=\"${{ inputs.model || 'claude-sonnet-4' }}\"" in content
        assert 'if [[ "$MODEL" == "claude-sonnet-4-5" ]]; then' in content
        assert 'MODEL="claude-sonnet-4"' in content
