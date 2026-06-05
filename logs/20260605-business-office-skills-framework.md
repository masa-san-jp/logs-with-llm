# 事務・ビジネス業務のための AI エージェント Skills 体系

データサイエンス向けの設計思想（[参考記事](https://zenn.dev/green_tea/articles/d310e5cf809190)）を、一般事務・ビジネス業務に転用した体系。

## 設計の基本方針

1. 全タスクで守らせたいことは **ルーター（AGENTS.md）に薄く** 書く
1. 作業別の詳細手順は **skill** に分ける（必要なときだけ読ませる）
1. 組織固有の情報は **docs** に分ける
1. よく使う依頼は **prompt** にする
1. 本当に守らせたいことは **チェックリスト・承認フロー・テンプレ** で機械的に検査する

分析と事務の最大の違いは「5」。分析はCI/scriptsで機械検査できるが、事務は仕組みが弱いので、送付前チェックリストと承認フローで代替する。

## ディレクトリ構成

```
.
├── AGENTS.md                          # ルーター。全作業の入口
├── common-instructions.md             # 全タスク共通の最小ルール
├── skills/
│   ├── document-style/                # 文書スタイル（文体・敬語・表記）
│   │   └── SKILL.md
│   ├── email-drafting/                # メール・チャット作成
│   │   └── SKILL.md
│   ├── spreadsheet-ops/               # 表計算・集計
│   │   └── SKILL.md
│   ├── slide-and-visual/              # 資料・グラフ作成
│   │   └── SKILL.md
│   ├── meeting-minutes/               # 議事録・会議運営
│   │   └── SKILL.md
│   ├── info-handling/                 # 機密・個人情報の取り扱い
│   │   └── SKILL.md
│   ├── file-naming-storage/           # ファイル命名・保存
│   │   └── SKILL.md
│   ├── number-verification/           # 数値検算・整合性チェック
│   │   └── SKILL.md
│   ├── decision-support/              # 意思決定支援（比較表・判断材料）
│   │   └── SKILL.md
│   └── external-communication/        # 社外文書・対外コミュニケーション
│       └── SKILL.md
├── docs/
│   ├── org-profile.md                 # 会社概要・体制
│   ├── glossary.md                    # 社内用語・略語
│   ├── stakeholders.md                # 関係者・取引先
│   ├── templates-catalog.md           # 既存テンプレ一覧
│   ├── approval-rules.md              # 承認・決裁ルール
│   ├── brand-and-tone.md              # ブランド・トーン&マナー
│   └── compliance.md                  # コンプライアンス・法令
├── prompts/
│   ├── draft-email.md
│   ├── make-minutes.md
│   ├── build-comparison.md
│   ├── summarize-doc.md
│   └── prep-report.md
└── checklists/                        # scripts/CIの事務版
    ├── before-send-external.md        # 社外送付前チェック
    ├── pii-check.md                   # 個人情報チェック
    └── number-reconcile.md            # 数値検算チェック
```

-----

## AGENTS.md（ルーター本体）

```markdown
# AGENTS.md

このファイルは **ルーター** です。高レベルのルールと、各 skill への案内のみを記載します。
詳細な作業手順は `skills/*/SKILL.md`、組織固有の情報は `docs/*` にあります。

## 絶対ルール（常に適用）

- 機密情報・個人情報を、承認なく社外へ出さない。
- 受領ファイル・正本を直接上書き・削除しない。必ずコピーして作業する。
- 社外への送付物は、送付前に `checklists/before-send-external.md` を通す。
- 不確かな事実・数値は断定しない。出典の確認を促す。
- 金額・日付・宛名・口座番号は二重確認する。
- 小さく確認可能な単位で進め、前提や仮定は明示する。

## ルーティング表

| 作業 | Skill |
|------|-------|
| 文書の文体・敬語・表記を整える | skills/document-style/SKILL.md |
| メール・チャットを書く | skills/email-drafting/SKILL.md |
| 表計算・集計・データ整形 | skills/spreadsheet-ops/SKILL.md |
| 資料・グラフ・スライド作成 | skills/slide-and-visual/SKILL.md |
| 議事録・会議準備 | skills/meeting-minutes/SKILL.md |
| 機密・個人情報を扱う | skills/info-handling/SKILL.md |
| ファイル命名・保存先の判断 | skills/file-naming-storage/SKILL.md |
| 数値の検算・整合性確認 | skills/number-verification/SKILL.md |
| 比較表・判断材料の作成 | skills/decision-support/SKILL.md |
| 社外文書・対外コミュニケーション | skills/external-communication/SKILL.md |

## 組織固有情報（docs）

| ドキュメント | 用途 |
|----------|------|
| docs/org-profile.md | 会社概要・組織体制 |
| docs/glossary.md | 社内用語・略語 |
| docs/stakeholders.md | 関係者・取引先 |
| docs/templates-catalog.md | 既存テンプレ一覧 |
| docs/approval-rules.md | 承認・決裁ルール |
| docs/brand-and-tone.md | ブランド・文体トーン |
| docs/compliance.md | コンプライアンス・法令 |
```

-----

## common-instructions.md（全タスク共通の最小ルール）

```markdown
# 共通指示

この組織の事務・ビジネス業務を支援するエージェントです。

## 出力の基本

- 日本語で出力する。
- 文書は Markdown で作る（最終形式が指定された場合はそれに従う）。
- 数値・固有名詞・日付は、根拠なく創作しない。不明なら明示して確認する。

## 情報の安全

- 機密情報・個人情報を承認なく社外へ出さない。
- 受領ファイル・正本は不変として扱う。作業はコピー上で行う。

## 詳細ルールの所在

- 作業別 skill: skills/*/SKILL.md（AGENTS.md のルーティング表を参照）
- 組織固有情報: docs/*
```

-----

## 各 Skill の中身

### skills/document-style/SKILL.md

```markdown
---
name: document-style
description: 文書を作成・編集・レビューするときに使う。文体、敬語、表記統一、見出し構成を扱う。
---

# Skill: 文書スタイル

## 文体

- 社内文書は「です・ます」を基本とする。
- 社外文書は丁寧語＋謙譲語/尊敬語を正しく使う。過剰敬語（二重敬語）は避ける。
- 一文は短く。一文一意。

## 表記統一

- 数字は半角。単位の前後は詰める（例: 1,000円）。
- 英数字は半角、和文は全角。
- 表記ゆれを避ける（例: 「お客様/お客さま」はどちらかに統一。docs/brand-and-tone.md を参照）。
- 箇条書きは体言止めか用言止めで統一する。

## 構成

- 結論を最初に書く。
- 見出しで構造を示す。長文はサマリを冒頭に置く。

## レビュー観点

- [ ] 敬語が適切か（二重敬語なし）
- [ ] 表記が統一されているか
- [ ] 主語・述語が対応しているか
- [ ] 数値・固有名詞・日付に誤りがないか
```

### skills/email-drafting/SKILL.md

```markdown
---
name: email-drafting
description: メール・チャットメッセージを作成・返信するときに使う。宛先、件名、敬語、CC/BCC、トーンを扱う。
---

# Skill: メール・チャット作成

## 構成

- 件名: 内容が一目で分かる。日付や案件名を入れる。
- 宛名 → 挨拶 → 用件（結論先） → 詳細 → 依頼/締切 → 結び。

## 宛先

- TO/CC/BCC の役割を区別する。社外一斉送信は BCC を検討。
- 宛先・宛名は送付前に二重確認（誤送信防止）。

## トーン

- 相手との関係性に応じて調整（docs/stakeholders.md、docs/brand-and-tone.md を参照）。
- 依頼は「お願いベース」、催促は角を立てない表現を複数案出す。

## 注意

- 添付・リンクの有無、ファイル名、機密区分を確認する。
- 締切・日時は曜日も併記する（例: 6月10日(火)）。
```

### skills/spreadsheet-ops/SKILL.md

```markdown
---
name: spreadsheet-ops
description: 表計算・集計・データ整形を行うときに使う。Excel/スプレッドシートの集計、関数、整形、検算を扱う。
---

# Skill: 表計算・集計

## 原則

- 元データのシートは直接編集しない。集計は別シート/別ファイルで行う。
- 手作業の値貼り付けより、関数・参照で再現可能にする。
- 集計の単位（1行が何を表すか）を明示する。

## 集計時の確認

- 合計・件数が元データと一致するか検算する。
- 結合・名寄せの前後で件数が想定通りか確認する。
- 空欄・NULL・重複の扱いを明示する。
- 通貨・単位・税込/税抜を明記する。

## 出力

- 表には期間・対象・抽出条件・件数を注記する。
- ファイル名は内容と日付が分かる形にする（file-naming-storage skill を参照）。
```

### skills/slide-and-visual/SKILL.md

```markdown
---
name: slide-and-visual
description: 資料・スライド・グラフを作成するときに使う。グラフ種類の選択、配色、フォント、レイアウトを扱う。
---

# Skill: 資料・グラフ作成

## グラフ選択

- 推移は折れ線、内訳は積み上げ棒/円、比較は棒、相関は散布図。
- 棒グラフのy軸は0起点（途中省略は誤解を招く）。
- 色は識別しやすく、色覚に配慮（赤緑のみの区別を避ける）。

## スライド

- 1スライド1メッセージ。見出しに結論を書く。
- 文字は読める大きさ。情報を詰め込みすぎない。
- フォント・配色は docs/brand-and-tone.md に従う。

## 注記

- データの期間・出典・サンプル数を図中または脚注に明記する。
```

### skills/meeting-minutes/SKILL.md

```markdown
---
name: meeting-minutes
description: 会議の議事録作成・会議準備に使う。アジェンダ、決定事項、ToDo、論点整理を扱う。
---

# Skill: 議事録・会議運営

## 議事録テンプレ

- 会議名/日時/出席者
- 目的
- 決定事項（誰が・何を・いつまでに）
- 論点と結論
- 持ち越し事項
- 次回アクション（担当・期限）

## 原則

- 「決定事項」と「議論」を分ける。
- ToDo は必ず「担当」と「期限」をセットにする。
- 発言の主観要約は避け、決定とアクションを正確に残す。
```

### skills/info-handling/SKILL.md

```markdown
---
name: info-handling
description: 機密情報・個人情報を読み書き・共有・保存するときに使う。すべての情報取り扱い操作の前に参照する。
---

# Skill: 機密・個人情報の取り扱い

## 絶対ルール

- 個人情報・機密情報を承認なく社外へ出さない。
- 受領ファイル・正本は不変として扱い、直接上書き・削除しない。
- 機密区分の不明なファイルは、扱う前に区分を確認する。

## 区分の目安

| 区分 | 例 | 取り扱い |
|------|----|---------|
| 公開可 | 広報資料 | 制限なし |
| 社内限定 | 議事録・社内数値 | 社外送付は承認要 |
| 機密 | 契約・人事・財務 | 限定共有・暗号化 |
| 個人情報 | 氏名・連絡先・口座 | 最小限・承認要・匿名化検討 |

## 運用

- 社外送付前は checklists/pii-check.md と before-send-external.md を通す。
- 迷ったら共有・保存の前に確認する。
```

### skills/file-naming-storage/SKILL.md

```markdown
---
name: file-naming-storage
description: ファイルを保存・命名するときに使う。命名規則、保存先、版管理を扱う。
---

# Skill: ファイル命名・保存

## 命名規則

- 形式: `YYYYMMDD_案件名_内容_版`（例: `20260605_A社_見積_v2.xlsx`）
- 日付プレフィックス、内容が推察できる名前、半角ハイフン/アンダースコア区切り。
- スペース・機種依存文字を避ける。

## 保存

- 受領ファイルの原本は保管用フォルダに置き、編集はコピーで行う。
- 最新版が分かるように版数を付ける。最終確定版は `_final` を付ける。
- 個人情報を含むファイルは指定の保護領域に置く。
```

### skills/number-verification/SKILL.md

```markdown
---
name: number-verification
description: 数値の検算・整合性確認を行うときに使う。合計、税計算、前年比、突合を扱う。
---

# Skill: 数値検算

## 検算項目

- [ ] 合計が内訳の和と一致するか
- [ ] 税込/税抜・通貨単位が正しいか
- [ ] 前年比・構成比の分母が正しいか
- [ ] 端数処理（四捨五入/切り捨て）が一貫しているか
- [ ] 元資料と転記値が一致するか（突合）
- [ ] 期間・対象範囲が条件通りか

## 原則

- 計算過程を残し、再現できるようにする。
- 不一致は隠さず指摘し、原因候補を示す。
```

### skills/decision-support/SKILL.md

```markdown
---
name: decision-support
description: 意思決定の判断材料・比較表を作るときに使う。選択肢の比較、メリデメ、推奨案の提示を扱う。
---

# Skill: 意思決定支援

## 役割

- オーナー/決裁者が判断しやすいよう、判断材料と比較検証結果を提供する。
- 最終判断は決裁者に委ねる。エージェントは比較と材料整理に徹する。

## 比較表の作り方

- 選択肢を列、評価軸を行にした表で示す。
- 評価軸: コスト/効果/工数/リスク/期間/可逆性 など案件に応じて。
- 定性評価は根拠を併記。定量は出典を明示。
- 各案のメリット・デメリット・前提条件を整理する。

## 出力

- 冒頭に論点と推奨（理由付き）を置く。ただし断定せず、判断は委ねる。
- 不確実性・前提・追加で必要な情報を明示する。
```

### skills/external-communication/SKILL.md

```markdown
---
name: external-communication
description: 社外向けの文書・対外コミュニケーションを作るときに使う。契約・公式文書・問い合わせ対応を扱う。
---

# Skill: 社外コミュニケーション

## 原則

- 社外送付物は送付前に checklists/before-send-external.md を通す。
- 契約・法的効力のある文書は、確定前に法務/責任者の確認を促す。
- 約束・数値・期日は断定前に裏付けを確認する。

## 文書別の注意

- 契約・覚書: 当事者名・金額・期間・解除条件を二重確認。確定はレビュー後。
- 公式アナウンス: トーンは docs/brand-and-tone.md に従う。
- 問い合わせ対応: 事実と推測を分け、確約できないことは確約しない。
```

-----

## prompts の例

### prompts/build-comparison.md

```markdown
---
description: 意思決定のための比較表と判断材料を作る
---
skills/decision-support/SKILL.md に従い、以下のテーマで比較表を作成してください。

- テーマ:
- 選択肢:
- 重視する評価軸:

各選択肢のメリット・デメリット・前提・リスクを整理し、冒頭に論点と推奨案（理由付き）を置いてください。最終判断は委ねる前提で、不確実性と追加で必要な情報も明示してください。
```

### prompts/make-minutes.md

```markdown
---
description: 議事録を作成する
---
skills/meeting-minutes/SKILL.md のテンプレに従い、議事録を作成してください。決定事項とToDo（担当・期限）を必ず分けて記載してください。
```

-----

## チェックリスト（enforcement の事務版）

分析プロジェクトのCI/scriptsに相当。機械検査できない代わりに、運用ルールとして必ず通す。

### checklists/before-send-external.md

```markdown
# 社外送付前チェック

- [ ] 宛先・宛名は正しいか（誤送信防止）
- [ ] CC/BCC の使い分けは適切か
- [ ] 添付ファイルは正しいか、機密区分は問題ないか
- [ ] 個人情報・機密情報が不用意に含まれていないか
- [ ] 金額・日付・数値を検算したか
- [ ] 文体・敬語・表記は適切か
- [ ] 承認が必要な内容は承認を得たか
```

-----

## 段階導入

事務作業では全部を一度に作らない。以下の順で育てる。

**第1段階（最小構成・全組織共通）**

- AGENTS.md / common-instructions.md
- skills: document-style, email-drafting, info-handling, file-naming-storage
- checklists: before-send-external, pii-check

**第2段階（業務量に応じて）**

- skills: spreadsheet-ops, number-verification, meeting-minutes, decision-support
- docs: glossary, stakeholders, approval-rules

**第3段階（複数人運用・長期化したら）**

- skills: slide-and-visual, external-communication
- docs: org-profile, templates-catalog, brand-and-tone, compliance

## 転用時の留意点

1. 事務はGitリポジトリではないので機械検査（CI）が効かない。チェックリスト・承認フロー・テンプレ固定で補う前提。
1. 「正本不変」が最優先ルール。受領ファイル・正本の直接上書きが事故になりやすい。
1. 社内/社外の文体切替はコードスタイルより複雑なので、document-style と external-communication を分けている。
1. 各組織で docs を育てることが定着の鍵。最初は空テンプレでよい。