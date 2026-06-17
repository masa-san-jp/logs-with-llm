# ASUS GX10でAntigravity CLIをTelegramから操作するセットアップ手順書

作成日: 2026-06-17

## 1. 結論

ASUS GX10上のUbuntuにAntigravity CLIを導入し、Telegram Bot経由で操作する構成は実現可能です。

ただし、TelegramからAI coding agentを呼ぶ構成は、実質的に「スマホから自宅マシン上の開発エージェントを遠隔実行する」構成です。任意shell実行Botにはせず、次の制約を必ず入れます。

- Bot専用の非rootユーザーで実行する
- Telegramの許可chat_idを固定する
- 外部公開ポートを作らずpolling方式で動かす
- `agy`以外の任意shellコマンドをTelegramから実行させない
- 初期状態ではwrite modeを無効化する
- write modeを有効にする場合も、専用workspace配下のGit repositoryに限定する
- `--dangerously-skip-permissions`は使わない

推奨構成:

```text
Telegram app
  ↓
Telegram Bot API polling
  ↓
ASUS GX10 / Ubuntu
  ↓
専用ユーザー: agybot
  ↓
Python bridge daemon
  ↓
Antigravity CLI: agy -p / agy --sandbox -p
  ↓
/home/agybot/workspaces 配下のrepository
```

## 2. 前提

この手順では、GX10のUbuntuにSSHで入れる状態を前提にします。

必要なもの:

- ASUS GX10
- Ubuntu Linux
- Telegramアカウント
- BotFatherで作成したTelegram Bot token
- Googleアカウント、またはAntigravity CLIで使うGoogle Cloud project
- GX10上に置く作業repository

## 3. 重要な仕様確認

Antigravity CLIの実行ファイルは`agy`です。

公式READMEでは、macOS/Linuxのインストール方法は次のコマンドです。

```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

Antigravity CLIはTUIだけでなく、`-p`または`--print`で単発の非対話実行ができます。Telegram bridgeから呼ぶのはこの非対話実行です。

代表的な引数:

```bash
agy -p "プロンプト"
agy --sandbox -p "プロンプト"
agy --model "Gemini 3.5 Flash (High)" -p "プロンプト"
agy models
agy --help
agy --version
```

注意:

- `--sandbox`はterminal restrictionsを有効化します。
- `--dangerously-skip-permissions`は自動承認です。Telegram経由では使いません。
- Linux ARM64では、特殊な39-bit VA環境で起動クラッシュ報告があります。GX10の通常Ubuntuなら問題が出る可能性は低いですが、`agy --version`で必ず事前検証します。

## 4. GX10側の準備

### 4.1 OSとarchitecture確認

```bash
uname -a
uname -m
cat /etc/os-release
getconf PAGE_SIZE
```

想定:

```text
aarch64
Ubuntu系
```

ARM64 kernel設定が見える場合は確認します。

```bash
zgrep -E 'CONFIG_ARM64_VA_BITS|CONFIG_ARM64_.*PAGES' /proc/config.gz 2>/dev/null || true
```

## 5. 専用ユーザー作成

BotとAntigravity CLIを普段のユーザーやrootで動かさないため、専用ユーザーを作成します。

```bash
sudo adduser --disabled-password --gecos "Antigravity Telegram Bot" agybot
sudo usermod -L agybot
sudo mkdir -p /home/agybot/workspaces
sudo chown -R agybot:agybot /home/agybot/workspaces
```

sudo権限は付与しません。

確認:

```bash
id agybot
sudo -l -U agybot
```

`agybot`にsudo権限がないことを確認します。

## 6. Antigravity CLIの導入

`agybot`ユーザーでインストールします。

```bash
sudo -iu agybot bash -lc 'curl -fsSL https://antigravity.google/cli/install.sh | bash'
```

PATHを明示します。

```bash
sudo -iu agybot bash -lc 'grep -q ".local/bin" ~/.profile || echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> ~/.profile'
sudo -iu agybot bash -lc 'export PATH="$HOME/.local/bin:$PATH"; agy --version'
```

失敗する場合:

```bash
sudo -iu agybot bash -lc 'ls -la ~/.local/bin && file ~/.local/bin/agy'
sudo -iu agybot bash -lc 'export PATH="$HOME/.local/bin:$PATH"; agy --help'
```

## 7. Antigravity CLIの初回認証

非対話実行の前に、同じ`agybot`ユーザーでOAuth/TOS/workspace trustを完了させます。

```bash
sudo -iu agybot
export PATH="$HOME/.local/bin:$PATH"
mkdir -p ~/workspaces/default
cd ~/workspaces/default
agy
```

実施すること:

1. Google OAuthまたはGoogle Cloud projectを選択
2. 表示されたURLを手元のブラウザで開く
3. 認証コードを端末に貼り付ける
4. Terms of Serviceを承諾
5. `~/workspaces/default`をtrusted workspaceとして承諾
6. `/settings`または`/config`を開く
7. 初期運用ではTool Permissionを`strict`または`request-review`にする
8. `/quit`で終了

非対話テスト:

```bash
sudo -iu agybot bash -lc 'export PATH="$HOME/.local/bin:$PATH"; cd ~/workspaces/default && agy --sandbox -p "1行で自己紹介して"'
```

## 8. Telegram Bot作成

TelegramでBotFatherを開きます。

```text
/newbot
```

Bot nameとusernameを設定し、tokenを控えます。

例:

```text
1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

