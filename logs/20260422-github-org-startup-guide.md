# GitHub Organization スタートアップガイド

> 対象：初めてOrganizationを立ち上げる組織  
> 前提：GitHub Freeプランからスタート、1〜5名の小規模チームを想定  
> 方針：最初からガバナンスの「骨格」だけ入れる。肉付けは運用しながら行う

-----

## README 設計の原則（全リポジトリ共通）

**すべてのリポジトリの `README.md` は「最初に読むルールブック」として機能させる。**

新しいメンバーがリポジトリを開いたとき、READMEだけを読めば「何のリポジトリか・何を書いていいか・どう変更するか」がわかる状態を保つ。

### README に必ず含める4項目

|項目                 |内容                         |
|-------------------|---------------------------|
|**① このリポジトリは何か**   |1〜2行で目的を明示する               |
|**② 誰が使い・誰がメンテするか**|対象者と管理チームを明示する             |
|**③ ルール**          |書いていいこと・書いてはいけないこと、または開発ルール|
|**④ 変更するときの手順**    |PR必須かどうか、誰のApproveが必要か     |

### リポジトリ種別ごとのREADME要件

|リポジトリ              |必須項目|追加項目                      |
|-------------------|----|--------------------------|
|`.github`（Org共通）   |①②③④|**Public公開のため機密情報不可の警告**  |
|`ai-native-commons`|①②③④|テンプレートの使い方、フィードバックフロー     |
|short PJ           |①②④ |セットアップ手順                  |
|long PJ            |①②③④|セットアップ手順、ブランチ戦略、コントリビュート方法|

-----

## 始める前に決めること（30分）

手を動かす前に、以下の3点だけ口頭で合意しておく。

|決定事項            |理由                           |
|----------------|-----------------------------|
|Ownerを2名以上決める   |1名だと単一障害点。アカウント削除でOrgが宙に浮く   |
|PJ分類基準を決める（下表）  |short/longを判断できないとテンプレートが使えない|
|コミットメッセージの言語を決める|後から変えると履歴が汚れる                |

**PJ分類基準（例）**

|分類               |条件               |
|-----------------|-----------------|
|short（短命・ユーティリティ）|3ヶ月以内の見込み、またはソロ開発|
|long（長期育成）       |3ヶ月超の見込み、または複数人開発|

-----

## Phase 1｜Organization 基盤構築（Day 1・約1時間）

### Step 1-1：Organization を作成する

1. GitHub右上「＋」→「New Organization」
1. プラン：**Free** を選択
1. Organization name：チーム名を半角英数で入力
1. **この画面ではメンバーを招待しない**（権限未設定のまま入れると後が面倒）

### Step 1-2：デフォルト権限を確認する

Settings → Member privileges → Base permissions

```
推奨設定：Read（デフォルトのまま変えない）
```

> 権限はTeam経由で付与するので、ここはReadのままでよい。

### Step 1-3：Owner を追加する

People → Invite member → ロールを **Owner** に設定して招待

- Owner は必ず2名以上にする
- Ownerが1名の場合、その人の退職・アカウント削除でOrgの管理権を失う

-----

## Phase 2｜Team 設計と権限付与（Day 1・約30分）

### Step 2-1：Team を作成する

Teams → New team で以下の3チームを最初に作る。

|Team名       |権限                 |対象           |
|------------|-------------------|-------------|
|`dev-team`  |Write              |一般開発者        |
|`reviewer`  |Write + レビュー担当として明示|コードレビュー担当者   |
|`admin-team`|Admin              |プラットフォーム管理者のみ|


> Admin は絶対に全員に付けない。Admin権限があるとブランチ保護をバイパスできる。

### Step 2-2：メンバーを招待する（Team経由）

People → Invite member → ロールは **Member** で招待  
→ 招待受諾後、該当の Team に追加する

個人に直接権限を振らない。**Team単位で管理することで、メンバーの追加・削除が1箇所の操作で完結する。**

-----

## Phase 3｜.github リポジトリ構築（Day 2・約1時間）

Org共通の設定を置くリポジトリ。名前は `.github` 固定。

### Step 3-1：.github リポジトリを作成する

Repositories → New → リポジトリ名を `.github` にする

> **Public にする理由**：PRテンプレート・IssueテンプレートはGitHubの仕様上、  
> Publicリポジトリにないと他のリポジトリへ自動適用されない。  
> そのため `.github` リポジトリには機密情報を一切書かないルールを設ける（次のステップ）。

### Step 3-2：README.md を作成する（ルールブック）

`.github/README.md` を作成する。これがこのリポジトリの憲法になる。

