# logs-with-llm

## 概要
このリポジトリは、LLM との対話ログ、週次ブログ、自動化スクリプト、プロンプト資産をまとめて管理するための作業場所です。
日々の記録を `logs/` に残し、それをもとに GitHub Actions で週次ブログ生成と次のドキュメント目標の提案を自動化しています。

## 主なディレクトリ
- `logs/`: LLM との対話や作業メモ
- `blog/`: 週次ブログの生成結果
- `articles/`: Zenn 向け記事原稿
- `prompts/`: 会話や執筆に使うプロンプト
- `scripts/`: GitHub Actions から実行する Python スクリプト
- `scripts/tests/`: 自動化スクリプトのテスト
- `docs/`: 設計仕様書と運用ガイド
- `researches/`: 調査メモ

## GitHub Actions で自動化していること
### 1. 週次ブログ生成
- 実行スクリプト: `scripts/generate_weekly_blog.py`
- 内容: `logs/` の直近記録を集約し、日本語版・英語版の週次ブログを `blog/` に出力
- 詳細: `docs/weekly-blog-generator-spec.md`
- **定期実行は gx10（ローカル Ollama）に移行**: `scripts/run_weekly_blog_gx10.sh` を gx10 の cron から実行する。要約フェーズは `gpt-oss:20b`、記事生成フェーズは `gpt-oss:120b`、reasoning（thinking）on。土曜 08:00 JST までに完了するよう早朝起動（例: `0 5 * * 6`）。
  - クラウド（`.github/workflows/weekly-blog.yml`）は `workflow_dispatch` の手動実行のみ残し、定期 cron は停止（二重生成防止）。
  - モデル切替の環境変数: `OLLAMA_SUMMARIZE_MODEL` / `OLLAMA_COMPOSE_MODEL` / `OLLAMA_THINK` / `OLLAMA_TIMEOUT`

### 2. 週次ドキュメント目標 Issue 生成
- ワークフロー: `.github/workflows/weekly-doc-goal-issue.yml`
- 実行スクリプト: `scripts/generate_weekly_goal_issue.py`
- 内容: README、`prompts/`、`blog/`、`logs/` を棚卸しし、次に取り組むテーマの GitHub Issue を提案
- 詳細: `docs/weekly-doc-goal-issue-spec.md`

### 3. Zenn 記事 Front Matter 自動補完
- ワークフロー: `.github/workflows/auto-front-matter.yml`
- 対象: `articles/**/*.md`
- 内容: GitHub Models を使って Zenn の Front Matter を生成・更新し、差分があればコミット

## docs ディレクトリ
- `docs/README.md`: `docs/` 配下の案内
- `docs/weekly-blog-generator-spec.md`: 週次ブログ生成の設計仕様書
- `docs/weekly-doc-goal-issue-spec.md`: 週次ドキュメント目標 Issue 生成の設計仕様書
- `docs/operation-guide.md`: 運用ガイド

## ローカルでの確認
```bash
pip install -r requirements.txt pytest
python -m pytest -q scripts/tests
```

## 運用メモ
- 週次処理の詳細仕様は `docs/` を参照してください
- Zenn 向けの記事原稿は `articles/` に置き、Front Matter は必要に応じて GitHub Actions で補完します
- GitHub Actions の入力・出力・成果物を変更した場合は README と `docs/` を同時に更新してください
- 認証情報や秘密情報はリポジトリ外の設定で管理し、このリポジトリ内の文書には書かない方針です
