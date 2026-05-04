# 東京単館系映画館 上映情報プッシュシステム ベストプラクティス

## 結論：推奨アーキテクチャ

**Claude Code（開発）+ Google Apps Script（実行）** の構成。

- コスト：無料
- 精度：サイト固有パーサーによるため高い
- 運用：一度構築すれば全自動

-----

## システム全体像

```
[開発フェーズ]
Claude Code → サイト固有スクレイパー（GASスクリプト）を生成

[実行フェーズ]
[GAS 定時トリガー]
    → [各映画館サイトをfetch + サイト固有パーサーで構造化]
    → [Google Sheets に保存・前回との差分検出]
    → [差分あり時のみ Gmail で通知]
```

実行時にLLMは介在しない。スクレイパーを精度よく書くことで正確性を担保する。

-----

## 各コンポーネントの役割と使用ツール

### 1. スクレイパー開発：Claude Code

各映画館のHTMLを見せながら「このHTMLから上映情報を抽出するGAS関数を書いて」と指示する。映画館ごとにサイト構造が異なるため、Claude Codeで個別に生成するのが現実的。

- 初回：20館分のパーサーを生成（数時間）
- 以後：サイトリニューアル時のみ修正

### 2. 実行環境：Google Apps Script（無料）

- Google Workspace Business Standardに含まれる
- 毎週月曜8時など週次トリガーで自動実行
- `UrlFetchApp`でHTTP取得、`GmailApp`で送信、`SpreadsheetApp`でDB管理

```javascript
// GAS スクレイパー例（ユーロスペース）
function fetchEurospace() {
  const html = UrlFetchApp.fetch("https://www.eurospace.co.jp/").getContentText("UTF-8");
  // Claude Codeが生成したサイト固有のパーサーロジック
  const movies = parseEurospaceHtml(html);
  return movies;
}
```

### 3. データ管理：Google Sheets

- 上映情報のマスターDB（映画館名、タイトル、期間、時間帯）
- 前回取得分との差分検出
- URLリスト・有効/無効フラグを設定シートで管理

### 4. 通知：Gmail

- 週1回、変更・新着があれば送信（なければスキップ）
- 件名例：`【映画情報更新】新着2件 - ポレポレ東中野、シアター・イメージフォーラム`
- HTMLメールで映画館ごとにグルーピング

-----

## LM Studio + Brave Search MCPの位置づけ

GASのUrlFetchAppはJavaScriptレンダリングが必要なサイトを取得できない。そのようなサイトへの対処として使う。

- **用途**：JSレンダリング必須サイトの手動確認・補完調査
- **方法**：Brave Search MCPで「映画館名 上映スケジュール」を検索し、ローカルLLMで整理
- 定常的な自動収集はGAS、取得できない館の補完はLM Studio+Braveと役割分担

-----

## Codexの位置づけ

GASスクリプトの補助的なコード生成に使える。Claude Codeと使い分けるというより、アクセスしやすい方を使う程度の位置づけ。

-----

## 対象映画館リスト（初期セット）

|映画館           |備考           |
|--------------|-------------|
|ユーロスペース       |静的HTML、取得しやすい|
|ポレポレ東中野       |静的HTML       |
|アップリンク吉祥寺     |要確認          |
|シアター・イメージフォーラム|静的HTML       |
|ラピュタ阿佐ヶ谷      |静的HTML       |
|早稲田松竹         |静的HTML       |
|下高井戸シネマ       |静的HTML       |
|新宿武蔵野館        |要確認          |
|ヒューマントラストシネマ渋谷|要確認          |
|キネカ大森         |静的HTML       |

事前にClaude Codeに各サイトのHTMLを確認させ、静的/動的を判別してから開発に入る。

-----

## 構築ステップ

```
Step 1: Google Sheetsで映画館URLリストを作成（30分）
Step 2: 各映画館サイトのHTMLをClaude Codeに確認させ、
        GAS用パーサー関数を館ごとに生成（2〜4時間）
Step 3: GASに実装・手動実行でデバッグ（1〜2時間）
Step 4: 差分検出ロジックとGmail送信を実装（1時間）
Step 5: 時間トリガーを設定して本番稼働（5分）
```

