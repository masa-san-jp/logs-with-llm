#!/usr/bin/env bash
# Weekly "next research theme" proposal as a GitHub issue, generated on the gx10
# box with a local LLM (gpt-oss:120b, reasoning on). Replaces the cloud GitHub
# Action (OpenAI) — same idea, zero API cost.
#
# Flow: build prompt (generate_weekly_goal_issue.py) -> local LLM -> parse title
# /body -> create issue via gh (dedup by title) -> Telegram heads-up with link.
#
# Cron (Friday 18:00 JST):
#   0 18 * * 5 /home/masa/dev/logs-with-llm/scripts/run_weekly_goal_issue_gx10.sh >> /tmp/weekly-goal-issue-gx10.log 2>&1
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
MODEL="${OLLAMA_GOAL_MODEL:-gpt-oss:120b}"
THINK="${OLLAMA_THINK:-true}"
TIMEOUT="${OLLAMA_TIMEOUT:-1800}"

echo "[goal-issue-gx10] $(date '+%F %T') start (model=$MODEL)"

git pull -q --ff-only origin main || true

python3 scripts/generate_weekly_goal_issue.py > /tmp/goal_prompt.txt

OLLAMA_URL="$OLLAMA_URL" MODEL="$MODEL" THINK="$THINK" TIMEOUT="$TIMEOUT" \
python3 - /tmp/goal_prompt.txt /tmp/goal_issue.md <<'PY'
import os, sys, json, re, urllib.request
prompt = open(sys.argv[1], encoding="utf-8").read()
payload = json.dumps({
    "model": os.environ["MODEL"],
    "prompt": prompt,
    "stream": False,
    "think": os.environ.get("THINK", "true").lower() in ("1", "true", "yes", "on"),
}).encode()
req = urllib.request.Request(
    f'{os.environ["OLLAMA_URL"]}/api/generate',
    data=payload, headers={"Content-Type": "application/json"}, method="POST",
)
with urllib.request.urlopen(req, timeout=int(os.environ["TIMEOUT"])) as r:
    resp = json.loads(r.read())
text = re.sub(r"<think(?:ing)?>[\s\S]*?</think(?:ing)?>", "", resp.get("response", "")).strip()
open(sys.argv[2], "w", encoding="utf-8").write(text)
PY

TITLE=$(grep -m1 '^# ' /tmp/goal_issue.md | sed 's/^#\+ *//')
if [ -z "$TITLE" ]; then
    echo "[goal-issue-gx10] could not parse a title; aborting"; sed -n '1,20p' /tmp/goal_issue.md; exit 1
fi
tail -n +2 /tmp/goal_issue.md > /tmp/goal_issue_body.md

if gh issue list --state open --json title --jq '.[].title' | grep -qF "$TITLE"; then
    echo "[goal-issue-gx10] an open issue with this title already exists; skipping: $TITLE"
    exit 0
fi

URL=$(gh issue create --title "$TITLE" --body-file /tmp/goal_issue_body.md)
echo "[goal-issue-gx10] created: $URL"

# Telegram heads-up so the proposal is visible without opening GitHub. Best-effort.
chat="${BLOG_NOTIFY_CHAT:-8903310093}"
if [ -n "$chat" ]; then
    for tenv in "$HOME"/.claude/channels/*/.env; do
        [ -f "$tenv" ] || continue
        tok=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' "$tenv" 2>/dev/null | cut -d= -f2- || true)
        [ -n "$tok" ] || continue
        if curl -sS --max-time 10 -X POST "https://api.telegram.org/bot${tok}/sendMessage" \
             --data-urlencode "chat_id=${chat}" \
             --data-urlencode "text=💡 新しい研究テーマ提案のIssueを立てたよ。${TITLE} ${URL}" \
             2>/dev/null | grep -q '"ok":true'; then
            break
        fi
    done
fi

echo "[goal-issue-gx10] $(date '+%F %T') done"
