## 2026-04-18

### 追加
- `spec.md` を新規作成。エージェント構成・ディレクトリ構造・通信プロトコル・ログ管理・git管理ポリシーを網羅した全体設計仕様書。
- `agents/secretary-masa/` を追加。第2担当アカウントを専任管理する2つ目の秘書エージェント。
- `logs.md` を新規作成。チーム全体の設計・構成変更の履歴ファイル（本ファイル）。
- `logs/secretary-setup.md` を新規作成。第1秘書エージェントの認証構成・CLIセットアップ手順を記録。

### 変更
- `ルール.md` → `rules.md` に全エージェントでリネーム（secretary / secretary-masa / cfo / coo / cio）。ファイル名の日本語エンコード問題を解消するため。
- 上記リネームに伴い、以下のファイル内のパス・文言を一括更新。
  - `agents/*/CLAUDE.md`（全5エージェント）
  - `skills/update_log.md`
  - `skills/update_rules.md`
  - `README.md`
  - `spec.md`
- `agents/secretary/CLAUDE.md` に担当アカウント情報とCLI操作方針を追記。Google CalendarはMCP、Gmail・DriveはCLIツール（`gws`）を使う構成を明示。

### 意思決定メモ
- Gmail認証方式の選定: MCPはClaudeログインアカウントに紐づくため別アカウントへの直接アクセスが不可。Googleのメール委任は同一組織間のみ対応。メール転送は2重管理になるため却下。CLIツールによるOAuth認証を採用した。
- 秘書エージェントの分離: 管理対象アカウントが複数のため、アカウントごとに独立した秘書エージェントを設ける設計とした。

### 残課題
- 第2秘書エージェントの認証セットアップ未完了（CLIへのアカウント追加・カレンダーMCP接続確認）。

### 初期構成（initial commit）
- エージェント4体（secretary / cfo / coo / cio）のCLAUDE.md・rules.mdを作成。
- 共通スキル（update_log / update_rules / git_push / task_handoff）を作成。
- 日次ログファイル（logs/*.md）を作成。

---
