# NotebookLM × Deep Research パイプライン 設計仕様書

作成日：2026-05-05
対象：NotebookLM MCP CLI を起点とし、マインドマップ → 構造化 Markdown → Deep Research を自動化するパイプライン
方針：基本 Claude Sonnet 4.6 を使用。深い推論が必要な場面のみ Opus 4.7 に切替

---

## 📌 導入状況（2026-05-12 追記）

**前提となる `notebooklm-mcp-cli` の導入は完了済み**（実機 v0.6.9）。本仕様書のパイプライン（分岐 A/B）実装は **未着手**。

| 構成要素 | 状態 |
|---------|------|
| `nlm` CLI / `notebooklm-mcp` MCP サーバー | ✅ 導入済み |
| Claude Code MCP 統合 | ✅ 導入済み |
| `nlm-skill`（Claude Code 操作ガイド） | ✅ 導入済み |
| 分岐 A：Claude Vision + Deep Research パイプライン | ⏸ 未着手 |
| 分岐 B：LM Studio + Brave Search パイプライン | ⏸ 未着手 |

詳細な導入手順・実機検証ログは前段ログ `logs/20260430-notebooklm-mcp-cli-rag.md` の §「導入状況」を参照。

---

## 1. 目的

検索クエリを起点に、

1. NotebookLM へソースを集約してナレッジベース化（永続 RAG）
2. ノートブックのマインドマップを生成
3. マインドマップ画像を構造化 Markdown に変換
4. その構造化 Markdown をアウトラインとして Deep Research を実施
5. 出典付きレポートを得る

までを **再現性高く・自動で** 回せるようにする。

---

## 2. 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                        共通部（NotebookLM）                  │
│                                                              │
│   [1] クエリ投入                                             │
│       │  nlm notebook create / source discover|add           │
│       ▼                                                      │
│   [2] NotebookLM ノートブック（永続 RAG）  ←──── 別途再利用可 │
│       │  nlm studio mindmap                                  │
│       ▼                                                      │
│   [3] mindmap.png（マインドマップ画像）                      │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐    ┌──────────────────────────┐
│  分岐 A          │    │  分岐 B                  │
│  Claude Max      │    │  LM Studio + Brave       │
│                  │    │                          │
│  [4A] Claude     │    │  [4B] llava 等            │
│       Vision     │    │       ローカル Vision    │
│       で MD 化   │    │       で MD 化           │
│       ▼          │    │       ▼                  │
│  [5A] Claude     │    │  [5B] gpt-oss + Brave    │
│       Code Agent │    │       で自前ループ       │
│       Deep R.    │    │       Deep Research      │
└────────┬─────────┘    └────────┬─────────────────┘
         ▼                       ▼
       report.md              report.md
```

---

## 3. 共通部（Pre-pipeline 環境セットアップ）

### 3.1 必要なソフトウェア

| ソフトウェア | バージョン | 用途 |
|------------|----------|------|
| Python | 3.11+ | nlm CLI |
| uv または pip | 任意 | Python パッケージ管理 |
| jq | 任意 | JSON 抽出 |
| git | 任意 | 成果物管理 |
| Chrome / Chromium | 最新 | NotebookLM 認証 |

### 3.2 Google アカウント前提

- NotebookLM が利用可能な Google アカウント（個人 or Workspace 個人プラン）
- Workspace Enterprise は CLI 動作未検証のため非推奨

### 3.3 nlm のインストール

```bash
# 推奨
uv tool install notebooklm-mcp-cli

# 確認
nlm --version    # → 0.6.1 以上
notebooklm-mcp --help
```

### 3.4 認証

```bash
nlm login                       # ブラウザ起動 → Google ログイン
nlm auth status                 # 状態確認
# クッキー保存先: ~/.notebooklm-mcp-cli/profiles/default/
```

> **再ログイン**：クッキーは数週間で失効。本番運用するなら週次で `nlm login` を実行する cron か、`nlm auth status` で失効検知 → 通知の運用を組む。

---

## 4. 共通部の処理フロー

### 4.1 ノートブック作成

```bash
QUERY="$1"  # 検索クエリ（例：「日本の障害福祉サービスのDX動向 2026」）
NB_TITLE="${QUERY} ($(date +%Y-%m-%d))"

