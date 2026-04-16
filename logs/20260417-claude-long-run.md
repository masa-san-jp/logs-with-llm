# 議事録

**議事録タイトル**: Anthropic Claude Codeにおける長時間稼働AIエージェント構築手法の技術共有  
**議題**: コンテキストウィンドウ制限克服のためのコンパクション戦略およびCLAUDE.md階層の詳細解説と実装テンプレート  
**目的**: 本件を意思決定プロセスに引き継ぐための詳細記録作成  
**日時**: 2026年4月17日  
**形式**: オンライン技術議論（Xポスト起点の継続議論）  
**参加者**: 匿名（関係者複数名）  
**議事録作成者**: 技術担当  
**参照元**: https://x.com/rohit4verse/status/2044846994074828888（Anthropic長時間稼働AIエージェント構築記事およびClaude Code実践デモ動画）

## 1. 背景・議題の概要
本議論は、X上で共有されたAnthropicのClaude Code（long-running agent harness）に関する投稿を起点とする。投稿では、コンテキストウィンドウ制限を克服するための4段階コンパクション戦略、ディスクバックアップタスクリスト、CLAUDE.md階層によるセッション間メモリ永続化、Initializer AgentとCoding Agentの分業、features_list.jsonを用いたテスト駆動開発、Gitコミットによる状態追跡が紹介されている。  
これを基に、長時間稼働エージェントの実装可能性、運用フロー、永続化手法の詳細を整理し、プロジェクトへの適用可否を意思決定する資料とする。

## 2. 議論内容（1）コンパクション戦略の詳細
コンテキスト肥大化による性能低下を防ぐための階層型アプローチ。**cheapest to most expensive**の順で段階的に適用する「ゴミ集め（garbage collection）」方式。  
主な4段階は以下の通り（一部実装で5段階に拡張される場合あり）。

### 2.1 Micro-compaction / Tool Result Clearing（最安・日常適用）
- 古いツール呼び出し結果（ファイル読み込み出力など）を自動クリアまたは要約。  
- ディスクに退避し、コンテキスト内では短い参照（summary + file path）に置き換え。  
- トリガー：ターンごとまたは軽い閾値。  
- 利点：ほぼゼロコスト。安全に冗長データを削減。

### 2.2 Snip / Partial Truncation or Context Collapse（低コスト・中間層）
- 古いメッセージ範囲を削除（snip）または折り畳み（collapse）。Head-Tail保持（システムプロンプトと最近作業を残す）。  
- トリガー：中程度のトークン閾値超過時。  
- 利点：速く安価。重要な最近コンテキストを保護。

### 2.3 Session Memory / Structured Note-taking / Auto-Summarization（中間〜高精度・永続化重視）
- 会話の重要部分を外部ファイル（CLAUDE.md、features_list.json、progress log、NOTES.mdなど）に抽出・保存。  
- セッション間で永続化。コンパクション時にモデルが構造化サマリーを生成し、<summary>タグなどでマーク。  
- トリガー：自動コンパクション閾値（92-95%容量）またはバックグラウンドプロセス。  
- 利点：コンテキスト外に状態を逃がし、セッション中断・再開に強い。Gitコミットと組み合わせ可能。

### 2.4 Full Compaction / Reactive Summarization（最高コスト・最終手段）
- 全体会話履歴をモデルに渡して高忠実度サマリーを生成。新規コンテキストとして置き換え（CompactBoundaryMessageなど）。  
- トリガー：緊急時（prompt too longエラー）または閾値超過。Proactive版とReactive版あり。  
- 利点：最高圧縮率と一貫性。  
- 欠点：LLM呼び出しコスト高。情報損失リスクあり（recall優先プロンプト設計必須）。

### 2.5 全体運用フロー
- Initializer Agent：features_list.json作成、全タスクを「failing」マーク、Git初期化、progress log作成。  
- Coding Agent：1機能ずつ処理 → テスト → Gitコミット → log更新 → コンパクション。  
- 自動監視：トークンカウント → 閾値で階層適用 → 必要時リトライ。  
- これにより数百〜数千ターンの長時間セッションが可能。

## 3. 議論内容（2）CLAUDE.md階層の詳細
セッション間・プロジェクト間の永続メモリとして最も重要な仕組み。毎セッション開始時に自動読み込み。現在の作業ディレクトリから上方向に走査し、より**具体的な（狭いスコープ）ものが優先（override）**される。

### 3.1 階層構造表

| レベル          | ファイル場所                          | 適用対象                  | Git共有 | ロードタイミング          | 優先度（具体性） |
|-----------------|---------------------------------------|---------------------------|---------|---------------------------|------------------|
| Managed (企業/管理) | `/etc/claude-code/CLAUDE.md` や組織設定 | 全ユーザー・全プロジェクト | 場合による | セッション開始           | 最低（最広）    |
| User (ユーザー全局) | `~/.claude/CLAUDE.md`                | あなたの全プロジェクト   | いいえ | セッション開始           | 中              |
| Project (プロジェクト) | `./CLAUDE.md` または `./.claude/CLAUDE.md` | このリポジトリの全メンバー | はい   | セッション開始           | 高              |
| Directory / Local (ディレクトリ/局所) | サブディレクトリ内の`CLAUDE.md` または `./CLAUDE.local.md` | 特定のフォルダ/個人のみ  | はい（localは.gitignore推奨） | 作業中・オンデマンド     | 最高（最狭）    |

### 3.2 各レベルの役割
- **Userレベル**: 個人設定（全プロジェクト共通）。例：コーディングスタイル、好みコマンド。  
- **Projectレベル**: リポジトリ全体の共有ルール。チームでgit管理。  
- **Directoryレベル**: monorepo対応。サブディレクトリごとに局所ルール。  
- **Local**: gitignore推奨の一時オーバーライド。

