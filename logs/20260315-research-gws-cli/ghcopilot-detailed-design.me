# Google Workspace CLI を活用した行動ログ・意思決定ログ可視化
## ユースケース設計仕様書（実装者向け詳細草案）

- 対象リポジトリ: `googleworkspace/cli`
- Repository ID: `1171026502`
- 対象CLI: `gws`
- Repository URL: `https://github.com/googleworkspace/cli`
- 作成日: 2026-03-15
- 文書種別: 使用設計 / PoC設計 / データ設計 草案

---

## 1. 文書の目的

本書は、`gws`（Google Workspace CLI）を用いて Google Workspace 上の行動ログ・発話ログ・議論ログを取得し、  
組織内で暗黙的に運用されている意思決定プロセスや業務プロセスを可視化・構造化し、  
最終的に LLM によるインサイト発見、自動化候補抽出、業務標準化へ接続するための  
**実装可能な設計草案** を示すことを目的とする。

本書は特に以下の読者を想定する。

- 使用設計担当
- PoC設計担当
- データ基盤担当
- アプリケーション実装担当
- LLM/AI活用担当
- セキュリティ・ガバナンス担当

---

## 2. 背景と課題認識

多くの組織における重要な意思決定や業務推進は、  
明示された業務プロセスではなく、以下に依存している。

- 会議
- チャット上の相談・依頼・承認
- 個人間の暗黙知
- ドキュメントに残らない合意形成
- 繰り返し行われるが標準化されていない調整行為

このため、以下の課題が発生する。

- 意思決定の経路が追跡できない
- 何がどこで決まったか分からない
- 誰が実質的に進行・調整・判断しているか可視化されない
- 同じ種類の調整・確認・承認が何度も発生する
- LLMに渡すべき文脈が生ログに埋もれている

---

## 3. 解決アプローチ

`gws` を用いて Google Workspace の複数データソースからログを取得し、  
以下の段階で処理する。

1. **収集**
   - Calendar / Chat / Gmail / Drive 等から構造化データ取得

2. **正規化**
   - APIレスポンス差異の吸収
   - 共通スキーマへの整形

3. **意味抽出**
   - トピック
   - 発言行為
   - 決定
   - アクション
   - 関与者
   - 重み

4. **可視化**
   - 時系列
   - トピック頻度
   - アクション残件
   - 決定密度

5. **LLM投入**
   - 生ログではなく、中間構造をLLMに渡す

6. **業務変革**
   - 自動要約
   - ネクストアクション抽出
   - 標準化候補抽出
   - エージェント化

---

## 4. Google Workspace CLI (`gws`) 前提

`gws` は Google Discovery Service をもとに動的にコマンド面を構築する CLI であり、  
Google Workspace API に対して JSON 出力で統一的にアクセスできる。

### 4.1 本取り組みにおける重要な性質
- Google Workspace APIを横断して扱える
- JSON出力を前提とした機械処理に向く
- `--fields` により応答フィールドを絞れる
- `--page-all` でページネーションに対応できる
- `gws schema <service.resource.method>` によりスキーマ確認が可能
- helper command も存在するが、本設計ではまず Discovery ベースAPI呼び出しを主対象とする

### 4.2 実装上の注意
- APIレスポンスはサービスごとに構造差が大きい
- フィールド不足に注意しつつ、`--fields` でコンテキスト量を抑制する
- 生ログ保存と、LLM投入用整形ログを分離する
- OAuthスコープとアクセス権限に依存する
- Chat や Gmail はプライバシー・監査観点の設計が必要

---

## 5. ユースケース一覧

- **UC-01**: Googleカレンダーの1週間分の行動ログを取得し、活動レポートを作成する
- **UC-02**: 特定個人の1週間分の発言を取得し、指示・判断・意思決定促進行為をレポートする
- **UC-03**: 特定のGoogle Chatスペースログを取得し、意思決定ログとネクストアクションをレポートする

---

# 6. 共通アーキテクチャ

## 6.1 処理フロー

```text
[gws CLI]
   ↓
[Raw JSON取得]
   ↓
[Normalizer]
   ↓
[Canonical Event Store]
   ↓
[Feature Extraction]
   ├─ topic extraction
   ├─ speech act classification
   ├─ decision candidate detection
   ├─ next action detection
   └─ actor weighting
   ↓
[Visualization Layer]
   ↓
[LLM Context Builder]
   ↓
[Report / Insight / Automation]
```

## 6.2 保存レイヤ
最低でも以下の3層を分ける。