このtokenは秘密情報です。Git repositoryやチャットログに貼らないでください。

## 9. chat_id取得

作成したBotにTelegramから `/start` を送ります。

GX10または手元端末で次を実行します。

```bash
BOT_TOKEN='ここにBotFatherのtoken'
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook"
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates" | python3 -m json.tool
```

出力内の次を探します。

```json
"chat": {
  "id": 123456789,
  ...
}
```

この`id`が許可chat_idです。

## 10. Python bridgeの導入

### 10.1 Python仮想環境

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl jq

sudo -iu agybot bash -lc 'python3 -m venv ~/telegram-agy-venv'
sudo -iu agybot bash -lc '~/telegram-agy-venv/bin/pip install --upgrade pip'
sudo -iu agybot bash -lc '~/telegram-agy-venv/bin/pip install python-telegram-bot==22.6'
```

### 10.2 bridge配置

```bash
sudo -iu agybot bash -lc 'mkdir -p ~/telegram-agy-bot ~/workspaces'
```

```bash
sudo tee /home/agybot/telegram-agy-bot/bot.py >/dev/null <<'PY'
#!/usr/bin/env python3
import asyncio
import os
from pathlib import Path
from typing import Iterable

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_CHAT_IDS = {
    int(x.strip())
    for x in os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
    if x.strip()
}

WORKSPACE_ROOT = Path(os.environ.get("AGY_WORKSPACE_ROOT", "/home/agybot/workspaces")).resolve()
AGY_BIN = os.environ.get("AGY_BIN", "/home/agybot/.local/bin/agy")
AGY_MODEL = os.environ.get("AGY_MODEL", "").strip()
AGY_TIMEOUT_SEC = int(os.environ.get("AGY_TIMEOUT_SEC", "900"))
AGY_ALLOW_WRITE = os.environ.get("AGY_ALLOW_WRITE", "0") == "1"
MAX_TELEGRAM_CHARS = 3900

RUN_LOCK = asyncio.Lock()


def is_allowed(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id in ALLOWED_CHAT_IDS)


def split_text(text: str, limit: int = MAX_TELEGRAM_CHARS) -> Iterable[str]:
    text = text or "(no output)"
    while text:
        yield text[:limit]
        text = text[limit:]


def resolve_repo(repo_name: str) -> Path:
    if not repo_name or repo_name.startswith("-"):
        raise ValueError("repo名が不正です")
    root = WORKSPACE_ROOT.resolve()
    candidate = (root / repo_name).resolve()
    if not str(candidate).startswith(str(root) + os.sep):
        raise ValueError("workspace root外のpathは拒否しました")
    if not candidate.exists() or not candidate.is_dir():
        raise ValueError(f"repoが存在しません: {repo_name}")
    return candidate


async def reply_long(update: Update, text: str) -> None:
    for part in split_text(text):
        await update.effective_message.reply_text(part)


async def run_agy(prompt: str, cwd: Path, sandbox: bool, timeout_sec: int = AGY_TIMEOUT_SEC) -> tuple[int, str]:
    cmd = [AGY_BIN]
    if sandbox:
        cmd.append("--sandbox")
    if AGY_MODEL:
        cmd.extend(["--model", AGY_MODEL])
    cmd.extend(["-p", prompt])

    env = os.environ.copy()
    env["HOME"] = "/home/agybot"
    env["PATH"] = "/home/agybot/.local/bin:/usr/local/bin:/usr/bin:/bin"
    env.setdefault("AGY_CLI_DISABLE_LATEX", "1")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return 124, f"TIMEOUT: {timeout_sec}sを超えたため停止しました"

    out = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()
    combined = out
    if err:
        combined = f"{combined}\n\n[stderr]\n{err}" if combined else f"[stderr]\n{err}"
    return proc.returncode or 0, combined


