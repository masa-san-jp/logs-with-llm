# GitHub Memory Router

Claude Code が Telegram からの質問・保存リクエストをどの GitHub repository へルーティングするかを定める規約。

**このファイルを最初に読む。**

---

## Repository Routing Table

| Priority | Topic | Repository | Primary Paths | Read | Write |
|---:|---|---|---|:---:|:---:|
| 1 | LLM会話ログ・Claude Code・Telegram連携・MCP運用・プロンプト・週次ブログ・調査メモ | `masa-san-jp/logs-with-llm` | `logs/`, `prompts/`, `docs/`, `researches/`, `articles/` | ✅ | ✅ |
| 2 | エージェント基盤・Agent Team・役割・スキル・ツール・Aiko開発ラボ・業務エージェント | `masa-san-jp/Agent-Lab` | `Agent-team/`, `roles/`, `skills/`, `tools/`, `agents/aiko/` | ✅ | 要確認 |
| 3 | Aiko配布版・人格システム・Claude Code/Codex/Gemini版の使い方・slash command | `masa-san-jp/Agent-Aiko` | `README.md`, `claude-code/`, `codex/`, `antigravity/` | ✅ | 要確認 |
| 4 | 自分用OS・意思決定・行動指針・内省・プロトコル・テンプレ | `masa-san-jp/log-for-myself` | `myself/`, `docs/`, `templates/`, `archive/` | ✅ | ✅ |

---

## Topic Classification

### → logs-with-llm
- Claude Code Channels / Telegram plugin / MCP設定・トラブル
- LLMとの作業ログ・プロンプト資産
- 週次ブログ・Zenn記事・調査メモ

### → Agent-Lab
- Agent Team の設計・業務エージェントの役割・ルール
- tools / skills / workflows
- Aiko 開発ラボ内の未公開・実験的仕様

### → Agent-Aiko
- Aiko 配布版仕様・インストール方法
- Claude Code / Codex / Gemini CLI 版の違い
- `/aiko-*` command・persona / invariant / override の公開仕様

### → log-for-myself
- 自分の価値観・判断基準・思考整理
- 意思決定プロトコル・振り返りテンプレ
- 対人・生活・仕事上の行動指針

---

## Default Read Order

1. このファイル（`memory-router/README.md`）
2. 質問テーマに対応する repository の `README.md`
3. 必要な下位 README / docs / logs
4. 関連する直近ログまたは決定事項

---

## Write Policy

### 確認なしで書いてよい
- 「保存して」「覚えて」「記録して」と明示された内容
- トラブルシューティングの確定ログ
- 決定済みの運用ルール・未完了タスク
- README / docs の軽微なリンク更新

### 書く前に確認する
- Agent-Lab の仕様変更
- Agent-Aiko の公開向け説明変更
- log-for-myself の個人的・機微な内容
- 既存ルールの削除または大幅変更

### 絶対に書かない
- API key / token / password / secret / PAT
- Telegram bot token
- 未確認の推測
- 第三者の機微情報

---

## Telegram Command Mapping

| Command | Action |
|---|---|
| `/ask <question>` | このREADMEを読み、該当リポを参照して回答する |
| `/mem search <query>` | 複数リポから該当情報を検索して要約する |
| `/mem save <text>` | topic classification に従って適切なリポへ保存する |
| `/mem where <topic>` | その話題をどのリポ/pathで見るべきか返す |
| `/mem status` | このREADMEと主要リポの状態を要約する |
| `/mem route` | 現在のルーティング表を返す |

---

## Answering Rules

- 最初に結論を返す
- 参照した repository / path を簡潔に示す
- 長文ログをそのまま貼らない
- 書き込み済みの場合は、保存先と変更内容を短く返す

---

## Source

設計ドキュメント: `docs/20260605-github-memory-router-readme.md`
