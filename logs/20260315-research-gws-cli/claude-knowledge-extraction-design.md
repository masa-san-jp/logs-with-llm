# 組織暗黙知抽出システム設計

## 目的の再定義

**やりたいこと**：言語化・体系化されていない組織の意思決定プロセスと業務プロセスを、コミュニケーションログから文脈・重みごとLLMに渡し、インサイトを発見させる。

**やりたくないこと**：ログの可視化ダッシュボードを作ること（それは副産物）。

---

## 設計の核心：何を「重み」として扱うか

単純なログ収集との違いは、**文脈と重みを保存したままLLMに渡す**点にある。

| 重みの種類 | 意味 | 取得ソース |
|---|---|---|
| **発言頻度** | 特定トピックへの組織的注目度 | Chat / Gmail |
| **発言者の役割** | 意思決定の影響力 | Admin API / Calendar主催者 |
| **応答速度** | 優先度・緊急度の暗黙的評価 | Gmailスレッド timestamp差分 |
| **会議の密度** | 議論が必要な問題の重さ | Calendar参加者数 × 時間 |
| **繰り返しパターン** | 制度化されていない定常業務 | Calendar recurrence / Chat定期発言 |
| **スレッド深度** | 合意形成の困難さ | Gmailスレッド返信数 |

---

## アーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: Raw Collection（gws CLI）                  │
│  Calendar / Gmail / Chat → JSON                      │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│  Layer 2: Context Assembly（重み付けと文脈結合）      │
│  - イベント × 参加者 × スレッド の時系列マージ       │
│  - トピッククラスタリング（キーワード / embedding）  │
│  - 発言者ネットワークグラフの構築                    │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│  Layer 3: LLM Analysis（Claude API）                 │
│  - コンテキスト付きプロンプトでインサイト抽出        │
│  - 暗黙プロセスの命名・構造化                        │
│  - 自動化・AI委譲候補のスコアリング                  │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│  Layer 4: Output                                      │
│  - 暗黙プロセスカタログ（Sheets / Doc）              │
│  - 自動化候補リスト（優先度付き）                    │
└─────────────────────────────────────────────────────┘
```

---

## Layer 1: gws CLIによるデータ収集

### 1-1. カレンダー（行動パターン + 参加者ネットワーク）

```bash
# 4週間分取得（1週間では定常/非定常の区別不能）
gws calendar events list \
  --params '{
    "calendarId": "primary",
    "timeMin": "2026-02-15T00:00:00Z",
    "timeMax": "2026-03-15T00:00:00Z",
    "singleEvents": true,
    "orderBy": "startTime",
    "maxResults": 500
  }' \
  --page-all > raw_calendar.json
```

**LLMに渡す文脈**：
- `summary`（件名）、`description`（アジェンダ）
- `attendees[]`（参加者リスト → 誰と誰が一緒に意思決定するか）
- `recurrence`（繰り返し → 制度化されていない定例業務の検出）
- `start/end`（所要時間 → 議題の重さ）

### 1-2. Gmail送信ログ（指示・承認・意思決定の発信元）

```bash
# 送信スレッド一覧
gws gmail users threads list \
  --params '{
    "userId": "me",
    "q": "in:sent after:2026/02/15 before:2026/03/15",
    "maxResults": 500
  }' \
  --page-all > sent_thread_ids.json

# スレッド詳細（返信数・参加者・本文）
# jqでIDを抽出してループ
cat sent_thread_ids.json | jq -r '.threads[].id' | while read id; do
  gws gmail users threads get \
    --params "{\"userId\": \"me\", \"id\": \"$id\", \"format\": \"full\"}" \
    >> sent_threads_full.ndjson
  sleep 0.1  # レート制限対策
done
```

**LLMに渡す文脈**：
- スレッド内のメッセージ数（深度 → 合意形成の困難さ）
- 返信者の変化（誰がエスカレーション先か）
- 件名のキーワード
- 送信から初回返信までの時間差（優先度の暗黙的評価）

### 1-3. Google Chat（リアルタイム意思決定の密度）

```bash
# スペース一覧と種類の把握
gws chat spaces list --params '{"pageSize": 50}' > spaces.json

# 全スペースのメッセージを収集（重要：スペースを絞らない）
cat spaces.json | jq -r '.spaces[].name' | while read space; do
  gws chat spaces messages list \
    --params "{
      \"parent\": \"$space\",
      \"pageSize\": 1000,
      \"filter\": \"createTime > \\\"2026-02-15T00:00:00Z\\\"\"
    }" \
    --page-all >> chat_all.ndjson
  sleep 0.2
done
```

**LLMに渡す文脈**：
- `sender.name`（誰が発言しているか）
- `createTime`（発言の時系列密度）
- `text`（内容）
- スペース名（どの文脈での発言か）
- スレッド構造（`thread.name` が同じメッセージ群）

---

## Layer 2: Context Assembly

### 2-1. トピッククラスタリング（重みの算出）

生ログをそのままLLMに渡すのは非効率。まずキーワードベースで事前クラスタリングする。

```python
# 擬似コード：トピック別発言数の集計
topics = {}
for message in all_messages:
    keywords = extract_keywords(message.text)  # TF-IDF or simple tokenizer
    for kw in keywords:
        topics[kw] = topics.get(kw, [])
        topics[kw].append({
            "source": message.source,  # calendar/gmail/chat
            "sender": message.sender,
            "timestamp": message.timestamp,
            "text": message.text
        })

