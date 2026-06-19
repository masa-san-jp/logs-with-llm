英語mdファイル名提案: 20260619-claude-code-remote-self-recovery-manual-recovery.md

結論

遠隔操作しているClaude Codeの復旧設計は、Claude Code内部に自己復旧を任せるのではなく、外側に監督レイヤーを置くべきです。

推奨構成は次です。

スマホ / ブラウザ / 別PC
        │
        ▼
Claude Code Remote Control
        │
        ▼
リモートマシン上の Claude Code
        │
        ├── tmux: 端末状態の保持
        ├── systemd user service: 起動・再起動
        ├── hooks: heartbeat / 通知 / 危険操作ブロック / 監査ログ
        ├── git: 作業差分の退避・復旧
        └── recovery scripts: status / attach / revive / safe-mode

Claude Code Remote Controlは、Webやモバイルからローカルマシン上のClaude Codeセッションを操作する機能です。処理はローカルマシン上で走り、Web/モバイル側はそのセッションへの窓として動きます。ただしRemote Controlはローカルプロセスが動き続ける必要があり、ターミナルを閉じたり claude プロセスが止まるとセッションは終了します。また、ネットワーク断が長引くとタイムアウトしてプロセスが終了する可能性があります。したがって、tmuxやsystemdなどの外部復旧機構が必要です。 

⸻

目標設計

復旧で守るべきもの

対象	守る理由
Claude Codeプロセス	Remote Controlの入口そのもの
tmux session	端末状態・ログ・手動介入経路
作業ディレクトリ	未コミット変更、生成物、調査結果
conversation/session ID	claude --resume で復帰するため
監査ログ	何が起きたかを人間が判断するため
kill switch	暴走・誤操作・危険操作を止めるため

やってはいけない設計

避けるべきです。

Claude Code が壊れたら Claude Code 自身に直させる

これは、監督対象と監督者が同一になるためです。認証エラー、設定ファイル破損、hook暴走、MCP不調、ネットワーク断、permission prompt停止などは、Claude Codeの外側から検知・復旧する必要があります。

⸻

推奨アーキテクチャ

レイヤー構成

L0: Git / filesystem safety
    - 作業ブランチ
    - 自動diff保存
    - stash / patch
    - protected path
L1: tmux persistence
    - Claude Codeをtmux内で起動
    - SSH切断後も手動復旧可能
L2: process supervisor
    - systemd user service
    - runner script
    - exit時の再起動
L3: Claude Code hooks
    - heartbeat
    - notification
    - audit log
    - dangerous command block
L4: manual recovery interface
    - cc-status
    - cc-attach
    - cc-revive
    - cc-safe
    - cc-kill
L5: remote interface
    - Claude Code Remote Control
    - SSH
    - optionally: channels / chat bridge

tmuxはdetach/attachできる端末セッションを維持でき、Claude CodeのRemote ControlはCLI上で claude remote-control または claude --remote-control として起動できます。Remote ControlのCLIモードでは、通常の対話セッションを維持しながらWebやモバイルからも操作できます。 

⸻

最小構成

まずはこの構成で十分です。

systemd user service
  └── cc-supervisor
        └── tmux session: cc-myproject
              └── cc-runner
                    └── claude --remote-control "myproject"

ディレクトリ

mkdir -p ~/.local/bin
mkdir -p ~/.config/systemd/user
mkdir -p ~/work/myproject/.claude/recovery

⸻

1. tmux内でClaude Codeを起動する

~/.local/bin/cc-runner

#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${1:?PROJECT_DIR required}"
SESSION_NAME="${2:?SESSION_NAME required}"
cd "$PROJECT_DIR"
mkdir -p .claude/recovery
while true; do
  date -Is > .claude/recovery/last-started-at
  echo "$SESSION_NAME" > .claude/recovery/session-name
  {
    echo "===== Claude Code started: $(date -Is) ====="
    claude --remote-control "$SESSION_NAME" --permission-mode plan
    rc=$?
    echo "===== Claude Code exited: rc=$rc at $(date -Is) ====="
    echo "$rc" > .claude/recovery/last-exit-code
  } 2>&1 | tee -a .claude/recovery/claude-runner.log
  date -Is > .claude/recovery/last-exited-at
  # crash loopを少し抑制
  sleep 10
