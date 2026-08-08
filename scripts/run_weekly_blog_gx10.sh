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
  CHAT="$chat" PUB="$PUBLISH" PROVENANCE="${PROVENANCE:-}" python3 - "${tokens[@]}" -- "${files[@]}" <<'PY'
import os, sys, json, urllib.request, urllib.parse
chat = os.environ["CHAT"]; published = os.environ.get("PUB") == "1"
provenance = os.environ.get("PROVENANCE", "").strip()
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
if provenance:
    banner += "\n\n数値の出所チェック:\n" + provenance
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

# Send a banner image (note/Medium concept banner) to Telegram. Best-effort.
send_banner_telegram() {
  local img="$1" chat="${BLOG_NOTIFY_CHAT:-8903310093}"
  [ -f "$img" ] && [ -n "$chat" ] || return 0
  local tenv tok
  for tenv in "$HOME"/.claude/channels/*/.env; do
    [ -f "$tenv" ] || continue
    tok=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' "$tenv" 2>/dev/null | cut -d= -f2- || true)
    [ -n "$tok" ] || continue
    if curl -sS --max-time 60 -F "chat_id=${chat}" -F "photo=@${img}" \
         -F "caption=🖼️ 今週のバナー（note/Medium用・記事から自動生成）" \
         "https://api.telegram.org/bot${tok}/sendPhoto" 2>/dev/null | grep -q '"ok":true'; then
      break
    fi
  done
}

# 記事本文から note/Medium 用の概念バナーを生成（ローカル・無料）。失敗しても本処理は止めない。
CONCEPT_GEN="${CONCEPT_GEN:-/home/masa/dev/Agent-Lab/Agent-team/tools/local-image-gen/concept_image.py}"
gen_banner() {  # $1=JA記事(相対パス) -> echo バナー相対パス（失敗時は空）
  local post="$1" banner
  [ -n "$post" ] && [ -f "$post" ] && [ -f "$CONCEPT_GEN" ] || return 0
  banner="${post%.md}-banner.png"
  if python3 "$CONCEPT_GEN" --file "$post" --out "$banner" >/dev/null 2>&1; then
    [ -f "$banner" ] && echo "$banner"
  fi
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
    # JA 記事（-en でない方）からバナーを自動生成
    JA_POST=$(printf '%s\n' "${POSTS[@]}" | grep -vE '\-en\.md$' | head -1)
    # 本文の数値が元ログにあるか照合する（2026-08-08: 元ログに無い実測値が公開された）。
    # 公開は止めない——判定材料として通知に載せる。
    PROVENANCE=""
    for p in "${POSTS[@]}"; do
        line=$(python3 scripts/check_number_provenance.py "$p" 2>/dev/null || true)
        [ -n "$line" ] && PROVENANCE="${PROVENANCE}$(basename "$p"): ${line#provenance: }"$'\n'
    done
    export PROVENANCE
    printf '%s' "$PROVENANCE"
    BANNER=$(gen_banner "$JA_POST" || true)
    deliver_telegram "${POSTS[@]}" || true
    [ -n "$BANNER" ] && send_banner_telegram "$BANNER" || true
    if [ "$PUBLISH" = "1" ]; then
        git add blog/ .blog_state.json
        [ -n "$BANNER" ] && git add "$BANNER" 2>/dev/null || true
        git commit -m "📝 Weekly blog post + banner (gx10 local LLM)"
        git push origin HEAD:main
        echo "[run_weekly_blog_gx10] published and delivered (banner: ${BANNER:-none})"
    else
        git checkout -- blog/ .blog_state.json 2>/dev/null || true
        echo "[run_weekly_blog_gx10] review mode — delivered to Telegram, NOT published (banner: ${BANNER:-none})"
    fi
else
    echo "[run_weekly_blog_gx10] no changes to deliver"
fi

echo "[run_weekly_blog_gx10] $(date '+%Y-%m-%d %H:%M:%S') done"
