# Claude Code スキル集リポジトリ調査

調査日: 2026-04-30  
調査者: r-d エージェント  
目的: 導入候補技術の把握・優先度評価

---

## メイン調査対象

### mattpocock/skills

**URL**: https://github.com/mattpocock/skills  
**著者**: Matt Pocock（TypeScript教育者・Total TypeScript創設者）  
**スター数**: 42,673  
**更新頻度**: 2026-04-29更新（直近2日で10コミット）

#### 概要

Claude Code向けのスキル集。`.claude/skills/` に置くMarkdownファイル群で、エージェントの4大失敗モードを解決することを目的とする。GSD・BMAD・Spec-Kitのような「プロセスをエージェントに丸投げする」アプローチへのアンチテーゼとして設計。

| 失敗モード | 対応スキル |
|---|---|
| 意図の誤解 | `/grill-me`, `/grill-with-docs` |
| 共通言語の欠如（出力が冗長） | `/grill-with-docs`（CONTEXT.md構築） |
| 生成コードが動かない | `/tdd`, `/diagnose` |
| コードベースの泥団子化 | `/improve-codebase-architecture`, `/zoom-out` |

#### 公開スキル一覧（12本）

| スキル | カテゴリ | 概要 |
|---|---|---|
| `/grill-me` | Productivity | 計画をエージェントに1問ずつ徹底尋問させる |
| `/grill-with-docs` | Engineering | ドメイン言語固め＋CONTEXT.md・ADRをインライン更新 |
| `/tdd` | Engineering | 垂直スライス型TDD（水平スライスを明示禁止） |
| `/diagnose` | Engineering | バグ診断6フェーズループ（フィードバックループ構築を最重視） |
| `/improve-codebase-architecture` | Engineering | 「深いモジュール」理論ベースのアーキテクチャ改善 |
| `/triage` | Engineering | Issueのトリアージステートマシン |
| `/to-prd` | Engineering | 会話コンテキストからPRDを生成しIssueに投稿 |
| `/to-issues` | Engineering | PRD・仕様を独立可能なGitHub Issueに分解 |
| `/zoom-out` | Engineering | 未知コードの全体コンテキスト把握 |
| `/setup-matt-pocock-skills` | Engineering | Issueトラッカー・ラベル・ドキュメント置き場を1回セットアップ |
| `/caveman` | Productivity | トークン消費量75%削減の圧縮通信モード |
| `/write-a-skill` | Productivity | 新スキルの作成補助 |

#### 技術スタック

- 実体はMarkdownファイル（SKILL.md）1枚のみ、コードなし
- `npx skills@latest add mattpocock/skills` でインストール可能
- 設計思想: プロンプトエンジニアリングのみ、依存関係ゼロ

#### 思想的基盤

- *The Pragmatic Programmer*
- *Domain-Driven Design*
- *A Philosophy of Software Design*（John Ousterhout の「深いモジュール」理論）

#### 評価

| 項目 | 評価 |
|---|---|
| 導入コスト | 低（1コマンド or 手動コピー） |
| 導入リスク | 低（Markdownコピーのみ、破壊的変更なし） |
| 自社適合性 | 高（既存スキル構造と完全一致） |

**即効性が高いスキル3本**:
1. `/grill-with-docs` — CONTEXT.md + ADR パターン。knowledge-curator との親和性が高い
2. `/diagnose` — フィードバックループ構築優先の6フェーズ診断。build-error-resolver 強化に活用可
3. `/tdd` の垂直スライス哲学 — tdd-guide の記述品質向上のリファレンスとして活用

---

## 次点リポジトリ 10選

導入優先度順に並べた。自社r-dエージェント構成への適合性を加味して評価。

---

### 1位 — SuperClaude_Framework

**URL**: https://github.com/SuperClaude-Org/SuperClaude_Framework  
**スター数**: 22,542  
**更新**: 2026-04-29

#### 概要

Claude Code に特化した設定フレームワーク。専用コマンド群、認知ペルソナ（architect, security, mentor 等）、開発方法論を一体で提供する。`.claude/` ディレクトリへの設定注入方式。

#### 主な機能

- コマンド群（`/analyze`, `/test`, `/deploy` 等）
- 認知ペルソナ切替（architect, security, mentor 等）
- `install.sh` / `pip install` によるワンコマンド導入
- 日本語・韓国語・中国語 README 完備

