# ASUS GX10 Codex SSH セットアップ手順書

作成日: 2026-06-17  
対象: ASUS Ascent GX10 / Ubuntu Linux / ARM64 / Codex CLI / Codex App SSH Remote

---

## 1. 結論

ASUS GX10をCodex用のリモート開発ホストとして使う場合、最も確実な構成は次の通り。

```text
ChatGPT mobile app
        │
        ▼
Mac または Windows の公式 Codex App
        │ SSH
        ▼
ASUS GX10: Ubuntu Linux + OpenSSH Server + Codex CLI + 開発リポジトリ
```

重要点:

- GX10上に公式Codex Appを直接入れる構成は採用しない。
- GX10にはCodex CLIを入れる。
- 公式Codex AppはMacまたはWindowsに入れる。
- Codex AppからGX10へSSH接続し、GX10上のファイルシステムとshellでCodex threadを走らせる。
- スマホ操作を使う場合も、スマホはGX10へ直接つながるのではなく、Mac/WindowsのCodex App hostに接続する。

---

## 2. 前提

### 2.1 ハードウェア/OS前提

ASUS Ascent GX10は、ASUS公式仕様上、OSがUbuntu Linux、CPUがARM v9.2-A CPU (GB10)の構成。

GX10側で確認する。

```bash
uname -m
cat /etc/os-release
hostnamectl
```

期待値:

```text
uname -m: aarch64
OS: Ubuntu Linux または DGX OS / Ubuntu base
```

### 2.2 クライアント前提

以下のどちらかを用意する。

- Mac: 公式Codex Appをインストール
- Windows: 公式Codex Appをインストール

Linuxデスクトップ上の非公式Codex App移植は、本手順の本線では使わない。

### 2.3 アカウント前提

- Codex利用権のあるChatGPTアカウントまたはOpenAI API key
- Mac/Windows Codex AppとChatGPT mobile appでは、同じChatGPT account/workspaceを使う
- GX10上のCodex CLIは、最初に対話ログインして認証を完了する

---

## 3. 変数を決める

以降のコマンドでは、次の値を置き換える。

| 変数 | 例 | 説明 |
|---|---|---|
| `<GX10_USER>` | `codex` | GX10上の作業用Linuxユーザー |
| `<GX10_HOSTNAME>` | `gx10` | GX10のhostname |
| `<GX10_IP>` | `192.168.1.50` | LAN内IPまたはTailscale IP |
| `<CLIENT_IP>` | `192.168.1.20` | Mac/Windows側IP |
| `<SSH_ALIAS>` | `gx10-codex` | クライアント側SSH configのHost名 |
| `<PROJECT_DIR>` | `/home/codex/work/myrepo` | Codexで開くリモートプロジェクト |

推奨:

- `<GX10_USER>` は `codex`
- `<SSH_ALIAS>` は `gx10-codex`
- 外出先から使う場合は、グローバルIPへのport forwardではなくTailscale等のVPN/mesh networkを使う

---

## 4. GX10側: 基本セットアップ

GX10のローカル端末、または既に安全に入れるSSHセッションで実行する。

```bash
sudo apt update
sudo apt install -y \
  ca-certificates \
  curl \
  git \
  openssh-server \
  build-essential \
  ufw

sudo systemctl enable --now ssh
systemctl status ssh --no-pager
```

hostnameを固定する。

```bash
sudo hostnamectl set-hostname gx10
hostnamectl
```

IPを確認する。

```bash
ip -4 addr
```

ルーター側でDHCP reservationを設定し、GX10のLAN IPを固定する。OS側で固定IPを直接書くより、家庭内運用ではルーター側予約の方が安全。

---

## 5. GX10側: Codex専用ユーザー作成

既存ユーザーで運用してもよいが、Codexに作業させる範囲を分離するため、専用ユーザーを推奨する。

```bash
sudo adduser codex
sudo mkdir -p /home/codex/work
sudo chown -R codex:codex /home/codex/work
```

sudo権限は原則付けない。ビルドやパッケージ導入が頻繁に必要で、リスクを許容する場合だけ追加する。

