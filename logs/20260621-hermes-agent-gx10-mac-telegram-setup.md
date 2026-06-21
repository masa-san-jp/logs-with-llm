# Hermes Agent を GX10 と Mac に導入し、GX10 を Telegram 連携する手順

作成日: 2026-06-21  
対象: ASUS Ascent GX10 / NVIDIA DGX Spark 系の GB10 マシン、macOS 12 以降  
目的: Mac では通常利用・検証用に Hermes Agent を導入し、GX10 では Claude Code Channels と同じ感覚で Telegram から Hermes Agent を操作できる常時稼働構成にする。

---

## 1. 結論

推奨構成は次の通り。

| 役割 | 推奨配置 | 理由 |
|---|---|---|
| メインの常時稼働 Hermes Agent | GX10 | Ubuntu / DGX OS ベースで常時起動しやすく、Telegram Gateway を置きやすい |
| Telegram Bot | GX10 の Hermes Gateway に接続 | スマホから常時アクセスする入口にする |
| Mac 側 Hermes Agent | ローカル作業・検証・設定確認用 | デスクトップアプリまたは CLI で使う。Telegram 常時接続は原則 GX10 に集約 |
| Telegram Bot token | 1 bot token = 1 gateway instance | 同じ token を GX10 と Mac で同時に使うと polling conflict が起きやすい |

GX10 には `hermes gateway` または `hermes gateway start` を常駐させ、Telegram からメッセージを投げる。Claude Code Channels では「Claude Code の実行中セッションにチャネルプラグインがイベントを注入する」構成だが、Hermes Agent では「Hermes Gateway が Telegram などのメッセージング面を受け持ち、Hermes の会話・記憶・スキル・cron に接続する」構成になる。

---

## 2. 理解しておくべき背景情報

### 2.1 Hermes Agent とは

Hermes Agent は Nous Research の OSS エージェントで、CLI、Desktop、Messaging Gateway、記憶、スキル、cron、Web 検索、各種ツール接続を持つ。特徴は次の通り。

- 会話や作業履歴を記憶する。
- 成功した作業からスキルを作る。
- Telegram / Discord / Slack / WhatsApp / Signal / Email などの Gateway から使える。
- ローカルマシン、VPS、GPU マシン、Docker、SSH などの実行環境に置ける。
- モデルプロバイダを選べる。Nous Portal、OpenRouter、OpenAI、Anthropic、NVIDIA NIM、Hugging Face、独自 endpoint などを利用できる。

### 2.2 Claude Code Channels との違い

Claude Code Channels は Claude Code のチャネルプラグインを使い、Telegram / Discord / iMessage などから実行中の Claude Code セッションにメッセージを入れる方式。Claude Code が `--channels plugin:telegram@claude-plugins-official` のように起動している必要がある。

Hermes Agent は Hermes 自体に Messaging Gateway があり、`hermes gateway` または `hermes gateway start` で Telegram Bot を受ける。したがって、Claude Code Channels と同じ「スマホからローカル／常時稼働マシンのエージェントを操作する」体験は作れるが、内部構造は異なる。

| 観点 | Claude Code Channels | Hermes Agent Gateway |
|---|---|---|
| 起動単位 | Claude Code セッション | Hermes Gateway |
| Telegram 接続 | Claude plugin | Hermes built-in gateway |
| 設定場所 | `~/.claude/channels/...` など | `~/.hermes/.env` / `~/.hermes/config.yaml` |
| 認可 | pairing / allowlist | Telegram user ID allowlist |
| 常時稼働 | tmux / systemd 等で Claude を維持 | gateway service として維持しやすい |
| 記憶・スキル | Claude Code 側の文脈・プロジェクト依存 | Hermes の memory / skills / sessions が中心 |

### 2.3 GX10 で注意すべきこと

ここでいう GX10 は ASUS Ascent GX10 / NVIDIA DGX Spark 系の GB10 マシンを想定する。主な前提は次の通り。

- OS は Ubuntu Linux または NVIDIA DGX OS 系。
- CPU は ARM64 / aarch64。
- 常時稼働サーバー的に扱いやすい。
- Python / Node / ffmpeg / ripgrep などの依存は Hermes 公式 installer が導入する想定。
- ローカル LLM 実行も可能だが、Hermes の初期導入ではまず API 型モデルプロバイダで動作確認する方が失敗が少ない。

