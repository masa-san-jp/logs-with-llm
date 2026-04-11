# 変更履歴

このファイルはリポジトリへの主要な変更を時系列で記録する。
新しいエントリは先頭に追加する。

---

## 2026-04-11

### 多層 LLM 要約パイプラインへの処理フロー改善

**ブランチ:** `claude/optimize-blog-generation-flow-ApsHm`

**概要:**  
週次ブログ生成スクリプトで全ログを結合して1回の LLM 呼び出しに渡していた処理を、
ファイルごとの独立コンテキスト要約 → 前回ブログ要約 → ブログ生成という多層パイプラインに変更。
軽量モデルでも品質の高いブログ記事を生成できるようにした。

**変更ファイル:**
- `docs/weekly-blog-generator-spec.md` — Section 5 処理フローを新設計に合わせて更新（手順 10 → 11 に拡張）
- `scripts/generate_weekly_blog.py` — `read_log_files()` の戻り型変更、`summarize_content()` / `summarize_log_files()` / `summarize_previous_blog()` を追加、`main()` を多層パイプライン構成に変更
- `scripts/tests/test_generate_weekly_blog.py` — `TestReadLogFiles`, `TestSummarizeContent`, `TestSummarizeLogFiles`, `TestSummarizePreviousBlog` を追加（計 41 テスト）
