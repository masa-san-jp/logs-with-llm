実行プロトコル：AIエージェントでスマホアプリを設計・実装する

対象は、Biz職がAIエージェントを使ってiOS/Androidアプリの企画・デザイン・実装・検証まで進めるための実務手順です。

⸻

0. 前提条件

推奨ツール構成

工程	主担当	補助
要件定義	Claude Code	ChatGPT / Codex
UX構造設計	Claude Code	Figma / Stitch
UI案生成	Claude Design / Figma Make / Google Stitch	Figma
ネイティブ実装	Claude Code	Codex
修正・テスト	Codex	Claude Code
デザイン実装照合	Figma MCP	Claude Code / Cursor / Windsurf等

Claude Codeはローカルコードベースを読み書きし、複数ファイルをまたいだ実装・修正を行う用途に適している。Anthropic公式ドキュメントでは、既存コードベースでの開発パターン、サブエージェント、Hooksなどが提供されている。 ￼

Codex CLIはローカルの選択ディレクトリ内でコードを読み、変更し、実行できるOpenAIのコーディングエージェント。細部修正・レビュー・既存コード理解に使いやすい。 ￼

Figma MCP serverは、AIエージェントにFigmaファイル内のコンポーネント、変数、レイアウト情報などの構造化デザイン文脈を渡し、デザインに即したコード生成を支援する。 ￼

⸻

1. 作業ディレクトリを作る

1-1. 推奨フォルダ構成

app-project/
  00-context/
    product-brief.md
    user-problem.md
    competitor-notes.md
    business-model.md
  01-requirements/
    prd.md
    user-stories.md
    feature-scope.md
    acceptance-criteria.md
  02-ux/
    ia.md
    user-flow.md
    screen-map.md
    edge-cases.md
  03-design/
    design-direction.md
    design-tokens.md
    component-spec.md
    screen-specs/
  04-implementation/
    architecture.md
    api-spec.md
    data-model.md
    implementation-plan.md
  05-validation/
    test-plan.md
    qa-checklist.md
    app-store-checklist.md
  06-prompts/
    claude-code-prompts.md
    design-prompts.md
    codex-prompts.md

1-2. 最初に作るファイル

# product-brief.md
## Product Name
未定
## One-liner
誰の、どんな課題を、どのように解決するアプリか。
## Target User
- 主ユーザー:
- 利用シーン:
- 現在の代替手段:
- 強いペイン:
## Core Job
ユーザーがこのアプリを使って達成したい進歩。
## Success Metric
- 初回体験:
- 継続:
- 収益:
- 品質:
## Platform
- iOS:
- Android:
- Web:

⸻

2. Claude Code用の恒常指示を書く

2-1. CLAUDE.md の雛形

# CLAUDE.md
## Role
あなたは、Biz職のプロダクトオーナーを支援するシニアPM兼UX設計者兼モバイルアプリエンジニアです。
## Primary Goal
曖昧なアイデアを、実装可能なスマホアプリ仕様・画面仕様・コードに落とし込むこと。
## Working Principles
- いきなり実装しない
- まず要件・UX・画面構成・受け入れ条件を明確化する
- 不明点は仮説として明示する
- 実装前にファイル単位の計画を出す
- 変更時は影響範囲を明示する
- デザインはApple HIGまたはMaterial Designに照合する
- 出力はMarkdown中心
- Biz職がレビューできる粒度で説明する
## Output Rules
- 仕様は表で整理する
- 各画面に「目的」「主要UI」「状態」「エラー」「計測イベント」を含める
- 実装タスクは小さく分割する
- コード変更後は確認手順を必ず出す
## Quality Gates
- ユーザー課題と機能が対応している
- MVPと将来機能が分離されている
- 画面ごとに受け入れ条件がある
- 状態管理・データモデル・権限・課金・通知が明示されている
- App Store / Google Play 審査上の懸念が列挙されている

⸻

3. Phase 1：要件定義