### 2.4 Telegram Bot の基本

Telegram 連携では BotFather で bot token を発行し、その token を Hermes Gateway に設定する。さらに、許可する Telegram user ID を `TELEGRAM_ALLOWED_USERS` に設定する。

重要な注意点:

- bot token は秘密情報。漏れたら BotFather の `/revoke` で再発行する。
- Telegram username ではなく、数値の user ID を使う。
- 同じ bot token を複数の gateway / bot process で同時に使わない。
- Group で使う場合、BotFather の privacy mode を無効化するか、bot を group admin にする。
- privacy mode を変えた場合、既存 group から bot を一度削除して再追加する。

---

## 3. 全体構成

```text
[iPhone / Telegram]
        |
        | Telegram Bot API
        v
[Hermes Gateway on GX10]
        |
        | Hermes session / memory / tools / model provider
        v
[Hermes Agent runtime on GX10]
        |
        +-- local shell / files / repo / scripts
        +-- web tools / model API / optional local model
        +-- scheduled tasks delivered back to Telegram

[Mac]
  +-- Hermes CLI / Desktop for local experiments
  +-- not using the same Telegram bot token simultaneously
```

---

## 4. 事前準備

### 4.1 必要なアカウント・情報

用意するもの:

1. GX10 にログインできる Linux ユーザー
2. Mac の管理者権限または通常ユーザー権限
3. Telegram アカウント
4. BotFather で作る Telegram bot token
5. 自分の Telegram numeric user ID
6. Hermes で使う LLM provider の API key

LLM provider は最初は次のどれかが簡単。

- Nous Portal
- OpenRouter
- OpenAI API
- Anthropic API

ローカル LLM を最初から Hermes に直結する構成も可能だが、GX10 の Telegram 化の第一段階では API provider で疎通確認し、その後にローカル推論へ寄せる方が切り分けしやすい。

### 4.2 GX10 で基本確認

GX10 でターミナルを開く。

```bash
uname -m
cat /etc/os-release
python3 --version || true
node --version || true
ffmpeg -version || true
```

期待値:

```text
aarch64
Ubuntu / NVIDIA DGX OS 系
```

