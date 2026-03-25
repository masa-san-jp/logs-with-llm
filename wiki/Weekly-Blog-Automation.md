# 週次ブログ自動化 (Weekly Blog Automation)

毎週月曜日に `logs/` の直近1週間のログを読み込み、ブログ記事を自動生成してPRを作成するワークフローです。

## 仕組み

```
logs/ の日付付きファイル
       ↓
scripts/generate_weekly_blog.py
       ↓ LLM API
blog/YYYY-MM-DD.md として保存
       ↓
PR として提出
```

1. `logs/` 内の `yyyymmdd` 形式の日付を含むファイルをスキャン
2. 直近7日以内のファイルを収集
3. 日付付きファイルが見つからない場合は `git diff` でフォールバック
4. 直前のブログ記事をコンテキストとして読み込む（差分を表現するため）
5. LLM APIにプロンプトを送信し、レスポンスを `blog/YYYY-MM-DD.md` に書き出す

## セットアップ

### GitHub Secretsの設定

OpenAIモードを使う場合:

| Secret名 | 説明 |
|---|---|
| `OPENAI_API_KEY` | OpenAI APIキー |

設定場所: **Settings → Secrets and variables → Actions → New repository secret**

## 環境変数

| 変数名 | デフォルト | 説明 |
|---|---|---|
| `BLOG_MODE` | `openai` | LLMバックエンド: `openai` または `ollama` |
| `BLOG_DAYS` | `7` | 何日前まで遡るか |
| `BLOG_DATE` | 今日（UTC） | 出力ファイルの日付（`YYYY-MM-DD`形式で上書き可） |
| `OPENAI_API_KEY` | — | OpenAIモード時に必須 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI互換エンドポイント |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAIモード時のモデル |
| `OLLAMA_URL` | `http://localhost:11434` | Ollamaエンドポイント |
| `OLLAMA_MODEL` | `llama3` | Ollamaモード時のモデル |

## ローカル実行

### Ollamaを使う場合

```bash
# 1. Ollamaを起動（まだ動いていなければ）
ollama serve &

# 2. モデルを取得（初回のみ）
ollama pull llama3

# 3. スクリプトを実行
BLOG_MODE=ollama python scripts/generate_weekly_blog.py
```

### 外部API（OpenAI等）を使う場合

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o-mini

python scripts/generate_weekly_blog.py
```

OpenAI互換API（Azure OpenAI、Together AI、Groq など）も利用可能:

```bash
export OPENAI_BASE_URL=https://your-compatible-api/v1
export OPENAI_API_KEY=your-key
export OPENAI_MODEL=your-model

python scripts/generate_weekly_blog.py
```

## GitHub Actionsからの手動実行

**Actions → Weekly Blog Generator → Run workflow** から実行できます。

実行前に以下の入力を上書き可能:

| 入力項目 | 説明 |
|---|---|
| `blog_mode` | `openai` / `ollama` |
| `blog_days` | 遡る日数 |
| `blog_date` | 出力日付の指定（`YYYY-MM-DD`） |

## 自動実行スケジュール

Cron設定: `0 9 * * 1`（毎週月曜 09:00 UTC）

スケジュールを変更するには `.github/workflows/weekly-blog.yml` を編集します。

## テストの実行

```bash
pip install pytest
pytest scripts/tests/
```

## 出力例

生成されたブログは `blog/YYYY-MM-DD.md` に保存されます。

```
blog/
├── 20260313-weekly.md
├── 20260313-weekly-en.md
├── 20260320-weekly.md
└── 20260320-weekly-en.md
```

日本語版と英語版が生成されます。
