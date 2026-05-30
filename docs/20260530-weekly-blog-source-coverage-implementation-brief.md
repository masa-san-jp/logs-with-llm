# Weekly Blog Source Coverage Improvement Brief

## 目的

`logs-with-llm` の週次ブログ自動生成において、複数のログが存在するにもかかわらず、生成結果が「一つのドキュメントだけを読んだような内容」に寄ってしまう問題を改善する。

今回の方針は、モデルを高価なものに変更するのではなく、**入力構造・抜粋抽出・プロンプト制約**によって改善すること。

## 前提

- 現在の per-file summarization 仕様は維持する。
- OpenAI model は `gpt-5.4-mini` のままでよい。
- 追加の LLM 呼び出しは原則増やさない。
- コスト最小化を重視する。
- ブログ素材としては、設計書・調査ログ・比較メモ・実装メモなどをすべて扱ってよい。
- 「何を調べていたか」「何を考えていたか」「どう設計したか」が記事に見えることを重視する。
- 語彙注入は最小限でよい。
- 前回ブログは内容要約ではなく、文体・構成・リズムの参照として使う。

## 現状の問題

現在の `scripts/generate_weekly_blog.py` は、以下の流れで週次ブログを生成している。

1. 対象期間のログファイルを収集する。
2. 各ログファイルを読み込む。
3. 各ログファイルを独立した LLM 呼び出しで要約する。
4. 要約結果を連結する。
5. 前回ブログを要約する。
6. 要約済みログと前回ブログ要約を使って、言語別にブログ本文を生成する。

この設計自体は問題ではない。

問題は、最終生成プロンプトに以下の制御が不足していること。

- 各ソースを明示的に区別する構造が弱い。
- 複数ソースをどの程度扱うべきかのカバレッジ要件がない。
- 一つのソースが記事全体を支配することを防ぐ制約がない。
- 各ソースから最低一つ具体ディテールを残す要件がない。
- 要約だけでは、元ログの具体性・温度感・判断の痕跡が消えやすい。
- 前回ブログ要約が「内容の継承」になりやすく、「文体参照」としては弱い。
- 語彙注入が強すぎると、複数ログの具体性より抽象テーマが前面に出すぎる。

## 改善方針

現在の要約パイプラインは維持する。

ただし、最終生成プロンプトに以下を追加する。

1. Source Cards
2. Raw Excerpts
3. Coverage Requirements
4. Previous Style Capsule
5. Relaxed Vocabulary Guidance

全体構造は以下にする。

```text
Raw logs
  ↓
Per-file summaries     ← 既存仕様を維持
  ↓
Source cards           ← 追加。ルールベースで生成
  ↓
Raw excerpts           ← 追加。LLMを使わず抽出
  ↓
Previous style capsule ← 追加。LLMを使わず抽出
  ↓
Final blog prompt
  ↓
Generated blog
```

## 実装対象ファイル

主に編集するファイル。

- `scripts/generate_weekly_blog.py`
- `scripts/tests/test_generate_weekly_blog.py`

必要に応じて更新するファイル。

- `docs/weekly-blog-generator-spec.md`
- `README.md`

## 非目標

今回やらないこと。

- 高価なモデルへの変更
- 追加の LLM 呼び出し
- 生成後の二段階レビュー LLM
- ブログ本文の固定テンプレート化
- 手動選別前提の運用
- ログの種類を限定すること

## 追加する関数

### 1. `extract_raw_excerpts()`

#### 目的

各ログファイルから、ブログ本文に具体性を戻すための生ログ抜粋をルールベースで抽出する。

#### シグネチャ案

```python
def extract_raw_excerpts(
    content: str,
    max_excerpts: int = 4,
    max_chars: int = 350,
) -> list[str]:
    ...
```

#### 要件

- LLMを呼ばない。
- Markdown本文を paragraph-like block に分割する。
- 空ブロックを除外する。
- コードフェンス全体を除外する。
- 巨大な表を除外する。
- 短すぎる断片を除外する。
- 長すぎるブロックは `max_chars` で切り詰める。
- 元文の表現をなるべく保持する。
- 最大 `max_excerpts` 件を返す。