OS 更新:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y curl git ca-certificates build-essential tmux jq
```

`tmux` は必須ではないが、初期テスト中に Gateway を落とさずログを見るために便利。

---

## 5. GX10 に Hermes Agent を導入する

### 5.1 公式 installer を実行

GX10 で次を実行する。

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

installer 後、shell 設定を読み直す。

```bash
source ~/.bashrc 2>/dev/null || true
source ~/.zshrc 2>/dev/null || true
```

確認:

```bash
which hermes
hermes --help
hermes doctor
```

`hermes` が見つからない場合:

```bash
echo $PATH
ls -la ~/.hermes
find ~/.hermes -maxdepth 3 -type f -name hermes 2>/dev/null
```

必要なら `~/.bashrc` に Hermes の PATH を追加する。installer が出したメッセージに従うのが優先。

### 5.2 初期セットアップ

最も簡単なのは full setup wizard。

```bash
hermes setup
```

Nous Portal を使う場合:

```bash
hermes setup --portal
```

モデルだけ個別に設定する場合:

```bash
hermes model
```

ツール設定を確認する場合:

```bash
hermes tools
```

診断:

```bash
hermes doctor
```

### 5.3 CLI で疎通確認

```bash
hermes
```

Hermes の対話画面で次を入力する。

```text
今日の作業用に、1行で自己紹介して
```

正常に返答すれば、Hermes 本体と model provider の最低限の接続は通っている。

---

## 6. Mac に Hermes Agent を導入する

Mac は CLI または Desktop のどちらでもよい。運用上は次の使い分けがよい。

- Mac: 手元の作業・UI・検証用
- GX10: 常時稼働・Telegram Gateway 用

### 6.1 CLI installer

macOS の Terminal で実行する。

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

shell 設定を読み直す。

```bash
source ~/.zshrc 2>/dev/null || true
source ~/.bashrc 2>/dev/null || true
```

確認:

```bash
which hermes
hermes --help
hermes doctor
```

初期設定:

```bash
hermes setup
# または
hermes setup --portal
```

モデル設定:

```bash
hermes model
```

起動:

```bash
hermes
```

### 6.2 Desktop app を使う場合

Hermes 公式サイトから macOS 版 Desktop app を入れる。CLI と Desktop は用途が重なるため、まずは CLI で疎通確認し、その後 Desktop を入れる方が問題切り分けがしやすい。

### 6.3 Mac では Telegram Gateway を原則起動しない

GX10 と Mac の両方で同じ Telegram bot token を使って Gateway を起動しない。Telegram の long polling は同一 bot token に対して複数 process が `getUpdates` を叩くと conflict になる。

Mac でも Telegram 連携を試したい場合は、次のいずれかにする。

- GX10 の Gateway を止めてから Mac で同じ bot token を使う。
- Mac 用に別の Telegram bot を BotFather で作る。
- Hermes の profile を分け、token も分ける。

---

## 7. Telegram Bot を作る

### 7.1 BotFather で bot token を発行

Telegram で `@BotFather` を開く。

1. `/newbot` を送る。
2. display name を入力する。例: `GX10 Hermes Agent`
3. username を入力する。必ず `bot` で終わる必要がある。例: `gx10_hermes_agent_bot`
4. BotFather が token を返す。

例:

```text
123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
```

この token は `.env` にだけ保存し、GitHub、メモ、Slack、スクショ共有に載せない。

### 7.2 Bot の説明・コマンドを設定

BotFather で任意設定を行う。

```text
/setdescription
```

例:

```text
GX10 上で動く個人用 Hermes Agent。許可ユーザーのみ利用可能。
```

```text
/setabouttext
```

例:

```text
Hermes Agent on GX10
```

```text
/setcommands
```

貼り付け例:

```text
help - Show help
new - Start a new conversation
status - Show session status
sethome - Set this chat as home channel
stop - Stop current task
model - Show or change model
```

### 7.3 Group で使う場合の privacy mode

DM だけで使うなら privacy mode はそのままでよい。

Group で普通のメッセージも読ませたい場合は、BotFather で privacy mode を off にする。

1. `@BotFather` に `/mybots`
2. 対象 bot を選択
3. `Bot Settings`
4. `Group Privacy`
5. `Turn off`

既に group に bot を入れていた場合、privacy mode 変更後に一度 group から bot を削除し、再追加する。

---

## 8. 自分の Telegram user ID を取得する

Telegram username ではなく、数値 ID が必要。

方法 1:

1. Telegram で `@userinfobot` を開く。
2. `/start` または任意メッセージを送る。
3. `Id: 123456789` のような数値を控える。

方法 2:

1. `@get_id_bot` を開く。
2. 表示される user ID を控える。

以後、この値を `TELEGRAM_ALLOWED_USERS` に設定する。

---

## 9. GX10 の Hermes Gateway に Telegram を設定する

### 9.1 推奨: interactive setup

GX10 で実行する。

```bash
hermes gateway setup
```

選択・入力するもの:

1. Platform: `Telegram`
2. Bot token: BotFather の token
3. Allowed user IDs: 自分の numeric user ID
4. 必要に応じて home channel / group 設定

設定後、確認する。

```bash
ls -la ~/.hermes
cat ~/.hermes/.env
```

`~/.hermes/.env` に最低限次が入っていればよい。

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
TELEGRAM_ALLOWED_USERS=123456789
```

複数ユーザーを許可する場合:

```bash
TELEGRAM_ALLOWED_USERS=123456789,987654321
```

### 9.2 手動設定

wizard を使わず直接設定する場合:

```bash
mkdir -p ~/.hermes
chmod 700 ~/.hermes
nano ~/.hermes/.env
```

以下を入れる。

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
TELEGRAM_ALLOWED_USERS=123456789
```

権限を絞る。

```bash
chmod 600 ~/.hermes/.env
```

### 9.3 Gateway を foreground で起動してテスト

まずは systemd 化せず foreground で起動する。

```bash
hermes gateway
```

別端末、またはスマホの Telegram から bot に DM を送る。

```text
ping. 1行で返事して
```

返答が来れば OK。

停止は `Ctrl+C`。

### 9.4 Gateway の managed command を確認

Hermes のバージョンによっては次が使える。

```bash
hermes gateway start
hermes gateway status
hermes gateway stop
hermes gateway restart
```

動く場合は、まずこれを使う。

```bash
hermes gateway start
hermes gateway status
```

ログ確認:

```bash
tail -n 200 ~/.hermes/logs/gateway.log
```

---

## 10. GX10 で Gateway を常時稼働させる

### 10.1 まずは tmux で簡易運用

初期検証中は tmux が簡単。

```bash
tmux new -s hermes-gateway
hermes gateway
```

切り離し:

```text
Ctrl+b → d
```

再接続:

```bash
tmux attach -t hermes-gateway
```

### 10.2 systemd user service で常時稼働

`hermes gateway start` が環境に合わない場合、systemd user service にする。

Hermes の絶対パスを確認する。

```bash
which hermes
```

例として `/home/masa/.local/bin/hermes` だったとする。実際の出力に置き換える。

service directory を作る。

```bash
mkdir -p ~/.config/systemd/user
```

service file を作る。

```bash
nano ~/.config/systemd/user/hermes-gateway.service
```

内容:

```ini
[Unit]
Description=Hermes Agent Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h
Environment=HOME=%h
ExecStart=/home/masa/.local/bin/hermes gateway
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