**総構築時間の目安：5〜8時間**

-----

## コスト

|項目                      |コスト             |
|------------------------|----------------|
|Google Apps Script      |無料              |
|Claude Code / Codex     |無料（Max 5xプランに含む）|
|LM Studio + Brave Search|無料              |
|**合計**                  |**$0/月**        |

-----

## 精度向上のTips

1. **HTMLを前処理してscript/styleタグを除去**：パーサーのノイズ低減
1. **映画館ごとに取得成否をログ**：Sheetsにエラー列を設け、毎回の実行状態を可視化
1. **週次でURLの生死確認**：404になった館は自動スキップ
1. **失敗時はリトライロジック**：try-catchで次の映画館に進む設計

```javascript
// HTML前処理（GAS）
function cleanHtml(html) {
  return html
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
```

-----

## SNSアカウント監視による精度補完

### 目的と位置づけ

週1取得では「速報性」は不要。SNS監視の目的は**公式サイトに載りにくい情報の補完**に絞られる。

|情報の種類       |公式サイトスクレイプ|SNS監視|
|------------|----------|-----|
|通常スケジュール    |◎         |不要   |
|舞台挨拶・イベント登壇 |載らないことが多い |◎    |
|特集上映のコメント・背景|△         |◎    |
|上映変更・中止     |◎（週1で十分）  |不要   |

### 実装方法：RSSHub経由でXをRSS化

X（旧Twitter）のAPIは有料のため、**RSSHub**を使ってXアカウントのタイムラインをRSSフィードに変換し、GASで取得する。

```
[X 映画館アカウント]
    → [RSSHub（RSS変換）]
    → [GAS: fetchRssFeed()]
    → [Sheets に保存・キーワードフィルタ]
    → [Gmail 通知に追記]
```

#### RSSHubのエンドポイント例

```
https://rsshub.app/twitter/user/eurospace_info
https://rsshub.app/twitter/user/pole2_staff
https://rsshub.app/twitter/user/imageforum
```

GASからは通常のHTTPリクエストで取得できる。

```javascript
function fetchCinemaSnsFeeds() {
  const accounts = [
    { cinema: "ユーロスペース", url: "https://rsshub.app/twitter/user/eurospace_info" },
    { cinema: "ポレポレ東中野", url: "https://rsshub.app/twitter/user/pole2_staff" },
    { cinema: "イメージフォーラム", url: "https://rsshub.app/twitter/user/imageforum" },
  ];

  const keywords = ["上映", "舞台挨拶", "特集", "追加", "変更", "中止", "緊急"];

  accounts.forEach(({ cinema, url }) => {
    try {
      const xml = UrlFetchApp.fetch(url).getContentText();
      const items = parseRssItems(xml); // タイトル+本文を抽出
      items.forEach(item => {
        if (keywords.some(kw => item.text.includes(kw))) {
          // Sheetsに記録・通知対象に追加
          logSnsPost(cinema, item);
        }
      });
    } catch (e) {
      Logger.log(`SNS fetch failed: ${cinema} - ${e}`);
    }
  });
}
```

### RSSHubの可用性リスク

公開インスタンス（rsshub.app）は無料だが、アクセス制限や停止のリスクがある。安定性を重視する場合はGoogle Cloud Run（無料枠）でRSSHubをセルフホストする選択肢もある。

### Instagramは現状対応困難

RSSHubのInstagramルートはログイン情報が必要なため、個人利用でのGAS連携は設定コストが高い。X監視で代替する。

### SNS監視を加えた精度の整理

|ケース         |Webスクレイプのみ|Webスクレイプ + SNS監視|
|------------|----------|----------------|
|通常スケジュール取得  |◎         |◎               |
|舞台挨拶・登壇情報   |見逃しあり     |カバー率向上          |
|特集上映の背景・コメント|△         |◎               |
|誤検知リスク      |低         |中（キーワードフィルタに依存） |