# 重みの算出
topic_weights = {
    kw: {
        "count": len(messages),
        "unique_senders": len(set(m["sender"] for m in messages)),
        "sources": list(set(m["source"] for m in messages)),
        "timespan_days": (max_ts - min_ts).days
    }
    for kw, messages in topics.items()
}
```

### 2-2. LLMへ渡すコンテキストパッケージの構造

```json
{
  "analysis_period": "2026-02-15 to 2026-03-15",
  "topic_cluster": {
    "label": "予算承認",
    "weight": {
      "total_mentions": 47,
      "unique_participants": 8,
      "sources": ["calendar", "gmail", "chat"],
      "recurrence": "weekly"
    },
    "evidence": [
      {
        "source": "calendar",
        "event": "予算レビュー定例",
        "attendees": ["A", "B", "C"],
        "frequency": "毎週火曜",
        "avg_duration_min": 60
      },
      {
        "source": "gmail",
        "thread_depth": 12,
        "escalation_path": ["A → B → C"],
        "avg_response_hours": 2.3
      },
      {
        "source": "chat",
        "space": "経営企画",
        "message_burst": "月末に集中",
        "sample_messages": ["...", "..."]  // 3-5件のサンプル
      }
    ]
  }
}
```

---

## Layer 3: LLMへのプロンプト設計

ここが最も重要。何を問うかで発見できるインサイトが変わる。

### プロンプト設計の原則

**やってはいけないこと**：「意思決定を抽出してください」という曖昧な指示。

**やるべきこと**：仮説を持った問いを複数投げ、クロスバリデーションする。

### プロンプト群

#### P1：暗黙プロセスの命名

```
以下は組織のコミュニケーションログからトピック「{topic}」に関連する
証拠を収集したものです。

{context_package}

このデータから、明文化されていないが繰り返し発生している業務プロセスを
推定してください。以下の形式で出力してください：
- プロセス名（命名してください）
- トリガー：何が起点でこのプロセスが始まるか
- 関与者：誰が、どの役割で関与するか
- 判断基準：どのような基準で意思決定されているか（ログから推定）
- 所要時間：開始から完了まで
- ボトルネック：どこで滞留が発生しているか
```

#### P2：自動化・AI委譲可能性のスコアリング

```
上記のプロセス「{process_name}」について、
自動化またはAIへの委譲可能性を以下の軸で0-10でスコアリングしてください：

1. ルール化可能性：判断基準が明示的か
2. 繰り返し性：頻度と均一性
3. データ依存性：人間の経験・感覚への依存度（低いほど委譲しやすい）
4. リスク：誤判断した場合の影響度（低いほど委譲しやすい）
5. 関与者数：少ないほど委譲しやすい

スコアに基づき、推奨アクションを以下から選択：
- 即時自動化可能
- AIアシスト（人間が最終判断）
- プロセス文書化が先決
- 現状維持（自動化不適）
```

#### P3：組織ネットワークの暗黙的構造

```
以下の参加者ネットワークデータから、
公式の組織図には現れない意思決定の実態を分析してください：

{network_data}  // 誰と誰が共同で意思決定しているかのグラフ

特に注目してください：
- 情報のハブになっている人物（多くのトピックに登場する）
- 特定トピックにのみ登場する専門家
- 公式職位と実際の影響力の乖離
- 孤立しているトピック（特定個人に閉じた意思決定）
```

---

## Layer 4: 出力形式

### 暗黙プロセスカタログ（Sheetsへ書き込み）

```bash
gws sheets spreadsheets values append \
  --params '{
    "spreadsheetId": "SHEET_ID",
    "range": "プロセスカタログ!A1",
    "valueInputOption": "USER_ENTERED"
  }' \
  --json '{
    "values": [
      ["プロセス名", "トリガー", "関与者", "判断基準", "自動化スコア", "推奨アクション", "根拠ログ数"]
    ]
  }'
```

---

## 重要な設計判断：スペースを絞らない理由

あなたの案では「特定のチャットスペースログ」を対象にしていたが、**これは暗黙知発見の観点では逆効果**。

暗黙知は複数のチャンネルをまたいで分散している。特定スペースのみを見ると：
- そのスペース内で完結しているように見える意思決定が、実はDMやメールで事前合意されているケースを見逃す
- どのチャンネルに重要な情報が集まっているか自体が発見すべきインサイト

**全スペース収集 → トピック別クラスタリング → ソース横断分析** の順序が正しい。

---

## 実装ロードマップ

| Week | 作業 | 成果物 |
|---|---|---|
| 1 | gws認証 + 全ソース収集スクリプト作成・実行 | 生ログJSON（4週間分） |
| 2 | トピッククラスタリング + コンテキストパッケージ生成スクリプト | topic_clusters.json |
| 3 | LLMプロンプト設計・検証（上位5トピックで試行） | インサイトドラフト |
| 4 | 全トピックへの適用 + Sheetsカタログ化 | 暗黙プロセスカタログ v1 |
| 5〜 | カタログに基づく自動化実装の優先順位決定 | 自動化ロードマップ |