### 3.3 拡張機能
- `@import`構文で他ファイルをインクルード。  
- `.claude/rules/*.md` で細かいルールをpath-scoped分割。  
- skills/、agents/フォルダでオンデマンドロード。  
- コンパクション後も再注入されやすい設計。

## 4. 議論内容（3）CLAUDE.mdテンプレート例
**基本テンプレート（汎用・おすすめスターター）**  
プロジェクトルートまたは`.claude/CLAUDE.md`に配置。

```markdown
# [プロジェクト名] - CLAUDE.md

## Overview
このプロジェクトは[1文で概要]。主な目的は[具体的なゴール]。

## Tech Stack
- [言語/フレームワーク] [バージョン]
- [DB/ORM]
- [主要ライブラリ]（例: React 19 + TypeScript 5.5, Tailwind, Prisma）
- [テスト/ツール]（例: Vitest, ESLint, Prettier）

## Project Structure
- `src/` - ソースコード
  - `components/` - UIコンポーネント
  - `lib/` - ユーティリティ・共有ロジック
  - `api/` - APIルート/ハンドラ
- `tests/` - テスト
- `docs/` - 追加ドキュメント

## Commands (重要: 常にこれを使う)
- Dev: `npm run dev` (または `pnpm dev`)
- Build: `npm run build`
- Test: `npm test` または `npm run test:watch`（単体テスト優先）
- Lint/Format: `npm run lint` && `npm run format`
- DB関連: `prisma generate` / `prisma migrate dev`

## Code Style & Conventions (厳守)
- **命名**: camelCase（変数/関数）、PascalCase（コンポーネント/クラス）
- **Import**: ES modules優先、`import { foo } from 'bar'` でdestructure
- **Error Handling**: 例外よりResult型/早期return優先
- **コメント**: 複雑なロジックのみ。自己説明的なコードを優先
- **IMPORTANT**: 常にTypeScript strict mode遵守。any型禁止

## Architecture Rules
- [Clean Architecture / Feature-Sliced Design など] を厳守
- Domain層は外部依存ゼロ
- 状態管理は[Recoil/Zustand]優先
- コンポーネントは1責任原則（SRP）

## Testing Rules
- 単体テストはロジック中心、統合テストはエンドツーエンド優先
- テスト名: `[Method]_[Scenario]_[Expected]`
- 常にテスト通過を確認してからコミット

## Git & Workflow
- Branch: `feature/xxx`, `bugfix/yyy`
- Commit: Conventional Commits（feat:, fix:, refactor:）
- PR前に `npm test && npm run lint` 実行
- 変更時は必ずCLAUDE.mdも更新検討

## Gotchas & Anti-Patterns (絶対避ける)
- [よくやるミス] をリスト
- 例: 直接DBアクセスせずRepository/Service経由

## Domain Terms
- [用語]: [説明]

**最重要**: 変更を加えたら「この変更が既存ルールと矛盾しないか」確認せよ。
```

**.NET特化テンプレート例（抜粋・カスタマイズ元）**

```markdown
# CLAUDE.md - [Project Name]

## Overview
[1文概要]

## Tech Stack
- .NET 8/9, ASP.NET Core Minimal APIs
- Entity Framework Core + PostgreSQL
- Mediator (CQRS), FluentValidation, xUnit + FluentAssertions

## Project Structure
- `src/Api/` → Endpoints
- `src/Application/` → Commands/Queries/Handlers
- `src/Domain/` → Entities/Value Objects
- `src/Infrastructure/` → EF Core, Repositories

## Commands
- Build: `dotnet build`
- Test: `dotnet test`
- Migration: `dotnet ef migrations add ...`

## Architecture Rules
- Domain層は外部依存ゼロ
- Result<T>パターン使用（例外はフロー制御に使わない）
- 常にCancellationTokenを渡す

## Anti-Patterns
- Repositoryパターン禁止（EF Core直接使用）
- AutoMapper禁止（手動マッピング）
```

**グローバル（Userレベル）用シンプル例（`~/.claude/CLAUDE.md`）**

```markdown
# 個人グローバル設定

## 常に適用
- コードはシンプル・読みやすく。過度な抽象化を避ける
- テストは最初に書く or 即時検証
- コミット前: lint + test + type check 必須
- Prefer named exports, async/await, 2-space indent（好みに応じて）
- IMPORTANT: セキュリティ・パフォーマンス考慮を常に忘れず
```

### テンプレート作成Tips
- /initコマンドで自動生成可能。  
- 短く保つ（200行以内推奨）。  
- セクション分け明確に。  
- `@import`や`.claude/rules/`を活用。

## 5. 結論・決定事項・次アクション
- 本手法により、コンテキスト制限を克服した長時間AIエージェント運用が可能であることを確認。  
- CLAUDE.md階層とコンパクション戦略の組み合わせがセッション永続化の鍵。  
- **決定保留事項**: 本プロジェクトへの正式採用可否（コスト・スケーラビリティ検証後）。  
- **次アクション**:  
  1. プロトタイプ実装（Initializer Agent + features_list.json作成）。  
  2. CLAUDE.mdテンプレートをプロジェクトルートに配置し、/initで初期化。  
  3. 意思決定会議にて本議事録を基にレビュー。  
  4. 必要に応じて特定言語（React/Pythonなど）専用テンプレート追加生成。

**添付資料**: 本議事録に記載の全テンプレートおよび参照Xポスト。  
**保存場所**: プロジェクト共有ドキュメントフォルダ  
**更新日**: 2026年4月17日  