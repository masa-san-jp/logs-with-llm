# 議事録：週次ブログ自動生成の品質改善方針

## 基本情報

- 日付: 2026-05-30
- 議題: `logs-with-llm` における週次ブログ自動生成アウトプットの品質改善
- 対象リポジトリ: `masa-san-jp/logs-with-llm`
- 主な対象ファイル:
  - `scripts/generate_weekly_blog.py`
  - `scripts/tests/test_generate_weekly_blog.py`
  - `docs/weekly-blog-generator-spec.md`

## 背景

週次ブログ自動生成の出力が、複数のログを材料にしているにもかかわらず、読後感として「一つのドキュメントだけを読んで書いたような内容」になっていた。

初期分析では「生ログを使わず、要約だけを使っていること」が品質低下要因として挙げられたが、確認の結果、要約ベースの仕様自体は以前から存在していた。したがって、主因は要約処理そのものではなく、最終生成時に複数ソースを扱うための制約やカバレッジ制御が不足していることだと整理した。

## 現状の課題

### 1. 複数ログのカバレッジ保証がない

現在の処理では、各ログを個別に要約し、それを集約して最終ブログ生成プロンプトに渡している。

ただし、最終生成プロンプト側に以下のような制約がない。

- 各ソースを別個の材料として扱うこと
- 何本以上のログを本文に反映すること
- 一つのログが記事全体を支配しないこと
- 各ログから具体的な痕跡を残すこと
- 抽象テーマだけに回収しないこと

そのため、LLMが「もっとも記事にしやすい一つのログ」を中心に据えてしまう可能性がある。

### 2. 抽象テーマに吸収されすぎる

直近の生成結果では、複数ログは一応参照されていたが、構成上は「分解」「統合」「身体性」などの抽象テーマに強く吸収されていた。

その結果、読者から見ると「何を調べていたのか」「どのログが材料になっているのか」が見えにくくなっていた。

### 3. 語彙注入が強すぎる

現行プロンプトでは、Masaらしい文体を出すために「装置」「解像度」「手触り感」などの語彙注入を強く指定している。

ただし、語彙注入が多すぎると、各記事が同じ抽象語に寄り、具体的な調査内容や検討内容が薄く見える。語彙注入は最小限に抑える方針とした。

### 4. 前回ブログの渡し方が内容継承に寄っている

前回ブログは現在、LLMで要約してから最終プロンプトに渡している。

しかし、前回ブログから引き継ぎたいのは内容そのものではなく、文体・リズム・構成感である。したがって、前回ブログは「要約」ではなく「スタイルカプセル」として渡す方が適切だと判断した。

## 合意した方針

### 基本方針

要約パイプラインは維持する。

ただし、最終生成プロンプトに以下を追加する。

1. ソースカード
2. 生ログ抜粋
3. カバレッジ制約
4. 前回ブログのスタイルカプセル

これにより、`gpt-5.4-mini` のまま、追加LLMコストを増やさずに、アルゴリズムとプロンプト構造で品質改善する。

## 決定事項

### 1. モデルは `gpt-5.4-mini` を維持する

コストを最小限に抑えたい方針のため、上位モデルへの変更は行わない。

改善は以下で行う。

- 入力構造の整理
- ルールベースの抜粋抽出
- 最終プロンプトのカバレッジ制御
- 語彙注入の弱体化

### 2. 生ログ抜粋を最終プロンプトに渡す

要約だけではなく、各ログからルールベースで抽出した生ログ抜粋を渡す。

目的は以下。

- 具体性を戻す
- 各ログの存在感を残す
- 記事が一つのログに偏ることを防ぐ
- LLMが本文内に具体ディテールを入れやすくする

### 3. 抜粋抽出はLLMを使わず、Pythonで実装する

追加コストを避けるため、抜粋抽出は決定的なルールで行う。

抽出候補の評価軸:

- 見出し直下の段落
- 太字を含む段落
- 数字を含む段落
- コード識別子やバッククォートを含む段落
- 判断語・結論語を含む段落
- 80〜500字程度の適度な長さの段落

使用するキーワード例:

```python
KEY_MARKERS = [
    "目的", "結論", "評価", "重要", "注意", "設計思想", "仮説",
    "つまり", "一方で", "だから", "要するに",
    "定義", "前提", "課題", "改善", "運用", "判断",
]
```

### 4. ソースカードを作る

各ログを以下のような構造で最終プロンプトに渡す。

```md
## Source Card

- source: logs/20260524-disability-welfare-genai-training-60min-v2.md
- date: 2026-05-24
- raw_excerpts:
  - ...
  - ...
  - ...
```

ソースカードは、各ログを独立した材料としてLLMに認識させるために使う。

### 5. 最終プロンプトにカバレッジ制約を追加する

追加する制約案:

```text
Coverage requirements:
- Treat each Source Card as a distinct source.
- Cover at least min(4, number_of_sources) distinct sources in the main body.
- Do not let one source dominate the article unless there is only one source.
- Each covered source must leave at least one concrete trace: project name, decision, tool name, comparison point, number, or direct detail.
- You may synthesize sources under a shared theme, but do not collapse them into a single abstract essay.
- Prefer headings that include concrete subjects, not only abstract concepts.
- Do not output a checklist or coverage plan.
```

### 6. 見出しは具体対象を含める方向にする

現状の「概念：切り口」形式は維持してもよいが、抽象語だけの見出しは避ける。

悪い例:

```text
分解：役割の明確化
統合：装置間の静かな対話
```

良い例:

```text
Claude Design：最初に型を作る意味
福祉研修：AIを個人技にしない設計
DB設計：状態ではなく出来事を残す
Agent-Aiko：人格管理と常駐化の違い
```

### 7. 語彙注入を弱める

現行の「5〜15箇所」の強制は廃止する。

新方針:

```text
- 語彙注入は任意
- 使う場合も3〜6箇所まで
- 「装置」「解像度」「手触り感」などの抽象語は、具体対象を説明できる場合だけ使う
- 同じ抽象語を複数セクションで繰り返さない
```

英語版も同様に、mechanism / apparatus などの強制使用を弱める。

### 8. 前回ブログはスタイルカプセルとして渡す

前回ブログをLLM要約するのではなく、ルールベースで以下を抽出する。

```md
## Previous Style Capsule

### Previous title
...

### Opening sample
冒頭1〜2段落

### Heading pattern
- ...
- ...

### Closing sample
末尾1〜2段落
```

目的:

- 前回記事の内容ではなく文体を参照する
- 今回の記事内容を前回記事が支配しないようにする
- 文体・リズム・構成感だけを継承する

## 実装対象

### 追加する関数

#### `extract_raw_excerpts()`

```python
def extract_raw_excerpts(
    content: str,
    max_excerpts: int = 4,
    max_chars: int = 350,
) -> list[str]:
    ...
```

要件:

- Markdown本文を段落単位に分割する
- 空ブロック、コードフェンス、巨大な表、短すぎる断片を除外する
- 決定的なヒューリスティックでスコアリングする
- 最大 `max_excerpts` 件を返す
- 各抜粋は `max_chars` 以内に丸める
- 原文表現を保持する

#### `build_source_cards()`

```python
def build_source_cards(log_files_dict: dict[str, str]) -> str:
    ...
```

要件:

- 空でないログごとに1枚のSource Cardを作る
- source pathを明示する
- 日付が抽出できる場合はdateを入れる
- `extract_raw_excerpts()` の結果を含める
- LLM呼び出しは行わない

#### `build_previous_style_capsule()`

```python
def build_previous_style_capsule(language: str) -> str:
    ...
```

要件:

- 指定言語の前回ブログを読む
- タイトル、冒頭、H2見出し一覧、末尾を抽出する
- LLM呼び出しは行わない
- 前回ブログがない場合は空文字を返す

