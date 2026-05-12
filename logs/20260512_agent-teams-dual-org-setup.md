# Agent-Teams 2組織対応セットアップ

リポジトリ: https://github.com/masa-san-jp/Agent-Teams

-----

## 現状整理

|要素                    |状態           |対応    |
|----------------------|-------------|------|
|エージェント設定（スキル・ルール・委譲設計）|GitHub 同期済み ✓|なし    |
|各マシンは組織固定             |設計済み ✓       |なし    |
|認証情報の gitignore       |未設定 ⚠️        |要追加   |
|VISIBILITY.md の内容     |TODO のまま ⚠️   |要記入   |
|gws 認証（各マシン）          |未実施          |初回のみ実行|

-----

## 変更1：`.gitignore` に認証情報パスを追加

```gitignore
# 既存
.DS_Store
Thumbs.db
__pycache__/
*.pyc
**/.claude/sensitive-patterns.local.txt

# 追加：認証情報・端末固有ファイル
.config/gws/
**/*.credentials.json
**/token.json
**/client_secret.json
**/freee_token.json
**/.env.local
```

**確認：** 追加後に `visibility-check.sh` を実行してセクション2がOKになること。

```bash
bash .claude/scripts/visibility-check.sh
```

-----

## 変更2：`VISIBILITY.md` の TODO を埋める

VISIBILITY.md の TODO セクションを以下に置き換える。

### 公開対象（GitHub に同期される）

- エージェント定義（`agents/` 以下の CLAUDE.md・スキルファイル）
- チーム共通設定（`README.md`、`VISIBILITY.md`）
- スクリプト雛形（`.claude/scripts/`）

### 非公開対象（gitignore で除外）

- gws 認証情報（`~/.config/gws/`）
- freee トークン（`**/freee_token.json`）
- OAuth クライアント情報（`**/client_secret.json`、`**/token.json`）
- 端末固有の環境変数（`**/.env.local`）
- Aiko ローカルインスタンス（`agents/Aiko*/`）

### 関連リポジトリ

|リポ                                 |用途              |
|-----------------------------------|----------------|
|`github.com/masa-san-jp/Agent-Aiko`|Aiko 人格システム（配布版）|

-----

## 各マシンの初回セットアップ（一度だけ）

### 前提：全マシン共通

```bash
# リポジトリをクローン
git clone git@github.com:masa-san-jp/Agent-Teams.git
cd Agent-Teams

# gws CLI をインストール（未インストールの場合）
npm install -g @googleworkspace/cli
```

### ラップトップA（組織A）

```bash
# 組織Aの gws 認証
gws auth login --scopes drive,gmail,calendar,chat
# → ~/.config/gws/credentials.json に保存（gitignore 済み）

# freee 認証（CFO エージェントを使う場合）
# agents/cfo-fpa/skills/freee_setup を参照
```

### ラップトップB・デスクトップ（組織B）

```bash
# 組織Bの gws 認証
gws auth login --scopes drive,gmail,calendar,chat

# freee 認証（CFO エージェントを使う場合）
# agents/cfo-fpa/skills/freee_setup を参照
```

### スマートフォン

Claude.ai アプリで使用する前提。端末での設定は不要。

- 組織A で使うとき → 組織A の Google アカウントで Claude.ai にログイン
- 組織B で使うとき → 組織B の Google アカウントに切り替え

Google Drive MCP・Gmail MCP・Calendar MCP は Claude.ai のコネクター設定でアカウントに紐づく。エージェントの設定（スキル・ルール）は GitHub リポジトリ側で管理されているため、スマートフォン側では管理不要。

-----

## 日常運用

### エージェント設定の更新

```bash
# どのマシンでも
git pull
```

認証情報はローカルに残り続ける。エージェントの設定だけが同期される。

### 認証の更新（トークン期限切れ時）

```bash
gws auth login --scopes drive,gmail,calendar,chat
```

### 整合性チェック（push 前の習慣に）

```bash
bash .claude/scripts/visibility-check.sh
```

-----

## 検証チェックリスト

### リポジトリ側

- [ ] `.gitignore` に認証情報パスを追加済み
- [ ] `VISIBILITY.md` の TODO を埋めた
- [ ] `bash .claude/scripts/visibility-check.sh` → すべて OK
- [ ] `git ls-files | grep -E "(credentials|token|client_secret|\.env)"` → 出力なし

### 各マシン

- [ ] `gws drive files list --params '{"pageSize": 1}'` → 正しい組織のファイルが返る
- [ ] `gws calendar +agenda` → 正しい組織のカレンダーが返る
- [ ] 誤った組織のファイルが見えていないことを目視確認

### スマートフォン

- [ ] 組織A の Google アカウントで Claude.ai にログイン → Drive MCP が組織A を参照
- [ ] 組織B に切り替え → Drive MCP が組織B を参照