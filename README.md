# logs-with-llm

## 概要
このリポジトリは、LLM との対話ログ、週次ブログ、自動化スクリプト、プロンプト資産をまとめて管理するための作業場所です。
日々の記録を `logs/` に残し、それをもとに GitHub Actions で週次ブログ生成と次のドキュメント目標の提案を自動化しています。

## 主なディレクトリ
- `logs/`: LLM との対話や作業メモ
- `blog/`: 週次ブログの生成結果
- `prompts/`: 会話や執筆に使うプロンプト
- `scripts/`: GitHub Actions から実行する Python スクリプト
- `scripts/tests/`: 自動化スクリプトのテスト
- `docs/`: 設計仕様書と運用ガイド
- `researches/`: 調査メモ

## GitHub Actions で自動化していること
### 1. 週次ブログ生成
- ワークフロー: `.github/workflows/weekly-blog.yml`
- 実行スクリプト: `scripts/generate_weekly_blog.py`
- 内容: `logs/` の直近記録を集約し、日本語版・英語版の週次ブログを `blog/` に出力
- 詳細: `docs/weekly-blog-generator-spec.md`

### 2. 週次ドキュメント目標 Issue 生成
- ワークフロー: `.github/workflows/weekly-doc-goal-issue.yml`
- 実行スクリプト: `scripts/generate_weekly_goal_issue.py`
- 内容: README、`prompts/`、`blog/`、`logs/` を棚卸しし、次に取り組むテーマの GitHub Issue を提案
- 詳細: `docs/weekly-doc-goal-issue-spec.md`

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
- GitHub Actions の入力・出力・成果物を変更した場合は README と `docs/` を同時に更新してください
- 認証情報や秘密情報はリポジトリ外の設定で管理し、このリポジトリ内の文書には書かない方針です