#### mattpocock/skills との差別化

mattpocock が「小さく手動で組み合わせる」哲学なのに対し、こちらは「フレームワーク全体を一括導入」する思想。コンフィグ主導で設定量が多いが網羅性が高い。

| 導入難易度 | 自社関連性 |
|---|---|
| 中（Python環境必要） | 現在のエージェント専門化（trend-analyst/disruption-scout）をペルソナ概念でさらに精緻化できる |

---

### 2位 — PAUL（Plan-Apply-Unify Loop）

**URL**: https://github.com/ChristopherKahler/paul  
**スター数**: 810  
**更新**: 2026-04-29

#### 概要

「コンテキスト劣化」問題を解決するための構造化AI開発ループ。PLAN→APPLY→UNIFYの3フェーズで計画を必ず閉じ、セッションをまたいだ状態管理を行う。

#### 主な機能

- `/plan`, `/apply`, `/unify` の3コアコマンド
- BDD形式のAcceptance Criteria（Given/When/Then）
- 計画ステート永続化（セッション間引き継ぎ）
- `npx paul-framework` でワンコマンド導入

#### mattpocock/skills との差別化

mattpocock がタスク単位の小粒なスキルを提供するのに対し、PAULは「開発ループ全体の品質保証」に特化。コンテキスト管理とループ完結性が主眼。

| 導入難易度 | 自社関連性 |
|---|---|
| 低（`npx paul-framework` のみ） | 仮説検証サイクル（計画→テスト→評価→改善）と構造的に直接対応 |

---

### 3位 — gentle-ai

**URL**: https://github.com/Gentleman-Programming/gentle-ai  
**スター数**: 2,463  
**更新**: 2026-04-29

#### 概要

Claude Code / Cursor / Gemini CLI など10種のAIエージェントをまとめて設定するエコシステムコンフィギュレータ。SDD（Spec-Driven Development）ワークフロー、Engram永続メモリ、MCP連携を一括構成。

#### 主な機能

- 10エージェント対応（Claude Code, Cursor, OpenCode, Gemini CLI 等）
- SDD 9フェーズオーケストレーター + judgment-day
- Engram プロトコルによるセッション横断記憶
- Per-phaseモデルルーティング（フェーズ別にHaiku/Sonnet/Opus切替）

#### mattpocock/skills との差別化

エージェント間の設定統一とセッション永続記憶に特化。「AIツールスタック全体の標準化」を目指す点が最大の差異。

| 導入難易度 | 自社関連性 |
|---|---|
| 中（brew install または shell script） | 複数エージェント構成（r-d/cfo-fpa/logi-ops等）のスキル共有・メモリ設計の参考になる |

---

### 4位 — claude-code-tresor

**URL**: https://github.com/alirezarezvani/claude-code-tresor  
**スター数**: 700  
**更新**: 2026-04-29

#### 概要

Claude Code向けの大規模スキル・エージェント・スラッシュコマンド集。v2.7.0時点で133サブエージェントと10オーケストレーションコマンドを擁する。Smithery経由でも配布。

#### 主な機能

- 133+エージェント（10チームカテゴリ）
- セキュリティ監査系: `/audit`, `/vulnerability-scan`, `/compliance-check`
- 運用系: `/deploy-validate`, `/health-check`, `/incident-response`
- Tresor Workflow Framework（メタプロンプト・コンテキストハンドオフ）

#### mattpocock/skills との差別化

mattpocock が軽量・手動組み合わせを重視するのに対し、規模（133エージェント）と自動オーケストレーションが強み。エンタープライズ寄り。

| 導入難易度 | 自社関連性 |
|---|---|
| 中（手動コピーまたはSmithery経由） | セキュリティ・コンプライアンス系スキルをr-dの技術検証フェーズで活用できる可能性あり |

---

### 5位 — claude-code-skill-factory

**URL**: https://github.com/alirezarezvani/claude-code-skill-factory  
**スター数**: 733  
**更新**: 2026-04-29

#### 概要

スキル・エージェント・スラッシュコマンド・フックを量産するためのファクトリーツールキット。「作るための道具」としての位置付けで、69種のプロンプトプリセットも内包。