done
chmod +x ~/.local/bin/cc-runner

ここでは初期permission modeを plan にしています。Remote Controlのローカルセッションでは、Ask permissions、Auto accept edits、Plan modeが利用でき、AutoとBypass permissionsは利用できません。最初から編集させるより、復旧後はまず計画モードに戻す方が安全です。 

⸻

2. tmux sessionを維持するsupervisor

~/.local/bin/cc-supervisor

#!/usr/bin/env bash
set -euo pipefail
PROJECT_NAME="${1:?project name required}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/work/$PROJECT_NAME}"
SESSION_NAME="${SESSION_NAME:-cc-$PROJECT_NAME}"
if [ ! -d "$PROJECT_DIR" ]; then
  echo "Project directory not found: $PROJECT_DIR" >&2
  exit 1
fi
mkdir -p "$PROJECT_DIR/.claude/recovery"
while true; do
  if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "[$(date -Is)] starting tmux session: $SESSION_NAME"
    tmux new-session -d \
      -s "$SESSION_NAME" \
      -n claude \
      -c "$PROJECT_DIR" \
      "$HOME/.local/bin/cc-runner '$PROJECT_DIR' '$SESSION_NAME'"
    echo "$SESSION_NAME" > "$PROJECT_DIR/.claude/recovery/tmux-session"
    date -Is > "$PROJECT_DIR/.claude/recovery/tmux-started-at"
  fi
  # tmuxが存在すること自体をheartbeatとして記録
  date -Is > "$PROJECT_DIR/.claude/recovery/supervisor-heartbeat"
  sleep 30
done
chmod +x ~/.local/bin/cc-supervisor

このsupervisorは「tmux sessionがなければ作る」だけに絞ります。Claude Code自体の再起動は cc-runner のループで行います。

⸻

3. systemd user serviceで起動・再起動する

~/.config/systemd/user/claude-code@.service

[Unit]
Description=Claude Code Remote Control supervisor for %i
After=network-online.target
[Service]
Type=simple
Environment=PROJECT_DIR=%h/work/%i
Environment=SESSION_NAME=cc-%i
ExecStart=%h/.local/bin/cc-supervisor %i
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=10
[Install]
WantedBy=default.target

有効化します。

systemctl --user daemon-reload
systemctl --user enable --now claude-code@myproject.service
systemctl --user status claude-code@myproject.service

systemdの Restart=on-failure は、プロセスが非ゼロ終了、シグナル終了、タイムアウト、watchdog timeoutなどで失敗した場合に再起動します。RestartSec= で再起動前の待機時間も設定できます。 

サーバー再起動後もユーザーサービスを動かしたい場合は、Linux環境では通常これも設定します。

loginctl enable-linger "$USER"

⸻

4. 手動復旧コマンドを作る

~/.local/bin/cc-status

#!/usr/bin/env bash
set -euo pipefail
PROJECT_NAME="${1:?project name required}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/work/$PROJECT_NAME}"
SESSION_NAME="${SESSION_NAME:-cc-$PROJECT_NAME}"
echo "project: $PROJECT_NAME"
echo "dir:     $PROJECT_DIR"
echo "tmux:    $SESSION_NAME"
echo
echo "systemd:"
systemctl --user --no-pager status "claude-code@$PROJECT_NAME.service" || true
echo
echo "tmux:"
tmux has-session -t "$SESSION_NAME" 2>/dev/null \
  && tmux list-panes -t "$SESSION_NAME" -F '#{session_name}:#{window_name}.#{pane_index} pid=#{pane_pid} cmd=#{pane_current_command}' \
  || echo "tmux session not found"
echo
echo "recovery files:"
ls -lah "$PROJECT_DIR/.claude/recovery" 2>/dev/null || true
echo
echo "git status:"
cd "$PROJECT_DIR"
git status --short || true
chmod +x ~/.local/bin/cc-status

~/.local/bin/cc-attach

#!/usr/bin/env bash
set -euo pipefail
PROJECT_NAME="${1:?project name required}"
SESSION_NAME="${SESSION_NAME:-cc-$PROJECT_NAME}"
tmux attach -t "$SESSION_NAME"
chmod +x ~/.local/bin/cc-attach

~/.local/bin/cc-revive