`ExecStart` は必ず自分の `which hermes` の結果に置き換える。

有効化:

```bash
systemctl --user daemon-reload
systemctl --user enable --now hermes-gateway.service
systemctl --user status hermes-gateway.service
```

ログ:

```bash
journalctl --user -u hermes-gateway.service -f
```

ログアウト後も user service を動かす場合:

```bash
sudo loginctl enable-linger "$USER"
```

再起動テスト:

```bash
sudo reboot
```

再起動後:

```bash
systemctl --user status hermes-gateway.service
journalctl --user -u hermes-gateway.service -n 100 --no-pager
```

Telegram にメッセージを送り、返答が来れば常時稼働化完了。

---

## 11. `/sethome` と cron 配信

Hermes Gateway は scheduled tasks / cron の結果を Telegram に届けられる。まず DM で bot に送る。

```text
/sethome
```

これで、その chat が home channel になる。

テスト例:

```text
明日の朝9時に、今日やるべきことを3つ思い出させて
```

または Hermes 側で cron / schedule 機能を使う場合も、結果の配信先が Telegram になる。

手動で `.env` に入れる場合:

```bash
TELEGRAM_HOME_CHANNEL=123456789
TELEGRAM_HOME_CHANNEL_NAME="Masa DM"
```

Group の chat ID は通常 `-100...` のような負数になる。

---

## 12. Group で使う場合の推奨設定

Group で GX10 Hermes Agent を使う場合は、誤爆を防ぐため「bot は group の会話を見られるが、mention された時だけ反応する」構成がよい。

`~/.hermes/config.yaml` に次のような設定を入れる構成が考えられる。

```yaml
telegram:
  allowed_chats:
    - "-1001234567890"
  group_allowed_chats:
    - "-1001234567890"
  require_mention: true
  observe_unmentioned_group_messages: true
```

環境変数で設定する場合:

```bash
TELEGRAM_ALLOWED_CHATS=-1001234567890
TELEGRAM_GROUP_ALLOWED_CHATS=-1001234567890
TELEGRAM_OBSERVE_UNMENTIONED_GROUP_MESSAGES=true
```

この場合も、Telegram が通常メッセージを bot に届ける必要があるため、privacy mode off または bot admin 化が必要。

---

## 13. ファイル生成・添付送信の注意

Hermes Gateway は agent の返答に `MEDIA:/path/to/file` が含まれると、対応プラットフォームでファイル添付として送れる。

例:

```text
MEDIA:/home/masa/.hermes/cache/documents/report.md
```

Docker backend を使う場合、agent が container 内に作ったファイルを Gateway が読めないことがある。Gateway は host 側 process なので、host から読める path を使う。

推奨:

```yaml
terminal:
  backend: docker
  docker_volumes:
    - "/home/masa/.hermes/cache/documents:/output"
```

agent には container 内で `/output/report.md` に書かせ、最終応答では host path を指定する。

```text
MEDIA:/home/masa/.hermes/cache/documents/report.md
```

---

## 14. セキュリティ設計

### 14.1 最低限の守り

必須:

```bash
chmod 700 ~/.hermes
chmod 600 ~/.hermes/.env
```

`.env` を Git 管理しない。

```bash
cat >> ~/.gitignore_global <<'EOF_GITIGNORE'
.env
*.env
.hermes/.env
EOF_GITIGNORE

git config --global core.excludesfile ~/.gitignore_global
```

### 14.2 Bot token が漏れた場合