1. **raw/**
   - gwsの取得結果そのまま
2. **normalized/**
   - 共通スキーマに整形後
3. **derived/**
   - LLM向け特徴量・要約・意思決定候補

---

# 7. 共通データモデル

---

## 7.1 Canonical Event Model

Google Workspace の異なるログソースを共通的に扱うため、  
以下の共通イベントモデルを定義する。

```json
{
  "event_id": "string",
  "source_type": "calendar|chat|gmail|drive|doc",
  "source_system": "google_workspace",
  "tenant_id": "string",
  "user_id": "string",
  "actor_id": "string",
  "actor_display_name": "string",
  "channel_id": "string",
  "channel_type": "calendar|space|mailbox|drive",
  "thread_id": "string",
  "timestamp": "2026-03-15T10:00:00Z",
  "title": "string",
  "body_text": "string",
  "participants": [
    {
      "id": "string",
      "display_name": "string",
      "role": "organizer|attendee|sender|recipient|member"
    }
  ],
  "references": [
    {
      "type": "drive_file|meeting|message|thread|url",
      "id": "string",
      "label": "string"
    }
  ],
  "metadata": {},
  "raw_ref": "raw/calendar/2026-03-15/events-001.json"
}
```

---

## 7.2 Decision Candidate Model

```json
{
  "decision_candidate_id": "string",
  "source_event_ids": ["string"],
  "topic": "string",
  "decision_text": "string",
  "decision_type": "approval|rejection|priority|scope|assignment|policy|strategy",
  "decision_strength": 0.82,
  "decision_maker_candidates": [
    {
      "actor_id": "string",
      "score": 0.91
    }
  ],
  "supporting_context": [
    "string"
  ],
  "timestamp": "2026-03-15T10:00:00Z",
  "status": "candidate|confirmed|rejected"
}
```

---

## 7.3 Next Action Model

```json
{
  "action_id": "string",
  "source_event_ids": ["string"],
  "action_text": "string",
  "assignee_candidates": [
    {
      "actor_id": "string",
      "score": 0.77
    }
  ],
  "due_date": "2026-03-20",
  "priority": "low|medium|high|critical",
  "status": "open|done|unknown",
  "topic": "string",
  "confidence": 0.79
}
```

---

## 7.4 Topic Weight Model

```json
{
  "topic": "採用計画",
  "period_start": "2026-03-08",
  "period_end": "2026-03-15",
  "message_count": 42,
  "participant_count": 7,
  "decision_count": 4,
  "action_count": 9,
  "meeting_count": 3,
  "weight_score": 0.88
}
```

---

# 8. UC-01: Googleカレンダーの1週間分の行動ログ可視化

## 8.1 目的
個人または特定ロールの活動実態をカレンダーイベントから可視化し、  
会議中心の働き方、意思決定の場、繰り返し業務の温床を把握する。

## 8.2 対象API
- `calendar.events.list`

## 8.3 CLI想定
```bash
gws calendar events list \
  --params '{"calendarId":"primary","timeMin":"2026-03-08T00:00:00Z","timeMax":"2026-03-15T23:59:59Z","singleEvents":true,"orderBy":"startTime"}' \
  --fields "items(id,status,summary,description,start,end,attendees,organizer,location,recurrence,htmlLink,created,updated)"
```

## 8.4 主な取得項目
| API Field | 用途 |
|---|---|
| `id` | イベント識別子 |
| `summary` | 会議タイトル |
| `description` | 文脈補助 |
| `start` / `end` | 時間計算 |
| `attendees` | 関与者抽出 |
| `organizer` | 主催者把握 |
| `location` | 会議種別推定 |
| `recurrence` | 定例判定 |
| `status` | キャンセル除外 |
| `created` / `updated` | 変更頻度把握 |

## 8.5 正規化後スキーマ例
```json
{
  "event_id": "cal_evt_001",
  "source_type": "calendar",
  "timestamp": "2026-03-12T09:00:00Z",
  "title": "採用定例",
  "body_text": "候補者進捗確認",
  "actor_id": "user@example.com",
  "channel_id": "primary",
  "participants": [
    {"id": "a@example.com", "display_name": "A", "role": "attendee"},
    {"id": "b@example.com", "display_name": "B", "role": "attendee"}
  ],
  "metadata": {
    "end_time": "2026-03-12T10:00:00Z",
    "location": "Google Meet",
    "is_recurring": true
  }
}
```

## 8.6 派生特徴量
- duration_minutes
- attendee_count
- recurring_flag
- external_attendee_flag
- topic_cluster
- meeting_density_per_day
- focus_time_gap

## 8.7 可視化例
- 日別会議時間
- テーマ別会議時間割合
- 社内/社外会議比率
- 参加者ネットワーク
- 定例/非定例比率

## 8.8 LLMへの入力単位
- 1日単位サマリ
- 1週間単位サマリ
- トピック別サマリ
- recurring meeting cluster summary

## 8.9 リスク
- 会議名だけでテーマ特定が不安定
- 実際の稼働とカレンダー差分
- 空き時間＝集中時間ではない

---

# 9. UC-02: 特定個人の1週間分の発言から意思決定促進ログを抽出

## 9.1 目的
個人の発言行動から、組織内で果たしている役割
（指示、整理、承認、優先順位付け、促進）を見える化する。

## 9.2 対象API候補
主対象:
- `chat.spaces.messages.list`

補助:
- `gmail.users.messages.list`
- `gmail.users.messages.get`

## 9.3 CLI想定（Chat）
```bash
gws chat spaces messages list \
  --params '{"parent":"spaces/SPACE_ID"}' \
  --fields "messages(name,text,createTime,sender,thread,annotations,space)"
```

## 9.4 主な取得項目
| API Field | 用途 |
|---|---|
| `name` | メッセージID |
| `text` | 発言本文 |
| `createTime` | 時系列分析 |
| `sender` | 発言者識別 |
| `thread` | 文脈復元 |
| `annotations` | リンク/メンション補助 |
| `space` | 所属スペース |

## 9.5 正規化後スキーマ例
```json
{
  "event_id": "chat_msg_001",
  "source_type": "chat",
  "timestamp": "2026-03-12T11:30:00Z",
  "actor_id": "user@example.com",
  "actor_display_name": "Masa",
  "channel_id": "spaces/AAAA",
  "channel_type": "space",
  "thread_id": "threads/123",
  "body_text": "この件は今週中に方針決めましょう。Aさんは見積もり、Bさんはリスク整理お願いします。",
  "participants": [],
  "metadata": {
    "message_name": "spaces/AAAA/messages/BBB"
  }
}
```

## 9.6 分類対象（Speech Act）
- instruction
- request
- approval
- rejection
- escalation
- prioritization
- clarification
- synthesis
- proposal
- decision_prompt

## 9.7 推奨派生特徴量
- message_length
- reply_count
- mention_count
- action_verb_count
- decision_keyword_count
- interrogative_flag
- imperative_flag
- assignee_candidate_count
- topic_cluster

## 9.8 ルールベース初期判定例
### 指示候補
- 「お願いします」
- 「対応してください」
- 「進めてください」
- 「確認してください」

### 判断候補
- 「これでいきます」
- 「今回は見送ります」
- 「方針は〜とします」
- 「優先度を上げます」

### 論点整理候補
- 「論点は3つあります」
- 「整理すると」
- 「まず」
- 「一方で」

## 9.9 LLMに期待する役割
- 発言タイプ分類
- 決定促進発言の抽出
- リーダーシップ行動の要約
- 反復指示パターンの抽出
- テンプレート化候補の示唆

## 9.10 出力例
```json
{
  "actor_id": "user@example.com",
  "period": "2026-03-08/2026-03-15",
  "summary": {
    "message_count": 56,
    "decision_prompt_count": 14,
    "instruction_count": 12,
    "approval_count": 4
  },
  "top_topics": [
    {"topic": "採用", "weight_score": 0.91},
    {"topic": "プロダクト優先度", "weight_score": 0.74}
  ],
  "behavioral_insights": [
    "論点整理と担当割り振りの発言が多い",
    "最終決定よりも意思決定促進役として機能している"
  ]
}
```

## 9.11 リスク
- 発言者の文体差
- 役職による発言バイアス
- 発言数と影響力の乖離
- 個人監視への誤用

---

# 10. UC-03: 特定チャットスペースの意思決定ログとネクストアクション抽出

## 10.1 目的
チーム/プロジェクト単位の議論ログから、意思決定、未決事項、担当付きアクションを抽出し、
実務運営を可視化する。

## 10.2 対象API
- `chat.spaces.messages.list`

## 10.3 CLI想定
```bash
gws chat spaces messages list \
  --params '{"parent":"spaces/SPACE_ID"}' \
  --fields "messages(name,text,createTime,sender,thread,annotations)"
```

## 10.4 主な取得項目
| API Field | 用途 |
|---|---|
| `name` | メッセージID |
| `text` | 本文 |
| `createTime` | 時系列 |
| `sender` | 発言者 |
| `thread` | スレッド復元 |
| `annotations` | リンク・メンション・補足情報 |

## 10.5 正規化後スキーマ例
```json
{
  "event_id": "chat_msg_101",
  "source_type": "chat",
  "timestamp": "2026-03-10T08:45:00Z",
  "actor_id": "pm@example.com",
  "channel_id": "spaces/PROJ001",
  "thread_id": "threads/789",
  "body_text": "仕様変更は来週リリースには入れません。今週は不具合修正を優先します。田中さんは告知文、佐藤さんはテスト観点整理をお願いします。",
  "metadata": {
    "message_name": "spaces/PROJ001/messages/ABC"
  }
}
```

## 10.6 抽出対象
### 意思決定
- 採用/不採用
- 優先順位変更
- スコープ変更
- 方針決定
- 担当アサイン
- 期限設定

### ネクストアクション
- 誰が何をやるか
- いつまでにやるか
- 依存関係はあるか
- 未着手/進行中/完了の推定

### 未決事項
- 回答待ち
- 方針未定
- 担当未定
- 情報不足

## 10.7 スレッド統合ルール
- `thread_id` 単位でメッセージ束を構築
- thread がない/不十分な場合は時間近接 + topic similarity で疑似束化
- 1スレッド = 1論点 とは限らないため topic segmentation を追加考慮

## 10.8 出力例
```json
{
  "space_id": "spaces/PROJ001",
  "period": "2026-03-08/2026-03-15",
  "decisions": [
    {
      "decision_text": "来週リリースに仕様変更は入れない",
      "decision_type": "scope",
      "decision_maker_candidates": [
        {"actor_id": "pm@example.com", "score": 0.94}
      ]
    }
  ],
  "next_actions": [
    {
      "action_text": "告知文を作成する",
      "assignee_candidates": [
        {"actor_id": "tanaka@example.com", "score": 0.96}
      ],
      "priority": "high"
    }
  ],
  "open_questions": [
    "仕様変更の次回投入時期は未定"
  ]
}
```

## 10.9 可視化例
- topic timeline
- decision timeline
- open issue burn-down
- assignee heatmap
- repeated unresolved topic list

## 10.10 リスク
- Chatだけで決定が閉じない
- 添付Docsや会議を見ないと意味不足
- スレッド文化の薄い組織では再構成が難しい

---

# 11. API項目一覧（初期実装用）

## 11.1 Calendar
推奨取得フィールド:
```text
items(
  id,
  status,
  summary,
  description,
  start,
  end,
  attendees,
  organizer,
  location,
  recurrence,
  created,
  updated,
  htmlLink
)
```

## 11.2 Chat
推奨取得フィールド:
```text
messages(
  name,
  text,
  createTime,
  sender,
  thread,
  annotations,
  space
)
```

## 11.3 Gmail（将来拡張）
一覧:
```text
messages(id,threadId)
```

詳細:
```text
id,threadId,labelIds,snippet,payload,internalDate
```

---

# 12. JSONスキーマ観点の設計指針

## 12.1 Raw Schema
- gwsレスポンスをそのまま保存
- 将来のパーサ改善に備えて欠損なく保持

## 12.2 Normalized Schema
- すべてのデータを Canonical Event Model に写像
- ソース差異を metadata に押し込む
- `body_text` と `participants` を極力共通化

## 12.3 Derived Schema
- topic
- speech_act
- decision_candidate
- next_action
- actor_weight
- urgency
- confidence

---

# 13. 非機能要件

## 13.1 セキュリティ
- OAuth資格情報の安全保管
- 取得データの暗号化保存
- 個人情報のアクセス制御
- 出力レポートの共有制限

## 13.2 ガバナンス
- 監視ではなく改善目的であることの明文化
- 対象者同意
- 保存期間と削除ルール
- 匿名化レベル定義

## 13.3 可観測性
- 取得件数
- API失敗率
- 正規化失敗率
- 分類信頼度分布
- LLM推論コスト

## 13.4 拡張性
- 将来的に Gmail / Drive / Docs / Meet 連携可能
- スキーマ変更に耐えやすい
- topic model / classifier 差し替え可能

---

# 14. PoC推奨スコープ

## Phase 1
- 1人
- 1つのChatスペース
- 1週間
- Calendar + Chat のみ

## Phase 2
- 3〜5人
- 2〜3スペース
- 4週間
- 意思決定抽出とアクション抽出の評価

## Phase 3
- チーム横断
- レポート自動生成
- LLMサマリ定期実行
- 業務改善提案まで接続

---

# 15. 成功判定の観点

- 活動ログから意味のあるテーマが抽出できるか
- 個人発言から意思決定促進行動を説明できるか
- スペースログから決定とアクションを一定精度で抽出できるか
- 実務上「役に立つ」と評価されるか
- 自動化候補の発見につながるか

---

# 16. 結論

本設計の本質は、Google Workspace のログを収集すること自体ではなく、  
**人間同士のコミュニケーションの中に埋もれている意思決定構造と業務構造を再記述し、  
LLMが扱える構造化コンテキストへ変換すること** にある。

そのため初期フェーズでは、可視化だけに留まらず、以下を一体で進めるべきである。

- 共通スキーマ設計
- 意思決定候補抽出
- ネクストアクション抽出
- トピック重み付け
- ガバナンス設計

この3ユースケースは、その最初の具体的な実装単位として適している。