#### 抽出対象として望ましいブロック

- 見出し直後の段落
- 太字 Markdown を含む段落
- 数値を含む段落
- 固有名詞・ツール名・コード識別子を含む段落
- 判断・設計意図・評価を含む段落
- 「結論」「目的」「評価」「注意」「重要」などの語を含む段落
- 「つまり」「一方で」「だから」「要するに」など、筆者の思考展開が見える段落

#### スコアリング用キーワード案

```python
KEY_MARKERS = [
    "目的",
    "結論",
    "評価",
    "重要",
    "注意",
    "設計思想",
    "仮説",
    "定義",
    "前提",
    "課題",
    "改善",
    "運用",
    "判断",
    "つまり",
    "一方で",
    "だから",
    "要するに",
    "必要",
    "狙い",
    "方針",
    "比較",
    "リスク",
]
```

#### 実装イメージ

```python
def extract_raw_excerpts(
    content: str,
    max_excerpts: int = 4,
    max_chars: int = 350,
) -> list[str]:
    blocks = _split_markdown_blocks(content)
    scored: list[tuple[int, int, str]] = []

    for idx, block in enumerate(blocks):
        normalized = _normalize_excerpt_block(block)
        if not _is_excerpt_candidate(normalized):
            continue

        score = _score_excerpt_candidate(normalized, idx, blocks)
        if score <= 0:
            continue

        excerpt = _truncate_excerpt(normalized, max_chars)
        scored.append((score, -idx, excerpt))

    scored.sort(reverse=True)

    result: list[str] = []
    seen: set[str] = set()
    for _, _, excerpt in scored:
        key = excerpt[:80]
        if key in seen:
            continue
        seen.add(key)
        result.append(excerpt)
        if len(result) >= max_excerpts:
            break

    return result
```

補助関数は必要に応じて追加する。

```python
def _split_markdown_blocks(content: str) -> list[str]:
    ...


def _normalize_excerpt_block(block: str) -> str:
    ...


def _is_excerpt_candidate(block: str) -> bool:
    ...


def _score_excerpt_candidate(block: str, index: int, blocks: list[str]) -> int:
    ...


def _truncate_excerpt(text: str, max_chars: int) -> str:
    ...
```

### 2. `build_source_cards()`

#### 目的

最終プロンプトに渡すため、各ログファイルを明示的な source card として構造化する。

#### シグネチャ案

```python
def build_source_cards(log_files_dict: dict[str, str]) -> str:
    ...
```

#### 出力形式

```md
## Source Card

- source: logs/20260524-disability-welfare-genai-training-60min-v2.md
- date: 2026-05-24
- raw_excerpts:
  - 個人が試行錯誤して便利に使うのではなく、効果のあったプロンプトを標準化し、誰が使っても同じ品質で再現できる状態を作る。
  - 個人技を磨かせる研修ではなく、組織知化・標準化・PDCAの起点となる人を育てる研修にする。
```

#### 要件

- 空ファイルはスキップする。
- 各 non-empty source file につき1つの Source Card を作る。
- `source` に相対パスを入れる。
- `date` は既存の `extract_date_from_path()` を利用する。
- 日付抽出できない場合は `unknown` とする。
- `raw_excerpts` には `extract_raw_excerpts()` の結果を入れる。
- raw excerpts が空の場合でも、source card 自体は残す。
- LLMは呼ばない。

#### 実装イメージ

```python
def build_source_cards(log_files_dict: dict[str, str]) -> str:
    cards: list[str] = []

    for source_name, content in log_files_dict.items():
        if not content.strip():
            continue

        d = extract_date_from_path(source_name)
        date_text = d.isoformat() if d else "unknown"
        excerpts = extract_raw_excerpts(content)

        lines = [
            "## Source Card",
            "",
            f"- source: {source_name}",
            f"- date: {date_text}",
            "- raw_excerpts:",
        ]

        if excerpts:
            for excerpt in excerpts:
                lines.append(f"  - {excerpt}")
        else:
            lines.append("  - (No suitable raw excerpt found.)")

        cards.append("\n".join(lines))

    return "\n\n---\n\n".join(cards)
```