1. Telegram で `@BotFather` を開く。
2. `/revoke` を送る。
3. 対象 bot を選ぶ。
4. 新 token を取得する。
5. GX10 の `~/.hermes/.env` を更新する。
6. Gateway を再起動する。

```bash
nano ~/.hermes/.env
systemctl --user restart hermes-gateway.service
# または
hermes gateway restart
```

### 14.3 allowed users を必ず設定する

`TELEGRAM_ALLOWED_USERS` を空にしない。個人運用なら自分の user ID だけにする。

```bash
TELEGRAM_ALLOWED_USERS=123456789
```

### 14.4 エージェントへの権限付与を絞る

GX10 上の Hermes は shell / file / network / model provider にアクセスできる。Telegram から操作できるということは、スマホから GX10 上の作業を起動できるということでもある。

運用上の推奨:

- 秘密情報を置くディレクトリを明確に分ける。
- Hermes 用 Linux user を分けることを検討する。
- sudo 権限を与えすぎない。
- 本番鍵、顧客データ、秘密鍵を agent 作業ディレクトリに置かない。
- group では mention 必須にする。
- Telegram bot を public group に入れない。

---

## 15. Mac 側での運用パターン

### 15.1 Mac は Hermes の作業端末として使う

Mac の Terminal で:

```bash
hermes
```

ローカル repo で使う場合:

```bash
cd ~/path/to/project
hermes
```

### 15.2 GX10 に SSH して操作する

Mac から GX10 に SSH できるようにする。

GX10 の IP 確認:

```bash
hostname -I
```

Mac から:

```bash
ssh masa@<GX10_IP>
```

SSH config 例:

```bash
nano ~/.ssh/config
```

```sshconfig
Host gx10
  HostName <GX10_IP>
  User masa
  ServerAliveInterval 30
  ServerAliveCountMax 3
```

接続:

```bash
ssh gx10
```

Gateway ログを見る:

```bash
ssh gx10 'tail -n 100 ~/.hermes/logs/gateway.log'
```

systemd user service の状態を見る:

```bash
ssh gx10 'systemctl --user status hermes-gateway.service --no-pager'
```

---

## 16. 更新手順

GX10 と Mac の両方で定期的に実施する。

```bash
hermes update
hermes doctor
```

Gateway 運用中の GX10 では更新後に再起動する。

```bash
hermes gateway restart
```

systemd user service の場合:

```bash
systemctl --user restart hermes-gateway.service
```

---

## 17. 動作確認チェックリスト

### 17.1 GX10 本体

```bash
which hermes
hermes --help
hermes doctor
hermes model
```

### 17.2 Telegram 設定

```bash
grep -E 'TELEGRAM_BOT_TOKEN|TELEGRAM_ALLOWED_USERS' ~/.hermes/.env
```

token を画面共有する場合は伏せる。

### 17.3 Gateway foreground

```bash
hermes gateway
```

Telegram で bot に送る。

```text
/status
```

または:

```text
GX10で動いているか、1行で返事して
```

### 17.4 Gateway service

```bash
systemctl --user status hermes-gateway.service
journalctl --user -u hermes-gateway.service -n 100 --no-pager
```

### 17.5 再起動後

```bash
sudo reboot
```

再起動後、Telegram bot に送信。

```text
再起動後も動いている？
```

返答が来れば完了。

---

## 18. トラブルシューティング

### 18.1 bot が全く返答しない

確認:

```bash
hermes gateway
```

または:

```bash
tail -n 200 ~/.hermes/logs/gateway.log
journalctl --user -u hermes-gateway.service -n 100 --no-pager
```

見る点:

- `TELEGRAM_BOT_TOKEN` が正しいか。
- Gateway が起動しているか。
- GX10 からインターネットに出られるか。
- 同じ bot token を Mac や別 process で使っていないか。

### 18.2 `unauthorized` と出る

`TELEGRAM_ALLOWED_USERS` の値が自分の numeric user ID と違う。

確認:

```bash
grep TELEGRAM_ALLOWED_USERS ~/.hermes/.env
```

Telegram で `@userinfobot` を再確認し、修正する。

```bash
nano ~/.hermes/.env
hermes gateway restart
# または
systemctl --user restart hermes-gateway.service
```

### 18.3 Group では反応しないが DM では動く

原因候補:

- BotFather の privacy mode が on。
- bot が group admin ではない。
- privacy mode 変更後に bot を remove / re-add していない。
- `allowed_chats` に group chat ID が入っていない。
- `require_mention: true` なのに mention していない。