```bash
# 必要な場合のみ
sudo usermod -aG sudo codex
```

---

## 6. クライアント側: SSH key作成

MacならTerminal、WindowsならPowerShellで実行する。

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -C "gx10-codex-$(date +%Y%m%d)" -f ~/.ssh/gx10_codex_ed25519
```

passphraseは設定推奨。完全自動化したい場合のみ空にする。

---

## 7. クライアント側: 公開鍵をGX10へ登録

`ssh-copy-id`が使える場合:

```bash
ssh-copy-id -i ~/.ssh/gx10_codex_ed25519.pub codex@<GX10_IP>
```

`ssh-copy-id`がない場合:

```bash
cat ~/.ssh/gx10_codex_ed25519.pub | ssh codex@<GX10_IP> \
  'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

接続確認:

```bash
ssh -i ~/.ssh/gx10_codex_ed25519 codex@<GX10_IP> 'whoami; hostname; uname -m'
```

期待値:

```text
codex
gx10
aarch64
```

この確認が通るまで、SSH password loginを無効化しない。

---

## 8. GX10側: SSH serverの安全設定

鍵認証が通ることを確認してから実行する。

```bash
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d%H%M%S)
sudo install -d -m 0755 /etc/ssh/sshd_config.d

cat <<'EOF' | sudo tee /etc/ssh/sshd_config.d/90-codex-hardening.conf
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
X11Forwarding no
EOF

sudo sshd -t
sudo systemctl reload ssh
```

別ターミナルから再確認する。

```bash
ssh -i ~/.ssh/gx10_codex_ed25519 codex@<GX10_IP> 'echo SSH_OK'
```

期待値:

```text
SSH_OK
```

任意で、SSH可能ユーザーを絞る。複数の管理ユーザーがいる場合は、誤って自分を締め出さないように含める。

```bash
# 例: codex と masa のみSSH許可
cat <<'EOF' | sudo tee /etc/ssh/sshd_config.d/91-allow-users.conf
AllowUsers codex masa
EOF

sudo sshd -t
sudo systemctl reload ssh
```

---

## 9. GX10側: Firewall設定

### 9.1 LAN内だけで使う場合

`<CLIENT_IP>`からだけSSHを許可する。

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from <CLIENT_IP> to any port 22 proto tcp
sudo ufw enable
sudo ufw status verbose
```

複数端末から使う場合は、家庭内CIDRで許可する。

```bash
sudo ufw allow from 192.168.1.0/24 to any port 22 proto tcp
```

### 9.2 Tailscale経由で使う場合

Tailscale interfaceからのSSHだけを許可する。

```bash
sudo ufw allow in on tailscale0 to any port 22 proto tcp
sudo ufw status verbose
```

注意:

- ルーターでTCP/22をインターネット公開しない。
- Codex app-server transportを直接公開しない。
- 外出先から使う場合はVPN/mesh networkを使う。

---

## 10. 任意: Tailscale導入

外出先から確実に使うなら、Tailscaleを推奨する。

GX10側:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

表示されたURLを開いて認証する。

確認:

```bash
tailscale ip -4
tailscale status
```

Mac/Windows側にもTailscaleを入れ、同じtailnetに参加させる。

SSH configでは、`HostName`にTailscale IPまたはMagicDNS名を使う。

```sshconfig
Host gx10-codex
    HostName <GX10_TAILSCALE_IP_OR_MAGICDNS_NAME>
    User codex
    IdentityFile ~/.ssh/gx10_codex_ed25519
    IdentitiesOnly yes
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

---

## 11. GX10側: Codex CLIインストール

`codex`ユーザーでログインしてから実行する。

```bash
su - codex
```

公式インストーラーを使う。

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

PATHを確認する。

```bash
command -v codex
codex --version
```

`command -v codex`が空の場合、よくあるインストール先をPATHに追加する。

```bash
cat <<'EOF' >> ~/.profile

# Codex CLI
export PATH="$HOME/.local/bin:$HOME/bin:$PATH"
EOF

. ~/.profile
command -v codex
codex --version
```