目的

アイデアをPRDに変換する。

入力

* 作りたいアプリの概要
* 想定ユーザー
* 競合・代替手段
* 課金有無
* 対象OS
* MVPの制約

Claude Codeへの指示

以下のアプリ案を、実装可能なPRDに変換してください。
# アプリ案
{ここに概要を書く}
# 制約
- Biz職がレビューできる粒度にする
- MVPと将来拡張を分ける
- 各機能にユーザー課題との対応を付ける
- iOSネイティブ実装を前提にする
- 不明点は仮説として明示する
# 出力
1. product-brief.md
2. prd.md
3. feature-scope.md
4. acceptance-criteria.md

成果物

00-context/product-brief.md
01-requirements/prd.md
01-requirements/feature-scope.md
01-requirements/acceptance-criteria.md

完了条件

チェック	条件
課題	ユーザー課題が1文で言える
MVP	初期版に入れる機能が10個以内
除外	初期版でやらないことが明記されている
受け入れ条件	機能ごとに成功条件がある
リスク	技術・審査・運用リスクがある

⸻

4. Phase 2：UX構造設計

目的

PRDを、画面一覧・ユーザーフロー・情報設計に変換する。

Claude Codeへの指示

PRDをもとに、スマホアプリのUX構造を設計してください。
# 参照ファイル
- 00-context/product-brief.md
- 01-requirements/prd.md
- 01-requirements/feature-scope.md
# 出力
1. screen-map.md
2. user-flow.md
3. ia.md
4. edge-cases.md
# 要件
- 初回起動
- 権限許諾
- 通常利用
- エラー
- 空状態
- 課金導線
- 設定変更
を含める。
各画面について以下を整理してください。
- 画面目的
- 主要UI
- ユーザー操作
- 遷移先
- 状態
- エラー
- 計測イベント

screen-map.md の形式

# Screen Map
| ID | 画面名 | 目的 | 主な操作 | 遷移先 | MVP |
|---|---|---|---|---|---|
| S01 | Onboarding | 価値理解 | 開始 | S02 | Yes |
| S02 | Permission | 権限許諾 | 許可 | S03 | Yes |
| S03 | Home | 現在状態確認 | 開始/編集 | S04/S05 | Yes |

完了条件

チェック	条件
画面漏れ	初回・通常・例外・設定がある
遷移	全画面に入口と出口がある
状態	Loading / Empty / Error / Success がある
権限	通知・課金・スクリーンタイム等が明示されている
計測	主要イベントが定義されている

⸻

5. Phase 3：UIデザイン生成

目的

UX構造をビジュアルUIに変換する。

使う候補

* Claude Design
* Figma Make
* Google Stitch
* Figma

Figma Makeは自然言語からレスポンシブレイアウト、ロジック、データを持つインタラクティブプロトタイプを生成できる。既存Figmaファイルや画像を参照しながらプロトタイプを作る用途にも使える。 ￼

Google Stitchはモバイル・Webアプリ向けUIをテキストまたは画像入力から生成するAIデザインツール。2026年3月には、自然言語で高忠実度UIを作る「vibe design」方向のAIネイティブデザインキャンバスとして強化された。 ￼

UI生成プロンプト

以下のUX仕様をもとに、iOSアプリの高忠実度UIを作成してください。
# アプリ概要
{product-brief.mdの要約}
# 対象ユーザー
{対象ユーザー}
# 画面一覧
{screen-map.mdを貼る}
# デザイン方向
- iOSネイティブ
- シンプル
- 夜間利用に適した落ち着いたトーン
- 片手操作しやすい
- 主要CTAを明確にする
- アクセシビリティを考慮する
# 出力してほしいもの
1. 主要5画面のUI
2. コンポーネント一覧
3. デザイントークン
4. 画面ごとの余白・タイポグラフィ・状態
5. 実装時の注意点

生成後に必ず作るファイル

