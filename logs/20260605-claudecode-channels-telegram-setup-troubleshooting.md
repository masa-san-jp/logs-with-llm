# Claude Code Channels（Telegram）セットアップ対応記録

- 日付：2026-06-05
- 対象：Claude Code v2.1.163 / macOS（Apple Silicon）
- 目的：Claude Code Channels の Telegram プラグインを導入し、スマホから Claude Code セッションを操作できるようにする

---

## 最終結果

Telegram から Claude Code セッションへのメッセージ送受信が正常に動作することを確認。

---

## 発生した問題と対応

### 問題1：Telegram Bot からペアリングコードが返ってこない

**原因**  
`--channels` フラグを付けずに Claude Code を起動していた。Channels が有効になっていない状態だった。

**対応**  
以下のコマンドで再起動。

```bash
claude --channels plugin:telegram@claude-plugins-official
```

---

### 問題2：MCP に `plugin:telegram:telegram · ✘ failed` が表示される

**診断コマンド**

```
/doctor
/mcp
```

**出力されたエラー**

```
plugin:telegram:telegram: failed — Skipping connection (recent failure cached; retries automatically in 15 min)
```

再試行後：

```
plugin:telegram:telegram: ENOENT
```

**原因の調査手順**

1. Bun の PATH 確認

```bash
which bun
bun --version
```

→ 別ターミナルでは認識されるが、Claude Code 起動時のサブプロセスでは見つからない状態だった。

2. プラグインの MCP 起動設定を確認

```bash
cat ~/.claude/plugins/cache/claude-plugins-official/telegram/<バージョン>/.mcp.json
```

```json
{
  "mcpServers": {
    "telegram": {
      "command": "bun",
      "args": ["run", "--cwd", "${CLAUDE_PLUGIN_ROOT}", "--shell=bun", "--silent", "start"]
    }
  }
}
```

**根本原因**  
`"command": "bun"` が相対パス指定のため、Claude Code がサブプロセス起動時に bun の実行ファイルを見つけられなかった。

**対応**

```bash
sudo mkdir -p /usr/local/bin
sudo ln -sf ~/.bun/bin/bun /usr/local/bin/bun
```

備考：Apple Silicon Mac では `/usr/local/bin/` が初期状態で存在しないケースがあるため、`mkdir -p` で作成してからリンクを張る。

---

### 問題3：修正後も `/mcp` に `plugin:telegram:telegram` が表示されない

**原因**  
プラグインインストール時に誤って project scope を選択していた。その後のアンインストール時に「disable just for you」を選択した結果、`settings.local.json` に `false` が書き込まれていた。

**確認コマンド**

```bash
cat .claude/settings.local.json
```

**出力（該当箇所）**

```json
"enabledPlugins": {
  "telegram@claude-plugins-official": false
}
```

**対応**  
`false` を `true` に修正。

```json
"enabledPlugins": {
  "telegram@claude-plugins-official": true
}
```

---

## 正常動作確認

- `/mcp` にて `plugin:telegram:telegram · ✔ connected · 4 tools` を確認
- Telegram Bot に DM を送信 → ペアリングコードが返ってきたことを確認
- `/telegram:access pair <コード>` でペアリング完了
- `/telegram:access policy allowlist` でアクセス制限を設定
- Telegram から `Hi` を送信 → Claude Code が返信することを確認

---

## 設定ファイルの場所

| ファイル | 用途 |
|---|---|
| `~/.claude/plugins/installed_plugins.json` | インストール済みプラグイン一覧 |
| `~/.claude/plugins/cache/claude-plugins-official/telegram/<バージョン>/.mcp.json` | MCPサーバー起動設定 |
| `~/.claude/channels/telegram/.env` | Bot トークン（環境変数） |
| `~/.claude/channels/telegram/access.json` | 許可済み送信者・ポリシー設定 |
| `.claude/settings.local.json` | ローカルスコープのプラグイン有効/無効設定 |