NB_ID=$(nlm notebook create "$NB_TITLE" --json | jq -r '.id')
echo "Notebook ID: $NB_ID"
```

### 4.2 ソース収集

> **検証ポイント**：v0.6.1 で `nlm source discover` が CLI 提供されているかを実機確認。
> 提供されていれば優先利用。されていなければ、自前 WebSearch（Brave / DuckDuckGo / Google CSE）で URL を取得し `nlm source add --url` のループで投入する。

#### パターン A: `source discover` が使える場合

```bash
nlm source discover $NB_ID --query "$QUERY" --max 20
```

#### パターン B: フォールバック（自前検索）

```bash
# Brave Search API で 20 件取得
URLS=$(curl -s -H "X-Subscription-Token: $BRAVE_API_KEY" \
  "https://api.search.brave.com/res/v1/web/search?q=$(jq -rn --arg q "$QUERY" '$q|@uri')&count=20" \
  | jq -r '.web.results[].url')

# 1 件ずつ投入
for url in $URLS; do
  nlm source add $NB_ID --url "$url" || true
done
```

`true` で叩いて失敗を握り潰すのは、有料壁・取得失敗 URL があるため。最終投入数を後でカウント検証する。

```bash
SOURCES_COUNT=$(nlm source list $NB_ID --json | jq 'length')
echo "Sources added: $SOURCES_COUNT"
[ "$SOURCES_COUNT" -ge 5 ] || { echo "Too few sources"; exit 1; }
```

### 4.3 マインドマップ生成

```bash
nlm studio mindmap $NB_ID --output ./out/mindmap.png
# 出力形式が PNG/SVG/HTML のどれかは v0.6.1 で要確認
# HTML の場合は --format png オプションで変換指定（要検証）
```

> **検証ポイント**：実際に出力される拡張子と寸法。Vision モデルへ渡す前提で **PNG** が望ましい。HTML や Mermaid テキスト出力なら別経路でレンダリングが必要。

成果物：`./out/mindmap.png`、ノートブック ID `$NB_ID` を環境変数 / メタファイルに保存。

```bash
cat > ./out/meta.json <<EOF
{
  "query": "$QUERY",
  "notebook_id": "$NB_ID",
  "notebook_title": "$NB_TITLE",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "sources_count": $SOURCES_COUNT
}
EOF
```

---

## 5. 分岐 A：Claude Max ルート

### 5.1 前提

- Claude Max プラン契約済み
- Claude Code CLI インストール済み（このセッションそのものの環境）
- Anthropic API キー（Claude Code 内なら不要、独立 SDK 利用時は必要）

### 5.2 [4A] Claude Vision でマインドマップ → Markdown

#### 方針

`claude-sonnet-4-6` に画像と変換指示を渡し、階層化 Markdown を返させる。

#### 実装：Anthropic SDK（Python）

```python
# scripts/img_to_md_claude.py
import sys, base64, anthropic, pathlib

MODEL = "claude-sonnet-4-6"