#!/usr/bin/env bash
set -euo pipefail
PROJECT_NAME="${1:?project name required}"
systemctl --user restart "claude-code@$PROJECT_NAME.service"
sleep 2
systemctl --user --no-pager status "claude-code@$PROJECT_NAME.service"
chmod +x ~/.local/bin/cc-revive

~/.local/bin/cc-safe

#!/usr/bin/env bash
set -euo pipefail
PROJECT_NAME="${1:?project name required}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/work/$PROJECT_NAME}"
cd "$PROJECT_DIR"
echo "Starting Claude Code in safe mode."
echo "This bypasses project customizations, hooks, plugins, MCP, skills, etc."
claude --safe-mode --permission-mode plan
chmod +x ~/.local/bin/cc-safe

--safe-mode は、CLAUDE.md、skills、plugins、hooks、MCP servers、custom commands、agents、status lineなどのカスタマイズを無効にして起動するトラブルシューティング用モードです。壊れたhookやMCP設定で通常起動できない場合の逃げ道として重要です。 

⸻

5. Claude Code hooksでheartbeatと監査を取る

Claude Code hooksは、Claude Codeのライフサイクル上の特定ポイントでshell commandを実行できる仕組みです。ファイル編集後のformatter、危険操作のブロック、通知、context再注入などに使えます。hookは設定JSONに定義し、PreToolUse や Notification などのイベントに紐づけます。 

~/.local/bin/cc-hook-heartbeat

#!/usr/bin/env bash
set -euo pipefail
payload="$(cat)"
cwd="$(jq -r '.cwd // "."' <<< "$payload")"
mkdir -p "$cwd/.claude/recovery"
date -Is > "$cwd/.claude/recovery/claude-hook-heartbeat"
jq -c '{
  at: now | todateiso8601,
  session_id,
  transcript_path,
  cwd,
  permission_mode,
  hook_event_name,
  tool_name
}' <<< "$payload" >> "$cwd/.claude/recovery/hook-events.jsonl"
chmod +x ~/.local/bin/cc-hook-heartbeat

hook入力には session_id、transcript_path、cwd、permission_mode、hook_event_name などが含まれます。これを保存しておくと、復旧時にどのセッション・どの作業ディレクトリ・どのtranscriptだったかを追えます。 

~/.local/bin/cc-hook-guard

#!/usr/bin/env bash
set -euo pipefail
payload="$(cat)"
tool_name="$(jq -r '.tool_name // ""' <<< "$payload")"
command="$(jq -r '.tool_input.command // ""' <<< "$payload")"
if [ "$tool_name" != "Bash" ]; then
  exit 0
fi
# 必要に応じて調整
danger_regex='rm -rf /|rm -rf \$HOME|sudo |mkfs|dd if=|chmod -R 777|chown -R|git reset --hard|git clean -fdx|curl .* \| sh|wget .* \| sh'
if grep -Eiq "$danger_regex" <<< "$command"; then
  cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Recovery guard blocked a destructive or high-risk shell command."
  }
}
JSON
fi
chmod +x ~/.local/bin/cc-hook-guard

PreToolUse hookは、コマンド内容を検査してJSONでdenyを返すことでtool callをブロックできます。公式例でも、危険な rm -rf 系コマンドをhookで拒否する形が示されています。 

~/.claude/settings.json

既存設定がある場合は、hooks をマージしてください。

{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.local/bin/cc-hook-guard"
          },
          {
            "type": "command",
            "command": "$HOME/.local/bin/cc-hook-heartbeat"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.local/bin/cc-hook-heartbeat"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.local/bin/cc-hook-heartbeat"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.local/bin/cc-hook-heartbeat"
          }
        ]
      }
    ]
  }
}

Notification hookはClaude Codeが入力待ち・permission待ちになったときなどに使えます。公式ドキュメントでは、permission_prompt や idle_prompt などのmatcherも用意されています。 

⸻

6. Gitベースの作業復旧

Claude Codeの復旧では、プロセス復旧より 作業差分の保護 が重要です。

起動前にブランチを切る

cd ~/work/myproject
git switch -c ai/claude-$(date +%Y%m%d-%H%M%S)

手動snapshot

mkdir -p .claude/recovery
git status --short > .claude/recovery/git-status.$(date +%Y%m%d-%H%M%S).txt
git diff > .claude/recovery/wip.$(date +%Y%m%d-%H%M%S).patch
git diff --staged > .claude/recovery/staged.$(date +%Y%m%d-%H%M%S).patch

