# Personal AI Mentor Kit 議事録

## 0. ファイル名提案

`20260530-personal-ai-mentor-kit-meeting-notes.md`

---

## 1. 基本情報

| 項目 | 内容 |
|---|---|
| 日付 | 2026-05-30 |
| テーマ | 自分用AIメンター作成パッケージの構想整理 |
| 議題 | AIメンターの設計、専門性、スキルランタイム、ソース設計、公開可能性、仕様書化 |
| 参加者 | Masa、ChatGPT |
| 成果物 | 初期設計仕様、公開戦略、ソース戦略、ユーザー入力ガイドライン |

---

## 2. 会議の目的

AIエージェントではなく、**AIメンター**を作る構想について、初期設計を整理する。

特に、以下を明確にすることを目的とした。

```text
- AIメンターとは何か
- どのような構造で動かすか
- どのような専門性を持たせるか
- RAGではなくスキル型にする理由
- Claude Code上でどう実装するか
- ユーザーがどの情報を提供すべきか
- 将来的に公開パッケージ化できるか
```

---

## 3. 背景

最初のアイデアは、以下のようなものだった。

```text
AIエージェントならぬ、AIメンターを作る。
ベンチマークしたい人の発信を収集して蓄積する層、
蓄積した情報から学び取りたい領域に情報を整理して抽出する層、
抽出した学びをプロトコル化してAIメンターのプロンプトにする層を作る。
そのうえで、AIメンターにレビューしてもらう仕組みを設計する。
```

議論を通じて、当初の「発信を収集してRAG的に参照する」設計から、**Claude Code上で必要なメンタースキルを呼び出すSkill Runtime型**へと設計方針が変化した。

---

## 4. 主要論点と決定事項

---

## 4.1 AIメンターの定義

### 議論内容

AIメンターは、単なるチャットボットやAIエージェントではない。  
また、特定人物を完全再現するものでもない。

AIメンターは、ベンチマーク対象者の発信・実績・判断基準から以下を抽出し、ユーザーの相談に活用するものとして定義した。

```text
- 判断原則
- 問い
- 評価基準
- 失敗パターン
- レビュー観点
- 介入パターン
- 次アクション化の手順
```

### 決定事項

AIメンターは、以下のように定義する。

```text
AIメンター
= 3つ程度の専門性を持つ人物の発信・判断基準・問い・助言パターンを構造化し、
  ユーザーとの会話の中で必要なメンタースキルを呼び出して、
  実用的なレビューと次アクションを返すシステム
```

### 補足

重要なのは、人物の口調や人格を模倣することではない。  
価値があるのは、その人の「判断の型」をユーザーの思考や成果物の改善に使うことである。

---

## 4.2 メンター1人に持たせる専門性

### 議論内容

当初は、1人のメンターに対して1領域の専門性を持たせる想定だった。  
しかし、それでは回答が偏り、メンタリングというより単一視点の評価AIになってしまう懸念があった。

一度は以下の整理が出た。

```text
Primary Domain
Secondary Domain
Counterweight Domain
```

ただし、これは「偏り補正」の設計に寄りすぎており、Masaの意図とは異なっていた。

Masaの意図は、以下だった。

```text
3つぐらいの専門領域を実際に語れる人をAIメンターにしたい。
その人が持つ複数の専門性からアドバイスを受けたい。
```

### 決定事項

AIメンターは、以下の構造で設計する。

```text
Person
  ├── Expertise 1
  ├── Expertise 2
  └── Expertise 3
        ↓
  Cross-domain Integration Style
        ↓
  Mentor Advice
```

### 例

| メンター類型 | 専門性1 | 専門性2 | 専門性3 |
|---|---|---|---|
| 事業創造型 | 事業戦略 | プロダクト | 組織・採用 |
| クリエイティブ事業型 | クリエイティブ | マーケティング | 事業化 |
| 思想・文章型 | 文章 | 思想 | メディア設計 |
| 投資・未来洞察型 | 投資 | テクノロジー | 社会変化 |
| 研究・実装型 | 研究 | 技術実装 | 教育・普及 |

### 重要判断

専門性は、AI側が人工的に足すものではない。  
対象人物が実際に語っている領域、成果を出している領域、ユーザーが学びたい領域から抽出する。

---

## 4.3 RAGではなくSkill Runtime型にする

### 議論内容

知識ベースは、RAGのような「関連文書を検索して回答するもの」ではなく、**スキルのようなもの**として扱う方がよいという認識になった。

Masaのイメージは、Claude Code上で動く以下の構造だった。