```markdown
# [Org名] / .github

このリポジトリは Organization 全体に自動適用される共通設定を管理します。
**Public リポジトリのため、外部から誰でも閲覧できます。**

---

## このリポジトリに置いてよいもの

汎用的な規約・テンプレートのみ置きます。

- コミットメッセージ形式・出力言語などの汎用ルール
- PR・Issue のテンプレート
- Copilot への汎用指示（「日本語で出力」「Markdownで返す」など）

---

## このリポジトリに書いてはいけないもの

以下は絶対に書かない。

| NG の内容 | 具体例 |
|-----------|--------|
| 社内システムの URL・ドメイン | `https://internal.example.co.jp` |
| チーム名・担当者名・メールアドレス | `@yamada-taro` |
| インフラ・技術スタックの詳細 | 「本番は AWS ap-northeast-1 の RDS を使用」 |
| 規制・コンプライアンス要件の詳細 | 「〇〇法に準拠するため…」 |
| セキュリティポリシーの詳細 | 「脆弱性スキャンは〇〇ツールで実施」 |

**迷ったときの判断基準**

> 「この内容を競合他社が見たら困るか？」  
> 困らない → 書いてよい  困る → 書かない

---

## PJ 固有の情報はどこに書くか

各 PJ リポジトリ（Private）内の `.github/copilot-instructions.md` に書いてください。

---

## ファイル構成

.github/
├── README.md                     ← このファイル
├── copilot-instructions.md       ← Org共通のCopilot指示（汎用ルールのみ）
├── pull_request_template.md      ← 全リポジトリに自動適用されるPRテンプレート
└── ISSUE_TEMPLATE/
    ├── bug.yml
    └── feature.yml

---

## 変更するときのルール

- 変更は必ず PR 経由で行う
- `admin-team` の Approve が必要
- 機密情報・PJ固有情報を追加しようとしている場合、そのPRは却下する
```

### Step 3-3：PR テンプレートを配置する

`.github/pull_request_template.md` を作成する。

```markdown
## 変更内容
<!-- 何を・なぜ変えたかを書く -->

## 確認項目
- [ ] 自己レビュー済み
- [ ] テスト追加 or 既存テストがパスする
- [ ] ドキュメント更新（必要な場合）

## 関連 Issue
Closes #
```

### Step 3-4：Issue テンプレートを配置する

`.github/ISSUE_TEMPLATE/bug.yml` と `feature.yml` を作成する。

```yaml
# bug.yml
name: バグ報告
description: バグを報告する
body:
  - type: textarea
    id: description
    attributes:
      label: 不具合の内容
      placeholder: 何が起きているか
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: 再現手順
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: 期待する動作
```

```yaml
# feature.yml
name: 機能要望
description: 新機能・改善を提案する
body:
  - type: textarea
    id: motivation
    attributes:
      label: 背景・目的
    validations:
      required: true
  - type: textarea
    id: proposal
    attributes:
      label: 提案内容
    validations:
      required: true
```

### Step 3-5：Copilot 共通指示を配置する

`.github/copilot-instructions.md` を作成する。

```markdown
# [Org名] 共通指示

## 出力言語
日本語

## ドキュメント形式
Markdownファイル（.md）で出力する

## コミットメッセージ形式
Conventional Commits に従い、日本語で記述する

例：
- feat: ユーザー認証機能を追加
- fix: ログイン時のNullPointerExceptionを修正
- docs: READMEにセットアップ手順を追記
- chore: 依存パッケージをアップデート

## バグ票・ログ形式
JSON形式で出力する
```

-----

## Phase 4｜テンプレートリポジトリ構築（Day 2〜3・約2時間）

### Step 4-1：ai-native-commons リポジトリを作成する

プロンプトとテンプレートを育てる場所。新PJ立ち上げ時のコピー元になる。

```
ai-native-commons/
├── README.md                     ← ルールブック（次のステップで作成）
├── prompts/
│   └── _common/
│       ├── self-review.prompt.md
│       ├── bug-ticket.prompt.md
│       └── refactor.prompt.md
└── templates/
    ├── short-project/
    │   └── .github/
    │       ├── copilot-instructions.md
    │       └── prompts/
    │           ├── generate-code.prompt.md
    │           └── self-review.prompt.md
    └── long-project/
        └── .github/
            ├── copilot-instructions.md
            ├── CODEOWNERS
            ├── rules/
            │   ├── coding-rules.md
            │   └── branch-protection-checklist.md
            └── prompts/
                ├── generate-code.prompt.md
                ├── self-review.prompt.md
                └── bug-ticket.prompt.md
```

### Step 4-2：ai-native-commons の README.md を作成する（ルールブック）

```markdown
# ai-native-commons

Org全体で共有するプロンプト・テンプレートを管理するリポジトリです。
新しいPJを立ち上げるときは、ここからテンプレートをコピーして使います。

## 対象者・管理者