Codex AppがSSH越しにremote Codex app serverを起動する際、remote userのlogin shell上で`codex`コマンドがPATHに見えている必要がある。したがって、`~/.profile`にPATHを入れておく。

初回ログイン:

```bash
codex
```

画面の指示に従い、ChatGPTアカウントまたはAPI keyで認証する。

---

## 12. GX10側: プロジェクト配置

例:

```bash
su - codex
mkdir -p ~/work
cd ~/work

git clone <YOUR_REPOSITORY_URL>
cd <YOUR_REPOSITORY_NAME>
```

GitHub SSH keyを別途使う場合は、GX10上の`codex`ユーザーにもGitHub用keyを設定する。

```bash
ssh-keygen -t ed25519 -C "gx10-github-$(date +%Y%m%d)" -f ~/.ssh/github_ed25519
cat ~/.ssh/github_ed25519.pub
```

GitHubに公開鍵を登録後、`~/.ssh/config`に追記する。

```sshconfig
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_ed25519
    IdentitiesOnly yes
```

確認:

```bash
ssh -T git@github.com
```

---

## 13. クライアント側: SSH config作成

### 13.1 Mac

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/config
```

以下を記入する。

```sshconfig
Host gx10-codex
    HostName <GX10_IP_OR_TAILSCALE_NAME>
    User codex
    IdentityFile ~/.ssh/gx10_codex_ed25519
    IdentitiesOnly yes
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

権限調整:

```bash
chmod 600 ~/.ssh/config
chmod 600 ~/.ssh/gx10_codex_ed25519
```

確認:

```bash
ssh gx10-codex 'whoami; hostname; command -v codex; codex --version'
```

### 13.2 Windows PowerShell

```powershell
New-Item -ItemType Directory -Force $env:USERPROFILE\.ssh
notepad $env:USERPROFILE\.ssh\config
```

以下を記入する。