#### 主な機能

- `/build skill/agent/prompt/hook` のインタラクティブビルダー
- 69種類のプロフェッショナルプロンプトプリセット
- `/validate-output`, `/install-skill`, `/install-hook` コマンド群
- GitHub Issue連携（`/sync-todos-to-github`）

#### mattpocock/skills との差別化

mattpocock が「完成品のスキルを配布」するのに対し、こちらは「スキルを作るためのインフラ」。スキル開発者向けのメタツール。

| 導入難易度 | 自社関連性 |
|---|---|
| 低（ファイルコピーのみ） | `agents/r-d/skills/` へのスキル保存標準化に直接活用できる |

---

### 6位 — spec-based-claude-code

**URL**: https://github.com/papaoloba/spec-based-claude-code  
**スター数**: 126  
**更新**: 2026-04-22

#### 概要

仕様書駆動開発（SDD）のワークフローをClaude Codeのスラッシュコマンドで実装。要件→設計→タスク→実装の4フェーズを各フェーズで承認を挟みながら進める。

#### 主な機能

- `/spec-requirements`, `/spec-design`, `/spec-tasks`, `/spec-implement` コマンド
- `/spec-status` による進捗確認
- `spec/` ディレクトリ配下への仕様書自動生成
- ゼロ依存（Pure Markdown）

#### mattpocock/skills との差別化

mattpocock が「個々の問題に対するスキル」を提供するのに対し、こちらはフィーチャー単位の仕様書管理プロセスそのものを構造化。ドキュメントファーストな開発を強制する。

| 導入難易度 | 自社関連性 |
|---|---|
| 低（スラッシュコマンドのコピーのみ） | r-dの仮説検証サイクル（計画→テスト→評価→改善）と構造が一致 |

---

### 7位 — refly

**URL**: https://github.com/refly-ai/refly  
**スター数**: 7,258  
**更新**: 2026-04-29

#### 概要

スキルをワンタイムプロンプトではなく「バージョン管理された永続的インフラ」として定義・実行・共有するOSSプラットフォーム。Claude Code / Cursor / Codex にスキルをエクスポートできる。

#### 主な機能

- Vibe Workflowによるスキル定義
- refly.ai上でのスキルレジストリ（コミュニティ共有）
- Claude Code / Cursor / Codex へのエクスポート
- APIとしてデプロイする機能
- Slack / Lark / FeishuへのBot連携

#### mattpocock/skills との差別化

mattpocock が静的な `.md` ファイルを配布するのに対し、reflyはスキルをSaaS型プラットフォームで管理・共有・実行する。ローカルツールではなくクラウドサービスが主体。

| 導入難易度 | 自社関連性 |
|---|---|
| 中（refly.aiアカウント必要 or OSS自己ホスト） | 将来的にスキルをチーム間共有する際のレジストリ設計の参考になる |

---

### 8位 — molyanov-ai-dev

**URL**: https://github.com/pavel-molyanov/molyanov-ai-dev  
**スター数**: 199  
**更新**: 2026-04-29

#### 概要

AI-Firstな開発方法論をClaude Code CLIで実践するフレームワーク。spec-drivenパイプラインに20+スキルと20+エージェントを組み合わせ、チーム実行（マルチエージェント並列）に対応。

#### 主な機能

- User Spec → Tech Spec → Decompose → Do → Done の5フェーズパイプライン
- Project Knowledge（`project.md`, `architecture.md`, `patterns.md` 等）の分離管理
- 5並列バリデーターによる品質ゲート
- code-researcher エージェントによるコードベース事前調査
- Context7 MCP 統合（外部ライブラリのリアルタイム仕様取得）

#### mattpocock/skills との差別化

エンタープライズグレードのバリデーションチェーンと、「人間が承認する」ゲートを各フェーズに持つ点が特徴。重量級だがProject Knowledge分離の思想は参考になる。

| 導入難易度 | 自社関連性 |
|---|---|
| 高（スキル・エージェント数が多く学習コストが高い） | 知識グラフ構築（Project Knowledge分離）はr-dの内部インサイト蓄積設計に参照可能 |

---

### 9位 — spec-kit-zh

**URL**: https://github.com/loulanyue/spec-kit-zh  
**スター数**: 239  
**更新**: 2026-04-29

