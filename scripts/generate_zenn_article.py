#!/usr/bin/env python3
"""
Zenn 技術記事パイプライン（ローカル LLM）.

配布用リポジトリ（例: Agent-Aiko）を対象に、リポ本体（README/設計文書/コミット
履歴/構造）＋関連ログを素材として、Zenn 向け技術記事を生成する。

2 フェーズ:
  phase=intent  : 素材から「開発の意図」を抽出して提示（捏造防止の確認ゲート用）
  phase=article : 確認済みの意図 + 素材から、技術記事本文 + Zenn front matter を生成

設計合意（2026-06-14）:
  - 対象は配布リポを持つプロジェクト。素材の本体はリポそのもの（コード/README/設計/
    コミット履歴）＋ logs-with-llm/logs/ の関連ログ。
  - 素材が薄ければ書かない（材料十分性は呼び出し側で判断）。
  - 意図は推測で埋めず、intent フェーズで人に確認してから article を書く。
  - 技術寄りトーン（再現・応用できる解説）。週次ナラティブ（内省）とは別物。

Usage:
  PHASE=intent  PROJECT_REPO=~/dev/Agent-Aiko PROJECT_NAME=Agent-Aiko \
    LOG_KEYWORDS="aiko,agent-team,persona,nullevi03,mentor-kit" \
    python3 scripts/generate_zenn_article.py > /tmp/zenn-intent.md

  PHASE=article PROJECT_REPO=~/dev/Agent-Aiko PROJECT_NAME=Agent-Aiko \
    LOG_KEYWORDS="..." INTENT_FILE=/tmp/zenn-intent-confirmed.md \
    python3 scripts/generate_zenn_article.py > articles/<date>-agent-aiko.md
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PHASE = os.environ.get("PHASE", "intent").lower()
PROJECT_REPO = Path(os.path.expanduser(os.environ.get("PROJECT_REPO", ""))).resolve() if os.environ.get("PROJECT_REPO") else None
PROJECT_NAME = os.environ.get("PROJECT_NAME", PROJECT_REPO.name if PROJECT_REPO else "project")
LOG_KEYWORDS = [k.strip() for k in os.environ.get("LOG_KEYWORDS", "").split(",") if k.strip()]
LOGS_DIR = REPO_ROOT / "logs"
ARTICLES_DIR = REPO_ROOT / "articles"
INTENT_FILE = os.environ.get("INTENT_FILE", "")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
MODEL = os.environ.get("OLLAMA_COMPOSE_MODEL", "gpt-oss:120b")
THINK = os.environ.get("OLLAMA_THINK", "true").lower() in ("1", "true", "yes", "on")
TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "2400"))

DOC_NAMES = ("README.md", "INVARIANTS.md", "CLAUDE.md", "VISIBILITY.md", "INSTALL.md")
MAX_DOC_CHARS = 6000
MAX_LOG_CHARS = 3500
MAX_LOGS = 8


def read_capped(path: Path, cap: int) -> str:
    try:
        t = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return t if len(t) <= cap else t[:cap].rstrip() + "\n…(以下略)"


def gather_repo_material() -> str:
    if not PROJECT_REPO or not PROJECT_REPO.is_dir():
        sys.exit(f"PROJECT_REPO not found: {PROJECT_REPO}")
    parts = [f"# 対象配布リポ: {PROJECT_NAME} ({PROJECT_REPO})"]

    # 主要ドキュメント（意図・設計思想の一次資料）
    for name in DOC_NAMES:
        for p in PROJECT_REPO.rglob(name):
            rel = p.relative_to(PROJECT_REPO).as_posix()
            if rel.count("/") > 2:  # 浅い階層の主要文書だけ
                continue
            body = read_capped(p, MAX_DOC_CHARS)
            if body.strip():
                parts.append(f"\n## doc: {rel}\n{body}")

    # ディレクトリ構造（上位2階層）
    try:
        tree = subprocess.run(
            ["git", "-C", str(PROJECT_REPO), "ls-files"],
            capture_output=True, text=True, timeout=20,
        ).stdout.splitlines()
    except Exception:
        tree = []
    top = sorted({"/".join(f.split("/")[:2]) for f in tree})
    parts.append("\n## リポ構造（上位2階層）\n" + "\n".join(f"- {t}" for t in top[:60]))

    # コミット履歴（意図の時系列）。実日付を渡す（日付を LLM に推測させると捏造する）。
    try:
        log = subprocess.run(
            ["git", "-C", str(PROJECT_REPO), "log", "-50",
             "--date=short", "--format=%ad %h %s"],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip()
    except Exception:
        log = ""
    if log:
        parts.append(
            "\n## コミット履歴（最近50・実日付つき。ここに無い日付・コミットを創作しないこと）\n"
            "```\n" + log + "\n```")

    return "\n".join(parts)


def gather_related_logs() -> str:
    if not LOGS_DIR.is_dir() or not LOG_KEYWORDS:
        return ""
    matched = []
    for entry in sorted(LOGS_DIR.iterdir()):
        name = entry.name.lower()
        if any(k.lower() in name for k in LOG_KEYWORDS):
            matched.append(entry)
    matched = matched[:MAX_LOGS]
    if not matched:
        return ""
    parts = ["\n# 関連開発ログ（なぜ・どう判断したかの記録）"]
    for entry in matched:
        f = entry if entry.is_file() else next((p for p in entry.rglob("*.md")), None)
        if not f:
            continue
        parts.append(f"\n## log: {entry.name}\n{read_capped(f, MAX_LOG_CHARS)}")
    return "\n".join(parts)


def call_llm(prompt: str) -> str:
    payload = json.dumps({
        "model": MODEL, "prompt": prompt, "stream": False, "think": THINK,
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = json.loads(resp.read())
    text = body.get("response", "")
    return re.sub(r"<think(?:ing)?>[\s\S]*?</think(?:ing)?>", "", text).strip()


def intent_prompt(material: str) -> str:
    return f"""あなたは、配布される技術プロジェクトの「開発の意図」を、一次資料から読み取って言語化する役割です。
