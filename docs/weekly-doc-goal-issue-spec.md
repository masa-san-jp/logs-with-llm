# 週次ドキュメント目標 Issue 生成ワークフロー設計仕様書

## 1. 対象
- GitHub Actions: `.github/workflows/weekly-doc-goal-issue.yml`
- 実行スクリプト: `scripts/generate_weekly_goal_issue.py`

## 2. 目的
README、`prompts/`、`blog/`、`logs/` を横断的に棚卸しし、次に取り組むべきテーマを週次の GitHub Issue として提案することを目的とします。

## 3. 実行契機
- 定期実行: 毎週金曜日 09:00 UTC
- 手動実行: GitHub Actions の `workflow_dispatch`

## 4. 主な入力
### ワークフロー入力
- `llm_provider`: 利用する LLM プロバイダの選択
- `issue_date`: Issue タイトルに埋め込む日付の上書き

### リポジトリ入力
- `README.md`
- `prompts/**/*.yml`, `prompts/**/*.yaml`
- `blog/*.md`
- `logs/**/*.md`, `logs/**/*.pdf`

### 実行環境入力
- Python 3.12
- `requirements.txt` に定義された依存ライブラリ
- リポジトリ設定側で渡される LLM 接続設定
- GitHub CLI（Issue 作成と重複確認に使用）

## 5. 処理フロー
1. リポジトリをチェックアウトし、Python と依存ライブラリを準備する
2. `scripts/generate_weekly_goal_issue.py` を実行して、ドキュメント目録付きのプロンプトを生成する
3. スクリプトは対象ファイルを収集し、日付・見出し・抜粋を抽出してリポジトリ全体の要約を作る
4. ワークフローは生成したプロンプトを LLM に渡し、Issue 本文候補を Markdown で受け取る
5. 1 行目の見出しから Issue タイトルを抽出し、残りを本文として分離する
6. 同名の未完了 Issue が存在するか確認する
7. 重複がなければ新しい GitHub Issue を作成する

## 6. 出力
- GitHub Issue 1 件
- 一時ファイル `/tmp/issue_prompt.txt`, `/tmp/issue_content.md`, `/tmp/issue_body.md`

## 7. 期待する Issue 構成
- `# [Weekly Docs Goal YYYY-MM-DD] ...` 形式のタイトル
- Why this goal now
- Goal
- Why it is original and challenging
- Proposed deliverables
- First actions
- Source signals from the docs

## 8. 異常系・フォールバック
- PDF の読み取りに失敗した場合はその内容を空として処理継続する
- LLM からタイトル形式を満たす応答が返らない場合はワークフローを失敗として扱う
- 同名の未完了 Issue がある場合は新規作成を行わず終了する

## 9. 保守観点
- 収集対象のディレクトリや拡張子を変える場合は `DOC_PATTERNS` と仕様書を同時に更新する
- 出力セクションを変更する場合は `scripts/tests/test_generate_weekly_goal_issue.py` の期待値も合わせて見直す
- 週次テーマの粒度は README と整合するように保つ
