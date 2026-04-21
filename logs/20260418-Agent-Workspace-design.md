# エージェント作業環境 設計ドキュメント

作成日: 2025-04-18

-----

## 1. 要件定義

### やりたいこと

- 自宅のUbuntuマシンでエージェント（Claude Code）を常時稼働させる
- 職場PC・私用Mac・iPhone・iPadの4デバイスから遠隔操作したい
- 職場データは職場マシンの外に出したくない
- どのデバイスから作業を再開しても状況を引き継げるようにしたい

### 保有リソース

- 自宅: Ubuntu常時稼働マシン
- 職場: PC（Google Workspace環境）
- 私用: Mac、iPhone、iPad、Google Workspace、GitHub

-----

## 2. 意思決定ログ

### 2-1. 遠隔接続方式

**選択肢**

|方式               |メリット                 |デメリット             |
|-----------------|---------------------|------------------|
|Tailscale        |ルーター設定不要・ゼロトラスト・全OS対応|無料枠3台まで           |
|Cloudflare Tunnel|無料・独自ドメイン可           |独自ドメインが必要         |
|ポートフォワーディング      |シンプル                 |セキュリティ対策が必要・固定IP推奨|

**決定: Tailscale + SSH**

- ルーター設定不要でNAT越えできる
- 全デバイス対応
- ゼロトラスト設計でセキュア

### 2-2. セッション維持方式

**決定: tmux**

- SSH切断後もClaude Codeのセッションが生き続ける
- 複数ウィンドウ・ペイン管理が可能
- どのデバイスから接続しても同じセッションにアタッチできる

### 2-3. SSH鍵管理

**決定: 秘密鍵は各デバイスのみ保管 / 公開鍵・SSH Configは私用GitHubプライベートリポジトリで管理**

|情報          |管理場所                           |
|------------|-------------------------------|
|秘密鍵         |各デバイスのみ（絶対に外部に出さない）            |
|公開鍵         |私用GitHub privateリポジトリ（dotfiles）|
|SSH Config  |私用GitHub privateリポジトリ（dotfiles）|
|TailscaleのIP|Tailscale管理画面で完結               |

**やってはいけないこと**

- 秘密鍵をGoogle Driveに置く
- 秘密鍵をGitHubにpush（publicはもちろん、privateでも非推奨）
- 職場Google Workspaceに私用の鍵情報を置く（会社管理下のため）

### 2-4. 作業データの扱い

**前提: 職場GitHubなし・職場データの持ち出し不可**

**決定: エージェントを役割別に分散配置**

|エージェント      |稼働場所    |扱うデータ                 |
|------------|--------|----------------------|
|秘書エージェント    |自宅Ubuntu|Googleカレンダー・Gmail・チャット|
|調査エージェント    |自宅Ubuntu|Web・ドキュメント生成・情報整理     |
|オペレーターエージェント|職場マシン   |職場データ（外に出さない）         |

**根拠**

- 秘書・調査は職場データを直接触らないため自宅Ubuntuで完結できる
- 職場データを触る操作は職場マシン上のエージェントが担い、データは職場外に出ない

### 2-5. 作業状況の引き継ぎ方式

**決定: handoff.mdを私用GitHubプライベートリポジトリで管理**

- エージェントが作業終了・セッション開始時に自動でhandoff.mdを読み書き
- どのマシンから入っても同じファイルを参照して状況を把握できる
- タスクの「状態」のみを記録し、職場の「データ」は含めない

-----

## 3. 最終アーキテクチャ

```
職場PC / Mac / iPhone / iPad
        ↓ Tailscale VPN
   自宅Ubuntu（SSH + tmux）
   ├── 秘書エージェント（Claude Code）
   │   MCP: Gmail / Googleカレンダー / チャット
   └── 調査エージェント（Claude Code）
       MCP: Web検索 / Googleドライブ（私用）
            ↕ handoff.md の読み書き
   私用GitHub privateリポジトリ（agent-context）

職場マシン
└── オペレーターエージェント（Claude Code）
    職場データのみ取り扱い
    ↕ handoff.mdを読んで状況把握・書いて引き継ぎ
```