```sshconfig
Host gx10-codex
    HostName <GX10_IP_OR_TAILSCALE_NAME>
    User codex
    IdentityFile ~/.ssh/gx10_codex_ed25519
    IdentitiesOnly yes
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

確認:

```powershell
ssh gx10-codex "whoami; hostname; command -v codex; codex --version"
```

Windowsでkey passphrase入力が面倒な場合:

```powershell
Get-Service ssh-agent | Set-Service -StartupType Automatic
Start-Service ssh-agent
ssh-add $env:USERPROFILE\.ssh\gx10_codex_ed25519
```

---

## 14. Mac/Windows側: 公式Codex App導入

1. 公式Codex AppをMacまたはWindowsへインストールする。
2. ChatGPTアカウントでサインインする。
3. ローカルプロジェクトを一度開き、Codex Appの基本動作を確認する。
4. `ssh gx10-codex`が通ることを確認する。

Codex App公式対応はmacOS/Windows。GX10上に公式Codex Appを直接入れる手順ではない。

---

## 15. Codex AppからGX10 SSH hostを追加

Mac/WindowsのCodex Appで実施する。

1. Codex Appを開く。
2. `Settings` > `Connections`を開く。
3. SSH host一覧に`gx10-codex`が見えることを確認する。
   - 見えない場合、`~/.ssh/config`または`%USERPROFILE%\.ssh\config`のHost名、権限、改行を確認する。
4. `gx10-codex`を有効化または追加する。
5. Remote project folderとして次を選ぶ。

```text
/home/codex/work/<YOUR_REPOSITORY_NAME>
```

6. 簡単なthreadを実行する。

例:

```text
このリポジトリの構成を確認して、主要なディレクトリとテスト実行方法を要約して。
```

成功条件:

- CodexがGX10上のプロジェクトファイルを読める
- CodexがGX10上で`pwd`、`ls`、テストコマンド等を実行できる
- approval requestがCodex Appに出る

---

## 16. ChatGPT mobile appから操作する場合

重要: mobile setupはCodex CLIやIDE extensionからは開始できない。Mac/WindowsのCodex App hostから開始する。

手順:

1. Mac/WindowsのCodex Appを起動する。
2. 同じChatGPT account/workspaceでサインインしていることを確認する。
3. Mac/Windowsがsleepしない設定にする。
4. Codex App sidebarで`Set up Codex mobile`を選ぶ。
5. 表示されたQR codeをスマホで読み取る。
6. ChatGPT mobile app上で同じaccount/workspaceを確認し、MFA/SSO/passkeyを完了する。
7. mobile appのCodex画面にhostが表示されることを確認する。
8. GX10のremote project threadを開き、follow-up、approval、diff reviewを試す。

運用上の注意:

- スマホはGX10へ直接SSHしない。
- スマホはMac/WindowsのCodex App hostを操作する。
- Mac/WindowsのCodex App hostがsleep/offlineだと、mobile側から操作できない。
- GX10がsleep/offlineだと、SSH remote sessionが切れる。

---

## 17. 動作確認チェックリスト

### 17.1 GX10本体

```bash
uname -m
systemctl is-active ssh
command -v codex
codex --version
```

期待値:

```text
aarch64
active
/path/to/codex
codex-cli x.y.z
```

### 17.2 クライアントからSSH

```bash
ssh gx10-codex 'whoami; hostname; pwd; command -v codex; codex --version'
```

期待値:

```text
codex
gx10
/home/codex
/path/to/codex
codex-cli x.y.z
```

### 17.3 Codex AppからRemote project

Codex AppでGX10 remote projectを開き、次を依頼する。

```text
pwd、uname -m、git statusを実行して、結果を要約して。
```

期待値:

- `pwd`がGX10上のproject directory
- `uname -m`が`aarch64`
- `git status`が対象repoの状態を返す

### 17.4 Mobile操作

スマホから同じthreadにfollow-upを送る。

```text
READMEを読んで、セットアップに必要なコマンドだけ抽出して。
```

期待値:

- スマホ側から送った指示がMac/Windows Codex App host経由で処理される
- 必要なapprovalがスマホまたはhost側に表示される

---

## 18. トラブルシューティング

### 18.1 Codex AppにSSH hostが出ない

確認:

```bash
cat ~/.ssh/config
ssh gx10-codex
```

対処:

- `Host gx10-codex`のような具体的Host aliasを使う
- `Host *`だけ、wildcardだけの定義にしない
- `IdentityFile`のpathを確認する
- Windowsでは`%USERPROFILE%\.ssh\config`に置く
- Codex Appを再起動する

### 18.2 SSHは通るがCodex App remoteが失敗する

原因候補:

- GX10のlogin shellで`codex`がPATHにない
- `codex`の初回認証が完了していない
- remote project folderの権限がない

確認:

```bash
ssh gx10-codex 'echo $SHELL; echo $PATH; command -v codex; codex --version'
```

対処:

```bash
ssh gx10-codex
cat <<'EOF' >> ~/.profile
export PATH="$HOME/.local/bin:$HOME/bin:$PATH"
EOF
. ~/.profile
codex
```

### 18.3 PasswordAuthenticationを切った後に入れない

ローカル画面/キーボードでGX10にログインし、設定を戻す。

```bash
sudo rm /etc/ssh/sshd_config.d/90-codex-hardening.conf
sudo sshd -t
sudo systemctl reload ssh
```

またはbackupから戻す。

```bash
ls -1 /etc/ssh/sshd_config.bak.*
sudo cp /etc/ssh/sshd_config.bak.<TIMESTAMP> /etc/ssh/sshd_config
sudo sshd -t
sudo systemctl reload ssh
```

### 18.4 UFWで締め出した

GX10のローカル画面から実行する。

```bash
sudo ufw status numbered
sudo ufw disable
```

必要なSSH allow ruleを入れてから再有効化する。

```bash
sudo ufw allow from <CLIENT_IP> to any port 22 proto tcp
sudo ufw enable
```

### 18.5 外出先から接続できない

推奨確認順:

```bash
tailscale status
tailscale ip -4
ssh gx10-codex
```

確認点:

- GX10とクライアントが同じtailnetにいる
- GX10のTailscale device keyがexpireしていない
- `HostName`がTailscale IPまたはMagicDNS名になっている
- UFWで`tailscale0`からのSSHを許可している

### 18.6 Mobileにhostが出ない

確認点:

- Mac/WindowsのCodex Appが起動中
- `Allow other devices to connect`相当の設定が有効
- Mac/Windowsとスマホが同じChatGPT account/workspace
- ChatGPT mobile appが最新版
- workspace管理下の場合、Remote Control accessが有効
- Mac/Windowsがsleepしていない

---

## 19. 非公式Linux Codex Desktopについて

非公式のLinux Codex Desktop wrapperは存在するが、本手順の本線では使わない。

理由:

- 公式Codex AppはmacOS/Windows対応で、Linuxは公式配布対象外。
- GX10はARM64 Linuxであり、Electron/GUI/patch/packaging周りの不確定要素が増える。
- Codex remote SSHの本来の設計は、公式Codex App hostからSSH host上のprojectを扱う構成で足りる。

検証目的で試す場合は、メイン環境とは別ユーザーまたは別snapshotで実施する。

---

## 20. 運用ルール

推奨ルール:

- GX10のSSHは鍵認証のみ。
- root loginは禁止。
- password loginは禁止。
- internetへのTCP/22 port forwardは禁止。
- 外出先アクセスはTailscale等のVPN/mesh network経由。
- Codex用ユーザーは原則sudoなし。
- Codex作業対象は`/home/codex/work`配下に限定。
- 重要repoではCodex変更を必ずdiff reviewしてからcommitする。
- 秘密情報 `.env`, credentials, private keys をrepoに置かない。

---

## 21. 最短コマンドまとめ

### GX10

```bash
sudo apt update
sudo apt install -y ca-certificates curl git openssh-server build-essential ufw
sudo systemctl enable --now ssh
sudo hostnamectl set-hostname gx10
sudo adduser codex
sudo mkdir -p /home/codex/work
sudo chown -R codex:codex /home/codex/work
```

### クライアント

```bash
ssh-keygen -t ed25519 -C "gx10-codex-$(date +%Y%m%d)" -f ~/.ssh/gx10_codex_ed25519
ssh-copy-id -i ~/.ssh/gx10_codex_ed25519.pub codex@<GX10_IP>
```

`~/.ssh/config`:

```sshconfig
Host gx10-codex
    HostName <GX10_IP_OR_TAILSCALE_NAME>
    User codex
    IdentityFile ~/.ssh/gx10_codex_ed25519
    IdentitiesOnly yes
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