async def guard(update: Update) -> bool:
    if not is_allowed(update):
        chat_id = update.effective_chat.id if update.effective_chat else "unknown"
        await update.effective_message.reply_text(f"拒否: このchat_idは未許可です。chat_id={chat_id}")
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.effective_message.reply_text(
        "Antigravity Telegram bridge is running.\n"
        "Commands:\n"
        "/ping\n"
        "/repos\n"
        "/ask <prompt>\n"
        "/review <repo> <prompt>\n"
        "/run <repo> <prompt>  # disabled unless AGY_ALLOW_WRITE=1"
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.effective_message.reply_text("pong")


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    await update.effective_message.reply_text(f"chat_id={chat.id if chat else 'unknown'}")


async def repos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    names = sorted([p.name for p in WORKSPACE_ROOT.iterdir() if p.is_dir()])
    await update.effective_message.reply_text("\n".join(names) if names else "repoなし")


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.effective_message.reply_text("使い方: /ask <prompt>")
        return
    async with RUN_LOCK:
        await update.effective_chat.send_action(ChatAction.TYPING)
        code, output = await run_agy(prompt, WORKSPACE_ROOT, sandbox=True)
    await reply_long(update, f"exit={code}\n{output}")


async def review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    if len(context.args) < 2:
        await update.effective_message.reply_text("使い方: /review <repo> <prompt>")
        return
    repo = context.args[0]
    prompt = " ".join(context.args[1:]).strip()
    try:
        cwd = resolve_repo(repo)
    except ValueError as e:
        await update.effective_message.reply_text(str(e))
        return

    safe_prompt = (
        "あなたはrepository reviewerです。ファイル変更やコマンド実行は最小限にし、"
        "まず現状分析・リスク・変更方針・推奨diffを日本語で返してください。"
        "実ファイルを変更せず、レビュー結果を返してください。\n\n"
        f"依頼: {prompt}"
    )
    async with RUN_LOCK:
        await update.effective_chat.send_action(ChatAction.TYPING)
        code, output = await run_agy(safe_prompt, cwd, sandbox=True)
    await reply_long(update, f"repo={repo}\nmode=review/sandbox\nexit={code}\n{output}")


async def run_write(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    if not AGY_ALLOW_WRITE:
        await update.effective_message.reply_text(
            "write modeは無効です。/reviewで確認してください。\n"
            "有効化する場合は /etc/telegram-agy-bot.env の AGY_ALLOW_WRITE=1 を設定し、serviceを再起動してください。"
        )
        return
    if len(context.args) < 2:
        await update.effective_message.reply_text("使い方: /run <repo> <prompt>")
        return
    repo = context.args[0]
    prompt = " ".join(context.args[1:]).strip()
    try:
        cwd = resolve_repo(repo)
    except ValueError as e:
        await update.effective_message.reply_text(str(e))
        return

    guarded_prompt = (
        "あなたはこのGit repository内だけで作業する coding agentです。"
        "root権限、sudo、外部secret参照、破壊的操作、git push、remote変更は禁止。"
        "変更前に現状を確認し、必要最小限の変更を行い、最後に変更ファイル一覧とgit diff要約を日本語で返してください。\n\n"
        f"依頼: {prompt}"
    )
    async with RUN_LOCK:
        await update.effective_chat.send_action(ChatAction.TYPING)
        code, output = await run_agy(guarded_prompt, cwd, sandbox=False)
    await reply_long(update, f"repo={repo}\nmode=write\nexit={code}\n{output}")


def main() -> None:
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")
    if not ALLOWED_CHAT_IDS:
        raise SystemExit("TELEGRAM_ALLOWED_CHAT_IDS is required")
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("repos", repos))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("review", review))
    app.add_handler(CommandHandler("run", run_write))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
PY