### 3. `build_previous_style_capsule()`

#### 目的

前回ブログを「内容要約」としてではなく、「文体・構成・リズム参照」として渡す。

#### シグネチャ案

```python
def build_previous_style_capsule(language: str) -> str:
    ...
```

#### 要件

- 既存の `read_previous_blog(language)` を使う。
- LLMは呼ばない。
- 前回ブログがない場合は空文字を返す。
- 抽出するもの。
  - タイトル
  - 冒頭1〜2段落
  - H2見出し一覧
  - 末尾1〜2段落
- 前回ブログの内容が今回の記事を支配しないよう、全文は渡さない。

#### 出力形式

```md
## Previous Style Capsule

### Previous title
# 装置を分けると、見える

### Opening sample
今週は、ひとつの完成形を作るというより、いくつもの装置をどう分けて、どう接続するかを見ていた週でした。

### Heading pattern
- 収益化：作家性をどう装置化するか
- 検索：今ある情報にどう触れるか
- 制作物：名札ではなく、構造として残す

### Closing sample
私自身の制作でも、今後はこの分け方をもう少し意識したいです。
```

#### 実装イメージ

```python
def build_previous_style_capsule(language: str) -> str:
    raw = read_previous_blog(language)
    if not raw.strip():
        return ""

    title = _extract_markdown_title(raw)
    opening = _extract_opening_paragraphs(raw, max_paragraphs=2)
    headings = _extract_h2_headings(raw)
    closing = _extract_closing_paragraphs(raw, max_paragraphs=2)

    parts = ["## Previous Style Capsule", ""]

    if title:
        parts.extend(["### Previous title", title, ""])
    if opening:
        parts.extend(["### Opening sample", opening, ""])
    if headings:
        parts.extend(["### Heading pattern"])
        parts.extend([f"- {h}" for h in headings])
        parts.append("")
    if closing:
        parts.extend(["### Closing sample", closing, ""])

    return "\n".join(parts).strip()
```

補助関数は必要に応じて追加する。

```python
def _extract_markdown_title(markdown: str) -> str:
    ...


def _extract_h2_headings(markdown: str) -> list[str]:
    ...


def _extract_opening_paragraphs(markdown: str, max_paragraphs: int = 2) -> str:
    ...


def _extract_closing_paragraphs(markdown: str, max_paragraphs: int = 2) -> str:
    ...
```

### 4. `build_prompt()` の変更

#### 現在のシグネチャ

```python
def build_prompt(logs_text: str, prev_blog: str, post_date: date, language: str) -> str:
    ...
```

#### 変更後のシグネチャ案

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

#### 追加するセクション

```md
## Source cards with raw excerpts

{source_cards}
```

```md
## Previous style reference

{prev_style_capsule}
```

#### 追加する Coverage Requirements

日本語・英語の両方に追加する。

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

日本語版には、同趣旨の自然な日本語も追加してよい。

```text
カバレッジ要件:
- Source Card をそれぞれ別個の材料として扱う。
- 本文では少なくとも min(4, source数) 個の異なる Source Card に触れる。
- Source が1つしかない場合を除き、1つの Source だけで記事全体を支配しない。
- 扱った Source ごとに、プロジェクト名、意思決定、ツール名、比較観点、数値、具体ディテールのいずれかを最低1つ残す。
- 複数 Source を共通テーマで統合してよいが、単一の抽象エッセイに潰さない。
- 見出しには抽象概念だけでなく、できるだけ具体対象を含める。
- カバレッジ計画やチェックリストは出力しない。
```

### 5. 語彙注入の弱体化

現在のような `5〜15箇所` の強制注入はやめる。

#### 日本語ガイダンスの置換案

```text
- 語彙注入は任意。使う場合も3〜6箇所までに留める
- 「装置」「解像度」「手触り感」「仮説」などの抽象語は、具体対象を説明できる場合だけ使う
- 同じ抽象語を複数セクションで繰り返さない
- 抽象語よりも、ログに含まれる具体的な調査対象・設計判断・比較観点を優先する
```

#### 英語ガイダンスの置換案