| 役割 | できること |
|------|-----------|
| 全メンバー | テンプレートのコピー・プロンプトの閲覧 |
| reviewer以上 | PRを通じてプロンプト・テンプレートの追加・修正 |
| admin-team | マージ・リポジトリ設定の変更 |

---

## テンプレートの使い方

1. `templates/short-project/` または `templates/long-project/` を選ぶ
2. 該当フォルダを新しいPJリポジトリの `.github/` にコピーする
3. `copilot-instructions.md` の末尾にPJ固有の補足を追記する（5〜10行）

short / long の判断基準はスタートアップガイドを参照してください。

---

## プロンプトをフィードバックするときのルール

開発中に良いプロンプトが生まれたら、このリポジトリに還元してください。

- 直接pushは禁止。必ずPRを出す
- PRには「どのPJで・どんな課題に使ったか」を書く
- `reviewer` または `admin-team` のApproveを得てからマージする

---

## ファイル構成

ai-native-commons/
├── README.md           ← このファイル
├── prompts/
│   └── _common/        ← PJを問わず使える汎用プロンプト
└── templates/
    ├── short-project/  ← 3ヶ月以内 or ソロ開発向け
    └── long-project/   ← 3ヶ月超 or 複数人開発向け
```

### Step 4-3：ai-native-commons のアクセス権を設定する

このリポジトリはOrg全体の知的財産。**誰でも書き込める状態にしない。**

|Team        |権限               |
|------------|-----------------|
|`admin-team`|Admin            |
|`reviewer`  |Write（PR経由でのみマージ）|
|`dev-team`  |Read（閲覧・コピーのみ）   |

### Step 4-4：long-project テンプレートに CODEOWNERS を入れる

`templates/long-project/.github/CODEOWNERS` を作成する。

```
# デフォルト：admin-teamがすべてのファイルの所有者
*       @[Org名]/admin-team

# ルール・設定ファイルの変更は reviewer も必須
/.github/   @[Org名]/admin-team @[Org名]/reviewer
/rules/     @[Org名]/admin-team
```

### Step 4-5：ブランチ保護チェックリストを作成する

ブランチ保護はGUIでしか設定できないため、手順書を残しておく。

`templates/long-project/.github/rules/branch-protection-checklist.md`

```markdown
# ブランチ保護設定チェックリスト

リポジトリ作成後、Settings → Branches → Add rule で以下を設定する。

## main ブランチ

- [ ] Require a pull request before merging
  - [ ] Required approvals: 1（ソロ） or 2（チーム）
- [ ] Require status checks to pass before merging（CI導入後に有効化）
- [ ] Do not allow bypassing the above settings
  - Adminもバイパス不可にする（重要）

## 設定完了サイン
設定者：          日付：
```

-----

## Phase 5｜最初の PJ を立ち上げる（各PJ・約10分）

```
1. short か long かを判断する（「始める前に決めること」の基準を参照）
        ↓
2. ai-native-commons/templates/ から該当フォルダをコピー
        ↓
3. README.md を作成する（下のテンプレートを使う）
        ↓
4. copilot-instructions.md の末尾にPJ固有の補足を追記（5〜10行）
        ↓
5. long-project の場合：branch-protection-checklist.md に従いブランチ保護を手動設定
        ↓
6. 開発開始
        ↓
7. 良いプロンプトが生まれたら ai-native-commons にPRを出してフィードバック
```

### PJ リポジトリの README テンプレート（short 用）

```markdown
# [リポジトリ名]

[このリポジトリが何をするものか、1〜2行で書く]

## 対象者・管理者

- 使用者：[誰が使うか]
- 管理：`admin-team`

## セットアップ

# 手順をここに書く

## 変更するときのルール

- 変更は PR 経由で行う
- `dev-team` の誰か1名の Approve が必要
```

### PJ リポジトリの README テンプレート（long 用）

```markdown
# [リポジトリ名]

[このリポジトリが何をするものか、1〜2行で書く]

## 対象者・管理者

- 使用者：[誰が使うか]
- 管理：`admin-team`

## セットアップ

# 手順をここに書く

## ブランチ戦略

- `main`：リリース済みコード。直接pushは禁止
- `develop`：開発の統合ブランチ（採用する場合）
- `feature/[機能名]`：機能開発ブランチ

## コーディングルール

`.github/rules/coding-rules.md` を参照してください。

## コントリビュート方法

1. `feature/` ブランチを切る
2. コミットメッセージは Conventional Commits 形式で書く
3. PRを出し、`reviewer` チームの Approve を得てからマージする

## 変更するときのルール