def main(image_path: str, output_path: str):
    image_bytes = pathlib.Path(image_path).read_bytes()
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": image_b64},
                    },
                    {
                        "type": "text",
                        "text": (
                            "添付はマインドマップの画像です。階層構造を Markdown に転写してください。\n"
                            "ルール：\n"
                            "- ルートノードを `# 見出し` とする\n"
                            "- 第2階層を `## 見出し`、第3階層以降は `- 箇条書き` の入れ子で表現\n"
                            "- すべての枝・葉ノードを漏らさず転写\n"
                            "- 図中の左→右、上→下の順序を保持\n"
                            "- 画像から読み取れない部分は推測せず `[unreadable]` と記す\n"
                            "出力は Markdown 本体のみ。前後に説明文を付けない。"
                        ),
                    },
                ],
            }
        ],
    )
    pathlib.Path(output_path).write_text(msg.content[0].text, encoding="utf-8")
    print(f"Wrote {output_path}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```

実行：

```bash
python scripts/img_to_md_claude.py ./out/mindmap.png ./out/mindmap.md
```

#### 実装：Claude Code CLI（非対話）

```bash
# ※ CLI 経由で画像入力する場合のフォーマットは Claude Code バージョンに依存
# 安定性を取るなら SDK 経路を推奨
claude --print --model claude-sonnet-4-6 \
  --image ./out/mindmap.png \
  "$(cat <<EOF
添付はマインドマップ画像です。階層 Markdown に転写してください。
- ルート: # 見出し
- 第2階層: ## 見出し
- それ以下: - 箇条書きの入れ子
- すべての枝を漏らさず、左→右・上→下の順で
- 出力は Markdown 本体のみ
EOF
)" > ./out/mindmap.md
```

### 5.3 [5A] Claude Code Agent で Deep Research

#### 方針

Claude Code の Agent 機能（`general-purpose` または `Explore`）を、Deep Research 風オーケストレータとして起動。アウトラインの各ノードに対して並列で WebSearch + WebFetch を実行し、ノードごとに出典付きの調査結果を生成 → 最終統合する。

Max プラン内で完結させたい場合：**Claude Code 対話セッションから Agent を呼ぶ**。Anthropic API 直叩きは API 課金が発生するため Max 月額には含まれない（要確認）。

#### Claude Code 対話セッション内のコマンド例

```
mindmap.md を読み込んでください。
ファイルパス: ./out/mindmap.md

各見出し（# / ## / 主要な - ノード）を 1 トピックとして、
general-purpose agent を並列で起動し、それぞれに以下を実行させてください：

1. WebSearch でトピックに関する直近 1 年の情報源を 3-5 件
2. WebFetch で内容取得
3. 出典 URL 明記で要約（500 文字程度）
4. 不明点・要追加調査ポイントの列挙

全 agent 完了後、結果を以下の構造で統合し ./out/report.md に保存してください：

# レポートタイトル（mindmap.md のルート見出しを流用）

## エグゼクティブサマリー（300 文字）

## 各トピック（mindmap.md の構造を保持）
### トピック1
- 要約
- 主要な情報源（出典 URL 列挙）
- 残課題

## 出典一覧（重複除去・URL 順）

## 調査メタ情報
- 実施日
- 使用モデル
- ノード数
- 発見した情報源数
```

#### 自動化（バッチ）したい場合

Claude Code を非対話で叩くか、Anthropic SDK で Tool Use ループを自前実装する。

```python
# scripts/deep_research_claude.py（要点のみ）
import anthropic, pathlib, json

MODEL = "claude-sonnet-4-6"
MD = pathlib.Path("./out/mindmap.md").read_text()

client = anthropic.Anthropic()
tools = [{"type": "web_search_20250305", "name": "web_search"}]

system = """
あなたはディープリサーチ・エージェントです。
与えられたアウトラインの各ノードについて web_search を使って調査し、
出典付きの統合レポートを Markdown で出力してください。
"""

resp = client.messages.create(
    model=MODEL,
    max_tokens=16000,
    system=system,
    tools=tools,
    messages=[
        {"role": "user", "content": f"以下のアウトラインで深掘り調査して統合レポートを書いてください。\n\n{MD}"}
    ],
)
# ※ tool_use ループ処理が必要。簡略化のため省略
pathlib.Path("./out/report.md").write_text(resp.content[-1].text, encoding="utf-8")
```

> **コスト注意**：このパスは Anthropic API 課金。Max プラン内完結を厳守したいなら対話セッション + Agent 経路にする。

### 5.4 分岐 A の最終シェルスクリプト

```bash
#!/bin/bash
# pipeline_claude.sh
set -euo pipefail
QUERY="$1"
mkdir -p ./out

# 共通部
NB_TITLE="${QUERY} ($(date +%Y-%m-%d))"
NB_ID=$(nlm notebook create "$NB_TITLE" --json | jq -r '.id')
nlm source discover $NB_ID --query "$QUERY" --max 20 || \
  bash scripts/source_add_via_brave.sh $NB_ID "$QUERY"
nlm studio mindmap $NB_ID --output ./out/mindmap.png

# 分岐 A 固有
python scripts/img_to_md_claude.py ./out/mindmap.png ./out/mindmap.md

# Deep Research（対話 or バッチを選択）
if [ "${USE_INTERACTIVE:-1}" = "1" ]; then
  echo "対話セッションで Claude Code を起動し、上記プロンプトを実行してください。"
  echo "アウトライン: ./out/mindmap.md"
else
  python scripts/deep_research_claude.py
fi

echo "完了。Notebook ID: $NB_ID（後日 nlm notebook query で再利用可）"
```

---

## 6. 分岐 B：LM Studio + Brave Search ルート

### 6.1 前提

- LM Studio または Ollama インストール済み
- gpt-oss:20b（または同等の 14-32B クラス）モデル DL 済み
- Vision 用に llava-1.6 / qwen2-vl 等の vision モデルも DL 済み
- Brave Search API キー取得済み（無料枠 月 2000 クエリ）
- VRAM 12-16GB 以上推奨

### 6.2 LM Studio をローカル API として起動

LM Studio の Local Server 機能で OpenAI 互換 API を `http://localhost:1234/v1` に立てる。

```bash
# 起動確認
curl http://localhost:1234/v1/models | jq
```

ロードするモデル：
- テキスト：`gpt-oss-20b`（gguf q4_k_m 等）
- Vision：`llava-v1.6-mistral-7b`（gguf）

> Ollama を使う場合は `ollama serve` 起動 → `http://localhost:11434/v1`（Ollama 0.5+ で OpenAI 互換）に読み替え。

### 6.3 [4B] ローカル Vision モデルで Markdown 化

```python
# scripts/img_to_md_local.py
import sys, base64, pathlib, requests, json

ENDPOINT = "http://localhost:1234/v1/chat/completions"
MODEL = "llava-v1.6-mistral-7b"  # LM Studio で読み込んでいるモデル名

def main(image_path: str, output_path: str):
    img_b64 = base64.b64encode(pathlib.Path(image_path).read_bytes()).decode()
    payload = {
        "model": MODEL,
        "max_tokens": 4000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {
                        "type": "text",
                        "text": (
                            "添付はマインドマップ画像です。階層 Markdown に転写してください。\n"
                            "- ルート: # 見出し / 第2階層: ## 見出し / それ以下: - 箇条書き\n"
                            "- すべての枝を漏らさず転写、左→右・上→下\n"
                            "- 出力は Markdown 本体のみ"
                        ),
                    },
                ],
            }
        ],
    }
    r = requests.post(ENDPOINT, json=payload, timeout=300)
    r.raise_for_status()
    md = r.json()["choices"][0]["message"]["content"]
    pathlib.Path(output_path).write_text(md, encoding="utf-8")
    print(f"Wrote {output_path}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```

> **品質注意**：ローカル vision モデルは Claude/Gemini に比べて構造抽出精度が落ちる。出力を目視 or LLM レビューで検証する手順を別途挟むのが安全。

### 6.4 [5B] gpt-oss + Brave で自前 Deep Research ループ

#### 設計：3 段ループ

```
for ノード in アウトライン:
    queries = LLM("ノードを調べる検索クエリを 3 個生成", node)
    for q in queries:
        results = BraveSearch(q, top=5)
        for r in results:
            content = WebFetch(r.url)
            summaries.append(LLM("出典付きで要約", content, r.url))
    node_report = LLM("要約群を統合", summaries)

final_report = LLM("各ノードレポートを統合", node_reports)
```

#### 実装スケルトン

```python
# scripts/deep_research_local.py
import os, re, requests, pathlib
from openai import OpenAI

LM = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
BRAVE_KEY = os.environ["BRAVE_API_KEY"]
MODEL = "gpt-oss-20b"

def llm(prompt: str, max_tokens=2000) -> str:
    resp = LM.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content

def brave_search(q: str, top: int = 5) -> list[dict]:
    r = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": q, "count": top},
        headers={"X-Subscription-Token": BRAVE_KEY},
        timeout=30,
    )
    r.raise_for_status()
    return [{"title": x["title"], "url": x["url"], "desc": x.get("description", "")} for x in r.json()["web"]["results"][:top]]

def fetch(url: str) -> str:
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        # HTML → text の簡易抽出（本番は trafilatura 等を推奨）
        text = re.sub(r"<[^>]+>", " ", r.text)
        return re.sub(r"\s+", " ", text)[:8000]
    except Exception as e:
        return f"[fetch error: {e}]"

def parse_outline(md: str) -> list[str]:
    """# / ## の見出しと第一階層 - のテキストを抽出してノード列にする"""
    nodes = []
    for line in md.splitlines():
        m = re.match(r"^(#{1,3})\s+(.+)", line) or re.match(r"^- (.+)", line)
        if m:
            nodes.append(m.group(2 if line.startswith("#") else 1))
    return nodes

def main():
    outline = pathlib.Path("./out/mindmap.md").read_text()
    nodes = parse_outline(outline)
    print(f"Nodes: {len(nodes)}")

    reports = []
    for i, node in enumerate(nodes):
        print(f"[{i+1}/{len(nodes)}] {node}")
        queries = llm(f"次のトピックを Web で調べる検索クエリを 3 個、改行区切りで:\n{node}").splitlines()[:3]
        summaries = []
        for q in queries:
            for hit in brave_search(q):
                content = fetch(hit["url"])
                s = llm(
                    f"出典 {hit['url']} の内容を 200 字で要約してください。事実のみ。\n\n{content}",
                    max_tokens=400,
                )
                summaries.append(f"- ({hit['url']}) {s}")
        report = llm(
            f"以下の出典付き要約を統合し、トピック「{node}」のレポートを 800 字で書いてください。出典 URL を本文中に明記:\n\n"
            + "\n".join(summaries),
            max_tokens=2000,
        )
        reports.append(f"## {node}\n\n{report}\n")

    final = llm(
        "以下のトピック別レポートを統合して、エグゼクティブサマリー付きの最終レポートにしてください:\n\n"
        + "\n".join(reports),
        max_tokens=4000,
    )
    pathlib.Path("./out/report.md").write_text(final, encoding="utf-8")
    print("Wrote ./out/report.md")

if __name__ == "__main__":
    main()
```

### 6.5 分岐 B の最終シェルスクリプト

```bash
#!/bin/bash
# pipeline_local.sh
set -euo pipefail
QUERY="$1"
: "${BRAVE_API_KEY:?BRAVE_API_KEY を設定してください}"
mkdir -p ./out

# LM Studio が起動しているか確認
curl -sf http://localhost:1234/v1/models > /dev/null || \
  { echo "LM Studio Local Server を起動してください"; exit 1; }

# 共通部
NB_TITLE="${QUERY} ($(date +%Y-%m-%d))"
NB_ID=$(nlm notebook create "$NB_TITLE" --json | jq -r '.id')
nlm source discover $NB_ID --query "$QUERY" --max 20 || \
  bash scripts/source_add_via_brave.sh $NB_ID "$QUERY"
nlm studio mindmap $NB_ID --output ./out/mindmap.png

# 分岐 B 固有
python scripts/img_to_md_local.py ./out/mindmap.png ./out/mindmap.md
python scripts/deep_research_local.py

echo "完了。Notebook ID: $NB_ID（後日 nlm notebook query で再利用可）"
```

---

## 7. ディレクトリ構成（推奨）

```
project-root/
├── pipeline_claude.sh
├── pipeline_local.sh
├── scripts/
│   ├── source_add_via_brave.sh
│   ├── img_to_md_claude.py
│   ├── img_to_md_local.py
│   ├── deep_research_claude.py
│   └── deep_research_local.py
├── out/                       # 実行ごとの成果物（gitignore 推奨）
│   ├── meta.json
│   ├── mindmap.png
│   ├── mindmap.md
│   └── report.md
├── .env.example
└── requirements.txt
```

`requirements.txt`：

```
anthropic>=0.40.0
openai>=1.50.0
requests>=2.32.0
trafilatura>=1.12.0   # オプション: HTML → text 高品質抽出
```

`.env.example`：

```bash
# 共通
BRAVE_API_KEY=...           # 分岐 A でフォールバック検索を使う／分岐 B で必須

# 分岐 A
ANTHROPIC_API_KEY=...       # SDK 直叩き時のみ必要。Claude Code 対話運用なら不要

# 分岐 B
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_TEXT_MODEL=gpt-oss-20b
LM_STUDIO_VISION_MODEL=llava-v1.6-mistral-7b
```

---

## 8. 再現性チェックリスト

実行前：

- [ ] `nlm --version` ≥ 0.6.1
- [ ] `nlm auth status` が valid
- [ ] `python --version` ≥ 3.11
- [ ] `jq --version` がインストール済み
- [ ] `./out/` ディレクトリが書き込み可能
- [ ] 分岐 A：Claude Code が動作 / または `ANTHROPIC_API_KEY` 設定済み
- [ ] 分岐 B：LM Studio Local Server が `:1234` で起動
- [ ] 分岐 B：vision モデル + テキストモデルが LM Studio にロード済み
- [ ] 分岐 B：`BRAVE_API_KEY` 設定済み

実行後：

- [ ] `./out/mindmap.png` のサイズが 0 でない
- [ ] `./out/mindmap.md` の見出し数が 3 以上
- [ ] `./out/report.md` が 1000 字以上
- [ ] `./out/meta.json` に notebook_id が記録されている
- [ ] `nlm notebook query $NB_ID "テスト質問"` が応答する（永続性確認）

---

## 9. 既知の課題と対策

| 課題 | 影響 | 対策 |
|------|------|------|
| `nlm source discover` の有無 | 共通部の収集ステップが詰む | フォールバック（Brave 経由）を必ず併設 |
| `nlm studio mindmap` 出力形式 | Vision に渡せないリスク | PNG 化のためのレンダラ準備 |
| NotebookLM 認証の数週間失効 | バッチ実行が突然失敗 | 週次 `nlm login` cron / 失効検知通知 |
| NotebookLM レート制限（≒ 50/日 free） | 連続実行で詰まる | バッチを夜間に分散、Pro プラン検討 |
| Claude Vision の API コスト（SDK 経由） | Max 月額枠外 | 対話セッション + Agent 経路を優先 |
| ローカル Vision の精度低下 | mindmap.md 品質が落ちる | 出力を Claude/Gemini で再レビューする工程を追加 |
| Brave Search 月 2000 クエリ無料枠 | 大量実行で課金発生 | 1 ノードあたりクエリ数を制限・キャッシュ実装 |
| 非公式 NotebookLM API | 仕様変更で破損 | バージョン固定、定期動作確認 |

---

## 10. 拡張アイデア

- **キャッシュ層**：同じ URL を再 fetch しない、同じクエリの Brave 結果を再利用
- **品質ゲート**：mindmap.md と report.md を Claude にレビューさせ、不足ノードを自動再調査
- **多言語対応**：英語ソース → 日本語要約の指示を LLM プロンプトに明示
- **永続検索層**：定期的に同テーマのノートブックを自動更新（cron + nlm source add）
- **Notion / Obsidian 連携**：report.md を自動投入

---

## 11. 参考

- 前段調査ログ：`logs/20260430-notebooklm-mcp-cli-rag.md`
- NotebookLM MCP CLI: https://github.com/jacob-bd/notebooklm-mcp-cli
- Anthropic Web Search Tool: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-search-tool
- Brave Search API: https://api.search.brave.com/
- LM Studio: https://lmstudio.ai/
- Ollama: https://ollama.com/

---

## 12. 改訂履歴

| 日付 | 改訂内容 |
|------|---------|
| 2026-05-05 | 初版作成（共通部 + 分岐 A/B 仕様） |
| 2026-05-12 | 前提コンポーネント（notebooklm-mcp-cli / Claude Code MCP 統合 / nlm-skill）の導入完了を冒頭に追記 |