---

## 別マシンへの展開手順

1. Claude Code・Bun をインストール
2. `/usr/local/bin/bun` へのシンボリックリンクを作成（上記と同じ手順）
3. プラグインを **user scope** でインストール
4. Bot トークンを設定（既存の Bot をそのまま使用可能）
5. 再ペアリング、またはペアリング済みの設定ディレクトリを転送

```bash
# 設定ディレクトリの転送（転送元マシンで実行）
scp -r ~/.claude/channels/telegram/ <転送先ホスト>:~/.claude/channels/telegram/
```

---

## 教訓

- プラグインインストール時のスコープ選択は **user scope** を選ぶ。Telegram は個人の連絡先に紐づくため project scope には不向き。
- Apple Silicon Mac では `/usr/local/bin/` が存在しない場合があるため、Bun インストール直後にシンボリックリンクを張る手順を標準化する。
- `--channels` フラグは毎回の起動コマンドに含める必要がある。エイリアス化を推奨。

```bash
# ~/.zshrc に追加推奨
alias claude-tg='claude --channels plugin:telegram@claude-plugins-official'
```

追記

# Claude Code Channels（Telegram）セットアップ対応記録

- 日付：2026-06-05
- 対象：Claude Code v2.1.163 / macOS（Apple Silicon）
- 目的：Claude Code Channels の Telegram プラグインを導入し、スマホから Claude Code セッションを操作できるようにする

---

## 最終結果

Telegram から Claude Code セッションへのメッセージ送受信が正常に動作することを確認。

---

## 発生した問題と対応

### 問題1：Telegram Bot からペアリングコードが返ってこない

**原因**  
`--channels` フラグを付けずに Claude Code を起動していた。Channels が有効になっていない状態だった。

**対応**  
以下のコマンドで再起動。

```bash
claude --channels plugin:telegram@claude-plugins-official
```

---

### 問題2：MCP に `plugin:telegram:telegram · ✘ failed` が表示される

**診断コマンド**

```
/doctor
/mcp
```

**出力されたエラー**

```
plugin:telegram:telegram: failed — Skipping connection (recent failure cached; retries automatically in 15 min)
```

再試行後：

```
plugin:telegram:telegram: ENOENT
```

**原因の調査手順**

1. Bun の PATH 確認

```bash
which bun
bun --version
```

→ 別ターミナルでは認識されるが、Claude Code 起動時のサブプロセスでは見つからない状態だった。

2. プラグインの MCP 起動設定を確認

```bash
cat ~/.claude/plugins/cache/claude-plugins-official/telegram/<バージョン>/.mcp.json
```

```json
{
  "mcpServers": {
    "telegram": {
      "command": "bun",
      "args": ["run", "--cwd", "${CLAUDE_PLUGIN_ROOT}", "--shell=bun", "--silent", "start"]
    }
  }
}
```

**根本原因**  
`"command": "bun"` が相対パス指定のため、Claude Code がサブプロセス起動時に bun の実行ファイルを見つけられなかった。

**対応**

```bash
sudo mkdir -p /usr/local/bin
sudo ln -sf ~/.bun/bin/bun /usr/local/bin/bun
```

備考：Apple Silicon Mac では `/usr/local/bin/` が初期状態で存在しないケースがあるため、`mkdir -p` で作成してからリンクを張る。

---

### 問題3：修正後も `/mcp` に `plugin:telegram:telegram` が表示されない

**原因**  
プラグインインストール時に誤って project scope を選択していた。その後のアンインストール時に「disable just for you」を選択した結果、`settings.local.json` に `false` が書き込まれていた。

**確認コマンド**

```bash
cat .claude/settings.local.json
```

**出力（該当箇所）**

```json
"enabledPlugins": {
  "telegram@claude-plugins-official": false
}
```

**対応**  
`false` を `true` に修正。

