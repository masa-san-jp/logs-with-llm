# 週次ブログ自動化 (Weekly Blog Automation)

毎週金曜日に `logs/` の直近1週間のログを読み込み、ブログ記事を自動生成してコミットするワークフローです。

## 仕組み

```
logs/ の日付付きファイル
       ↓
GitHub Actions (weekly-blog.yml)
  ↓ ファイルごとに要約
  ↓ 統合サマリ生成
  ↓ LLM API（日本語・英語）
blog/YYYYMMDD-weekly.md
blog/YYYYMMDD-weekly-en.md
```

1. `logs/` 内の `yyyymmdd` 形式の日付を含むファイルをスキャン
2. 直近7日以内のファイルを収集
3. ファイルごとに要約を生成
4. 要約を統合してブログ記事（日本語・英語）を生成
5. `blog/YYYYMMDD-weekly.md` と `blog/YYYYMMDD-weekly-en.md` としてコミット

## セットアップ

### GitHub Secretsの設定

| Secret名 | 説明 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic APIキー（`anthropic` バックエンド使用時に必要） |

> `GITHUB_TOKEN` はリポジトリに自動で提供されるため、手動設定は不要です。

設定場所: **Settings → Secrets and variables → Actions → New repository secret**

## GitHub Actionsからの手動実行

**Actions → Weekly Blog Generator → Run workflow** から実行できます。

実行前に以下の入力を上書き可能:

| 入力項目 | デフォルト | 説明 |
|---|---|---|
| `backend` | `github_models` | LLMバックエンド（`github_models` / `anthropic`） |
| `model` | （バックエンドのデフォルト） | 使用するモデル名（空欄=デフォルト） |
| `blog_days` | `7` | 遡る日数 |
| `blog_date` | 今日（UTC） | 出力日付の指定（`YYYY-MM-DD`） |

## 自動実行スケジュール

Cron設定: `0 9 * * 5`（毎週金曜 09:00 UTC / 日本時間 18:00）

スケジュールを変更するには `.github/workflows/weekly-blog.yml` を編集します。

## 出力例

生成されたブログは `blog/` に保存されます。

```
blog/
├── 20260313-weekly.md
├── 20260313-weekly-en.md
├── 20260320-weekly.md
└── 20260320-weekly-en.md
```

日本語版と英語版が生成されます。