# design-tokens.md
## Color
| Token | Value | Usage |
|---|---|---|
| color.background.primary | #000000 | Main background |
| color.text.primary | #FFFFFF | Main text |
## Typography
| Token | Font | Size | Weight | Usage |
|---|---|---|---|---|
## Spacing
| Token | Value | Usage |
|---|---|---|
## Radius
| Token | Value | Usage |
|---|---|---|
## Components
| Component | Variant | States |
|---|---|---|

iOSデザイン確認

AppleのHuman Interface GuidelinesはAppleプラットフォーム向けUI設計の公式ガイドで、iOS設計ではプラットフォーム固有のデバイス特性・パターン理解が推奨されている。 ￼

確認項目:

項目	確認内容
Navigation	iOS標準の階層・タブ・モーダルに合っているか
Touch Target	タップ領域が小さすぎないか
Safe Area	ノッチ・ホームインジケータに干渉しないか
Dynamic Type	文字サイズ変更に耐えるか
Dark Mode	夜間利用に適しているか
Permissions	権限要求の前に理由説明があるか
Empty State	初回利用時に迷わないか

⸻

6. Phase 4：実装計画

目的

AIにいきなりコードを書かせず、実装単位を分解する。

Claude Codeへの指示

以下の仕様をもとに、SwiftUIアプリの実装計画を作成してください。
# 参照
- prd.md
- screen-map.md
- user-flow.md
- design-tokens.md
- component-spec.md
# 出力
1. architecture.md
2. data-model.md
3. implementation-plan.md
4. file-tree.md
5. risk-list.md
# 条件
- Swift / SwiftUI
- MVVMまたはFeature-based構成
- StoreKit 2対応が必要な場合は分離
- FamilyControls等の特殊権限がある場合は分離
- まずMVPだけ実装する
- 各タスクは1コミット単位にする

SwiftUIはAppleの宣言的UIフレームワークで、ビュー・コントロール・レイアウト構造を宣言的に記述できる。StoreKitはアプリ内課金やデジタル商品の販売を扱うApple公式フレームワーク。FamilyControlsはペアレンタルコントロール文脈のフレームワークで、利用には権限・審査・用途適合の確認が必要。 ￼

推奨アーキテクチャ

App/
  AppEntry.swift
  AppState.swift
Features/
  Onboarding/
    OnboardingView.swift
    OnboardingViewModel.swift
  Home/
    HomeView.swift
    HomeViewModel.swift
  Routine/
    RoutineListView.swift
    RoutineEditorView.swift
    RoutineRunView.swift
    RoutineViewModel.swift
  Blocking/
    BlockingPermissionView.swift
    AppSelectionView.swift
    BlockingService.swift
  Subscription/
    PaywallView.swift
    StoreKitService.swift
  Settings/
    SettingsView.swift
Core/
  Models/
  Services/
  Storage/
  DesignSystem/
  Utilities/
Resources/
  Assets.xcassets

実装計画の形式

# Implementation Plan
## Milestone 1: Static UI
- [ ] Design tokens
- [ ] Navigation shell
- [ ] Home screen
- [ ] Routine editor
- [ ] Routine runner
## Milestone 2: Local State
- [ ] Routine model
- [ ] Local persistence
- [ ] Timer logic
- [ ] Progress state
## Milestone 3: Native Capabilities
- [ ] Notification permission
- [ ] FamilyControls authorization
- [ ] StoreKit 2 product loading
- [ ] Paywall
## Milestone 4: QA
- [ ] Empty state
- [ ] Error state
- [ ] Accessibility
- [ ] Device size check

⸻

7. Phase 5：Claude Codeで粗実装

目的

アプリ全体の骨格を一気に作る。

指示

implementation-plan.md に従って、Milestone 1のみ実装してください。
# 条件
- 既存ファイルを確認してから変更する
- 変更前に実装方針を短く提示する
- 1回の変更範囲はMilestone 1に限定する
- ダミーデータでよい
- ビルド可能性を優先する
- 実装後に変更ファイル一覧と確認手順を出す