```text
- Vocabulary injection is optional. If used, keep it to 3–6 instances.
- Abstract words such as mechanism, apparatus, texture, granularity, and hypothesis should be used only when they clarify a concrete source detail.
- Do not repeat the same abstract motif across multiple sections.
- Prefer concrete project names, tools, design decisions, comparison points, and source-specific details over abstract phrasing.
```

#### final gate の変更案

既存の「語彙注入が自然で過剰でない」は残してよいが、以下を追加する。

```text
- [ ] 複数の Source Card が本文に具体的に反映されている
- [ ] 1つの Source だけに記事が偏っていない
- [ ] 抽象テーマだけでなく、何を調べた・作った・比較したかが見える
```

英語版。

```text
- [ ] Multiple Source Cards are concretely reflected in the body
- [ ] The article is not dominated by a single source
- [ ] The post shows what was investigated, built, compared, or decided, not only an abstract theme
```

## `main()` の変更

### 現在の流れ

```python
log_files = collect_log_files(window_start, window_end)
log_files_dict = read_log_files(log_files)
aggregated_logs_summary = summarize_log_files(log_files_dict)

for language in SUPPORTED_LANGUAGES:
    prev_blog_summary = summarize_previous_blog(language)
    prompt = build_prompt(aggregated_logs_summary, prev_blog_summary, post_date, language)
    content = generate_blog_content(prompt)
```

### 変更後の流れ

```python
log_files = collect_log_files(window_start, window_end)
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

### 注意点

- `source_cards` は言語ごとに作り直す必要はない。
- `prev_style_capsule` は言語ごとに作る。
- `summarize_previous_blog()` は互換性や既存テストのために残してもよいが、`main()` では使わない。
- ログが存在しない場合は、source cards は空でもよい。
- ログが存在しない場合の placeholder 挙動は維持する。

## テスト追加

`tests/test_generate_weekly_blog.py` に以下を追加する。

### 1. `extract_raw_excerpts()` のテスト

#### 重要段落を返す

```python
def test_extract_raw_excerpts_returns_important_paragraphs():
    content = """
# Test

短い説明。

## 目的

この設計の目的は、個人技ではなく組織運用としてAI活用を定着させることです。

## その他

普通の説明文です。
"""
    excerpts = gen.extract_raw_excerpts(content)
    assert excerpts
    assert any("目的" in e or "組織運用" in e for e in excerpts)
```

#### 空本文では空配列

```python
def test_extract_raw_excerpts_empty_content():
    assert gen.extract_raw_excerpts("   ") == []
```

#### コードフェンスを避ける

```python
def test_extract_raw_excerpts_skips_code_fences():
    content = """
```python
print("important but code")
```

結論として、この運用は安全性を優先する。
"""
    excerpts = gen.extract_raw_excerpts(content)
    assert all("print(" not in e for e in excerpts)
    assert any("結論" in e for e in excerpts)
```

### 2. `build_source_cards()` のテスト

#### 全ソースパスを含む

```python
def test_build_source_cards_includes_all_source_paths():
    files = {
        "logs/20260524-a.md": "## 目的\n\n重要な本文です。",
        "logs/20260525-b.md": "## 結論\n\n別の重要な本文です。",
    }
    cards = gen.build_source_cards(files)
    assert "logs/20260524-a.md" in cards
    assert "logs/20260525-b.md" in cards
```

#### raw excerpts を含む

```python
def test_build_source_cards_includes_raw_excerpts():
    files = {
        "logs/20260524-a.md": "## 目的\n\nこの設計の目的は、運用改善です。",
    }
    cards = gen.build_source_cards(files)
    assert "raw_excerpts" in cards
    assert "運用改善" in cards
```

#### 空ファイルをスキップ

```python
def test_build_source_cards_skips_empty_files():
    files = {
        "logs/20260524-a.md": "   ",
        "logs/20260525-b.md": "## 結論\n\n重要な本文です。",
    }
    cards = gen.build_source_cards(files)
    assert "logs/20260524-a.md" not in cards
    assert "logs/20260525-b.md" in cards