自動snapshot script

~/.local/bin/cc-snapshot:

#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${1:-$PWD}"
cd "$PROJECT_DIR"
mkdir -p .claude/recovery/snapshots
ts="$(date +%Y%m%d-%H%M%S)"
git status --short > ".claude/recovery/snapshots/status.$ts.txt" || true
git diff > ".claude/recovery/snapshots/wip.$ts.patch" || true
git diff --staged > ".claude/recovery/snapshots/staged.$ts.patch" || true
git rev-parse HEAD > ".claude/recovery/snapshots/head.$ts.txt" || true
chmod +x ~/.local/bin/cc-snapshot

systemd timerやcronで5〜10分ごとに回すと、誤編集・Claude Codeクラッシュ・ネットワーク断に強くなります。

⸻

7. 復旧手順

A. Web/スマホから見えなくなった

まずSSHします。

ssh your-host

状態確認。

cc-status myproject

tmuxが生きていればattach。

cc-attach myproject

tmux内でClaude Codeが落ちていれば、cc-runner が通常は自動再起動します。再起動していない場合：

cc-revive myproject

Remote Controlはローカル claude プロセスが止まると終了します。再起動後は新しいRemote Control sessionとして再接続する前提で設計します。 

⸻

B. Claude Code設定が壊れている

通常起動が失敗する場合：

cd ~/work/myproject
claude --safe-mode --permission-mode plan

または：

cc-safe myproject

この状態ではhooksやMCPなどのカスタマイズを外して起動できます。まず原因が ~/.claude/settings.json、.claude/settings.json、MCP、hook、pluginのどれかを切り分けます。 

⸻

C. 以前のClaude Codeセッションに戻したい

Claude Codeは --resume で特定のセッションIDまたは名前を再開できます。--resume はID・名前・対話pickerに対応し、名前付きsessionも再開できます。 

claude --resume cc-myproject

IDが分かる場合：

claude --resume <session-id>

hookで保存した情報を見る：

tail -n 20 ~/work/myproject/.claude/recovery/hook-events.jsonl | jq .

⸻

D. Claude Codeが危険な作業をした疑いがある

まず停止。

systemctl --user stop claude-code@myproject.service

tmuxも止める場合：

tmux kill-session -t cc-myproject

差分退避。

cd ~/work/myproject
mkdir -p .claude/recovery/manual
git status --short > .claude/recovery/manual/status-before-recovery.txt
git diff > .claude/recovery/manual/wip-before-recovery.patch
git diff --staged > .claude/recovery/manual/staged-before-recovery.patch

確認。

git diff
git diff --staged
git status

必要ならstash。

git stash push -u -m "recovery-before-manual-reset-$(date +%Y%m%d-%H%M%S)"

⸻

E. Claude Codeが入力待ち・permission待ちで止まっている

tmuxに入る。

cc-attach myproject

またはRemote Controlに再接続します。Remote Controlではpermission promptはWebやモバイル側にも出ます。ローカルRemote Control sessionで使えるpermission modeはAsk permissions、Auto accept edits、Plan modeです。AutoやBypass permissionsを前提にした復旧設計にはしない方がよいです。 

⸻

8. 自己復旧プロンプトを固定する

Claude Codeに復旧を依頼する場合、自由に直させるのではなく、読み取り・診断・提案まで に制限します。

PROJECT/.claude/recovery/RECOVERY_PROMPT.md:

# Recovery mode instructions
You are recovering a possibly interrupted Claude Code session.
Constraints:
- Do not edit files unless explicitly approved.
- Do not run destructive commands.
- First inspect:
  - git status
  - .claude/recovery/*
  - recent test logs
  - recent hook-events.jsonl
- Produce:
  1. What likely happened
  2. Current repository state
  3. Risk assessment
  4. Safe next actions
  5. Exact commands for the human operator

実行例：

cd ~/work/myproject
claude --permission-mode plan "$(cat .claude/recovery/RECOVERY_PROMPT.md)"

非対話で診断だけさせる場合は claude -p が使えます。-p / --print はClaude Codeを非対話で実行するモードで、--output-format、--allowedTools、--continue などのCLIオプションと併用できます。 

例：

claude --bare -p "$(cat .claude/recovery/RECOVERY_PROMPT.md)" \
  --allowedTools "Read,Bash" \
  --permission-mode plan

--bare はhooks、skills、plugins、MCP、auto memory、CLAUDE.mdなどの自動読み込みを省いて、スクリプトやCIで再現性を上げるためのモードです。 

⸻

9. 通知設計

最小

Claude CodeのRemote Controlにはモバイルpush通知があります。Remote Controlが有効なとき、Claudeは長時間タスク終了時や判断が必要なときにpush通知を送ることがあります。 

追加

hookで Notification を拾って、Slack、Discord、LINE Notify代替、ntfy、メールなどに通知します。

例: ntfyを使う場合。

#!/usr/bin/env bash
set -euo pipefail
payload="$(cat)"
event="$(jq -r '.hook_event_name // "unknown"' <<< "$payload")"
cwd="$(jq -r '.cwd // "."' <<< "$payload")"
curl -sS \
  -H "Title: Claude Code" \
  -d "Claude Code needs attention. event=$event cwd=$cwd" \
  https://ntfy.sh/YOUR_TOPIC >/dev/null

より高度にするならClaude Code Channelsも候補です。ChannelsはMCP server経由で、CI結果・chat message・monitoring eventを実行中のClaude Code sessionへpushできます。ただしイベントが届くのはsessionが開いている間だけなので、常時運用するにはbackground processまたはpersistent terminalが必要です。 

⸻

10. Permission設計

推奨初期値

claude --remote-control "myproject" --permission-mode plan

復旧後に安全確認してから：

claude --permission-mode acceptEdits

acceptEdits は作業ディレクトリ内のファイル作成・編集を自動承認しますが、範囲外path、protected path、その他Bashコマンドは引き続きprompt対象です。 

避けるべきもの

* 復旧系で最初から広範な自動承認を使う
* rm -rf、git reset --hard、git clean -fdx をClaudeに許可する
* secretsやproduction credentialsがある作業ディレクトリで自由実行させる
* .claude/settings.json をClaudeに無制限編集させる
* hookやMCPの復旧をClaude自身に即時反映させる

⸻

11. 運用ルール

毎回Claude Codeを起動する前

cd ~/work/myproject
git status
git switch -c ai/task-$(date +%Y%m%d-%H%M%S)
systemctl --user start claude-code@myproject.service

遠隔作業中

cc-status myproject

止まったら

cc-attach myproject

壊れたら

cc-safe myproject

危ないと思ったら

systemctl --user stop claude-code@myproject.service
tmux kill-session -t cc-myproject

⸻

12. 実装優先順位

Phase 1: 最小復旧

まずこれだけ作ります。

1. Claude Codeをtmux内で動かす
2. systemd user serviceでcc-supervisorを動かす
3. cc-status / cc-attach / cc-revive / cc-safeを作る
4. 作業前にgit branchを切る

Phase 2: 自動監査

次に追加します。

1. hook heartbeat
2. hook event log
3. dangerous Bash guard
4. periodic git diff snapshot
5. Notification hook

Phase 3: 遠隔運用強化

最後に追加します。

1. Remote Control default enable
2. mobile push
3. ntfy / Slack / Discord通知
4. channels
5. recovery prompt template
6. read-only diagnostic headless run

Remote Controlは明示的に claude remote-control、claude --remote-control、またはsession内の /remote-control で開始できます。すべてのinteractive sessionで自動有効化する設定もありますが、複数instance運用ではsession数や名前管理を明確にする必要があります。 

⸻

実用上の推奨構成

個人・小規模用途なら、これが最もバランスが良いです。

- Claude Code起動:
  claude --remote-control "project-name" --permission-mode plan
- 実行場所:
  tmux session: cc-project-name
- 起動管理:
  systemd user service
- 復旧:
  cc-status
  cc-attach
  cc-revive
  cc-safe
- 安全策:
  git branch per task
  periodic git diff snapshot
  PreToolUse dangerous command guard
  --safe-mode escape hatch
- 遠隔操作:
  Claude Code Remote Control
  fallback: SSH + tmux attach

この設計なら、Claude Code本体、Remote Control、設定、hook、ネットワークのどれかが壊れても、SSH + tmux + git + safe-mode で人間が復旧できます。