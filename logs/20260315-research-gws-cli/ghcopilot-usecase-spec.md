# Google Workspace CLI を活用した行動ログ・意思決定ログ可視化
## ユースケース設計仕様書

- 対象リポジトリ: `googleworkspace/cli`
- Repository ID: `1171026502`
- 対象CLI: `gws`
- リポジトリURL: `https://github.com/googleworkspace/cli`
- 作成日: 2026-03-15
- 文書種別: 使用設計 / PoC設計 / 実装設計草案
- 想定配置先: `docs/usecase-spec.md`

---

## 目次

- [1. 文書の目的](#1-文書の目的)
- [2. 背景と課題認識](#2-背景と課題認識)
- [3. 解決アプローチ](#3-解決アプローチ)
- [4. Google Workspace CLI (`gws`) 前提](#4-google-workspace-cli-gws-前提)
- [5. ユースケース一覧](#5-ユースケース一覧)
- [6. 共通アーキテクチャ](#6-共通アーキテクチャ)
- [7. 共通データモデル](#7-共通データモデル)
- [8. UC-01: Googleカレンダーの1週間分の行動ログ可視化](#8-uc-01-googleカレンダーの1週間分の行動ログ可視化)
- [9. UC-02: 特定個人の1週間分の発言から意思決定促進ログを抽出](#9-uc-02-特定個人の1週間分の発言から意思決定促進ログを抽出)
- [10. UC-03: 特定チャットスペースの意思決定ログとネクストアクション抽出](#10-uc-03-特定チャットスペースの意思決定ログとネクストアクション抽出)
- [11. API項目一覧（初期実装用）](#11-api項目一覧初期実装用)
- [12. JSONスキーマ観点の設計指針](#12-jsonスキーマ観点の設計指針)
- [13. 非機能要件](#13-非機能要件)
- [14. PoC推奨スコープ](#14-poc推奨スコープ)
- [15. PoCタスク分解（WBS草案）](#15-pocタスク分解wbs草案)
- [16. 成功判定の観点](#16-成功判定の観点)
- [17. 今後の拡張候補](#17-今後の拡張候補)
- [18. 結論](#18-結論)

---

## 1. 文書の目的

本書は、`gws`（Google Workspace CLI）を用いて Google Workspace 上の行動ログ・発話ログ・議論ログを取得し、  
組織内で暗黙的に運用されている意思決定プロセスや業務プロセスを可視化・構造化し、  
最終的に LLM によるインサイト発見、自動化候補抽出、業務標準化へ接続するための  
**実装可能なユースケース設計仕様** を示すことを目的とする。

本書は、以下の読者を想定する。

- 使用設計担当
- PoC設計担当
- データ基盤担当
- アプリケーション実装担当
- LLM/AI活用担当
- セキュリティ・ガバナンス担当

---

## 2. 背景と課題認識

多くの組織における重要な意思決定や業務推進は、  
明示された業務プロセスではなく、以下のようなコミュニケーションに依存している。

- カレンダー上の会議
- Google Chat 上の相談・依頼・承認
- 特定個人の発言や調整による暗黙的な推進
- 会議後に明示されないまま進行するネクストアクション
- ドキュメント化されない合意形成

このため、以下の課題が発生する。

- 何がどこで決まったか追跡しづらい
- 意思決定の根拠が再利用されない
- 属人的な判断・調整に依存する
- 同じ種類の確認・承認・調整が繰り返される
- AI や自動化に渡すべき「文脈」が構造化されていない

---

## 3. 解決アプローチ

`gws` を用いて Google Workspace の複数データソースからログを取得し、  
以下の段階で処理する。

1. **収集**
   - Calendar / Chat / Gmail / Drive 等から構造化データを取得する

2. **正規化**
   - APIレスポンス差異を吸収し、共通スキーマへ整形する

3. **意味抽出**
   - トピック
   - 発言行為
   - 決定候補
   - ネクストアクション
   - 関与者
   - 重み

4. **可視化**
   - 時系列
   - トピック頻度
   - 決定密度
   - アクション残件

5. **LLM投入**
   - 生ログではなく、中間構造・要約済みデータを LLM に渡す

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
- `--page-all` によりページネーションに対応できる
- `gws schema <service.resource.method>` によりスキーマ確認が可能
- `calendar`, `chat`, `gmail`, `drive` などの主要サービスを扱える

### 4.2 実装上の前提

- APIレスポンスはサービスごとに構造差が大きい
- `--fields` を活用してレスポンス量を抑える
- 生ログ保存と LLM 投入用整形ログを分離する
- OAuthスコープ・権限・管理ポリシーに依存する
- Chat や Gmail はプライバシー・監査観点の設計が必要

---

## 5. ユースケース一覧

- **UC-01**: Googleカレンダーの1週間分の行動ログを取得し、活動レポートを作成する
- **UC-02**: 特定個人の1週間分の発言を取得し、指示・判断・意思決定促進行為をレポートする
- **UC-03**: 特定のGoogle Chatスペースログを取得し、意思決定ログとネクストアクションをレポートする

---

## 6. 共通アーキテクチャ

### 6.1 処理フロー

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

### 6.2 保存レイヤ

最低でも以下の3層を分ける。

1. **raw/**
   - `gws` の取得結果そのまま

2. **normalized/**
   - 共通スキーマに整形後のデータ

3. **derived/**
   - 特徴量、分類結果、意思決定候補、アクション候補、LLM向け要約

### 6.3 ディレクトリ構成案

```text
docs/
  usecase-spec.md

data/
  raw/
    calendar/
    chat/
    gmail/
  normalized/
  derived/

src/
  collectors/
  normalizers/
  extractors/
  reporters/
```

---

## 7. 共通データモデル

Google Workspace の異なるログソースを共通的に扱うため、共通モデルを定義する。

### 7.1 Canonical Event Model

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

### 7.2 Decision Candidate Model

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

### 7.3 Next Action Model

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

### 7.4 Topic Weight Model

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

## 8. UC-01: Googleカレンダーの1週間分の行動ログ可視化

### 8.1 目的

個人または特定ロールの活動実態をカレンダーイベントから可視化し、  
会議中心の働き方、意思決定の場、繰り返し業務の温床を把握する。

### 8.2 対象API

- `calendar.events.list`

### 8.3 CLI想定

```bash
gws calendar events list \
  --params '{"calendarId":"primary","timeMin":"2026-03-08T00:00:00Z","timeMax":"2026-03-15T23:59:59Z","singleEvents":true,"orderBy":"startTime"}' \
  --fields "items(id,status,summary,description,start,end,attendees,organizer,location,recurrence,htmlLink,created,updated)"
```

### 8.4 主な取得項目

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

### 8.5 正規化後スキーマ例

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

### 8.6 派生特徴量

- `duration_minutes`
- `attendee_count`
- `recurring_flag`
- `external_attendee_flag`
- `topic_cluster`
- `meeting_density_per_day`
- `focus_time_gap`

### 8.7 レポート出力

- 日別会議件数
- 日別会議時間
- テーマ別会議時間比率
- 社内/社外会議比率
- 定例/非定例比率
- 主要関係者一覧

### 8.8 留意点

- カレンダーは予定であり、実績と一致しない場合がある
- 会議タイトルだけでテーマ特定が難しい
- 空き時間がそのまま集中時間とは限らない

---

## 9. UC-02: 特定個人の1週間分の発言から意思決定促進ログを抽出

### 9.1 目的

特定個人の発言行動から、組織内で果たしている役割
（指示、整理、承認、優先順位付け、促進）を見える化する。

### 9.2 対象API候補

主対象:

- `chat.spaces.messages.list`

補助:

- `gmail.users.messages.list`
- `gmail.users.messages.get`

### 9.3 CLI想定（Chat）

```bash
gws chat spaces messages list \
  --params '{"parent":"spaces/SPACE_ID"}' \
  --fields "messages(name,text,createTime,sender,thread,annotations,space)"
```

### 9.4 主な取得項目

| API Field | 用途 |
|---|---|
| `name` | メッセージID |
| `text` | 発言本文 |
| `createTime` | 時系列分析 |
| `sender` | 発言者識別 |
| `thread` | 文脈復元 |
| `annotations` | リンク/メンション補助 |
| `space` | 所属スペース |

### 9.5 正規化後スキーマ例

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

### 9.6 分類対象（Speech Act）

- `instruction`
- `request`
- `approval`
- `rejection`
- `escalation`
- `prioritization`
- `clarification`
- `synthesis`
- `proposal`
- `decision_prompt`

### 9.7 推奨派生特徴量

- `message_length`
- `reply_count`
- `mention_count`
- `action_verb_count`
- `decision_keyword_count`
- `interrogative_flag`
- `imperative_flag`
- `assignee_candidate_count`
- `topic_cluster`

### 9.8 ルールベース初期判定例

#### 指示候補
- 「お願いします」
- 「対応してください」
- 「進めてください」
- 「確認してください」

#### 判断候補
- 「これでいきます」
- 「今回は見送ります」
- 「方針は〜とします」
- 「優先度を上げます」

#### 論点整理候補
- 「論点は3つあります」
- 「整理すると」
- 「まず」
- 「一方で」

### 9.9 出力例

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

### 9.10 留意点

- 発言量の多さは意思決定力と一致しない
- 非言語的な影響力は取得できない
- 個人監視として受け取られない設計が必要
- プライバシー・労務・ガバナンス上の合意が必要

---

## 10. UC-03: 特定チャットスペースの意思決定ログとネクストアクション抽出

### 10.1 目的

チーム/プロジェクト単位の議論ログから、意思決定、未決事項、担当付きアクションを抽出し、
実務運営を可視化する。

### 10.2 対象API

- `chat.spaces.messages.list`

### 10.3 CLI想定

```bash
gws chat spaces messages list \
  --params '{"parent":"spaces/SPACE_ID"}' \
  --fields "messages(name,text,createTime,sender,thread,annotations)"
```

### 10.4 主な取得項目

| API Field | 用途 |
|---|---|
| `name` | メッセージID |
| `text` | 本文 |
| `createTime` | 時系列 |
| `sender` | 発言者 |
| `thread` | スレッド復元 |
| `annotations` | リンク・メンション・補足情報 |

### 10.5 正規化後スキーマ例

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

### 10.6 抽出対象

#### 意思決定
- 採用/不採用
- 優先順位変更
- スコープ変更
- 方針決定
- 担当アサイン
- 期限設定

#### ネクストアクション
- 誰が何をやるか
- いつまでにやるか
- 依存関係はあるか
- 未着手/進行中/完了の推定

#### 未決事項
- 回答待ち
- 方針未定
- 担当未定
- 情報不足

### 10.7 スレッド統合ルール

- `thread_id` 単位でメッセージ束を構築する
- `thread_id` がない、または十分でない場合は時間近接 + topic similarity で疑似束化する
- 1スレッド = 1論点とは限らないため、topic segmentation を考慮する

### 10.8 出力例

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

### 10.9 可視化例

- topic timeline
- decision timeline
- open issue burn-down
- assignee heatmap
- repeated unresolved topic list

### 10.10 留意点

- Chat だけでは決定が閉じない場合がある
- 添付Docsや会議を見ないと文脈が不足する
- スレッド文化が弱い組織では再構成が難しい

---

## 11. API項目一覧（初期実装用）

### 11.1 Calendar

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

### 11.2 Chat

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

### 11.3 Gmail（将来拡張）

一覧:

```text
messages(id,threadId)
```

詳細:

```text
id,threadId,labelIds,snippet,payload,internalDate
```

---

## 12. JSONスキーマ観点の設計指針

### 12.1 Raw Schema

- `gws` レスポンスをそのまま保存する
- 将来のパーサ改善に備えて欠損なく保持する

### 12.2 Normalized Schema

- すべてのデータを Canonical Event Model に写像する
- ソース差異は `metadata` に保持する
- `body_text` と `participants` を極力共通化する

### 12.3 Derived Schema

以下を派生データとして保持する。

- `topic`
- `speech_act`
- `decision_candidate`
- `next_action`
- `actor_weight`
- `urgency`
- `confidence`

---

## 13. 非機能要件

### 13.1 セキュリティ

- OAuth資格情報の安全保管
- 取得データの暗号化保存
- 個人情報のアクセス制御
- 出力レポートの共有制限

### 13.2 ガバナンス

- 監視ではなく改善目的であることの明文化
- 対象者同意
- 保存期間と削除ルール
- 匿名化レベル定義

### 13.3 可観測性

- 取得件数
- API失敗率
- 正規化失敗率
- 分類信頼度分布
- LLM推論コスト

### 13.4 拡張性

- 将来的に Gmail / Drive / Docs / Meet へ拡張可能
- スキーマ変更に耐えやすい
- topic model / classifier を差し替え可能

---

## 14. PoC推奨スコープ

### Phase 1
- 対象: 1人
- 対象スペース: 1つ
- 期間: 1週間
- 対象ソース: Calendar + Chat

### Phase 2
- 対象: 3〜5人
- 対象スペース: 2〜3つ
- 期間: 4週間
- 実施内容: 意思決定抽出とアクション抽出の精度評価

### Phase 3
- 対象: チーム横断
- 実施内容:
  - レポート自動生成
  - LLMサマリ定期実行
  - 業務改善提案との接続

---

## 15. PoCタスク分解（WBS草案）

### 15.1 企画・要件定義
- [ ] 対象ユースケースの優先順位確定
- [ ] 対象部門 / 対象者 / 対象スペースの選定
- [ ] プライバシー・ガバナンス条件の整理
- [ ] 利用スコープ・除外条件の定義
- [ ] 成功指標（KPI / 評価方法）の合意

### 15.2 認証・環境準備
- [ ] `gws` の導入
- [ ] Google Cloud / OAuth設定
- [ ] 必要APIの有効化
- [ ] スコープ確認
- [ ] 実行環境（ローカル / CI / サーバ）決定

### 15.3 データ取得実装
- [ ] Calendar collector 実装
- [ ] Chat collector 実装
- [ ] raw保存処理実装
- [ ] 取得失敗時の再試行方針整理
- [ ] 期間指定・対象指定パラメータ化

### 15.4 正規化実装
- [ ] Canonical Event Model 定義確定
- [ ] Calendar normalizer 実装
- [ ] Chat normalizer 実装
- [ ] スレッド統合処理実装
- [ ] 欠損値 / 異常値処理方針整理

### 15.5 特徴量抽出・分析実装
- [ ] topic extraction 実装
- [ ] speech act classification 実装
- [ ] decision candidate detection 実装
- [ ] next action detection 実装
- [ ] actor weighting 実装

### 15.6 可視化・レポート実装
- [ ] 週次サマリ出力
- [ ] 会議可視化レポート
- [ ] 個人発言分析レポート
- [ ] スペース意思決定レポート
- [ ] LLM入力用コンテキスト生成

### 15.7 評価・改善
- [ ] 人手評価の実施
- [ ] 抽出精度の確認
- [ ] ノイズパターン整理
- [ ] プロンプト / ルール / 特徴量の改善
- [ ] 次Phaseへの改善計画作成

---

## 16. 成功判定の観点

- 活動ログから意味のあるテーマが抽出できるか
- 個人発言から意思決定促進行動を説明できるか
- スペースログから決定とアクションを一定精度で抽出できるか
- 実務上「役に立つ」と評価されるか
- 自動化候補の発見につながるか

---

## 17. 今後の拡張候補

- Gmail を用いた意思決定経路分析
- Drive / Docs の更新履歴との突合
- Calendar と Chat の横断分析
- 会議 → 議論 → 決定 → アクション のタイムライン統合
- エージェントによる定例レポート自動生成
- 組織ナレッジグラフ化
- 業務プロセステンプレート自動生成

---

## 18. 結論

本設計の本質は、Google Workspace のログを収集すること自体ではなく、  
**人間同士のコミュニケーションの中に埋もれている意思決定構造と業務構造を再記述し、  
LLMが扱える構造化コンテキストへ変換すること** にある。

そのため初期フェーズでは、可視化だけでなく、以下を一体で進めるべきである。

- 共通スキーマ設計
- 意思決定候補抽出
- ネクストアクション抽出
- トピック重み付け
- ガバナンス設計

この3ユースケースは、その最初の具体的な実装単位として適している。
