# 週次ゴールIssue自動化 (Weekly Documentation Goal Issue)

リポジトリのドキュメント全体を分析し、「次に取り組むべき最も独創的で挑戦的なゴール」をLLMが提案してGitHub Issueを自動作成するワークフローです。

## 仕組み

```
README.md + prompts/ + blog/ + logs/
           ↓
scripts/generate_weekly_goal_issue.py
           ↓ LLM API
GitHub Issue として作成
```

1. `README.md`, `prompts/`, `blog/`, `logs/` からドキュメント一覧を構築
2. LLMに「最も独創的で挑戦的な次のゴール」を問い合わせる
3. 返答をGitHub Issueとして作成

## セットアップ

### GitHub Secretsの設定

| Secret名 | 説明 |
|---|---|
| `OPENAI_API_KEY` | OpenAI APIキー（openaiモード時） |
| `GH_TOKEN` | GitHub Personal Access Token（Issue作成権限が必要） |

## 手動実行

**Actions → Weekly Documentation Goal Issue → Run workflow** から実行できます。

実行前に以下の入力を上書き可能:

| 入力項目 | 説明 |
|---|---|
| `backend` | LLMバックエンド（`openai` / `ollama`） |
| `model` | 使用するモデル名 |
| `issue_date` | Issueの日付指定（`YYYY-MM-DD`） |

## 自動実行スケジュール

ワークフローファイル: `.github/workflows/weekly-doc-goal-issue.yml`

## 活用方法

自動生成されたIssueをリポジトリの次のアクションとして活用します。

- 提案されたゴールを参考にLLMと議論する
- 議論ログを `logs/` に追加する
- ブログに反映させる

このサイクルにより、リポジトリが継続的に成長します。