```text
ユーザーとの会話
→ 相談内容を理解
→ 必要なメンタースキルを選択
→ スキルを実行
→ 必要なら複数スキルを組み合わせる
→ メンターとして統合回答する
```

### 決定事項

本システムの中心はRAGではなく、**Skill Runtime**とする。

```text
User Conversation
→ CLAUDE.md
→ skill-registry.yaml
→ relevant skill
→ knowledge cards
→ integrated mentor response
```

### RAG型との違い

| 観点 | RAG型 | Skill Runtime型 |
|---|---|---|
| 中心概念 | 文書検索 | スキル呼び出し |
| 入力 | 質問 | 会話文脈・相談内容・成果物 |
| 処理 | 関連チャンクを取得 | 必要なレビュー手順を選択・実行 |
| 出力 | 根拠付き回答 | メンター的介入・問い・レビュー・改善案 |
| 知識単位 | チャンク | Skill / Knowledge Card |
| 価値 | 情報想起 | 判断・レビュー・助言 |

### 補足

RAGは完全に不要ではない。  
ただし、主役ではなく、スキル実行時の根拠補強として使う。

---

## 4.4 Claude Code上の実装イメージ

### 議論内容

初期実装は、専用WebアプリではなくClaude Code上で始める方針になった。

理由は以下。

```text
- Markdown/YAMLでスキルやカードを管理しやすい
- ファイル構造がそのままメンターOSになる
- DBやWeb UIより先に設計検証ができる
- ユーザー自身が改善しやすい
- 公開パッケージ化しやすい
```

### 決定事項

初期構成は以下。

```text
personal-ai-mentor-kit/
  ├── README.md
  ├── CLAUDE.md
  ├── mentor.md
  ├── user-profile.yaml
  ├── expertise.yaml
  ├── skill-registry.yaml
  ├── skills/
  │   ├── idea-review.md
  │   ├── writing-review.md
  │   ├── decision-review.md
  │   ├── contradiction-finder.md
  │   └── next-action-planner.md
  ├── cards/
  │   ├── worldview/
  │   ├── principles/
  │   ├── questions/
  │   ├── rubrics/
  │   ├── tactics/
  │   ├── cases/
  │   ├── anti-patterns/
  │   └── interaction-patterns/
  ├── sources/
  │   ├── source-list.yaml
  │   ├── raw/
  │   └── notes/
  ├── protocols/
  │   ├── onboarding-flow.md
  │   ├── user-input-guide.md
  │   ├── source-collection-guide.md
  │   ├── evidence-policy.md
  │   ├── response-format.md
  │   └── skill-router.md
  ├── sessions/
  ├── examples/
  │   └── fictional-mentor/
  └── evals/
      ├── skill-selection.md
      ├── review-quality.md
      └── mentor-usefulness.md
```

---

## 4.5 初期スキル

### 決定事項

MVPでは多数のスキルを用意せず、実用性の高い5つに絞る。

| Skill ID | 役割 |
|---|---|
| `idea_review` | 新規事業・企画アイデアをレビューする |
| `writing_review` | 文章・発信・メッセージをレビューする |
| `decision_review` | 意思決定や選択肢を整理する |
| `contradiction_finder` | 矛盾・見落とし・弱い仮説を探す |
| `next_action_planner` | 助言を次の行動に落とす |

### Skillの構成

```text
Skill
= Purpose
+ Trigger
+ Inputs
+ Procedure
+ Rubric
+ Output Format
+ Failure Modes
```

---

## 4.6 Knowledge Cardの位置づけ

### 議論内容

Knowledge Cardは、RAG用のチャンクではなく、Skillが実行時に参照する判断材料として扱う。

### 決定事項

Knowledge Cardは以下の種類に分類する。

| Card Type | 内容 |
|---|---|
| Worldview Card | 世界観・価値観 |
| Principle Card | 原則 |
| Decision Rule Card | 判断ルール |
| Question Card | 問い |
| Rubric Card | 評価基準 |
| Checklist Card | 手順・確認項目 |
| Tactic Card | 具体的な手札 |
| Case Card | 事例 |
| Anti-pattern Card | 失敗パターン |
| Tension Card | トレードオフ |
| Interaction Pattern Card | 相談への返し方 |
| Review Pattern Card | レビューの型 |

### 重要判断

思想カードだけが増えると、AIメンターは説教臭くなる。  
特に重視すべきカードは以下。

```text
- Question Card
- Rubric Card
- Tactic Card
- Anti-pattern Card
- Interaction Pattern Card
- Review Pattern Card
```

---

## 4.7 ソース設計

### 議論内容

ネット上にある公開発信は、具体的な手練手札というより思想の表明に寄りがちである、という問題意識が提示された。

