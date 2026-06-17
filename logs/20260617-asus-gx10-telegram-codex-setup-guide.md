# ASUS GX10 Telegram-to-Codex セットアップ手順書

作成日: 2026-06-17

## 0. 結論

TelegramからASUS GX10上のCodexを操作する構成は実現可能。

ただし、これはOpenAI公式のCodex mobile remote controlではなく、Telegram Bot APIを使った自前ブリッジである。公式のスマホ連携はCodex App hostをmacOS/Windowsで起動し、ChatGPT mobile appから操作する構成であり、Telegramは公式クライアントではない。

本手順では安全側に倒し、次の構成を採用する。

```text
Telegram mobile app
        ↓
Telegram Bot API polling
        ↓
ASUS GX10 Ubuntu
        ↓
専用Linuxユーザー codexbot
        ↓
Python bridge daemon
        ↓
Codex CLI: codex exec
        ↓
/home/codexbot/workspaces 配下のGit repository
```

## 1. 設計方針

### 採用する方式

| 項目 | 採用方針 |
|---|---|
| Telegram受信方式 | polling |
| 外部公開ポート | なし |
| 実行ユーザー | 専用非rootユーザー `codexbot` |
| sudo権限 | 付与しない |
| 実行コマンド | `codex exec`のみ |
| 作業ディレクトリ | `/home/codexbot/workspaces`配下のみ |
| Codex sandbox | 原則 `workspace-write` または `read-only` |
| Codex approval | `never`。Telegram経由では対話承認しない |
| 禁止 | `--dangerously-bypass-approvals-and-sandbox`, `--yolo`, 任意shell実行 |

### この構成でできること

- TelegramからCodexに作業指示を送る
- CodexがGX10上の指定リポジトリを読んで回答する
- `workspace-write`モードでリポジトリ内のファイルを編集する
- 実行結果をTelegramに返す
- 進行中ジョブをTelegramから停止する

### この構成でやらないこと

- Telegramから任意のbashコマンドを実行する
- GX10のroot操作をTelegramから行う
- Codex Appの公式remote UIを再現する
- Codexの承認UI、diff UI、thread UIをTelegram上に完全実装する
- app-serverやwebhookをインターネット公開する

## 2. 前提条件

GX10側:

```bash
uname -m
lsb_release -a || cat /etc/os-release
```

想定:

```text
aarch64
Ubuntu 24.04 LTS 以降
```

必要なもの:

- GX10へSSH接続できること
- Telegramアカウント
- BotFatherで作成したTelegram Bot token
- Codex利用権限のあるChatGPTアカウント
- GX10上でCodex CLIにログインできること

## 3. Telegram Botを作成する

Telegramで `@BotFather` を開き、次を実行する。

```text
/newbot
```

Bot nameとusernameを指定し、Bot tokenを取得する。

Bot tokenは次の形式になる。

```text
1234567890:AA...
```

このtokenは秘密情報。Git、Notion、Slack、メモ、スクリーンショットに残さない。

## 4. GX10に専用ユーザーを作る

SSHでGX10へ入る。

```bash
ssh gx10
```

専用ユーザーを作成する。

```bash
sudo adduser --disabled-password --gecos "" codexbot
sudo passwd -l codexbot
```

作業ディレクトリを作成する。

```bash
sudo install -d -o codexbot -g codexbot -m 755 /home/codexbot/workspaces
sudo install -d -o codexbot -g codexbot -m 755 /opt/telegram-codex-bridge
sudo install -d -o root -g codexbot -m 750 /etc/telegram-codex-bridge
```

`codexbot`にはsudo権限を付けない。

確認:

```bash
sudo -l -U codexbot
```

期待値:

```text
User codexbot is not allowed to run sudo on ...
```

