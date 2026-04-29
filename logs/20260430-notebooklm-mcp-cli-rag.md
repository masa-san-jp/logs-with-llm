# NotebookLM MCP CLI — RAG的活用ガイド

調査日：2026-04-30  
対象：`notebooklm-mcp-cli` v0.6.1  
目的：Google NotebookLMをRAG（Retrieval-Augmented Generation）的に活用するための技術調査と操作手順

---

## 概要

NotebookLM MCP CLIは、Google NotebookLMをプログラマティックに操作するPythonパッケージ。CLIツール（`nlm`）とMCPサーバー（`notebooklm-mcp`）を一体提供し、Claude Codeからの直接操作を可能にする。

- **GitHub**: https://github.com/jacob-bd/notebooklm-mcp-cli
- **最新バージョン**: v0.6.1（2026-04-28リリース）
- **ライセンス**: MIT / **言語**: Python 3.11+

### RAG文脈での位置づけ

NotebookLMは内部的にGeminiを使ったベクトル検索＋RAGを実装している。このCLIを使うことで：

- 独自ドキュメントをNotebookLMにアップロード → RAGのナレッジベースとして活用
- Claude Codeから `nlm query` でドキュメントに対して質問 → Retrieval + Generation
- 調査→蓄積→横断分析のパイプラインを自動化

---

## インストール手順

### 前提

- Python 3.11以上
- Chrome/Chromiumブラウザ（認証に必要）
- Googleアカウント + NotebookLMアクセス権

### インストール

```bash
# 推奨：uvを使用（依存関係の分離）
uv tool install notebooklm-mcp-cli

# pip
pip install notebooklm-mcp-cli

# インストール不要で試す
uvx --from notebooklm-mcp-cli nlm --help
```

インストール後に使えるコマンド：
- `nlm` ... CLIインターフェース
- `notebooklm-mcp` ... MCPサーバー起動

---

## 認証設定

NotebookLMはGoogle認証が必要。CDPを使いブラウザのクッキーを抽出する方式。

```bash
# ログイン（ブラウザが自動起動する）
nlm login

# 複数アカウントを管理する場合
nlm login --profile work
nlm login --profile personal

# 認証状態の確認
nlm auth status
```

クッキーは `~/.notebooklm-mcp-cli/profiles/` に保存される。有効期限は数週間のため、定期的な再認証が必要。

> **注意**：2026年4月以降のGoogle認証フロー変更でタイムアウトが発生するケースあり（PR提出中、未マージ）。問題が発生したら手動でクッキーを設定するworkaroundが有効。

---

## Claude Code との統合

### セットアップ

```bash
# 自動セットアップ（推奨）
nlm setup add claude-code

# またはClaude Code標準コマンドで追加
claude mcp add --scope user notebooklm-mcp notebooklm-mcp
```

### 手動設定（uvxを使う場合）

`~/.claude/settings.json` の `mcpServers` に追記：

```json
{
  "mcpServers": {
    "notebooklm-mcp": {
      "command": "uvx",
      "args": ["--from", "notebooklm-mcp-cli", "notebooklm-mcp"]
    }
  }
}
```

### スキルのインストール（Claude Code向け）

```bash
# NotebookLM操作のガイドをClaude Codeに組み込む
nlm skill install claude-code
nlm skill update
```

---

## RAG的な使い方：具体的な操作手順

### ステップ1：ナレッジベース用ノートブックの作成

```bash
# テーマ別にノートブックを作成
nlm notebook create "競合調査 2026"
nlm notebook create "技術トレンド AI"
nlm notebook create "規制・法制度 福祉"

# 一覧確認
nlm notebook list
```

### ステップ2：ソースドキュメントの追加（インデックス化）

```bash
# URLから追加（Web記事・論文など）
nlm source add <notebook-id> --url "https://example.com/article"

# テキストで直接追加
nlm source add <notebook-id> --text "調査メモの内容..."

# Googleドライブのドキュメントを追加
nlm source add <notebook-id> --gdrive "https://docs.google.com/document/d/..."

# ローカルファイルを追加（PDF, TXT等）
nlm source add <notebook-id> --file "./report.pdf"

# 追加済みソース一覧
nlm source list <notebook-id>
```

### ステップ3：RAGクエリ（検索＋生成）

```bash
# ノートブックに対して自然言語で質問
nlm notebook query <notebook-id> "このテーマの主要な課題は何ですか？"
nlm notebook query <notebook-id> "競合他社のAI活用状況をまとめてください"
nlm notebook query <notebook-id> "規制上のリスクとその対応策を教えてください"
```

