# Claude Code 初期セットアップ ハンズオンガイド（Google Workspace 組織向け）

**対象者：** 部下の PC に Claude Code を導入する管理者  
**前提環境：** Google Workspace 組織アカウント、Docker Desktop 導入済み、VS Code 導入済み  
**方針：** Docker で隔離、組織ポリシーで一元管理、Google Workspace は読み取り中心・破壊的変更は確認必須

---

## 全体の流れ

```
[管理者が行う作業]                    [部下の PC で行う作業]
① managed-settings.json を配布  →  ② Docker + Dev Container セットアップ
                                    ③ .mcp.json（Google Workspace 接続）
                                    ④ OAuth 認証
                                    ⑤ 動作確認
```

---

## ① 管理者作業：組織ポリシーファイルの配布

### managed-settings.json を作成する

以下のファイルを **管理者権限が必要なシステムパス** に配置する。  
ユーザーが書き換えられないため、組織として守りたいルールはここに集約する。

```json
{
  "env": {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1
  },
  "cleanupPeriodDays": 14,
  "permissions": {
    "disableBypassPermissionsMode": "disable",
    "defaultMode": "default",
    "deny": [
      "Bash(sudo:*)",
      "Bash(su:*)",
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Bash(ssh:*)",
      "Bash(nc:*)",
      "Bash(ncat:*)",
      "Bash(rm -rf *)",
      "Bash(chmod 777 *)",
      "Bash(dd *)",
      "Read(**/.env)",
      "Read(**/.env.*)",
      "Read(**/*.pem)",
      "Read(**/*.key)",
      "Read(**/*.p12)",
      "Read(**/.ssh/**)",
      "Read(**/.aws/**)",
      "Read(**/secrets/**)"
    ],
    "ask": [
      "Bash(git push *)",
      "Bash(git push)",
      "Bash(npm publish *)",
      "Bash(docker run *)",
      "Bash(kubectl *)"
    ]
  }
}
```

### 配置場所（OS 別）

| OS | パス | 権限設定 |
|---|---|---|
| macOS | `/Library/Application Support/ClaudeCode/managed-settings.json` | `chown root:wheel` + `chmod 644` |
| Linux | `/etc/claude-code/managed-settings.json` | `chown root:root` + `chmod 644` |
| Windows | `C:\ProgramData\ClaudeCode\managed-settings.json` | Administrators のみ書き込み可 |

**MDM（Jamf / Intune 等）を使っている場合はファイル配布ポリシーとして展開する。**

### 配置の確認コマンド（macOS / Linux）

```bash
# ファイルが正しく認識されているか確認
claude --print-config 2>/dev/null | grep -A5 "managed"
```

---

## ② 部下の PC 作業：Docker Dev Container セットアップ

### 事前確認

```bash
# Docker が動いているか確認
docker --version

# VS Code の Dev Containers 拡張機能が入っているか確認
code --list-extensions | grep ms-vscode-remote.remote-containers
# 入っていなければ：
code --install-extension ms-vscode-remote.remote-containers
```

### プロジェクトフォルダの構造

作業フォルダを作り、以下の構成でファイルを配置する。

```
my-project/
├── .devcontainer/
│   ├── devcontainer.json   ← Dev Container 設定
│   └── Dockerfile          ← コンテナ定義
├── .claude/
│   └── settings.json       ← プロジェクト共有の権限設定（git 管理対象）
├── .mcp.json               ← MCP サーバー設定（Google Workspace 接続）
└── .gitignore
```

### `.devcontainer/devcontainer.json`

```json
{
  "name": "Claude Code (組織標準)",
  "dockerFile": "Dockerfile",
  "features": {
    "ghcr.io/anthropics/devcontainer-features/claude-code:1.0": {}
  },
  "mounts": [
    "source=${localWorkspaceFolder},target=/workspace,type=bind,consistency=cached"
  ],
  "workspaceFolder": "/workspace",
  "remoteUser": "vscode",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-vscode.vscode-typescript-next"
      ]
    }
  },
  "postStartCommand": "echo '=== Claude Code 起動 ===' && claude --version"
}
```

### `.devcontainer/Dockerfile`