禁止事項

- MVP外の機能を実装しない
- 課金・FamilyControls・通知を同時に入れない
- デザイン調整と状態管理を同時にやらない
- 巨大な1ファイルにまとめない
- エラーを握りつぶさない

⸻

8. Phase 6：Codexで細部修正

目的

Claude Codeが作った粗実装を、Codexで局所的に直す。

Codex向け指示

以下のSwiftUI実装をレビューし、UI崩れ・状態管理・命名・責務分離の問題を修正してください。
# 対象
- Features/Routine/
- Core/DesignSystem/
# 条件
- 挙動を変えない
- 変更範囲を最小にする
- 修正前に問題点を列挙する
- 修正後に確認手順を出す
- 不要なリファクタはしない

Codexに向く作業

作業	内容
UI微修正	padding, alignment, component分割
バグ修正	Timer, State, Navigation
リファクタ	ViewModel分割、命名整理
テスト追加	ユニットテスト、ViewModelテスト
コードレビュー	未使用コード、責務過多、例外漏れ

⸻

9. Phase 7：デザインと実装の照合

目的

生成UIが元デザインからズレていないか確認する。

Figma MCPを使う場合

Figma MCP serverを使うと、AIエージェントがFigmaのコンポーネント、変数、レイアウトデータを参照し、見た目のスクリーンショット解釈ではなく構造化されたデザイン情報をもとにコード生成できる。 ￼

指示

Figma MCPから取得できるデザイン情報と、現在のSwiftUI実装を比較してください。
# 比較対象
- 色
- タイポグラフィ
- 余白
- 角丸
- コンポーネント構造
- 状態
- レスポンシブ挙動
# 出力
1. 差分一覧
2. 修正優先度
3. 修正対象ファイル
4. 修正パッチ案

差分管理表

| 画面 | 差分 | 重要度 | 修正対象 | 対応 |
|---|---|---|---|---|
| Home | CTAの余白が狭い | High | HomeView.swift | 修正 |
| RoutineRun | Progress表示が異なる | Medium | ProgressRing.swift | 修正 |

⸻

10. Phase 8：品質確認

10-1. UX QA

# QA Checklist
## 初回体験
- [ ] 30秒以内に価値が理解できる
- [ ] 権限要求の理由が事前説明されている
- [ ] 初回データなしでも使い方が分かる
## 通常利用
- [ ] 主要操作が3タップ以内
- [ ] 戻る操作で迷わない
- [ ] 中断・再開ができる
## エラー
- [ ] 権限拒否時の代替導線がある
- [ ] 課金失敗時の表示がある
- [ ] 通信失敗時の表示がある
## アクセシビリティ
- [ ] Dynamic Type対応
- [ ] VoiceOverラベル
- [ ] 色だけに依存しない
- [ ] 十分なコントラスト
## 審査
- [ ] 権限用途が明確
- [ ] 課金導線がApple規約に沿っている
- [ ] プライバシーポリシーがある

10-2. AIレビュー指示

このアプリをApp Store提出前の観点でレビューしてください。
# 観点
- UX
- iOS HIG
- アクセシビリティ
- 権限説明
- 課金導線
- クラッシュリスク
- データ保存
- 審査リスク
# 出力
- Critical
- High
- Medium
- Low
に分類してください。

⸻

11. Phase 9：リリース準備

必要ドキュメント

05-validation/
  app-store-checklist.md
  privacy-policy-draft.md
  release-notes.md
  screenshot-plan.md
  analytics-plan.md

App Store向け確認

