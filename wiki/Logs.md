# ログの記録 (Logs)

## ディレクトリ構成

`logs/` ディレクトリにすべての会話ログを保存します。

```
logs/
├── 20260201-grok-framework-of-note
├── 20260211-claude-ollama-ver-of-100times-ai-heroes
├── 20260217-gemini-task-manege-on-gws
├── 20260218-gemini-gws-assistant-bot-design
├── 20260218-github-to-blog/          ← ディレクトリ形式も可
│   ├── minutes.md
│   └── output.md
└── ...
```

## ファイル命名規則

```
YYYYMMDD-{llm名}-{テーマ}[.md]
```

| 部分 | 説明 | 例 |
|---|---|---|
| `YYYYMMDD` | 会話した日付 | `20260325` |
| `{llm名}` | 使ったLLMの名前 | `claude`, `gemini`, `grok`, `chatgpt` |
| `{テーマ}` | 会話のテーマ（英語小文字・ハイフン区切り推奨） | `api-design`, `weekly-blog` |
| `.md` | マークダウンの場合は付ける（省略可） | |

### 例

- `20260201-grok-framework-of-note` — Grokとノートフレームワークについて議論
- `20260218-gemini-gws-assistant-bot-design` — GeminiとGWSボット設計
- `20260314-research-gws-cli.md` — GWS CLIの調査ログ

## ファイル形式

### 単一ファイル形式

```markdown
# テーマタイトル

## 参加者
- ユーザー
- {LLM名}

## 議題
...

## 議事録
...

## 結論・成果物
...
```

### ディレクトリ形式

複数ファイルに分ける場合はディレクトリにします。

```
20260218-github-to-blog/
├── minutes.md    ← 会話の議事録
└── output.md     ← 最終成果物
```

## ログが活かされる場面

### 続きの会話

```
（議事録を貼り付ける）

この話の続きで、〇〇について詳しく考えたい。
```

### 別のLLMに相談

```
（議事録を貼り付ける）

別のLLMとして、この設計についてどう思う？
改善点があれば教えて。
```

### 週次ブログへの自動変換

毎週月曜に `logs/` の直近1週間のファイルを読んで自動的にブログ記事を生成します。
→ [週次ブログ自動化](Weekly-Blog-Automation)

## ログ一覧（主なトピック）

| 日付 | LLM | テーマ |
|---|---|---|
| 2026-02-01 | Grok | ノートフレームワーク |
| 2026-02-11 | Claude | Ollamaで「AIヒーロー100回」 |
| 2026-02-17 | Gemini | GWSタスク管理 |
| 2026-02-17 | Grok | Gitリポジトリ命名 |
| 2026-02-18 | Gemini | Google AI Studio システム指示 |
| 2026-02-18 | Gemini | GWSアシスタントボット設計 |
| 2026-02-18 | - | GitHubからブログ生成 |
| 2026-02-19 | Claude | ブラウザ上の3LLM会議 |
| 2026-02-23 | - | ローカルLLM + Web検索API |
| 2026-03-10 | - | Grantエージェント |
| 2026-03-11 | - | GWS CLI調査 |
| 2026-03-14 | - | GWS CLI詳細調査 |
| 2026-03-16 | - | AI駆動企業 |
| 2026-03-20 | - | 清親〜巴水の研究 |
| 2026-03-21 | - | AI メタ開発 |