対処:

1. BotFather で privacy mode off。
2. bot を group から削除。
3. bot を group に再追加。
4. 必要なら admin にする。
5. `@bot_username` を付けて送る。

### 18.4 `409 Conflict: terminated by other getUpdates request`

同じ bot token を複数 process が使っている可能性が高い。

確認:

```bash
ps aux | grep -i hermes | grep -v grep
systemctl --user status hermes-gateway.service --no-pager
```

Mac 側で Gateway を起動していないか確認する。

対処:

```bash
hermes gateway stop || true
systemctl --user stop hermes-gateway.service || true
pkill -f 'hermes gateway' || true
```

GX10 で 1 instance だけ起動する。

```bash
systemctl --user start hermes-gateway.service
```

それでも直らない場合:

1. BotFather で token を revoke。
2. 新 token を `.env` に設定。
3. Gateway を再起動。

### 18.5 `hermes` command not found

shell の PATH が更新されていない。

```bash
source ~/.bashrc 2>/dev/null || true
source ~/.zshrc 2>/dev/null || true
which hermes
```

installer の出力に従って PATH を追加する。

### 18.6 model provider error

確認:

```bash
hermes model
hermes doctor
cat ~/.hermes/.env
```

API key、provider、model name を確認する。まず CLI の `hermes` で会話できることを確認し、その後 Telegram Gateway を試す。

### 18.7 Telegram からファイル添付が送れない

`MEDIA:/path/to/file` の path が Gateway process から読めるか確認する。

```bash
ls -la /path/to/file
```

Docker backend の container 内 path を指定していないか確認する。

---

## 19. 推奨ディレクトリ構成

```text
~/.hermes/
  .env                  # API keys, Telegram token, allowed users
  config.yaml           # Hermes config
  logs/
    gateway.log
  cache/
    documents/          # Telegram に添付する生成物置き場
  hermes-agent/          # installer が作る managed checkout の可能性
```

作業 repo は別に置く。

```text
~/work/
  project-a/
  project-b/
```

Hermes に触らせる対象を明確にする。

---

## 20. 最小実行コマンドまとめ

### GX10

```bash
sudo apt update
sudo apt install -y curl git ca-certificates build-essential tmux jq
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc 2>/dev/null || true
hermes setup
hermes doctor
hermes gateway setup
hermes gateway
```

問題なければ常駐化。

```bash
which hermes
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/hermes-gateway.service
systemctl --user daemon-reload
systemctl --user enable --now hermes-gateway.service
sudo loginctl enable-linger "$USER"
systemctl --user status hermes-gateway.service
```

### Mac

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.zshrc 2>/dev/null || true
hermes setup
hermes doctor
hermes
```

Mac で同じ Telegram bot token の Gateway は起動しない。

---

## 21. 運用方針

最初の安定構成:

1. GX10 に Hermes CLI を入れる。
2. GX10 で API provider を設定する。
3. GX10 の CLI で返答確認する。
4. BotFather で Telegram bot を作る。
5. `TELEGRAM_BOT_TOKEN` と `TELEGRAM_ALLOWED_USERS` を設定する。
6. `hermes gateway` を foreground 起動して DM で疎通確認する。
7. `/sethome` を送る。
8. `systemd --user` で常時稼働化する。
9. Mac には Hermes を入れるが、Telegram Gateway は動かさない。
10. 必要になったら Mac 用に別 bot を作る。

この順で進めると、問題が出た時に「Hermes 本体」「model provider」「Telegram token」「user ID allowlist」「Gateway 常駐化」のどこで失敗しているか切り分けやすい。

---

## 22. 参考情報

- Hermes Agent GitHub: https://github.com/NousResearch/hermes-agent
- Hermes Agent 公式サイト: https://hermes-agent.nousresearch.com/
- Hermes Telegram setup: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/telegram.md
- Hermes Team Telegram Assistant guide: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/guides/team-telegram-assistant.md
- Claude Code Channels docs: https://code.claude.com/docs/ja/channels
- ASUS Ascent GX10: https://www.asus.com/networking-iot-servers/desktop-ai-supercomputer/ultra-small-ai-supercomputers/asus-ascent-gx10/
- NVIDIA DGX Spark: https://www.nvidia.com/en-us/products/workstations/dgx-spark/