### 変更する関数

#### `build_prompt()`

現行:

```python
def build_prompt(logs_text: str, prev_blog: str, post_date: date, language: str) -> str:
    ...
```

変更案:

```python
def build_prompt(
    logs_text: str,
    source_cards: str,
    prev_style_capsule: str,
    post_date: date,
    language: str,
) -> str:
    ...
```

追加するセクション:

```md
## Source cards with raw excerpts

{source_cards}
```

```md
## Previous style capsule

{prev_style_capsule}
```

さらに、Coverage requirementsを追加する。

#### `main()`

現行フロー:

1. ログ収集
2. ログ読み込み
3. ログ要約
4. 前回ブログ要約
5. 最終プロンプト生成
6. ブログ生成

変更後フロー:

1. ログ収集
2. ログ読み込み
3. ログ要約
4. ソースカード構築
5. 前回ブログのスタイルカプセル構築
6. 最終プロンプト生成
7. ブログ生成

擬似コード:

```python
log_files_dict = read_log_files(log_files)
aggregated_logs_summary = summarize_log_files(log_files_dict)
source_cards = build_source_cards(log_files_dict)

for language in SUPPORTED_LANGUAGES:
    prev_style_capsule = build_previous_style_capsule(language)
    prompt = build_prompt(
        aggregated_logs_summary,
        source_cards,
        prev_style_capsule,
        post_date,
        language,
    )
    content = generate_blog_content(prompt)
```

## テスト方針

`tests/test_generate_weekly_blog.py` に以下を追加する。

### 追加テスト

1. `extract_raw_excerpts()` が重要段落を返す
2. `extract_raw_excerpts()` が空本文で空リストを返す
3. `extract_raw_excerpts()` が短すぎる断片を除外する
4. `extract_raw_excerpts()` が最大件数を守る
5. `build_source_cards()` がすべてのsource pathを含む
6. `build_source_cards()` がraw excerptsを含む
7. `build_previous_style_capsule()` がtitle/opening/headings/closingを抽出する
8. `build_prompt()` がsource cardsを含む
9. `build_prompt()` がcoverage requirementsを含む
10. `main()` が `build_source_cards()` と `build_previous_style_capsule()` を呼ぶ

## 受け入れ条件

- 既存テストが通る
- 新規テストが通る
- 追加のLLM呼び出しが発生しない
- 最終プロンプトに以下が含まれる
  - 各ログの要約
  - Source Card
  - raw excerpts
  - Previous Style Capsule
  - Coverage requirements
- 日本語プロンプトが語彙注入を強制しない
- 英語プロンプトも語彙注入を強制しない
- 複数ログが存在する場合、生成記事に複数ソースの具体的痕跡が残る

## エージェントへの推奨作業順

1. `extract_raw_excerpts()` を実装する
2. `build_source_cards()` を実装する
3. `build_prompt()` に source cards と coverage requirements を追加する
4. `main()` を接続する
5. テストを追加・更新する
6. 前回ブログの style capsule 化を行う
7. 語彙注入の弱体化を行う
8. `docs/weekly-blog-generator-spec.md` を更新する

## 未決事項

- Source Cardに `estimated_type` を入れるかどうか
- raw excerptの件数を固定にするか、ログの長さに応じて変えるか
- 見出しルールをどこまで強制するか
- 記事内で全ソースを必ず扱うか、最大4〜5本に絞るか
- 生成後にソースカバレッジ検査を自動化するかどうか

## 補足

今回の改善は、モデル性能に頼るのではなく、入力構造と制約設計で品質を上げる方針である。

主眼は、記事の文体を派手に変えることではなく、以下を満たすことにある。

- 何を調べていたのかが見える
- 何を考えていたのかが見える
- 複数ログを読んでいることが本文から分かる
- 抽象テーマに寄せすぎず、具体的な検討内容が残る
- コストは増やさない