## 5. 必要パッケージを入れる

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl ca-certificates
```

## 6. codexbotユーザーでCodex CLIを入れる

```bash
sudo -u codexbot -H bash -lc 'curl -fsSL https://chatgpt.com/codex/install.sh | sh'
```

PATHを確認する。

```bash
sudo -u codexbot -H bash -lc 'command -v codex && codex --version'
```

`codex`が見つからない場合は、インストール先を確認する。

```bash
sudo -u codexbot -H bash -lc 'find $HOME -type f -name codex -perm -111 2>/dev/null | head'
```

例: `/home/codexbot/.local/bin/codex` に入っている場合、以後のenvでは次を使う。

```text
CODEX_BIN=/home/codexbot/.local/bin/codex
```

## 7. codexbotユーザーでCodexへログインする

推奨はdevice auth。

```bash
sudo -u codexbot -H bash -lc 'codex login --device-auth'
```

表示されたURLとコードでChatGPTアカウントにログインする。

ログイン状態を確認する。

```bash
sudo -u codexbot -H bash -lc 'codex login status'
```

API keyをsystemd環境変数に常駐させる構成は推奨しない。Codex公式ドキュメント上、`CODEX_API_KEY`は`codex exec`の単発非対話実行用であり、リポジトリ制御下コードを実行する環境にjob-wideで置くべきではない。

## 8. 作業リポジトリを配置する

例として `main` というリポジトリを使う。

```bash
sudo -u codexbot -H bash -lc 'cd /home/codexbot/workspaces && git clone git@github.com:YOUR_ORG/YOUR_REPO.git main'
```

GitHub SSH keyが必要な場合は、`codexbot`専用keyを作る。

```bash
sudo -u codexbot -H bash -lc 'ssh-keygen -t ed25519 -C "codexbot@gx10" -f ~/.ssh/id_ed25519 -N ""'
sudo -u codexbot -H bash -lc 'cat ~/.ssh/id_ed25519.pub'
```

公開鍵をGitHubのDeploy keyまたは対象アカウントに登録する。

確認:

```bash
sudo -u codexbot -H bash -lc 'cd /home/codexbot/workspaces/main && git status'
```

## 9. Python bridgeを作成する

仮想環境を作る。

```bash
sudo -u codexbot -H bash -lc 'python3 -m venv /opt/telegram-codex-bridge/venv'
sudo -u codexbot -H bash -lc '/opt/telegram-codex-bridge/venv/bin/pip install --upgrade pip'
sudo -u codexbot -H bash -lc '/opt/telegram-codex-bridge/venv/bin/pip install "python-telegram-bot>=21.8,<23"'
```

bridge本体を作る。

```bash
sudo tee /opt/telegram-codex-bridge/bot.py >/dev/null <<'PY'
#!/usr/bin/env python3
import asyncio
import os
import re
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USERS = {
    int(x.strip())
    for x in os.environ.get("ALLOWED_TELEGRAM_USER_IDS", "").split(",")
    if x.strip()
}

WORKSPACE_ROOT = Path(os.environ.get("CODEX_WORKSPACE_ROOT", "/home/codexbot/workspaces")).resolve()
DEFAULT_REPO = os.environ.get("DEFAULT_REPO", "main")
CODEX_BIN = os.environ.get("CODEX_BIN", "codex")
CODEX_TIMEOUT_SECONDS = int(os.environ.get("CODEX_TIMEOUT_SECONDS", "1800"))
MAX_OUTPUT_CHARS = int(os.environ.get("MAX_OUTPUT_CHARS", "3500"))

ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
SAFE_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+$")

current_proc = None
current_desc = None


def user_id(update: Update) -> int | None:
    return update.effective_user.id if update.effective_user else None


def is_allowed(update: Update) -> bool:
    uid = user_id(update)
    return uid is not None and uid in ALLOWED_USERS


async def deny_if_needed(update: Update) -> bool:
    if is_allowed(update):
        return False
    uid = user_id(update)
    chat_id = update.effective_chat.id if update.effective_chat else None
    await update.effective_message.reply_text(
        "許可されていません。\n"
        f"user_id={uid}\nchat_id={chat_id}\n"
        "このuser_idをALLOWED_TELEGRAM_USER_IDSに追加してください。"
    )
    return True


def get_prompt(update: Update) -> str:
    text = update.effective_message.text or ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


def clean_output(s: str) -> str:
    s = ANSI_RE.sub("", s)
    s = s.replace("\r", "")
    return s.strip()