### GX10: SSH hardening

```bash
cat <<'EOF' | sudo tee /etc/ssh/sshd_config.d/90-codex-hardening.conf
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
X11Forwarding no
EOF
sudo sshd -t
sudo systemctl reload ssh
```

### GX10: Codex CLI

```bash
su - codex
curl -fsSL https://chatgpt.com/codex/install.sh | sh
cat <<'EOF' >> ~/.profile
export PATH="$HOME/.local/bin:$HOME/bin:$PATH"
EOF
. ~/.profile
codex --version
codex
```

### Codex App

```text
Settings > Connections > SSH host: gx10-codex > Project folder: /home/codex/work/<repo>
```

---

## 22. 参考情報

- OpenAI Codex App: https://developers.openai.com/codex/app
- OpenAI Codex CLI: https://developers.openai.com/codex/cli
- OpenAI Codex remote connections: https://developers.openai.com/codex/remote-connections
- OpenAI Codex GitHub: https://github.com/openai/codex
- ASUS Ascent GX10 specs: https://www.asus.com/networking-iot-servers/desktop-ai-supercomputer/ultra-small-ai-supercomputers/asus-ascent-gx10/techspec/
- Ubuntu OpenSSH server documentation: https://ubuntu.com/server/docs/how-to/security/openssh-server/
- Tailscale Linux install: https://tailscale.com/docs/install/linux