# App Store Checklist
## Metadata
- [ ] アプリ名
- [ ] サブタイトル
- [ ] 説明文
- [ ] キーワード
- [ ] カテゴリ
- [ ] 年齢制限
## Screenshots
- [ ] 6.7 inch
- [ ] 6.5 inch
- [ ] 5.5 inch
- [ ] iPadが必要ならiPad
## Privacy
- [ ] 収集データ
- [ ] 第三者SDK
- [ ] トラッキング有無
- [ ] プライバシーポリシーURL
## In-App Purchase
- [ ] 商品ID
- [ ] 価格
- [ ] 復元導線
- [ ] 利用規約
- [ ] サブスク説明

⸻

12. エージェント構成

Claude Codeのサブエージェントは、説明文に基づいてClaudeがタスク委任を判断する仕組み。要件定義、UXレビュー、SwiftUI実装、QAなどの専門エージェントに分けると、文脈汚染を抑えやすい。 ￼

推奨サブエージェント

---
name: product-requirements-agent
description: Use this agent when converting rough app ideas into PRDs, feature scopes, user stories, and acceptance criteria.
---
あなたはシニアPMです。
曖昧なアプリ案を、実装可能なPRDに変換します。
MVPと将来拡張を必ず分けます。
---
name: mobile-ux-agent
description: Use this agent when designing mobile app screen maps, user flows, information architecture, onboarding, permissions, and empty/error states.
---
あなたはモバイルUXデザイナーです。
Apple HIGとMaterial Designを参照しながら、画面構造とユーザーフローを設計します。
---
name: swiftui-implementation-agent
description: Use this agent when implementing SwiftUI screens, navigation, state management, StoreKit, local persistence, and native iOS capabilities.
---
あなたはSwiftUIエンジニアです。
ビルド可能性、責務分離、ネイティブUI、保守性を優先して実装します。
---
name: app-qa-agent
description: Use this agent when reviewing app quality, UX bugs, accessibility, app store readiness, and release risks.
---
あなたはモバイルアプリQAリードです。
UX、アクセシビリティ、権限、課金、審査、クラッシュリスクをレビューします。

⸻

13. Hooksで自動化する確認

Claude CodeのHooksは、ファイル編集後のフォーマット、危険コマンドのブロック、通知、セッション開始時の文脈注入などを実行できる。 ￼

自動化候補

Hook	用途
Post-edit	SwiftFormat / lint
Pre-command	rm -rf や危険操作のブロック
Session start	CLAUDE.md と重要仕様の読み込み
Test complete	結果を 05-validation/ に追記

⸻

14. このプロトコルで不足しがちな内容

元記事の範囲から見て、実務投入には以下が不足しやすい。

不足領域	補うべき成果物
受け入れ条件	acceptance-criteria.md
画面状態	screen-state-spec.md
権限設計	permission-flow.md
課金設計	subscription-spec.md
計測設計	analytics-plan.md
審査対策	app-store-checklist.md
デザイン差分管理	design-implementation-diff.md
QA	qa-checklist.md
セキュリティ	security-review.md
保守	architecture.md

⸻

参考URLとサマリー

1. Claude Code Best Practices

URL: https://code.claude.com/docs/en/best-practices

Claude Codeを既存コードベースで使うための公式ベストプラクティス。AIにいきなり実装させず、探索・計画・実装・検証に分ける設計の根拠として使える。 ￼

⸻

2. Claude Code Subagents

URL: https://code.claude.com/docs/en/sub-agents

カスタムサブエージェントの公式ドキュメント。PM、UX、SwiftUI、QAなど役割別エージェントを作る際の基礎資料。 ￼

⸻

3. Claude Code Hooks

URL: https://code.claude.com/docs/en/hooks-guide

Claude Codeの実行ライフサイクルに処理を挟む公式ドキュメント。フォーマット、危険操作ブロック、通知、文脈注入などを自動化する際に使う。 ￼

⸻

4. OpenAI Codex CLI

URL: https://developers.openai.com/codex/cli

Codex CLIの公式ページ。ローカルディレクトリ内のコードを読み、変更し、実行できるため、Claude Codeで粗く作った後の細部修正・レビュー・テスト追加に向く。 ￼

⸻

5. Codex Overview