```

### 3. `build_previous_style_capsule()` のテスト

#### タイトル・冒頭・見出し・末尾を抽出

```python
def test_build_previous_style_capsule_extracts_style_elements(tmp_path):
    blog_dir = tmp_path / "blog"
    blog_dir.mkdir()
    (blog_dir / "20260522-weekly.md").write_text(
        "# 前回タイトル\n\n"
        "冒頭段落1です。\n\n"
        "冒頭段落2です。\n\n"
        "## 見出しA\n\n"
        "本文A。\n\n"
        "## 見出しB\n\n"
        "本文B。\n\n"
        "締め段落です。\n",
        encoding="utf-8",
    )
    with mock.patch.object(gen, "BLOG_DIR", blog_dir):
        capsule = gen.build_previous_style_capsule("ja")

    assert "Previous Style Capsule" in capsule
    assert "前回タイトル" in capsule
    assert "冒頭段落1" in capsule
    assert "見出しA" in capsule
    assert "締め段落" in capsule
```

#### 前回ブログがなければ空

```python
def test_build_previous_style_capsule_empty_when_no_previous_blog(tmp_path):
    blog_dir = tmp_path / "blog"
    blog_dir.mkdir()
    with mock.patch.object(gen, "BLOG_DIR", blog_dir):
        assert gen.build_previous_style_capsule("ja") == ""
```

### 4. `build_prompt()` のテスト

#### source cards を含む

```python
def test_build_prompt_includes_source_cards():
    prompt = gen.build_prompt(
        logs_text="summary text",
        source_cards="## Source Card\n\n- source: logs/a.md",
        prev_style_capsule="",
        post_date=date(2026, 5, 30),
        language="ja",
    )
    assert "Source cards" in prompt or "Source Card" in prompt
    assert "logs/a.md" in prompt
```

#### coverage requirements を含む

```python
def test_build_prompt_includes_coverage_requirements():
    prompt = gen.build_prompt(
        logs_text="summary text",
        source_cards="## Source Card\n\n- source: logs/a.md",
        prev_style_capsule="",
        post_date=date(2026, 5, 30),
        language="en",
    )
    assert "Coverage requirements" in prompt
    assert "Do not let one source dominate" in prompt
```

#### previous style capsule を含む

```python
def test_build_prompt_includes_previous_style_capsule():
    prompt = gen.build_prompt(
        logs_text="summary text",
        source_cards="## Source Card\n\n- source: logs/a.md",
        prev_style_capsule="## Previous Style Capsule\n\n### Previous title\nOld",
        post_date=date(2026, 5, 30),
        language="en",
    )
    assert "Previous Style Capsule" in prompt
    assert "Old" in prompt