以下は対象プロジェクト「{PROJECT_NAME}」の素材（README・設計文書・コミット履歴・関連開発ログ）です。

この素材から読み取れる「開発の意図」だけを、推測で埋めずにまとめてください。素材に書かれていないことは書かないでください。

## 出力（この見出しで）
## 何を作ったか
- プロジェクトの正体を 2〜3 文で。

## なぜ作ったか（目的・解こうとした課題）
- 素材から読み取れる動機・課題意識。

## 設計思想・大事にしている原則
- INVARIANTS や README から読み取れる、譲れない原則・判断軸。

## どう進化してきたか
- コミット履歴から読み取れる、優先順位の変化・段階。

## 素材から読み取れない／確認したい点
- 意図のうち、素材に明示が無く推測になる部分を正直に挙げる（後で著者に確認するため）。

# 素材
{material}
"""


def article_prompt(material: str, intent: str) -> str:
    sample = ""
    for p in sorted(ARTICLES_DIR.glob("*.md"))[:1]:
        sample = read_capped(p, 3500)
    return f"""あなたは、配布される技術プロジェクトについて、読者が再現・応用できる Zenn 技術記事を書く書き手です。
週次ナラティブ（内省）とは違い、こちらは技術寄り。ただしマーケ的な煽り・CTA は書きません。

対象プロジェクト「{PROJECT_NAME}」。下に「確認済みの開発意図」と「素材」と「文体の見本」があります。

## 守ること
- 素材（リポ/ログ）と確認済み意図に書かれていることだけを書く。コード・数値・API・固有名を捏造しない。
- 「何を作ったか」だけでなく「なぜ・どんな設計思想で・どう解決したか」を、確認済み意図に沿って語る。
- 専門用語は初出時に一言で噛み砕く。読者が手元で試せる粒度の具体（構成・手順・コード断片）を入れる。
- 一方的な用語の羅列にしない。なぜその設計にしたかの判断を地の文で。
- このプロンプトの語に引っ張られない（自分の言葉で書く）。

## 出力（必ずこの形式）
1 行目から Zenn front matter を YAML で出す:
---
title: "（30字前後、内容を表す技術タイトル）"
emoji: "（1文字）"
type: "tech"
topics: ["（3〜5個。例: Claude, AIエージェント, 設計）"]
published: false
---

その後に本文（Markdown）。`# タイトル` から始め、導入（何のプロジェクトか・何が読めるか）→ 設計思想 → 実装/構造の解説 → 設計判断とトレードオフ → まとめ（残課題・発展）の流れ。

# 確認済みの開発意図
{intent}

# 素材
{material}

# 文体の見本（既存 Zenn 記事・トーン参考。内容は流用しない）
{sample}
"""


def main() -> None:
    material = gather_repo_material() + "\n" + gather_related_logs()
    if PHASE == "intent":
        print(call_llm(intent_prompt(material)))
    elif PHASE == "article":
        intent = ""
        if INTENT_FILE and Path(INTENT_FILE).is_file():
            intent = Path(INTENT_FILE).read_text(encoding="utf-8")
        else:
            sys.exit("article フェーズには確認済み INTENT_FILE が必要です")
        print(call_llm(article_prompt(material, intent)))
    else:
        sys.exit(f"unknown PHASE: {PHASE}")


if __name__ == "__main__":
    main()
