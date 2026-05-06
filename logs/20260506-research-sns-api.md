# SNS API リサーチ：X投稿自動化 + マルチSNS運用

> 調査日：2026年5月  
> 目的：Google Calendar / GitHub の更新をトリガーとして X にポストし、ナラティブを構築・蓄積する

-----

## 1. X (Twitter) API 現状

### 料金体系（2026年5月時点）

|プラン               |月額                |書き込み上限             |読み取り上限     |備考            |
|------------------|------------------|-------------------|-----------|--------------|
|**Free**          |無料                |500 posts/月        |100 reads/月|1アプリ・1プロジェクト  |
|**Basic**         |$200（年契約 $175）    |10,000 posts/月     |制限あり       |2アプリ環境        |
|**Pro**           |$5,000（年契約 $4,500）|1,000,000 posts/月  |制限あり       |3アプリ環境        |
|**Enterprise**    |$50,000〜          |50,000,000 posts/月〜|カスタム       |要問い合わせ        |
|**Pay-per-use（β）**|従量課金              |使った分だけ             |使った分だけ     |2026年2月6日に正式発表|

**Pay-per-use の要点：**

- 2026年2月に正式ローンチ（従来のティアと併存）
- Free ティアから移行するユーザーには $10 バウチャー付与
- X API Calculator でコストを事前試算可能
- Free/Basic ティアのまま opt-in することも可能

### 用途別の現実的なプラン選択

自動ポスト（カレンダー・GitHub トリガー）だけであれば：

- **投稿頻度が月 500 件以内 → Free ティアで足りる**（月500 posts は 1日約16件）
- 複数アカウント・高頻度 → Basic（$200/月）が現実的な最低ライン
- Free〜Basicの間に合理的な中間プランが存在しないため、量が増えると一気にコストが跳ね上がる

### X API v2 認証方式

|方式                    |用途               |
|----------------------|-----------------|
|OAuth 2.0             |推奨。ユーザー代理アクションに使用|
|OAuth 1.0a            |レガシー。v1.1 との後方互換 |
|Bearer Token（App-only）|読み取り専用・アプリレベル認証  |

-----

## 2. 自動化アーキテクチャ：トリガー → 投稿

### パターン A：ノーコード自動化ツール（推奨）

#### n8n（最有力）

- **セルフホスト可能**（OSS）かつクラウド版あり
- GitHub → X ポスト、Google Calendar → X ポストのワークフローを **ノードで直接構築可能**
- GitHub Webhook をトリガーとして、コミット・PR・リリースイベントを拾う
- Google Calendar はポーリングで新規イベント検知
- X (Twitter) ノードが標準搭載（OAuth 2.0 対応）
- AI ノードを組み合わせてポスト文章を LLM で生成することも可能
- セルフホスト版は **API コスト以外は無料**

**想定フロー例（GitHub リリース → X ポスト）：**

```
GitHub Webhook (release published)
  → HTTPリクエスト受信
  → AI Node（Claude/GPT）でリリースノートから投稿文生成
  → X Node（create tweet）
  → 必要に応じて Bluesky / Threads にも同時投稿
```

**想定フロー例（Google Calendar イベント → X ポスト）：**

```
Google Calendar Trigger（イベント開始 N時間前）
  → イベント情報取得
  → AI Node でイベント告知文生成
  → X Node（create tweet）
```

#### Zapier

- クラウドオンリー・ノーコード
- Google Calendar → X の公式 Zap テンプレートあり
- GitHub トリガー対応
- 無料プランは限定的（Zaps 5件・月100タスク）、実用的には $20/月〜

#### Make（旧Integromat）

- n8n と Zapier の中間的なポジション
- ビジュアルフローが直感的
- 無料プランあり（月1,000オペレーション）

### パターン B：直接 API 実装（コード）

X API v2 でポストを作成する最小コード例（Python）：

```python
import tweepy

client = tweepy.Client(
    consumer_key="...",
    consumer_secret="...",
    access_token="...",
    access_token_secret="..."
)

# Google Calendar / GitHub webhook を受けた後にこれを呼ぶ
client.create_tweet(text="リリース v1.2.0 をデプロイしました 🚀")
```

GitHub Actions から直接実行することもできる（secrets に API キーを登録）。

-----

## 3. X 以外の SNS API

### Bluesky（AT Protocol）

|項目         |内容                                           |
|-----------|---------------------------------------------|
|API コスト    |**無料**（レートリミットは存在するが料金なし）                    |
|認証         |App Password（ハンドル + アプリ専用パスワード）              |
|SDK        |TypeScript（`@atproto/api`）/ Python（`atproto`）|
|文字数        |約 300文字                                      |
|特徴         |オープンプロトコル（AT Protocol）・データポータビリティあり          |
|MAU（2025年末）|約4,100万（エンゲージメント率は高い）                        |

X API のコスト問題の回避策として最も現実的。開発者・技術者コミュニティへのリーチが強い。

```python
from atproto import Client

client = Client()
client.login('yourhandle.bsky.social', 'your-app-password')
client.send_post('GitHub リリース v1.2.0 公開しました')
```

### Threads API（Meta）

|項目     |内容                         |
|-------|---------------------------|
|API コスト|**無料**（Instagram アカウントと紐付け）|
|認証     |Meta OAuth 2.0             |
|月間アクティブ|4億（2025年8月）                |
|日次アクティブ|1億1,500万（2025年6月）          |
|制約     |Instagram Business アカウントが必要|