- 変更は必ず PR 経由で行う
- `reviewer` チームの Approve が必要
- `.github/` 以下の変更は `admin-team` の Approve も必要（CODEOWNERS参照）
```

-----

## チェックリスト：Phase 1〜5 の完了確認

|項目                                              |完了|
|------------------------------------------------|--|
|Owner が2名以上いる                                   |☐ |
|デフォルト権限が Read になっている                            |☐ |
|Team が3つ作られ、メンバーがTeam経由で参加している                  |☐ |
|`.github` リポジトリが Public で存在する                   |☐ |
|`.github/README.md` に機密情報不可ルールが明記されている          |☐ |
|PRテンプレート・Issueテンプレートが入っている                      |☐ |
|Org共通の `copilot-instructions.md` が入っている         |☐ |
|`ai-native-commons` が存在し、README.md が入っている       |☐ |
|`ai-native-commons` のアクセス権が設定されている              |☐ |
|short/long テンプレート（READMEテンプレート含む）がコピーできる状態になっている|☐ |
|各PJリポジトリに README.md が存在する                       |☐ |

-----

## 次フェーズのための考慮リスト

現時点では導入不要。以下の**トリガー条件**が発生したときに検討する。

### アクセス・認証まわり

|トリガー               |検討事項                                                  |
|-------------------|------------------------------------------------------|
|機密情報を扱うPJが出てきた     |Branch ProtectionのDo not allow bypassing を必ずAdmin含め有効化|
|メンバーが10名を超えた       |Team階層の見直し（サブチーム導入）                                   |
|退職・異動が発生した         |メンバー削除フローの明文化。IdP連携（SCIM）の検討                          |
|外部委託メンバーが入った       |Outside Collaboratorとして招待し、Teamには入れない                 |
|Enterprise移行を検討し始めた|EMU（Enterprise Managed Users）の評価を開始                   |

### ブランチ・レビューまわり

|トリガー             |検討事項                                                |
|-----------------|----------------------------------------------------|
|mainへの直接pushが発生した|Branch ProtectionのAdmin bypass禁止を即時有効化              |
|レビューが形骸化してきた     |Require approvals from code owners（CODEOWNERS連動）を有効化|
|CIを導入した          |Require status checks to pass をブランチ保護に追加            |
|コミットの真正性が問題になった  |Require signed commits を有効化                         |
|PJが5つを超えた        |Enterprise Rulesetsへの移行を検討（全Org一括適用）                |

### セキュリティまわり

|トリガー                 |検討事項                                          |
|---------------------|----------------------------------------------|
|秘密情報をコミットしたインシデントが起きた|GitHub Advanced Security（Secret Scanning）の導入評価|
|依存パッケージの脆弱性が問題になった   |Dependabot alerts の有効化                        |
|セキュリティ要件が厳しい顧客がついた   |Code Scanning（CodeQL）の導入評価                    |
|本番環境へのデプロイ権限を絞りたい    |Environment Protectionの設定                     |

### 監査・ログまわり

|トリガー             |検討事項                                    |
|-----------------|----------------------------------------|
|「誰がいつ何を変えたか」を問われた|Audit Logの確認フローを整備（Enterpriseなら外部SIEM転送）|
|権限設定が属人化してきた     |権限をYAML管理（GitOps化）し、CODEOWNERS で監視      |
|コンプライアンス要件が発生した  |ログ保持期間の要件確認と外部保管の検討                     |

### プロンプト・テンプレートまわり

|トリガー                   |検討事項                               |
|-----------------------|-----------------------------------|
|プロンプトが20個を超えた          |スタック別（python/, typescript/）にフォルダ分け |
|PJが5個を超えた              |GitHub Actionsで共通プロンプトの自動同期を導入     |
|プロンプトの品質にばらつきが出た       |レビュー基準（どんなプロンプトをマージするか）を rules/ に追加|
|AIツールが複数になった（Copilot以外）|prompts/ をツール別に整理                  |

### ドキュメント・READMEまわり

|トリガー                 |検討事項                               |
|---------------------|-----------------------------------|
|READMEが形骸化・陳腐化してきた   |四半期ごとのREADMEレビューを習慣化する             |
|オンボーディングに時間がかかるようになった|CONTRIBUTING.md を整備し、README からリンクする|
|リポジトリの目的が変わった        |README の「このリポジトリは何か」を最初に書き直す       |
|非エンジニアがリポジトリを使い始めた   |README に専門用語の注釈を追加する               |

### チーム・文化まわり

|トリガー               |検討事項                                            |
|-------------------|------------------------------------------------|
|非エンジニアがGitHubを使い始めた|GitHub Projectsのカンバン導入とIssueコメント文化の醸成           |
|チームメンバーが増えた        |CONTRIBUTING.md を整備し、オンボーディング資料化                |
|コードレビューのルールを統一したい  |rules/coding-rules.md を充実させる                    |
|ブランチ戦略を決めたい        |Git Flow / GitHub Flow / Trunk Based のどれかを選択し文書化|