公開発信だけでは、以下は取りやすい。

```text
- 思想
- 原則
- 世界観
- 価値観
```

一方で、AIメンターに本当に必要な以下は不足しがち。

```text
- 具体的な手札
- 判断の分岐条件
- 実務での打ち手
- 失敗時の修正方法
- 相手への問いかけ方
- レビューの順序
```

### 決定事項

ソースは5層で設計する。

```text
Layer 1: Worldview Source
Layer 2: Principle Source
Layer 3: Case Source
Layer 4: Practice Source
Layer 5: Interaction Source
```

| Layer | 役割 | 得られるもの |
|---|---|---|
| Worldview Source | 価値観・世界観を取る | 何を重視する人か |
| Principle Source | 判断原則を取る | どう考える人か |
| Case Source | 事例判断を取る | どんな場面でどう判断するか |
| Practice Source | 手札・手順を取る | 具体的に何をするか |
| Interaction Source | メンタリング挙動を取る | どう問い、どう返すか |

### 優先すべきソース

```text
1. Q&A / AMA / 相談回答
2. 公開レビュー / 添削 / コーチング
3. インタビュー / 対談
4. 講義 / ワークショップ / 教材
5. ブログ / エッセイ / note
6. SNS
```

### 重要判断

AIメンターに最も効くのは、理念ではなく「どう返すか」である。  
そのため、Q&A、相談回答、公開レビュー、添削、ワークショップ質疑を重視する。

---

## 4.8 ユーザー入力ガイドライン

### 議論内容

AIメンター作成には、ユーザーが情報を出す必要がある。  
そのため、設計仕様書はプロダクト仕様だけではなく、ユーザー入力ガイドラインにもなる必要がある。

### 決定事項

ユーザー入力は5カテゴリに分ける。

```text
1. Mentor Input
2. Expertise Input
3. Source Input
4. User Context Input
5. Use Case Input
```

| 入力カテゴリ | 目的 |
|---|---|
| Mentor Input | 誰をベースにするかを定義する |
| Expertise Input | 3つ程度の専門性を定義する |
| Source Input | 根拠・原則・手札になるソースを提供する |
| User Context Input | ユーザー本人の目的・課題・制約を定義する |
| Use Case Input | AIメンターをどの場面で使うかを定義する |

### 最小入力

```yaml
minimum_start:
  mentor_name:
  what_you_want_to_learn:
  three_expertise_candidates:
  first_use_case:
```

### 入力不足時の方針

```text
- 毎回大量の情報を求めない
- 足りない場合は最大3問まで質問する
- 進められる場合は仮定を明示して暫定レビューする
- 不足情報はSession Logに残す
```

---

## 4.9 公開パッケージ化

### 議論内容

初期は自分用に作るが、うまくいきそうなら「自分のためのAIメンター作成パッケージ」として公開してもよいのではないか、という論点が出た。

### 決定事項

公開する場合は、「特定人物のAIメンター」ではなく、**自分用AIメンターを作るためのキット**として公開する。

### 公開するもの

```text
- テンプレート
- CLAUDE.md
- skill-registry.yaml
- skills/*.md
- Knowledge Card雛形
- ソース収集ガイド
- 入力ガイドライン
- Evidence Policy
- 評価チェックリスト
- 架空メンターのサンプル
```

### 公開しないもの

```text
- 実在人物の発信本文
- 長文引用
- 実在人物の発信を大量に要約したカード
- 個人相談ログ
- 非公開メモ
- 本人になりすますプロンプト
```

### 推奨メッセージ

```text
原則・問い・スキルから、自分専用のAIメンターを作る。
```

### 避けるべき表現

```text
著名人を完全再現するAIを作る。
本人のように相談できる。
好きな人物をAI化できる。
```

---

## 5. 決定事項まとめ

| No. | 決定事項 |
|---:|---|
| 1 | AIメンターは本人再現ではなく、原則・問い・判断基準を使うメンタリングシステムとする |
| 2 | メンター1人には、実際に語れる3つ程度の専門性を持たせる |
| 3 | 知識ベースはRAGではなく、Skill Runtimeとして設計する |
| 4 | 初期実装はClaude Code上のMarkdown/YAMLベースで行う |
| 5 | 初期スキルは5つに絞る |
| 6 | Knowledge CardはSkillの判断材料として扱う |
| 7 | ソースは5層で整理し、特に相談応答・公開レビュー・Q&Aを重視する |
| 8 | ユーザー入力ガイドラインを仕様に組み込む |
| 9 | 入力不足時は最大3問まで質問し、可能なら仮定を明示して進める |
| 10 | 公開する場合は、完成済みメンターではなく作成キットとして公開する |