```json
"enabledPlugins": {
  "telegram@claude-plugins-official": true
}
```

---

### 問題4：別ディレクトリから起動すると `plugin:telegram:telegram · ✘ failed` になる

**症状**  
問題2・3を解決後、別のディレクトリから起動すると再び MCP が failed になる。

**原因**  
2つの問題が重なっていた。

1. **Bun のパス問題**（問題2と同根）  
   シンボリックリンクが特定のセッションでのみ有効だった。

2. **Bot トークンのスコープ問題**  
   `/telegram:configure` 実行時、トークンがプロジェクトディレクトリ内の `.claude/channels/telegram/.env` に書き込まれていた。そのため、そのプロジェクトディレクトリからの起動時のみトークンが読み込まれ、別ディレクトリからの起動では見つからずMCPサーバーが起動失敗していた。

**確認コマンド**

```bash
# ~/.claude/settings.json の enabledPlugins を確認
cat ~/.claude/settings.json
```

→ `"telegram@claude-plugins-official": true` はユーザーレベルで正しく設定されていた。問題はトークンの保存場所だった。

**対応**  
トークンをシェル環境変数として `~/.zshrc` に書き込む。シェル環境変数はプロジェクトに関係なく常に読み込まれるため、どのディレクトリから起動しても動作する。

```bash
echo 'export TELEGRAM_BOT_TOKEN="<Botトークン>"' >> ~/.zshrc
source ~/.zshrc

# 確認
echo $TELEGRAM_BOT_TOKEN
```

備考：シェル環境変数は `.env` ファイルより優先される。

---

## 正常動作確認

- `/mcp` にて `plugin:telegram:telegram · ✔ connected · 4 tools` を確認
- Telegram Bot に DM を送信 → ペアリングコードが返ってきたことを確認
- `/telegram:access pair <コード>` でペアリング完了
- `/telegram:access policy allowlist` でアクセス制限を設定
- Telegram から `Hi` を送信 → Claude Code が返信することを確認

---

## 設定ファイルの場所

| ファイル | 用途 |
|---|---|
| `~/.claude/plugins/installed_plugins.json` | インストール済みプラグイン一覧 |
| `~/.claude/plugins/cache/claude-plugins-official/telegram/<バージョン>/.mcp.json` | MCPサーバー起動設定 |
| `~/.claude/channels/telegram/.env` | Bot トークン（環境変数） |
| `~/.claude/channels/telegram/access.json` | 許可済み送信者・ポリシー設定 |
| `.claude/settings.local.json` | ローカルスコープのプラグイン有効/無効設定 |

---

## 別マシンへの展開手順

1. Claude Code・Bun をインストール
2. `/usr/local/bin/bun` へのシンボリックリンクを作成（上記と同じ手順）
3. プラグインを **user scope** でインストール
4. Bot トークンを設定（既存の Bot をそのまま使用可能）
5. 再ペアリング、またはペアリング済みの設定ディレクトリを転送

```bash
# 設定ディレクトリの転送（転送元マシンで実行）
scp -r ~/.claude/channels/telegram/ <転送先ホスト>:~/.claude/channels/telegram/
```

---

## 教訓

- プラグインインストール時のスコープ選択は **user scope** を選ぶ。Telegram は個人の連絡先に紐づくため project scope には不向き。
- Apple Silicon Mac では `/usr/local/bin/` が存在しない場合があるため、Bun インストール直後にシンボリックリンクを張る手順を標準化する。
- `--channels` フラグは毎回の起動コマンドに含める必要がある。エイリアス化を推奨。
- Bot トークンは `/telegram:configure` で設定するとプロジェクトディレクトリの `.env` に保存される。どのディレクトリからでも動作させるには `~/.zshrc` に環境変数として書くこと。

```bash
# ~/.zshrc に追加推奨
alias claude-tg='claude --channels plugin:telegram@claude-plugins-official'
```
