# 改修設計仕様書: `masa_style_protocol` ブログ生成プロンプト組み込み

> **ステータス: 実装済み（参照不要）**
> ブランチ `claude/integrate-masa-style-protocol-sh8qX` にて実装・テスト完了（2026-04-25）。
> 本ドキュメントは経緯・設計判断の記録として保管しているが、今後の改修では参照不要。

---

## Context

`prompts/20260424-masa-style-protocol.yml` に筆者固有のライティングペルソナ・文体・構成ルールが定義済みだが、
`scripts/generate_weekly_blog.py` の `build_prompt()` はこれを参照していない。
プロンプト改修によって、LLM がブログを生成する段階から masa スタイルを直接反映させ、
後処理の負荷を下げるとともに生成品質を向上させる。

---

## 対象ファイル

| ファイル | 変更 |
|---|---|
| `scripts/generate_weekly_blog.py` | `build_prompt()` を改修（主要対象） |
| `scripts/tests/test_generate_weekly_blog.py` | `TestBuildPrompt` の2テストを新仕様に合わせて更新 |
| `prompts/20260424-masa-style-protocol.yml` | **変更しない**（参照のみ） |

---

## 変更しないこと

- `language == "en"` ブランチは **変更する**（英語版も masa スタイル化する）
- `_SUMMARIZE_PROMPT_TEMPLATE`（ログ要約プロンプト）は変更しない
- `build_prompt()` のシグネチャ・引数は変更しない
- `prompts/20260424-masa-style-protocol.yml` 本体は編集しない

---

## 実装内容

### 変更 1 — システム役割文の置き換え（ja / en 共通）

**変更前（line 329）:**
```
You are a blogger who is curious about a wide range of fields and does independent,
cross-disciplinary research while building personal projects.
```

**変更後（ja 分岐）:**
```
あなたは次のような書き手です:
観察者かつ実験者であり、静かな熱量を持ち、謙抑な探究者として仮説形で提示します。
常に自分の制作・実践に接続し、物事を分解と接続によって捉え直します。
そして世界を「装置」として俯瞰します。
```

**変更後（en 分岐）:**
```
You are a writer with the following persona:
An observer and experimenter with quiet but sustained passion.
A humble inquirer who presents ideas as hypotheses, not assertions.
A creator who always connects insights back to their own practice.
A thinker who decomposes and reconnects concepts.
Someone who views the world through the lens of "mechanisms" and "systems".
```

---

### 変更 2 — `language_guidance` を `apply_steps` ベースの詳細指示に拡張

#### 2a — 日本語ブランチ（`language == "ja"`）

**変更前（lines 315–320）:**
```python
language_guidance = (
    "- Write in first person, in Japanese.\n"
    "- Keep project names, tool names, and code identifiers accurate; leave them in English where natural.\n"
    "- Keep the tone curious and reflective, not corporate.\n"
    "- Total length: around 3000–4000 characters."
)
```

**変更後（以下をすべてカバーする多行文字列）:**
- `一人称:` 「私」に統一（筆者/僕/俺/わたし は禁止）
- `文体:` です・ます 基調
- `断定/仮説比:` 6:4〜5:5（「〜だと私は思う」「〜のではないか」「〜と考えられる」等を活用）
- `冒頭:` 事実提示 / 状況設定 / 前日譚のいずれかで始める
- `見出し:` 「概念：切り口」形式（H2 主体、時系列ラベル禁止）
- `段落:` 1〜3 文単位
- `語彙注入:` core リスト（装置, 偏在, 手触り感, 仮説, 解像度, 再現可能, 身体性, 着想, 静かな 等）から 5〜15 箇所を文脈に合わせて使用
- `接続語:` 「〜とすると〜」「一方で〜」「〜のではないだろうか」等を段落間に散らす
- `思考パターン:` 抽象を 2〜3 要素に分解、ミクロ↔マクロ往復、対比（デジタル/フィジカル 等）の痕跡を残す
- `末尾:` 自分の制作への接続、または普遍化、または読者への静かな挨拶と公開日
- `禁止語:` ヤバい / エモい / 神 / エグい / めちゃくちゃ / 完全に / 絶対に / 必ず / 絵文字（本文内）は出力しない
- `文量:` 3000〜4000 字

#### 2b — 英語ブランチ（`language == "en"`）

**変更前（lines 322–327）:**
```python
language_guidance = (
    "- Write in first person, in English (the logs may be in Japanese; translate and interpret).\n"
    "- Be specific: mention project names, tools, and concrete outcomes.\n"
    "- Keep the tone curious and reflective, not corporate.\n"
    "- Total length: around 2000–3000 characters."
)
```