---

## 6. 未決事項

| No. | 未決事項 | 補足 |
|---:|---|---|
| 1 | 最初に作るAIメンターのベンチマーク対象者 | まだ具体名は確定していない |
| 2 | 3つの専門性の具体設定 | 対象者確定後に決める |
| 3 | 初期ソース30〜50件の選定 | Q&A・対談・講義を優先して探す |
| 4 | Knowledge Cardの作成方法 | 手動中心か、AI補助ありかを検討 |
| 5 | Claude Code用リポジトリの実装開始タイミング | 仕様書をもとに次工程で着手 |
| 6 | 公開時のライセンス | OSSか有料テンプレートか未定 |
| 7 | 架空メンターサンプルの内容 | 公開用には実在人物ではなく架空メンターが必要 |

---

## 7. 次アクション

### 7.1 最優先

```text
1. 最初に作るAIメンターのベンチマーク対象者を1人決める
2. その人の3専門性を仮置きする
3. 初期ユースケースを1つに絞る
```

推奨する初期ユースケース:

```text
- 新規事業アイデアレビュー
- 文章レビュー
- 意思決定レビュー
```

### 7.2 次にやること

```text
4. ソース候補を30件集める
5. ソースを5層に分類する
6. Knowledge Cardを20〜30枚だけ試作する
7. idea_reviewスキルを最初に作る
8. Claude Code上でCLAUDE.mdとskill-registry.yamlを作る
9. 自分の相談を5件流して検証する
```

### 7.3 検証観点

```text
- 適切なスキルが呼ばれるか
- 回答が一般論で終わらないか
- 3専門性の観点が出るか
- 次アクションが具体的か
- 自分の判断やアウトプットが改善されるか
```

---

## 8. 作成済み関連ドキュメント

| ファイル名 | 内容 |
|---|---|
| `20260530-ai-mentor-system-design.md` | AIメンター全体構想 |
| `20260530-multi-domain-ai-mentor-design.md` | 複数レンズ型の設計案 |
| `20260530-triple-expertise-ai-mentor-model.md` | 3専門性型AIメンターの修正版 |
| `20260530-skill-based-ai-mentor-runtime.md` | Skill Runtime設計 |
| `20260530-ai-mentor-initial-design-spec.md` | 初期設計仕様書 |
| `20260530-personal-ai-mentor-kit-publication-strategy.md` | 公開戦略 |
| `20260530-ai-mentor-source-strategy.md` | ソース設計戦略 |
| `20260530-personal-ai-mentor-kit-design-spec.md` | ユーザー入力ガイド込みの設計仕様書 |

---

## 9. 議論から得られた重要な洞察

### 9.1 AIメンターは思想だけでは弱い

公開発信は思想・原則に寄りやすい。  
しかし、AIメンターに必要なのは、思想だけではなく以下である。

```text
- どう問うか
- どうレビューするか
- どの順序で見るか
- 何を見落とさないか
- どう次アクションに落とすか
```

### 9.2 3専門性がメンターの厚みを作る

1領域だけでは評価AIになりやすい。  
3つ程度の専門性があることで、メンターとしての奥行きが出る。

### 9.3 スキル型にすることで実用性が上がる

関連文書を検索するだけでは、メンタリングにはならない。  
相談内容に応じて、適切なスキルを選び、手順に沿って介入する必要がある。

### 9.4 ユーザー入力が品質を決める

AIメンターは、完全自動で高品質に生成できるものではない。  
ユーザーが、誰から何を学びたいか、どんな相談に使いたいか、どんな出力を避けたいかを出す必要がある。

### 9.5 公開するなら作成キットがよい

完成済みの実在人物メンターを公開するより、ユーザー自身が自分用AIメンターを作るためのキットとして公開する方が、価値と安全性のバランスがよい。

---

## 10. 最終整理

本プロジェクトは、以下のように定義された。

```text
Personal AI Mentor Kit
= Claude Code上で動く
  3専門性型
  スキル呼び出し型
  Markdown/YAMLベースの
  自分用AIメンター作成パッケージ
```

中核構造は以下。

```text
User Input
→ Mentor Profile
→ Expertise Definition
→ Source Collection
→ Knowledge Cards
→ Skill Registry
→ Claude Code Runtime
→ Mentor Review
→ Session Feedback
```

最初の検証では、1人のベンチマーク対象者、3専門性、5スキル、30件程度のソースに絞る。  
そこで有用性が確認できれば、個人データと実在人物カードを抜き、架空メンター例を入れて公開パッケージ化する。
