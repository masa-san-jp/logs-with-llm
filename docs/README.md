# docs

このディレクトリには、このリポジトリで運用している GitHub Actions と関連スクリプトの設計・運用資料をまとめています。

## 収録ドキュメント
- `weekly-blog-generator-spec.md`: 週次ブログ生成ワークフローと `scripts/generate_weekly_blog.py` の設計仕様書
- `weekly-doc-goal-issue-spec.md`: 週次ドキュメント目標 Issue 生成ワークフローと `scripts/generate_weekly_goal_issue.py` の設計仕様書
- `operation-guide.md`: ディレクトリ構成、手動実行、テスト、更新時の確認観点をまとめた運用ガイド

## 想定読者
- ワークフローの挙動を把握したいメンテナ
- README だけでは足りない設計判断の背景を確認したい利用者
- GitHub Actions の入力・出力・依存関係を整理して確認したい開発者

## 更新方針
- ワークフローのトリガー、入出力、成果物、依存スクリプトのいずれかが変わったら関連仕様書を更新する
- README の要約と `docs/` 配下の詳細記述が食い違わないように保つ