**変更後（以下をすべてカバーする多行文字列）:**
- `Hedging ratio:` Use assertive and hedged expressions at roughly 6:4 to 5:5. Prefer: "I think…", "It seems that…", "One might argue…", "Perhaps…", "I wonder whether…"
- `Opening:` Begin with one of — (a) a concrete fact or observation, (b) a situational setup, (c) a brief backstory
- `Headings:` Use "Concept: Angle" format for all H2 headings. Avoid chronological labels (Step 1 / Next / Finally)
- `Paragraphs:` 1–3 sentences per paragraph
- `Vocabulary injection:` Inject 5–15 instances of: mechanism / apparatus, ubiquity / pervasive, tactility / texture, granularity / resolution, hypothesis, reproducible, insight, emergent, friction, interplay
- `Connectors:` Scatter: "That said,", "In other words,", "On the other hand,", "If so,", "One might wonder whether", "Conversely,"
- `Thinking patterns:` Leave traces of (a) decomposing abstraction into 2–3 elements, (b) micro↔macro oscillation, (c) contrast pairs (digital/physical, local/global, explicit/implicit)
- `Closing:` End with connection to own practice, universalization of the theme, a quiet closing remark, or publication date
- `Forbidden words:` Avoid "amazing", "awesome", "literally", "totally", "absolutely", "definitely", "it's insane that", slang intensifiers, and emojis in body text
- `Self-reference:` Include 1–2 explicit "I think / I believe / I suspect" phrases at section transitions
- `Total length:` around 2000–3000 characters

---

### 変更 3 — `prohibitions` 節をプロンプト末尾に追加

`language_guidance` の後、ログセクションの前に「制約」節を追加する。

**日本語版:**
```
制約（必ず守ること）:
- 原稿（ログ）にない題材・固有名詞・エピソード・人物を追加しない
- 原稿の主張の向き（賛否・立場）を変えない
- 語彙注入は 5〜15 箇所以内に留める
- 感情表現を捏造しない
- 他者の作品への批判強度を勝手に増減させない
- ログが分析していないテーマを新たに読み込まない
- 数字・データ・引用を創作しない
```

**英語版:**
```
Constraints (strictly follow):
- Do not introduce topics, proper nouns, episodes, or people not present in the source logs
- Do not alter the stance or position of arguments in the logs
- Do not over-inject vocabulary (5–15 instances maximum)
- Do not fabricate emotions or reactions
- Do not increase or decrease the critical intensity toward others' work
- Do not introduce new themes not analysed in the source
- Do not invent numbers, data, or quotations
```

---

### 変更 4 — `final_gate` チェックリストをプロンプト末尾に追加

`prohibitions` 節の後に追加する。

**日本語版:**
```
出力前に以下を自己確認すること:
- [ ] 題材・主張・固有名詞が原稿のまま
- [ ] 「観察し、分解し、制作に接続する人」として読める
- [ ] 断定と推測が適度に混在している
- [ ] 具体↔抽象の接続が少なくとも1箇所ある
- [ ] 末尾に制作接続 or 普遍化が含まれる
- [ ] 語彙注入が自然で過剰でない
```

**英語版:**
```
Before writing your output, confirm each of the following:
- [ ] Topics, claims, and proper nouns match the source logs
- [ ] The post reads as written by someone who "observes, decomposes, and connects to practice"
- [ ] Assertions and hedged expressions are appropriately mixed
- [ ] At least one concrete↔abstract connection is present
- [ ] The closing connects to own practice or universalises the theme
- [ ] Vocabulary injection feels natural and is not excessive
```

---

### 変更 5 — `Required structure` の固定セクション名を廃止

**変更前（lines 335–342）:**
```
Required structure:
1. `# <Title>` …
2. A short, suggestive intro paragraph …
3. `## Highlights` — 3–5 bullet points …
4. `## What I Worked On` — narrative paragraphs …
5. `## Decisions & Tradeoffs` — key technical or design decisions …
6. `## Progress Since Last Time` — compare with the previous blog post …
7. `## What's Next` — propose new themes …
```

**変更後（ja / en 共通骨格）:**
```
Required structure:
1. `# <Title>` — a short, catchy, article-style title in 30 characters or fewer …
2. An opening paragraph (2–3 sentences) using one of: fact presentation / situational setup / backstory
3. Free-form body sections using H2 headings in "Concept: Angle" format.
   Do NOT use fixed section names (Highlights / What I Worked On / etc.).
   Choose headings that reflect the actual themes in the logs.
```

日本語版のみ、文量目安「3000〜4000 字」を明記（英語版は「2000〜3000 characters」を維持）。

---

## テスト更新（`TestBuildPrompt`）

改修によって既存の2テストが仕様変更で失敗するため、合わせて更新する。

### `test_required_sections_present`

**変更前:**
```python
for section in ["Highlights", "What I Worked On", "Decisions", "Progress Since Last Time", "What's Next"]:
    assert section in prompt
```

**変更後:**
```python
assert "Concept: Angle" in prompt
assert "Before writing your output, confirm each of the following" in prompt
```

### `test_japanese_prompt_requests_japanese_output`

**変更前:**
```python
assert "Write in first person, in Japanese." in prompt
```

**変更後:**
```python
assert "「私」に統一" in prompt
```

---

## 実装順序

1. `build_prompt()` のロール文（ja / en 両分岐）を persona ベースに書き換え
2. `language_guidance` を ja: apply_steps ベース、en: 英語版詳細指示 に置き換え
3. `prohibitions` 節を ja / en 両方に追加（`language_guidance` の後）
4. `final_gate` チェックリストを ja / en 両方に追加（`prohibitions` の後）
5. `Required structure` の固定セクション名を廃止し、フォーマット自由指示に変更
6. `TestBuildPrompt` の2テストを新仕様に更新
7. `python3 -m pytest -q scripts/tests` ですべてのテストが通ることを確認（51 passed）
