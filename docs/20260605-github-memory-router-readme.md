# GitHub Memory Router

この README は、Telegram → Claude Code → GitHub → Claude Code → Telegram の会話で、Claude Code がどの GitHub repository を外部記憶として参照・更新するかを決めるためのルーティング規約である。

## 0. Core Principle

- 最初にこのファイルを読む。
- 会話内容から対象テーマを分類する。
- 対象テーマに対応する repository と path を参照する。
- 書き込みは、各 repository の write policy に従う。
- 秘密情報、API key、token、password、個人の機微情報は保存しない。
- 推測を事実として保存しない。

## 1. Repository Routing Table

| Priority | Topic | Repository | Primary Paths | Read | Write | Notes |
|---:|---|---|---|:---:|:---:|---|
| 1 | LLM会話ログ、Claude Code、Telegram連携、MCP運用、プロンプト、週次ブログ、調査メモ | `masa-san-jp/logs-with-llm` | `logs/`, `prompts/`, `docs/`, `researches/`, `articles/` | Yes | Yes | 会話ログと運用ログの司令塔。まずここを参照する。 |
| 2 | エージェント基盤、Agent Team、役割、スキル、ツール、Aiko開発ラボ、業務エージェント | `masa-san-jp/Agent-Lab` | `Agent-team/`, `Agent-team/roles/`, `Agent-team/skills/`, `Agent-team/tools/`, `Agent-team/agents/aiko/` | Yes | Controlled | 実装・設計の正本。雑多な記憶は書かない。 |
| 3 | Aiko配布版、人格システム、Claude Code/Codex/Gemini版の使い方、slash command | `masa-san-jp/Agent-Aiko` | `README.md`, `claude-code/`, `codex/`, `antigravity/`, `persona/` | Yes | Controlled | 公開・配布用の内容を中心に扱う。未整理メモは直接書かない。 |
| 4 | 自分用OS、意思決定、行動指針、内省、プロトコル、テンプレ | `masa-san-jp/log-for-myself` | `myself/`, `docs/`, `templates/`, `archive/` | Yes | Yes | 個人の思考・判断・行動プロトコルの外部記憶。機微情報はマスクする。 |

## 2. Default Read Order

Claude Code は Telegram から質問を受けたら、以下の順で読む。

1. `masa-san-jp/logs-with-llm/memory-router/README.md`
2. 質問テーマに対応する repository の `README.md`
3. 必要な下位 README / docs / logs
4. 関連する直近ログまたは決定事項

## 3. Topic Classification Rules

### logs-with-llm に行く話

- Claude Code Channels
- Telegram plugin
- MCP設定
- トラブルシューティング
- LLMとの作業ログ
- プロンプト資産
- 週次ブログ生成
- Zenn記事
- 調査メモ

### Agent-Lab に行く話

- Agent Team の設計
- 業務エージェントの役割やルール
- tools / skills / workflows
- 財務分析、PR、HR、logi-ops などのエージェント実装
- Aiko 開発ラボ内の未公開・実験的仕様

### Agent-Aiko に行く話

- Aiko の配布版仕様
- Aiko のインストール方法
- Claude Code / Codex / Gemini CLI 版の違い
- `/aiko-*` command
- persona / invariant / override の公開可能な仕様

### log-for-myself に行く話

- 自分の価値観・判断基準
- 思考整理
- 意思決定プロトコル
- 対人・生活・仕事上の行動指針
- 振り返りテンプレ
- 自分用のOS改善

## 4. Write Policy

### Allowed without extra confirmation

- 明示的に「保存して」「覚えて」「記録して」と言われた内容
- トラブルシューティングの確定ログ
- 決定済みの運用ルール
- 未完了タスク
- README / docs の軽微なリンク更新

### Require confirmation before writing

- Agent-Lab の仕様変更
- Agent-Aiko の公開向け説明変更
- log-for-myself の個人的・機微な内容
- 既存ルールの削除または大幅変更
- 複数repoにまたがる再編成

### Never write

- API key
- access token
- password
- secret key
- private credential
- Telegram bot token
- GitHub PAT
- 未確認の推測
- 第三者の機微情報

## 5. Telegram Command Mapping

| Telegram command | Action |
|---|---|
| `/ask <question>` | router READMEを読んで、該当repoを参照して回答する |
| `/mem search <query>` | 複数repoから該当情報を検索して要約する |
| `/mem save <text>` | topic classification に従って適切なrepoへ保存する |
| `/mem where <topic>` | その話題をどのrepo/pathで見るべきか返す |
| `/mem status` | router READMEと主要repoの状態を要約する |
| `/mem route` | 現在のルーティング表を返す |

## 6. Answering Rule

Telegramへ返すときは以下を守る。

- 最初に結論を返す。
- 参照した repository / path を簡潔に示す。
- 長文ログをそのまま貼らない。
- 必要なら「保存候補」と「保存先」を分けて提示する。
- 書き込み済みの場合は、保存先と変更内容を短く返す。

## 7. Example

User:

```text
/mem where Claude Code ChannelsのTelegram設定トラブルはどこ？
```

Expected routing:

```text
Repository: masa-san-jp/logs-with-llm
Path: logs/20260605-claudecode-channels-telegram-setup-troubleshooting.md
Reason: Claude Code Channels / Telegram plugin / MCP troubleshooting に該当するため。
```

User:

```text
/ask AikoのCodex版とClaude Code版の違いは？
```

Expected routing:

```text
Repository: masa-san-jp/Agent-Aiko
Path: README.md, claude-code/README.md, codex/README.md
Reason: Aiko配布版と実行環境ごとの仕様に該当するため。
```

User:

```text
/mem save 今後、意思決定ログは観測・解釈・判断を分けて書く
```

Expected routing:

```text
Repository: masa-san-jp/log-for-myself
Path: myself/ or templates/
Reason: 自分用OS・意思決定プロトコルに該当するため。
```