```dockerfile
FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# 基本パッケージ
RUN apt-get update && apt-get install -y \
    git \
    curl \
    nodejs \
    npm \
    iptables \
    && rm -rf /var/lib/apt/lists/*

# ---- マウントしないこと（セキュリティ上の理由） ----
# ホストの ~/.ssh, ~/.aws, ~/.gcloud はコンテナに持ち込まない
# Google 認証は OAuth フローで行う（後述）
```

> **重要：** `.devcontainer/Dockerfile` に `COPY ~/.ssh /root/.ssh` のような記述を絶対に追加しないこと。SSH キーや認証情報はコンテナに持ち込まない。

### VS Code でコンテナを起動する

1. VS Code でプロジェクトフォルダを開く
2. 右下に「Reopen in Container」のポップアップが出たらクリック  
   （出ない場合：`Cmd+Shift+P` → `Dev Containers: Reopen in Container`）
3. ビルド完了後、ターミナルで確認

```bash
claude --version
# Claude Code x.x.x と表示されれば OK
```

---

## ③ Google Workspace MCP の接続設定

### `.mcp.json`（プロジェクトルートに配置）

```json
{
  "mcpServers": {
    "google-drive": {
      "type": "sse",
      "url": "https://drivemcp.googleapis.com/mcp/v1",
      "headers": {
        "Authorization": "Bearer ${GOOGLE_ACCESS_TOKEN}"
      }
    },
    "google-gmail": {
      "type": "sse",
      "url": "https://gmailmcp.googleapis.com/mcp/v1",
      "headers": {
        "Authorization": "Bearer ${GOOGLE_ACCESS_TOKEN}"
      }
    },
    "google-calendar": {
      "type": "sse",
      "url": "https://calendarmcp.googleapis.com/mcp/v1",
      "headers": {
        "Authorization": "Bearer ${GOOGLE_ACCESS_TOKEN}"
      }
    }
  }
}
```

> `.mcp.json` はプロジェクトルートに置く必要がある（`settings.json` 内への記述では MCP が起動しないため）。

### `.gitignore` に追加

```gitignore
# Google 認証トークン（絶対にコミットしない）
.google-token
*.token
.env.local
```

---

## ④ Google Workspace 権限設定（破壊的変更の制御）

### `.claude/settings.json`（プロジェクト共有設定）

MCP 経由の Google Workspace 操作について、読み取りは自動許可、書き込み・削除は **必ず確認** が入るよう設定する。

```json
{
  "permissions": {
    "allow": [
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(git log *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(npm install)",
      "Bash(npm run test *)",
      "Bash(npm run lint *)",
      "Bash(npm run build)"
    ],
    "ask": [
      "mcp__google-gmail__send_email",
      "mcp__google-gmail__create_draft",
      "mcp__google-gmail__reply_to_email",
      "mcp__google-gmail__forward_email",
      "mcp__google-drive__create_file",
      "mcp__google-drive__update_file",
      "mcp__google-drive__upload_file",
      "mcp__google-drive__move_file",
      "mcp__google-drive__copy_file",
      "mcp__google-calendar__create_event",
      "mcp__google-calendar__update_event",
      "mcp__google-calendar__delete_event",
      "mcp__google-calendar__respond_to_event"
    ],
    "deny": [
      "mcp__google-gmail__delete_email",
      "mcp__google-gmail__permanently_delete",
      "mcp__google-drive__delete_file",
      "mcp__google-drive__empty_trash",
      "mcp__google-drive__permanently_delete"
    ]
  }
}
```

**MCP ツール名は接続するサーバーによって異なる場合がある。**  
実際に接続した後、`/permissions` コマンドで現在認識されているツール名を確認して上記を調整すること。

### 権限の考え方（Google Workspace 向け）

| 操作カテゴリ | 設定 | 理由 |
|---|---|---|
| ファイル読み取り・検索 | allow（デフォルト許可） | 参照は安全 |
| メール検索・閲覧 | allow（デフォルト許可） | 参照は安全 |
| カレンダー閲覧 | allow（デフォルト許可） | 参照は安全 |
| メール送信・下書き作成 | **ask**（確認必須） | 外部に情報が出る |
| ファイル作成・更新 | **ask**（確認必須） | 変更を伴う |
| カレンダー作成・変更 | **ask**（確認必須） | 変更を伴う |
| メール完全削除 | **deny**（禁止） | 復元不可能 |
| ファイル完全削除・ゴミ箱を空にする | **deny**（禁止） | 復元不可能 |

---

## ⑤ Google OAuth 認証