### LinkedIn API

- 個人プロフィール投稿・企業ページへの投稿が可能
- 認証が複雑（OAuth 2.0、申請審査が必要な場合あり）
- 技術・ビジネス系コンテンツとの相性が高い

-----

## 4. マルチ SNS 運用ツール

複数アカウント・複数プラットフォームを一括管理したい場合、以下のツールが有力候補。

### ツール比較

|ツール          |対応 SNS 数|API 有無  |無料プラン        |特徴                                |
|-------------|--------|--------|-------------|----------------------------------|
|**Ayrshare** |13+     |◎ 充実    |なし（$29〜）     |最も幅広いプラットフォーム対応、API ファーストで開発者向け   |
|**Zernio**   |14+     |◎       |なし           |ユニファイド API（1リクエストで複数 SNS に投稿）     |
|**n8n**      |数百（連携次第）|◎       |◎ セルフホスト無料   |自前で全制御、最も柔軟                       |
|**OneUp**    |10+     |◎（MCP対応）|△            |Claude MCP 対応（LLM から直接投稿可能）       |
|**Nuelink**  |12      |△       |△ 7日試用       |X/Bluesky/Threads 含む12プラットフォーム一括  |
|**Fedica**   |12      |△       |◎ Threads 無制限|RSS 自動投稿、12プラットフォーム対応             |
|**Metricool**|9+      |△       |◎（50posts/月） |X/Bluesky/Threads/TikTok 含む、分析機能充実|

### API ファースト統合レイヤー（開発者向け）

**Ayrshare**（`$29/月〜`）

- X、Bluesky、Threads、Instagram、LinkedIn、TikTok 等に単一 API で投稿
- `POST /v2/post` 一発でプラットフォームを選んで投稿

**Zernio**（`$5/月 + $0.01/post〜`）

- 統一 JSON スキーマ（X も Bluesky も同じ形式で書ける）
- 1 API コールで複数 SNS に同時投稿
- rate limit 管理・リトライを自動処理

-----

## 5. 推奨アーキテクチャ（ナラティブ構築用途）

### ローコスト・高柔軟性を優先する場合

```
[トリガー層]
  GitHub Webhook / Google Calendar Polling
          ↓
[オーケストレーション]
  n8n（セルフホスト or クラウド）
          ↓
[コンテンツ生成]
  Claude / GPT（AI Node）でナラティブ文生成
          ↓
[投稿層]
  X（Free ティア）+ Bluesky（無料）+ Threads（無料）
          ↓
[蓄積]
  Notion / Google Sheets にポスト内容を記録
```

**コスト概算：**

- X Free ティア（投稿のみ）：$0
- Bluesky：$0
- n8n セルフホスト（VPS 月$5〜）：$5〜
- Claude API（ポスト生成）：$2〜10/月程度（量次第）
- **合計：月 $7〜15 程度**

### マルチアカウント・スケールを優先する場合

```
[トリガー層]
  GitHub Webhook / Google Calendar
          ↓
[オーケストレーション]
  n8n
          ↓
[統一投稿 API]
  Ayrshare または Zernio
          ↓
[同時投稿先]
  X（Basic $200/月）+ Bluesky + Threads + LinkedIn
```

-----

## 6. リスク・留意点

|リスク              |内容                                                        |
|-----------------|----------------------------------------------------------|
|**X API 価格の不安定性**|2023〜2026年で複数回の値上げ実績あり。Free ティアの削減リスクが常に存在する              |
|**X の自動ポストポリシー** |スパム・bot 判定を受けるリスクがある。人間らしい投稿頻度・内容が重要                      |
|**Bluesky の分散性** |データポータビリティが高い一方、マネタイズモデルが未確立。長期的な安定性は X より不確実             |
|**Threads の制約**  |Instagram アカウント必須。API は使えるが Instagram との依存が強い             |
|**マルチアカウント規約**   |各 SNS の利用規約でマルチアカウント自動化に制限がある場合がある。Ayrshare 等の公式パートナー経由が安全|

-----

## 7. 結論・推奨アクション

1. **まず Bluesky + n8n で PoC を作る**：コスト $0 で GitHub/Calendar → 自動ポストを実証できる
1. **X は Free ティアを維持しつつ Pay-per-use を監視**：月 500 件以内に収まるなら Free で十分
1. **ナラティブ蓄積は Notion か Google Sheets に連携**：n8n から直接書き込めるため追加コスト不要
1. **スケール時は Ayrshare か Zernio の統一 API 採用**：X/Bluesky/Threads を一括管理
1. **X API の依存度を意図的に下げる**：Bluesky + Threads を並走させ、プラットフォームリスクを分散する

-----

## 参考リンク

- X API 公式ドキュメント：https://developer.x.com/en/support/x-api/v2
- X Pay-per-use 発表：https://devcommunity.x.com/t/announcing-the-launch-of-x-api-pay-per-use-pricing/256476
- Bluesky API ドキュメント：https://docs.bsky.app/
- n8n GitHub × X テンプレート：https://n8n.io/integrations/github/and/twitter/
- n8n Google Calendar × X テンプレート：https://n8n.io/integrations/google-calendar/and/twitter/
- Ayrshare（統一 SNS API）：https://www.ayrshare.com/
- Zernio（統一 SNS API）：https://zernio.com/