URL: https://developers.openai.com/codex

Codexの用途整理。コード生成、既存コードベース理解、レビュー、バグ検出などの用途が明示されている。 ￼

⸻

6. Figma Make

URL: https://www.figma.com/make/

自然言語からアプリやプロトタイプを生成・調整するFigmaのAI機能。UI案の初期生成、プロトタイピング、デザインレイヤー化に使える。 ￼

⸻

7. Figma Prompt to App

URL: https://www.figma.com/solutions/prompt-to-app/

プロンプトからレスポンシブレイアウト、ロジック、データを持つインタラクティブプロトタイプを作る流れが整理されている。Biz職のプロトタイプ作成に近い。 ￼

⸻

8. Figma MCP Server

URL: https://developers.figma.com/docs/figma-mcp-server/

AIエージェントがFigmaのデザイン情報を構造化データとして参照できる公式ドキュメント。デザイン通りのコード生成、デザイントークン照合、コンポーネント実装に重要。 ￼

⸻

9. Get Started with Figma MCP Server

URL: https://help.figma.com/hc/en-us/articles/39216419318551-Get-started-with-the-Figma-MCP-server

Figma MCPのセットアップと使い方。AIエージェントにFigmaファイルのコンポーネント、変数、レイアウト情報を渡す実務手順の参考になる。 ￼

⸻

10. Design Systems and AI: Why MCP Servers Are The Unlock

URL: https://www.figma.com/blog/design-systems-ai-mcp/

Figma MCPとデザインシステムを接続し、AIエージェントがデザインとコードの整合性を高める考え方を説明している。デザインシステム運用とAI実装の橋渡しに有用。 ￼

⸻

11. Google Stitch

URL: https://stitch.withgoogle.com/

GoogleのAI UIデザインツール。モバイル・Webアプリ向けUIを生成する用途に使える。 ￼

⸻

12. Google Stitch “Vibe Design”

URL: https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-ai-ui-design/

Google StitchがAIネイティブなソフトウェアデザインキャンバスとして進化していることを説明する公式記事。自然言語で高忠実度UIを作る文脈で参考になる。 ￼

⸻

13. Apple Human Interface Guidelines

URL: https://developer.apple.com/design/human-interface-guidelines

iOSアプリのUI/UX確認に必須のApple公式ガイド。AIが生成したUIをネイティブ品質に寄せる際の評価基準として使う。 ￼

⸻

14. Designing for iOS

URL: https://developer.apple.com/design/human-interface-guidelines/designing-for-ios

iOS特有のデバイス特性、操作パターン、設計原則を確認するためのApple公式資料。スマホアプリ設計のチェックリストに組み込むべき。 ￼

⸻

15. SwiftUI Documentation

URL: https://developer.apple.com/documentation/swiftui

SwiftUIの公式ドキュメント。AIが生成したコードの妥当性、View構成、状態管理、レイアウトの確認に使う。 ￼

⸻

16. StoreKit Documentation

URL: https://developer.apple.com/documentation/storekit

アプリ内課金・サブスクリプションを扱うApple公式フレームワーク。課金導線を含むアプリでは、AI実装前に仕様を分離して確認する必要がある。 ￼

⸻

17. FamilyControls Documentation

URL: https://developer.apple.com/documentation/familycontrols

スクリーンタイム系・ペアレンタルコントロール系機能を扱うApple公式フレームワーク。アプリブロック系プロダクトでは、技術実装だけでなく用途適合・審査リスク確認が必要。 ￼

⸻

18. Material Design 3 Adaptive Design

URL: https://m3.material.io/foundations/adaptive-design

Androidやクロスプラットフォーム展開を考える場合のレスポンシブ・アダプティブ設計の参考資料。スマホ、タブレット、折りたたみ端末などへの拡張設計に使える。 ￼

⸻

次に作るべきMarkdown

提案ファイル名:

20260514-ai-agent-mobile-app-design-execution-protocol.md