def clip(s: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(s) <= limit:
        return s
    head = s[: limit // 2]
    tail = s[-limit // 2 :]
    return head + "\n\n... [output truncated] ...\n\n" + tail


async def reply_long(update: Update, text: str) -> None:
    text = text or "完了しましたが、出力は空です。"
    text = clip(text, MAX_OUTPUT_CHARS)
    chunk_size = 3900
    for i in range(0, len(text), chunk_size):
        await update.effective_message.reply_text(text[i : i + chunk_size])


def repo_path(repo_name: str) -> Path:
    repo = repo_name or DEFAULT_REPO
    if not SAFE_REPO_RE.fullmatch(repo):
        raise ValueError("repo名に使える文字は英数字、dot、underscore、hyphenのみです。")
    path = (WORKSPACE_ROOT / repo).resolve()
    if path != WORKSPACE_ROOT and WORKSPACE_ROOT not in path.parents:
        raise ValueError("workspace root外は指定できません。")
    if not path.exists() or not path.is_dir():
        raise ValueError(f"repoが存在しません: {repo}")
    return path


def current_repo_name(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("repo", DEFAULT_REPO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Telegram Codex bridgeです。\n"
        "まず /whoami でuser_idを確認し、GX10側のALLOWLISTに登録してください。\n\n"
        "主要コマンド:\n"
        "/whoami\n"
        "/status\n"
        "/repos\n"
        "/repo main\n"
        "/readonly リポジトリ構造を要約して\n"
        "/run READMEを更新してセットアップ手順を追記して\n"
        "/stop"
    )


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = user_id(update)
    chat_id = update.effective_chat.id if update.effective_chat else None
    await update.effective_message.reply_text(
        f"user_id={uid}\nchat_id={chat_id}\nallowed={uid in ALLOWED_USERS if uid is not None else False}"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await deny_if_needed(update):
        return
    running = current_proc is not None and current_proc.returncode is None
    repo = current_repo_name(context)
    await update.effective_message.reply_text(
        "status\n"
        f"running={running}\n"
        f"job={current_desc}\n"
        f"repo={repo}\n"
        f"workspace_root={WORKSPACE_ROOT}\n"
        f"codex_bin={CODEX_BIN}"
    )


async def repos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await deny_if_needed(update):
        return
    items = []
    if WORKSPACE_ROOT.exists():
        for p in sorted(WORKSPACE_ROOT.iterdir()):
            if p.is_dir() and SAFE_REPO_RE.fullmatch(p.name):
                marker = " [git]" if (p / ".git").exists() else ""
                items.append(f"- {p.name}{marker}")
    await update.effective_message.reply_text("repos:\n" + ("\n".join(items) if items else "なし"))


async def repo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await deny_if_needed(update):
        return
    arg = get_prompt(update)
    if not arg:
        await update.effective_message.reply_text(f"current repo={current_repo_name(context)}")
        return
    try:
        path = repo_path(arg)
    except Exception as e:
        await update.effective_message.reply_text(f"repo指定エラー: {e}")
        return
    context.user_data["repo"] = arg
    await update.effective_message.reply_text(f"repo={arg}\npath={path}")


async def run_codex(update: Update, context: ContextTypes.DEFAULT_TYPE, sandbox: str) -> None:
    global current_proc, current_desc

    if await deny_if_needed(update):
        return

    if current_proc is not None and current_proc.returncode is None:
        await update.effective_message.reply_text(f"別ジョブが実行中です: {current_desc}")
        return

    prompt = get_prompt(update)
    if not prompt:
        await update.effective_message.reply_text("プロンプトが空です。例: /run READMEを改善して")
        return

    try:
        workdir = repo_path(current_repo_name(context))
    except Exception as e:
        await update.effective_message.reply_text(f"workspaceエラー: {e}")
        return

    current_desc = f"{sandbox} @ {workdir.name}: {prompt[:80]}"
    await update.effective_message.reply_text(f"Codex開始: {current_desc}")

    cmd = [
        CODEX_BIN,
        "exec",
        "-C",
        str(workdir),
        "--sandbox",
        sandbox,
        "--ask-for-approval",
        "never",
        "--color",
        "never",
        prompt,
    ]

    try:
        current_proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(workdir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )
        stdout_b, stderr_b = await asyncio.wait_for(
            current_proc.communicate(), timeout=CODEX_TIMEOUT_SECONDS
        )
        rc = current_proc.returncode
        stdout = clean_output(stdout_b.decode("utf-8", errors="replace"))
        stderr = clean_output(stderr_b.decode("utf-8", errors="replace"))

        if rc == 0:
            await reply_long(update, "Codex完了\n\n" + stdout)
        else:
            await reply_long(update, f"Codex失敗 rc={rc}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}")
    except asyncio.TimeoutError:
        if current_proc and current_proc.returncode is None:
            current_proc.kill()
            await current_proc.wait()
        await update.effective_message.reply_text(f"timeout: {CODEX_TIMEOUT_SECONDS}sで停止しました。")
    except Exception as e:
        await update.effective_message.reply_text(f"bridge error: {type(e).__name__}: {e}")
    finally:
        current_proc = None
        current_desc = None


async def run_write(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_codex(update, context, "workspace-write")


async def run_readonly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_codex(update, context, "read-only")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global current_proc, current_desc
    if await deny_if_needed(update):
        return
    if current_proc is None or current_proc.returncode is not None:
        await update.effective_message.reply_text("実行中ジョブはありません。")
        return
    desc = current_desc
    current_proc.terminate()
    try:
        await asyncio.wait_for(current_proc.wait(), timeout=10)
    except asyncio.TimeoutError:
        current_proc.kill()
        await current_proc.wait()
    await update.effective_message.reply_text(f"停止しました: {desc}")


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("repos", repos))
    app.add_handler(CommandHandler("repo", repo))
    app.add_handler(CommandHandler("readonly", run_readonly))
    app.add_handler(CommandHandler("run", run_write))
    app.add_handler(CommandHandler("stop", stop))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
PY

sudo chown codexbot:codexbot /opt/telegram-codex-bridge/bot.py
sudo chmod 750 /opt/telegram-codex-bridge/bot.py
```

## 10. 環境変数ファイルを作る

まず仮のallowlistなしで起動し、`/whoami`だけ使ってuser_idを確認する。

```bash
sudo tee /etc/telegram-codex-bridge/telegram-codex.env >/dev/null <<'ENV'
TELEGRAM_BOT_TOKEN=PASTE_YOUR_TELEGRAM_BOT_TOKEN
ALLOWED_TELEGRAM_USER_IDS=
CODEX_WORKSPACE_ROOT=/home/codexbot/workspaces
DEFAULT_REPO=main
CODEX_BIN=/home/codexbot/.local/bin/codex
CODEX_TIMEOUT_SECONDS=1800
MAX_OUTPUT_CHARS=3500
ENV

sudo chown root:codexbot /etc/telegram-codex-bridge/telegram-codex.env
sudo chmod 640 /etc/telegram-codex-bridge/telegram-codex.env
```

`CODEX_BIN`は環境に合わせて変更する。

確認:

```bash
sudo -u codexbot -H bash -lc 'source /etc/telegram-codex-bridge/telegram-codex.env && $CODEX_BIN --version'
```

## 11. systemd serviceを作る

```bash
sudo tee /etc/systemd/system/telegram-codex-bridge.service >/dev/null <<'SERVICE'
[Unit]
Description=Telegram to Codex Bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=codexbot
Group=codexbot
WorkingDirectory=/opt/telegram-codex-bridge
EnvironmentFile=/etc/telegram-codex-bridge/telegram-codex.env
ExecStart=/opt/telegram-codex-bridge/venv/bin/python /opt/telegram-codex-bridge/bot.py
Restart=on-failure
RestartSec=5

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=false
ReadWritePaths=/home/codexbot /opt/telegram-codex-bridge

[Install]
WantedBy=multi-user.target
SERVICE
```

有効化して起動する。

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now telegram-codex-bridge.service
sudo systemctl status telegram-codex-bridge.service --no-pager
```

ログ確認:

```bash
journalctl -u telegram-codex-bridge.service -f
```

## 12. Telegram user_idをallowlistに入れる

Telegramで作成したbotを開き、次を送る。

```text
/whoami
```

返ってきた `user_id` を控える。

例:

```text
user_id=123456789
chat_id=123456789
allowed=False
```

環境変数ファイルを編集する。

```bash
sudoedit /etc/telegram-codex-bridge/telegram-codex.env
```

変更:

```text
ALLOWED_TELEGRAM_USER_IDS=123456789
```

再起動する。

```bash
sudo systemctl restart telegram-codex-bridge.service
```

Telegramで確認する。

```text
/status
```

## 13. 動作確認

### read-only確認

Telegramから送る。

```text
/readonly このリポジトリの構成を短く要約して
```

期待:

- Codexがrepoを読む
- ファイル変更はしない
- 結果がTelegramへ返る

### workspace-write確認

```text
/run README.mdに「Telegram経由でCodexを実行する検証」セクションを追加して。変更内容を最後に要約して
```

GX10側で確認する。

```bash
sudo -u codexbot -H bash -lc 'cd /home/codexbot/workspaces/main && git status && git diff -- README.md'
```

必要なら通常のSSHまたはMac/WindowsのCodex Appからreviewしてcommitする。

## 14. 使い方

Telegram command:

```text
/whoami
/status
/repos
/repo main
/readonly 依存関係と起動方法を確認して
/run バグの原因を調査して修正案を実装して。テストも実行して
/stop
```

推奨運用:

1. まず `/readonly` で調査させる
2. 問題なければ `/run` で変更させる
3. 変更後はSSHまたはCodex Appで `git diff` を確認する
4. 自分でcommit/pushする

Telegramから自動commit/pushまではさせない方がよい。

## 15. セキュリティ設定の必須チェック

### bot token権限

```bash
sudo ls -l /etc/telegram-codex-bridge/telegram-codex.env
```

期待:

```text
-rw-r----- root codexbot ... telegram-codex.env
```

### codexbotにsudo権限がないこと

```bash
sudo -l -U codexbot
```

### systemd hardeningが効いていること

```bash
systemctl show telegram-codex-bridge.service \
  -p User -p Group -p NoNewPrivileges -p PrivateTmp -p ProtectSystem -p ProtectHome -p ReadWritePaths
```

### Codex dangerous modeを使っていないこと

bridge内で次が存在しないことを確認する。

```bash
grep -R "dangerously\|yolo\|danger-full-access" /opt/telegram-codex-bridge || true
```

出力なしが望ましい。

## 16. 外出先から使う場合

この構成はpollingなので、GX10側からTelegramへHTTPS outbound通信できればよい。

不要:

- 自宅ルーターのport forwarding
- webhook用の公開HTTPS endpoint
- app-serverの公開

必要:

- GX10が起動していること
- GX10がインターネットへ出られること
- systemd serviceが稼働していること

SSH保守用にTailscaleなどを入れるのは有効。ただし、Telegram bridge自体には必須ではない。

## 17. トラブルシュート

### botが返事しない

```bash
sudo systemctl status telegram-codex-bridge.service --no-pager
journalctl -u telegram-codex-bridge.service -n 100 --no-pager
```

確認項目:

- tokenが正しいか
- GX10が外向きHTTPS通信できるか
- `python-telegram-bot`が入っているか
- BotFatherでbotを削除・再発行していないか

### `/status`が「許可されていません」になる

```text
/whoami
```

で出る `user_id` を `ALLOWED_TELEGRAM_USER_IDS` に入れる。

複数人許可する場合:

```text
ALLOWED_TELEGRAM_USER_IDS=123456789,987654321
```

再起動:

```bash
sudo systemctl restart telegram-codex-bridge.service
```

### `codex: command not found`

`CODEX_BIN`を実パスにする。

```bash
sudo -u codexbot -H bash -lc 'find $HOME -type f -name codex -perm -111 2>/dev/null'
```

例:

```text
CODEX_BIN=/home/codexbot/.local/bin/codex
```

### Codex loginが切れている

```bash
sudo -u codexbot -H bash -lc '/home/codexbot/.local/bin/codex login status'
sudo -u codexbot -H bash -lc '/home/codexbot/.local/bin/codex login --device-auth'
```

### `/run`がtimeoutする

`CODEX_TIMEOUT_SECONDS`を延ばす。

```text
CODEX_TIMEOUT_SECONDS=3600
```

再起動:

```bash
sudo systemctl restart telegram-codex-bridge.service
```

### Telegram出力が途中で切れる

Telegramの単一メッセージ長制限を避けるため、bridgeは長文を切り詰める。
詳細ログが必要な場合は、Codexに「結果を `REPORT.md` に保存して」と指示し、SSHで確認する。

## 18. 改良案

優先度順:

1. job履歴をSQLiteに保存
2. `/diff` コマンド追加
3. `/gitstatus` コマンド追加
4. repoごとのallowlist
5. group chat禁止、private chatのみ許可
6. `/run`前に確認ボタンを出す
7. Docker/Podmanコンテナ内でCodexを実行
8. GitHub PR作成まで自動化。ただしpush権限管理が必要

## 19. 参考リンク

- OpenAI Codex CLI: https://developers.openai.com/codex/cli
- Codex CLI reference: https://developers.openai.com/codex/cli/reference
- Codex non-interactive mode: https://developers.openai.com/codex/noninteractive
- Codex approvals and security: https://developers.openai.com/codex/agent-approvals-security
- Codex environment variables: https://developers.openai.com/codex/environment-variables
- Codex remote connections: https://developers.openai.com/codex/remote-connections
- Telegram Bot API: https://core.telegram.org/bots/api
- python-telegram-bot Application docs: https://docs.python-telegram-bot.org/