```

### 5. `main()` の接続テスト

既存の `main()` テストがある場合は、以下を確認する。

- `build_source_cards()` が呼ばれる。
- `build_previous_style_capsule()` が言語ごとに呼ばれる。
- `build_prompt()` に `source_cards` が渡る。
- `summarize_previous_blog()` は `main()` から呼ばれない。

## プロンプト全体の方向性

### 日本語版で重視すること

- 記事は単なる要約ではなく、週次の思考ログとして読む。
- ただし、抽象テーマに潰しすぎない。
- 何を調べたか、何を比較したか、何を設計したかを本文に残す。
- 複数の Source Card がある場合、それぞれが記事内に痕跡を残す。
- 見出しには具体対象を入れる。
- 語彙注入は任意で、最小限にする。

### 見出し例

悪い例。

```md
## 分解：役割の明確化
## 統合：装置間の静かな対話
## 身体性：実践への接続
```

良い例。

```md
## Claude Design：最初に型を作る意味
## 福祉研修：AIを個人技にしない設計
## Agent-Aiko：人格管理と常駐運用の分岐
## DB設計：状態ではなく出来事を残す
```

### 英語版で重視すること

- Avoid making the article a single abstract essay.
- Preserve source-level traces.
- Headings should include concrete subjects when possible.
- Raw excerpts should be used as grounding, not quoted excessively.
- Abstract vocabulary should be optional and light.

## 受け入れ条件

以下を満たせば完了。

- 既存テストが通る。
- 新規テストが通る。
- 追加の LLM 呼び出しが増えていない。
- `build_source_cards()` がログごとの Source Card を生成する。
- `extract_raw_excerpts()` が生ログ抜粋をルールベースで抽出する。
- `build_previous_style_capsule()` が前回ブログから文体参照情報を抽出する。
- `main()` が以下を最終プロンプトに渡す。
  - per-file summaries
  - source cards
  - raw excerpts
  - previous style capsule
  - coverage requirements
- 日本語プロンプトが語彙注入を強制しない。
- 生成された記事が、複数ログがある場合に複数の調査・設計・比較対象を可視化する。
- 一つのログだけに偏った記事になりにくい。

## 動作確認手順

### 1. テスト実行

```bash
pytest scripts/tests/test_generate_weekly_blog.py
```

### 2. 手動実行

```bash
BLOG_DATE=2026-05-29 BLOG_DAYS=7 python scripts/generate_weekly_blog.py
```

### 3. 生成プロンプト確認用の一時ログ出力

必要なら、デバッグ目的で prompt をファイルに保存するオプションを追加してもよい。

例。

```python
DEBUG_PROMPT_DIR = os.environ.get("DEBUG_PROMPT_DIR", "")
```

```python
if DEBUG_PROMPT_DIR:
    debug_dir = REPO_ROOT / DEBUG_PROMPT_DIR
    debug_dir.mkdir(parents=True, exist_ok=True)
    (debug_dir / f"{post_date}-{language}-prompt.md").write_text(prompt, encoding="utf-8")
```

ただし、この機能は必須ではない。

## エージェントへの作業指示

以下をそのままエージェントに渡してよい。

```md
# Task: Improve weekly blog source coverage

## Goal

Improve `scripts/generate_weekly_blog.py` so weekly blog posts no longer read as if they were based on only one source document.

Keep the current low-cost architecture:

- keep per-file summarization
- keep `gpt-5.4-mini`
- do not add extra LLM calls
- improve quality through deterministic preprocessing and prompt structure

## Required changes

1. Add deterministic raw excerpt extraction.
2. Add source card construction.
3. Replace previous blog summarization in `main()` with previous style capsule extraction.
4. Update `build_prompt()` to include source cards, raw excerpts, previous style capsule, and coverage requirements.
5. Relax vocabulary injection rules.
6. Add tests.
7. Update docs if needed.

## Acceptance criteria

- Existing tests pass.
- New tests pass.
- No extra LLM calls are introduced.
- Final prompt includes compressed summaries, source cards, raw excerpts, previous style capsule, and coverage requirements.
- Japanese prompt no longer forces 5–15 vocabulary injections.
- Generated posts visibly reference multiple source documents when multiple logs exist.
```

## 推奨実装順

1. `extract_raw_excerpts()` を実装する。
2. `build_source_cards()` を実装する。
3. `build_prompt()` に `source_cards` と coverage requirements を追加する。
4. `main()` に接続する。
5. テストを追加する。
6. `build_previous_style_capsule()` を実装し、`main()` を切り替える。
7. 語彙注入ガイダンスを弱める。
8. 仕様書を更新する。
9. 手動生成で 2026-05-29 週の出力を確認する。

## 確認観点

生成されたブログを読むときは、以下を見る。

- Claude Design だけの記事になっていないか。
- 福祉研修、Agent-Aiko/nullevi03、DB設計などの複数ログが見えるか。
- 見出しが抽象語だけになっていないか。
- 「何を調べたか」「何を比較したか」「何を設計したか」が分かるか。
- 語彙注入が過剰でないか。
- 前回ブログの内容を引きずりすぎていないか。
- raw excerpt 由来の具体ディテールが本文に残っているか。

## 補足

今回の改善は、モデル性能で解くのではなく、**入力の構造化で小さいモデルを制御する**ための変更である。

`gpt-5.4-mini` のままでも、以下が揃えば改善できる可能性が高い。

- Source Card によるソース単位の明示
- Raw Excerpt による具体性の補強
- Coverage Requirements による偏り抑制
- Previous Style Capsule による文体参照の軽量化
- 語彙注入の任意化