-----

## 4. 実装手順

### Step 1: Tailscaleセットアップ

```bash
# 自宅Ubuntuで実行
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4  # 割り当てられたIPを確認
```

各デバイスにもTailscaleをインストールして同一アカウントでログイン。

### Step 2: tmuxセットアップ

```bash
sudo apt install tmux

cat << 'EOF' >> ~/.tmux.conf
set -g mouse on
set -g history-limit 50000
EOF
```

### Step 3: Claude Codeセットアップ

```bash
# Node.jsインストール
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# Claude Codeインストール
npm install -g @anthropic/claude-code
claude  # 認証
```

### Step 4: SSH鍵認証の設定

```bash
# 各クライアントで鍵生成
ssh-keygen -t ed25519 -C "device-name"

# 公開鍵をUbuntuに登録
ssh-copy-id ユーザー名@<tailscale-ip>

# パスワード認証を無効化
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### Step 5: 各デバイスからの接続

```bash
# SSH接続してtmuxにアタッチ
ssh ユーザー名@<tailscale-ip>
tmux attach -t claude || tmux new -s claude
```

|デバイス         |SSHクライアント                    |
|-------------|-----------------------------|
|職場PC（Windows）|Windows Terminal / PowerShell|
|Mac          |ターミナル（標準）                    |
|iPhone / iPad|Termius（App Store・無料）        |

### Step 6: dotfilesリポジトリの作成（私用GitHub）

```
dotfiles（private）
└── .ssh/
    ├── config          # 接続先設定
    └── authorized_keys # 公開鍵一覧（参照用）
```

```
# ~/.ssh/config の例
Host home-ubuntu
  HostName 100.xx.xx.xx
  User yourname
  IdentityFile ~/.ssh/id_ed25519
  ServerAliveInterval 60
```

### Step 7: agent-contextリポジトリの作成（私用GitHub）

```
agent-context（private）
├── handoff.md            # 引き継ぎ用サマリー（エージェントが自動更新）
├── current-tasks.md      # 現在進行中タスク
└── daily-log/
    └── YYYY-MM-DD.md     # 日別作業ログ
```

**handoff.mdの構造**

```markdown
# 作業引き継ぎ - YYYY-MM-DD HH:MM更新

## 進行中タスク
- [ ] タスク名（担当エージェント・進捗）

## 直近の決定事項
- 決定内容

## 次にやること
- アクション

## 各エージェントの状態
- 秘書: アイドル / 稼働中
- 調査: アイドル / ○○について調査中（進捗XX%）
- オペレーター: 停止中 / 稼働中
```

### Step 8: MCPの接続設定（自宅Ubuntu）

```json
// ~/.claude/claude.json
{
  "mcpServers": {
    "google-calendar": { ... },
    "gmail": { ... },
    "google-drive": { ... },
    "github": {
      "repo": "agent-context（privateリポジトリ）"
    }
  }
}
```

-----

## 5. 運用フロー

### セッション開始時

1. SSHで自宅Ubuntuに接続
1. tmuxにアタッチ
1. エージェントに `handoff.md を読んで状況を説明して` と指示

### セッション終了時

1. エージェントに `今日の作業をhandoff.mdに記録して` と指示
1. エージェントがhandoff.mdをpush
1. SSHをデタッチ（tmuxセッションは生き続ける）

### 職場マシンでオペレーター作業が必要なとき

1. handoff.mdを読んでコンテキストを把握
1. 職場マシン上でClaude Codeを起動して操作
1. 完了後handoff.mdに結果を記録

-----

## 6. 残課題

- [ ] 私用GitHubのプライベートリポジトリ（agent-context）の実際の構築
- [ ] MCP接続設定の詳細（Gmail・カレンダー・GitHub）
- [ ] 職場マシンへのClaude Codeインストールと権限確認
- [ ] Terminusへの鍵登録（iPhone / iPad）
- [ ] handoff.mdの自動更新をエージェントに習慣化させるプロンプト設計