> 回答はNotebookLM WebUIのチャット履歴にも反映される。

### ステップ4：複数ノートブックへの横断クエリ

```bash
# 全ノートブックに対してバッチクエリ
nlm batch query "AIによる業務自動化の最新動向は？" --all-notebooks

# 特定のノートブック群を指定
nlm batch query "福祉業界への影響は？" \
  --notebook-ids <id1> <id2> <id3>
```

### ステップ5：AI要約・コンテンツ生成

```bash
# AI要約を生成（ブリーフィング資料）
nlm notebook summary <notebook-id>

# スライドデッキ生成
nlm studio slides <notebook-id>

# ポッドキャスト音声生成
nlm audio create <notebook-id> --confirm
nlm download audio <notebook-id> <artifact-id>

# マインドマップ生成
nlm studio mindmap <notebook-id>

# フラッシュカード生成
nlm studio flashcards <notebook-id>
```

---

## 自動化パイプラインの設計例

### 調査→蓄積→分析パイプライン

```bash
# pipeline.yaml の例
name: weekly-trend-research
steps:
  - action: source_add
    notebook: "技術トレンド AI"
    urls:
      - "https://arxiv.org/..."
      - "https://techcrunch.com/..."
  - action: query
    notebook: "技術トレンド AI"
    question: "今週の主要な技術トレンドをまとめてください"
  - action: summary
    notebook: "技術トレンド AI"

# パイプライン実行
nlm pipeline run weekly-trend-research
```

### Claude Code内での操作（MCPツール経由）

Claude Codeのチャット内で以下のように操作できる：

```
@notebooklm-mcp ノートブック一覧を表示して
@notebooklm-mcp "技術トレンド AI" ノートブックに https://example.com を追加して
@notebooklm-mcp そのノートブックに「最新のLLM動向は？」と質問して
```

---

## ラベル管理（v0.6.0追加）

大量のソースを整理するためのラベル機能：

```bash
# AIが自動でラベルを付与
nlm label auto <notebook-id>

# 手動でラベル作成
nlm label create <notebook-id> "Research Papers" --emoji 📚
nlm label create <notebook-id> "News Articles" --emoji 📰

# 未ラベルソースを整理
nlm label reorganize <notebook-id> --unlabeled
```

---

## 既知の制限と対策

| 制限 | 内容 | 対策 |
|------|------|------|
| **非公式API** | Google内部API依存。仕様変更で突然壊れるリスク | バージョン固定、変更監視 |
| **認証の有効期限** | クッキーが数週間で失効 | 定期的に `nlm login` を実行 |
| **レート制限** | フリープラン約50クエリ/日 | バッチクエリを夜間に実行 |
| **35ツール問題** | MCPサーバーがコンテキストを大量消費 | 未使用時はサーバーを停止 |
| **CDP認証** | ヘッドレス・CI環境では動作しにくい | ローカル環境での利用を前提とする |
| **Enterprise未テスト** | Google Workspace環境は動作未確認 | 個人Googleアカウントで検証 |

---

## r-d エージェントとしての活用戦略

### 推奨ユースケース

1. **トレンドスキャン自動化**：WebResearcherが収集したURLをNotebookLMに自動追加→横断クエリで知識を統合
2. **調査ナレッジの永続化**：一時的な調査結果をNotebookLMに蓄積し、後から参照・再利用
3. **レポート自動生成**：ブリーフィング資料・スライドの自動生成でアウトプット効率化

### 実装優先度

| 優先度 | タスク |
|--------|--------|
| 高 | `nlm setup add claude-code` でClaude CodeへのMCP統合 |
| 高 | テーマ別ノートブック設計（競合・技術・規制カテゴリ） |
| 中 | パイプライン定義（weekly-trend-research）の実装 |
| 低 | スタジオコンテンツ生成（ポッドキャスト・スライド）の自動化 |

### リスク管理

非公式APIのため本番業務フローへの組み込みは慎重に。現時点での推奨スコープ：**実験・個人リサーチ用途**。Google公式APIが公開された場合は移行を検討する。

---

## 参考リンク

- GitHub: https://github.com/jacob-bd/notebooklm-mcp-cli
- PyPI: https://pypi.org/project/notebooklm-mcp-cli/
- NotebookLM公式: https://notebooklm.google.com
