#!/usr/bin/env bash
# Weekly blog generation on the gx10 box using local Ollama models.
# Summarize phase -> gpt-oss:20b, article phase -> gpt-oss:120b, reasoning on.
# Intended to run from cron early Saturday so it finishes before 08:00 JST.
#
# By default this runs in REVIEW mode: it generates the post and delivers the
# text to Telegram for reading, but does NOT publish to the public repo. Set
# PUBLISH=1 to actually commit & push. This prevents unreviewed content from
# going public (a manual/test run never publishes by accident).
#
# Cron (Saturday 05:00 JST, ~3h margin) — review mode (no publish):
#   0 5 * * 6 /home/masa/dev/logs-with-llm/scripts/run_weekly_blog_gx10.sh >> /tmp/weekly-blog-gx10.log 2>&1
# To auto-publish, add PUBLISH=1 in front of the command.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

PUBLISH="${PUBLISH:-0}"

export LLM_PROVIDER=ollama
export OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
export OLLAMA_SUMMARIZE_MODEL="${OLLAMA_SUMMARIZE_MODEL:-gpt-oss:20b}"
export OLLAMA_COMPOSE_MODEL="${OLLAMA_COMPOSE_MODEL:-gpt-oss:120b}"
export OLLAMA_THINK="${OLLAMA_THINK:-true}"
export OLLAMA_TIMEOUT="${OLLAMA_TIMEOUT:-1800}"

# Deliver generated post text to Telegram as message body (NOT a .md file, which
# renders as mojibake on some clients). Chunked for the 4096-char limit. Token is
# auto-resolved from any working channel bot; destination overridable.
deliver_telegram() {
  local chat="${BLOG_NOTIFY_CHAT:-8903310093}"
  [ -n "$chat" ] || return 0
  local files=("$@")
  [ "${#files[@]}" -gt 0 ] || return 0
  local token_envs=() tokens=()
  [ -n "${BLOG_NOTIFY_TOKEN_ENV:-}" ] && [ -f "${BLOG_NOTIFY_TOKEN_ENV}" ] && token_envs+=("$BLOG_NOTIFY_TOKEN_ENV")
  for f in "$HOME"/.claude/channels/*/.env; do [ -f "$f" ] && token_envs+=("$f"); done
  local tenv t
  for tenv in "${token_envs[@]:-}"; do
    [ -f "$tenv" ] || continue
    t=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' "$tenv" 2>/dev/null | cut -d= -f2- || true)
    [ -n "$t" ] && tokens+=("$t")
  done
  [ "${#tokens[@]}" -gt 0 ] || { echo "[run_weekly_blog_gx10] no telegram token found"; return 0; }
  CHAT="$chat" PUB="$PUBLISH" python3 - "${tokens[@]}" -- "${files[@]}" <<'PY'
import os, sys, json, urllib.request, urllib.parse
chat = os.environ["CHAT"]; published = os.environ.get("PUB") == "1"
sep = sys.argv.index("--")
tokens = sys.argv[1:sep]; files = sys.argv[sep+1:]

def send(token, text):
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    try:
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=20
        ) as r:
            return b'"ok":true' in r.read()
    except Exception:
        return False

# Pick the bot that can actually reach this chat (probe with the header line).
banner = ("📝 今週のブログ（公開済み）" if published
          else "📝 今週のブログ案（レビュー用・未公開）")
good = None
for tk in tokens:
    if send(tk, banner):
        good = tk
        break
if not good:
    sys.exit(0)

for path in files:
    try:
        text = open(path, encoding="utf-8").read()
    except Exception:
        continue
    for i in range(0, len(text), 3500):
        send(good, text[i:i+3500])
PY
}

echo "[run_weekly_blog_gx10] $(date '+%Y-%m-%d %H:%M:%S') start (PUBLISH=$PUBLISH)"

git pull -q --ff-only origin main || true

# Capture output so we can detect an empty-week placeholder and avoid an empty post.
RUN_OUT=$(python3 scripts/generate_weekly_blog.py 2>&1)
echo "$RUN_OUT"

mapfile -t POSTS < <(git status --porcelain blog/ | awk '{print $2}' | grep -E 'weekly.*\.md$' || true)

if printf '%s' "$RUN_OUT" | grep -q "No log files found for this period"; then
    echo "[run_weekly_blog_gx10] no source logs this week — nothing to do"
    git checkout -- blog/ .blog_state.json 2>/dev/null || true
elif [ "${#POSTS[@]}" -gt 0 ]; then
    deliver_telegram "${POSTS[@]}" || true
    if [ "$PUBLISH" = "1" ]; then
        git add blog/ .blog_state.json
        git commit -m "📝 Weekly blog post (gx10 local LLM)"
        git push origin HEAD:main
        echo "[run_weekly_blog_gx10] published and delivered"
    else
        git checkout -- blog/ .blog_state.json 2>/dev/null || true
        echo "[run_weekly_blog_gx10] review mode — delivered to Telegram, NOT published (set PUBLISH=1 to publish)"
    fi
else
    echo "[run_weekly_blog_gx10] no changes to deliver"
fi

echo "[run_weekly_blog_gx10] $(date '+%Y-%m-%d %H:%M:%S') done"