#### 概要

Spec-Driven Developmentを素早く始めるための多言語対応ツールキット。Claude Code / Gemini CLI / Cursor / Kiro Code / Windsurf など主要AIエージェント全般で動作する。

#### 主な機能

- 要件→設計→タスクの3段階仕様書テンプレート群
- 全主要AIエージェントへの対応（特定ツールへの依存なし）
- 中国語・英語対応README
- ゼロ依存のPure Markdownスキル

#### mattpocock/skills との差別化

エージェント非依存で最も導入ハードルが低いSDD実装。mattpocock の問題解決スキル集とは用途が異なり「仕様書管理プロセス標準化」に特化。

| 導入難易度 | 自社関連性 |
|---|---|
| 低（Markdownコピーのみ） | 既存ワークフローを壊さずにSDD概念を試験導入するのに最適 |

---

### 10位 — askjg-claude-agents

**URL**: https://github.com/askjohngeorge/askjg-claude-agents  
**スター数**: 52

#### 概要

個人が実際のAI支援開発で日常使用しているClaude Code用サブエージェントとカスタムコマンド集。mattpocock/skills と最も近い「実践者が自分用に作った実用集」という位置付け。

#### 主な機能

- 専門化されたサブエージェント定義（CLAUDE.mdベース）
- 開発ワークフロー向けカスタムコマンド
- 実際の使用実績に基づく設計
- 軽量・透明性の高い構成

#### mattpocock/skills との差別化

規模感は小さいが同様の「実用優先」哲学。大手フレームワークへのアンチテーゼとして参考になる。カスタマイズの出発点として使いやすい。

| 導入難易度 | 自社関連性 |
|---|---|
| 低（ファイルコピーのみ） | 現在のエージェント設計の参照アーキテクチャとして直接比較検討できる |

---

## 総合比較表

| 順位 | リポジトリ | スター | 哲学 | 主な差別化 | 難易度 |
|---|---|---|---|---|---|
| 本命 | mattpocock/skills | 42,673 | 小粒・実用・アンチフレームワーク | 問題特化スキル12本 | 低 |
| 1 | SuperClaude_Framework | 22,542 | フレームワーク全体注入 | ペルソナ・コマンド体系 | 中 |
| 2 | PAUL | 810 | ループ完結性 | コンテキスト劣化対策 | 低 |
| 3 | gentle-ai | 2,463 | エコシステム統一 | 10エージェント+永続記憶 | 中 |
| 4 | claude-code-tresor | 700 | 大規模コレクション | 133エージェント+セキュリティ系 | 中 |
| 5 | claude-code-skill-factory | 733 | スキル製造装置 | スキルを作るためのメタツール | 低 |
| 6 | spec-based-claude-code | 126 | 仕様書プロセス | 4フェーズ承認ゲート | 低 |
| 7 | refly | 7,258 | スキルインフラSaaS | クラウド型スキルレジストリ | 中 |
| 8 | molyanov-ai-dev | 199 | エンタープライズSDD | 5並列バリデーター+20+エージェント | 高 |
| 9 | spec-kit-zh | 239 | 軽量SDD入門 | ツール非依存・多言語 | 低 |
| 10 | askjg-claude-agents | 52 | 個人実用集 | 透明性・カスタマイズ出発点 | 低 |

---

## r-dエージェントへの活用示唆

### 即時参照推奨（読むだけでROIあり）

1. **mattpocock/skills の `/grill-with-docs`** — CONTEXT.md + ADR パターンを既存の knowledge-curator ワークフローに反映
2. **mattpocock/skills の `/diagnose`** — フィードバックループ構築優先の6フェーズ診断を build-error-resolver へ組み込み検討
3. **PAUL のコンテキスト管理思想** — セッション間引き継ぎ設計の参考

### 試験導入推奨（破壊的変更なし）

- `npx paul-framework` を1プロジェクトで試す
- spec-based-claude-code の `/spec-requirements` をr-d内の調査タスク管理に試験適用

### 中長期で追跡

- **refly** — スキルレジストリSaaSとして成熟したら、チーム間スキル共有のインフラ候補として評価
- **SuperClaude_Framework** — エージェントペルソナ設計が洗練されたら認知モデルの参考として再評価