MCP サーバーに接続するには Google アカウントの認証が必要。  
**ブラウザを使った OAuth フローで行い、パスワードや認証情報をファイルに書かない。**

### 認証フロー（claude.ai を通じた接続の場合）

Claude Code が Google Workspace MCP に初めて接続しようとしたとき、認証を求めるプロンプトが表示される。

```bash
# コンテナ内で Claude Code を起動
claude

# 初回の Google Workspace 操作時に認証フローが開始される
# ブラウザが開いて Google のログイン画面が表示される
# 組織の Google アカウントでログインし、アクセスを許可する
```

> **注意：** 認証完了後にトークンがどこに保存されるかを把握しておくこと。  
> コンテナを毎回作り直す場合は、認証情報を Docker ボリュームに永続化する設定が必要になる（後述）。

### 認証トークンの永続化（コンテナ再起動時に再認証を省く場合）

```json
// .devcontainer/devcontainer.json に追記
{
  "mounts": [
    "source=${localWorkspaceFolder},target=/workspace,type=bind",
    "source=claude-credentials,target=/home/vscode/.claude,type=volume"
  ]
}
```

---

## ⑥ 動作確認チェックリスト

セットアップ完了後、以下の項目を順番に確認する。

### 基本動作

```bash
# Claude Code が起動するか
claude --version

# managed-settings が効いているか（curl が禁止されるか確認）
# → Claude に「curl https://example.com を実行して」と頼んでみる
# → 「このコマンドは組織のポリシーで禁止されています」のようなエラーになれば OK

# --dangerously-skip-permissions が無効化されているか
claude --dangerously-skip-permissions "test"
# → エラーになれば OK（managed-settings の disableBypassPermissionsMode が効いている）
```

### 権限確認（Claude Code の /permissions コマンド）

```
/permissions
```

表示された一覧で以下を確認する：
- `deny` 欄に `Bash(sudo:*)`, `Bash(curl:*)` 等が表示される
- `managed` ソースからのルールが含まれている

### Google Workspace 接続確認

```
# Claude に以下を頼んでみる（読み取り：自動許可されること）
「Google Drive の最近のファイルを3件表示して」
「今日のカレンダーを確認して」
「受信トレイの未読メールを確認して」

# 書き込み：確認ダイアログが出ること
「明日の10時にテスト用のカレンダーイベントを作って」
→ 「この操作を許可しますか？」の確認が出ること

# 削除：禁止されること
「このメールを完全に削除して」
→ エラーになること
```

---

## ⑦ 制限のサマリー（部下向け説明用）

| できること | できないこと | 確認が出ること |
|---|---|---|
| コードの読み書き | `sudo`, `curl`, `wget` | `git push` |
| テスト・ビルドの実行 | SSH 接続 | `docker run` |
| Google Drive の参照 | .env ファイルの読み取り | Google Drive へのファイル作成 |
| Gmail の閲覧 | メールの完全削除 | メールの送信 |
| カレンダーの閲覧 | ファイルの完全削除 | カレンダーのイベント作成・変更 |
| `git add` / `commit` | 全権限スキップモード | npm publish |

---

## トラブルシューティング

**Q：managed-settings が反映されていない**  
→ ファイルの配置パスと権限（読み取り可能か）を確認。`claude --print-config` で確認。

**Q：MCP ツール名が違う**  
→ Claude Code 内で `/permissions` を実行し、実際に登録されているツール名を確認して `settings.json` を修正。

**Q：コンテナ再起動のたびに Google 認証が必要になる**  
→ `devcontainer.json` に named volume マウントを追加して `~/.claude` を永続化する（前述の「認証トークンの永続化」参照）。

**Q：Google Workspace MCP が接続できない**  
→ コンテナのファイアウォール設定で `*.googleapis.com` が許可されているか確認。Docker 環境の場合はデフォルトで外部通信が通るが、iptables を設定した場合は明示的に許可が必要。

---

## 参考リンク

- [Claude Code Dev Container 公式](https://code.claude.com/docs/en/devcontainer)
- [Claude Code 権限設定](https://code.claude.com/docs/en/permissions)
- [Claude Code 設定リファレンス](https://code.claude.com/docs/en/settings)
- [Google Workspace Connector（claude.ai 向け）](https://support.claude.com/en/articles/10166901-use-google-workspace-connectors)