sudo chown -R agybot:agybot /home/agybot/telegram-agy-bot
sudo chmod 700 /home/agybot/telegram-agy-bot
sudo chmod 700 /home/agybot/telegram-agy-bot/bot.py
```

## 11. 環境変数ファイル

`<BOT_TOKEN>`と`<CHAT_ID>`を書き換えます。

```bash
sudo tee /etc/telegram-agy-bot.env >/dev/null <<'ENVFILE'
TELEGRAM_BOT_TOKEN=<BOT_TOKEN>
TELEGRAM_ALLOWED_CHAT_IDS=<CHAT_ID>
AGY_WORKSPACE_ROOT=/home/agybot/workspaces
AGY_BIN=/home/agybot/.local/bin/agy
AGY_TIMEOUT_SEC=900
AGY_MODEL=
AGY_ALLOW_WRITE=0
ENVFILE

sudo chown root:root /etc/telegram-agy-bot.env
sudo chmod 600 /etc/telegram-agy-bot.env
```

複数chat_idを許可する場合:

```text
TELEGRAM_ALLOWED_CHAT_IDS=123456789,987654321
```

## 12. systemd service化

```bash
sudo tee /etc/systemd/system/telegram-agy-bot.service >/dev/null <<'UNIT'
[Unit]
Description=Telegram bridge for Antigravity CLI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=agybot
Group=agybot
WorkingDirectory=/home/agybot/telegram-agy-bot
EnvironmentFile=/etc/telegram-agy-bot.env
ExecStart=/home/agybot/telegram-agy-venv/bin/python /home/agybot/telegram-agy-bot/bot.py
Restart=on-failure
RestartSec=5

# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/agybot
CapabilityBoundingSet=
LockPersonality=true
RestrictRealtime=true
RestrictSUIDSGID=true

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now telegram-agy-bot.service
```

確認:

```bash
systemctl status telegram-agy-bot.service --no-pager
journalctl -u telegram-agy-bot.service -f
```

Telegramで確認:

```text
/ping
/ask Antigravity CLIとは何か1行で説明して
```

## 13. repository配置

例としてGitHub repositoryを置きます。

```bash
sudo -iu agybot bash -lc 'cd ~/workspaces && git clone <YOUR_REPO_URL> myrepo'
sudo -iu agybot bash -lc 'cd ~/workspaces/myrepo && git status'
```

Telegramで確認:

```text
/repos
/review myrepo READMEを読み、改善点を箇条書きで出して
```

## 14. write modeを有効化する場合

write modeは実ファイル変更を許すため、初期状態では無効です。

有効化前に、対象repoで専用branchを切ります。

```bash
sudo -iu agybot bash -lc 'cd ~/workspaces/myrepo && git checkout -b agy-telegram-work'
```

環境変数を変更します。

```bash
sudo sed -i 's/^AGY_ALLOW_WRITE=.*/AGY_ALLOW_WRITE=1/' /etc/telegram-agy-bot.env
sudo systemctl restart telegram-agy-bot.service
```

Telegramから実行:

```text
/run myrepo READMEにセットアップ手順の章を追加して
```

変更確認:

```bash
sudo -iu agybot bash -lc 'cd ~/workspaces/myrepo && git status && git diff --stat && git diff'
```

問題なければ、通常ユーザーでreviewしてからcommitします。

```bash
sudo -iu agybot bash -lc 'cd ~/workspaces/myrepo && git add -A && git commit -m "Update README via Antigravity"'
```

`git push`はTelegram経由では行わず、SSHで確認後に手動実行を推奨します。

## 15. Botコマンド仕様

| コマンド | 機能 | 安全性 |
|---|---|---|
| `/ping` | Bot疎通確認 | 安全 |
| `/whoami` | chat_id表示 | 安全 |
| `/repos` | workspace配下のrepo一覧 | 安全 |
| `/ask <prompt>` | `agy --sandbox -p`で一般質問 | 比較的安全 |
| `/review <repo> <prompt>` | repoをsandbox付きでレビュー | 比較的安全 |
| `/run <repo> <prompt>` | repoに対してwrite mode実行 | 危険。明示有効化が必要 |

## 16. 運用ルール

推奨ルール:

- `/ask`と`/review`を通常運用にする
- `/run`は短時間だけ有効化し、使い終わったら無効化する
- `/run`前に必ずGit branchを切る
- `/run`後に必ず`git diff`をSSHで確認する
- Bot tokenは定期的にrotateする
- Botをグループに入れない。private chat限定で使う
- `AGY_ALLOW_WRITE=1`のまま常時放置しない

write modeを無効化:

```bash
sudo sed -i 's/^AGY_ALLOW_WRITE=.*/AGY_ALLOW_WRITE=0/' /etc/telegram-agy-bot.env
sudo systemctl restart telegram-agy-bot.service
```

## 17. アップデート

Antigravity CLI:

```bash
sudo -iu agybot bash -lc 'export PATH="$HOME/.local/bin:$PATH"; agy update && agy --version'
```

Python library:

```bash
sudo -iu agybot bash -lc '~/telegram-agy-venv/bin/pip install --upgrade python-telegram-bot'
sudo systemctl restart telegram-agy-bot.service
```

変更履歴確認:

```bash
sudo -iu agybot bash -lc 'export PATH="$HOME/.local/bin:$PATH"; agy changelog | head -100'
```

## 18. トラブルシューティング

### 18.1 Botが反応しない

```bash
systemctl status telegram-agy-bot.service --no-pager
journalctl -u telegram-agy-bot.service -n 100 --no-pager
```

Webhookが残っている場合はpollingと競合します。

```bash
BOT_TOKEN='...'
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook"
sudo systemctl restart telegram-agy-bot.service
```

### 18.2 `TELEGRAM_ALLOWED_CHAT_IDS is required`

`/etc/telegram-agy-bot.env`にchat_idが入っていません。

```bash
sudo cat /etc/telegram-agy-bot.env
```

### 18.3 `agy`が見つからない

```bash
sudo -iu agybot bash -lc 'ls -la ~/.local/bin/agy; ~/.local/bin/agy --version'
```

`/etc/telegram-agy-bot.env`の`AGY_BIN`を確認します。

### 18.4 Antigravity CLIの認証が必要と言われる

systemd serviceと同じ`agybot`ユーザーで初回認証してください。

```bash
sudo -iu agybot
export PATH="$HOME/.local/bin:$PATH"
cd ~/workspaces/default
agy
```

### 18.5 `/run`が動かない、またはtimeoutする

原因候補:

- Tool Permissionがapproval待ちになっている
- 非対話実行で承認待ちになっている
- workspaceがtrustedになっていない
- promptが大きすぎる
- network/auth/quota問題

確認:

```bash
sudo -iu agybot bash -lc 'export PATH="$HOME/.local/bin:$PATH"; cd ~/workspaces/myrepo && agy -p "このrepoのファイル一覧を要約して"'
```

write modeで完全自律化する場合、Antigravity側のTool Permission設定を`always-proceed`にする必要が出る可能性があります。ただし、これはhost上での自動実行リスクが大きいため、専用branch・専用ユーザー・sudoなし・Git diff確認を必須にしてください。

### 18.6 Linux ARM64で`agy --version`が落ちる

まずCLIを更新します。

```bash
sudo -iu agybot bash -lc 'export PATH="$HOME/.local/bin:$PATH"; agy update || true; agy --version'
```

それでも落ちる場合は、ARM64/VA_BITS/TCMalloc関連の既知問題に該当する可能性があります。

確認:

```bash
uname -m
getconf PAGE_SIZE
zgrep -E 'CONFIG_ARM64_VA_BITS|CONFIG_ARM64_.*PAGES' /proc/config.gz 2>/dev/null || true
```

GX10の通常Ubuntu kernelでは再現しにくい想定ですが、LXC/Android/Proot系のARM64環境では問題化する可能性があります。

## 19. 削除手順

service停止:

```bash
sudo systemctl disable --now telegram-agy-bot.service
sudo rm -f /etc/systemd/system/telegram-agy-bot.service
sudo systemctl daemon-reload
```

設定削除:

```bash
sudo rm -f /etc/telegram-agy-bot.env
```

ユーザーとデータを削除する場合:

```bash
sudo deluser --remove-home agybot
```

Telegram tokenはBotFatherでrevokeしてください。

## 20. 参照情報

- Antigravity CLI GitHub README: https://github.com/google-antigravity/antigravity-cli
- Antigravity CLI product page: https://antigravity.google/product/antigravity-cli
- Antigravity CLI hands-on codelab: https://codelabs.developers.google.com/antigravity-cli-hands-on
- Google Developers Blog: Transitioning Gemini CLI to Antigravity CLI: https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/
- Telegram Bot API: https://core.telegram.org/bots/api
- Telegram webhook guide: https://core.telegram.org/bots/webhooks
- python-telegram-bot Application docs: https://docs.python-telegram-bot.org/en/v22.6/telegram.ext.application.html
- Linux ARM64 crash report: https://discuss.ai.google.dev/t/bug-agy-crashes-on-arm64/145425
