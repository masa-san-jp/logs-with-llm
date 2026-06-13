#!/usr/bin/env bash
# Weekly blog generation on the gx10 box using local Ollama models.
# Summarize phase -> gpt-oss:20b, article phase -> gpt-oss:120b, reasoning on.
# Intended to run from cron early Saturday so it finishes before 08:00 JST.
#
# Cron (Saturday 05:00 JST, ~3h margin):
#   0 5 * * 6 /home/masa/dev/logs-with-llm/scripts/run_weekly_blog_gx10.sh >> /tmp/weekly-blog-gx10.log 2>&1
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

export LLM_PROVIDER=ollama
export OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
export OLLAMA_SUMMARIZE_MODEL="${OLLAMA_SUMMARIZE_MODEL:-gpt-oss:20b}"
export OLLAMA_COMPOSE_MODEL="${OLLAMA_COMPOSE_MODEL:-gpt-oss:120b}"
export OLLAMA_THINK="${OLLAMA_THINK:-true}"
export OLLAMA_TIMEOUT="${OLLAMA_TIMEOUT:-1800}"

echo "[run_weekly_blog_gx10] $(date '+%Y-%m-%d %H:%M:%S') start"

git pull -q --ff-only origin main || true
python3 scripts/generate_weekly_blog.py

if git status --porcelain blog/ .blog_state.json | grep -q .; then
    git add blog/ .blog_state.json
    git commit -m "📝 Weekly blog post (gx10 local LLM)"
    git push origin HEAD:main
    echo "[run_weekly_blog_gx10] pushed new blog post"
else
    echo "[run_weekly_blog_gx10] no changes to commit"
fi

echo "[run_weekly_blog_gx10] $(date '+%Y-%m-%d %H:%M:%S') done"
