# LLMブラウザ操作によるナレッジ蓄積パイプライン 設計仕様書

> 作りたいものに応じて選択肢を組み合わせる、参考用の設計仕様書

-----

## 0. 本書の使い方

1. 「§1 要件チェックリスト」で自分のユースケースを定義する
1. 「§2 アーキテクチャ全体像」で全体構造を理解する
1. 各層（収集 / 差分検知 / 構造化 / 蓄積 / 通知 / 取得）ごとに選択肢から1つ以上選ぶ
1. 「§9 構成パターン例」を参考に組み合わせて構築する

-----

## 1. 要件チェックリスト

設計前に以下を確認する。回答が構成選択を決定する。

### 1.1 ターゲットサイトの性質

- [ ] 公開サイトのみか、ログイン必須サイトを含むか
- [ ] JavaScriptレンダリング必須のサイトを含むか
- [ ] RSSやAPIが提供されているか
- [ ] 取得頻度（リアルタイム / 15分 / 1時間 / 日次）

### 1.2 LLM利用の制約

- [ ] APIを使えるか / サブスクリプションUIのみか
- [ ] 利用可能なサブスク（Claude Max / ChatGPT Pro / Gemini Advanced）

### 1.3 蓄積要件

- [ ] 過去ログの全文検索（人間 / AI 両方？）
- [ ] 差分管理・履歴保持の必要性
- [ ] 構造化データ（表形式）か非構造化か
- [ ] 想定データ量（MB / GB / TB）

### 1.4 通知要件

- [ ] プッシュ通知の必要性
- [ ] 通知先（モバイル / デスクトップ / メール / チャット）
- [ ] 重要度フィルタリングの有無

### 1.5 運用環境

- [ ] 実行ホスト（常時稼働ローカル端末 / クラウド / 両方）
- [ ] 利用可能な契約サービス
- [ ] メンテナンス可能な頻度

-----

## 2. アーキテクチャ全体像

```
┌─────────────────────────────────────────────────────────────┐
│  ① 収集層    : サブスクLLM UI / Headlessブラウザ / API      │
├─────────────────────────────────────────────────────────────┤
│  ② 差分検知層: ハッシュ比較 / 段落差分 / セマンティック差分 │
├─────────────────────────────────────────────────────────────┤
│  ③ 構造化層  : LLMでファクト抽出・JSON化                    │
├─────────────────────────────────────────────────────────────┤
│  ④ 蓄積層    : GitHub / Sheets / SQLite / Notion 等         │
├─────────────────────────────────────────────────────────────┤
│  ⑤ 整合性層  : 重複除去・矛盾解決・confidence更新           │
├─────────────────────────────────────────────────────────────┤
│  ⑥ 通知層    : Chat Webhook / Mail / Push通知               │
├─────────────────────────────────────────────────────────────┤
│  ⑦ 取得層    : 人間/AIから検索・参照                        │
└─────────────────────────────────────────────────────────────┘
        ↑
   [スケジューラ層: cron / systemd timer / GitHub Actions]
```

-----

## 3. ① 収集層の選択肢

### 3.1 選択肢一覧

|選択肢                              |適性          |制約             |サブスク要否         |
|---------------------------------|------------|---------------|---------------|
|A. **Claude.ai UI 自動操作**         |公開サイト・JS重い  |ToS要確認・UI変更で壊れる|Claude Max     |
|B. **OpenAI Operator UI 自動操作**   |ログイン必須サイト   |同上・速度遅め        |ChatGPT Pro    |
|C. **Gemini UI 自動操作**            |Google系サイト統合|同上             |Gemini Advanced|
|D. **Claude/Gemini for Chrome拡張**|特定ページ常駐監視   |headless不可・受動的 |サブスク内          |
|E. **Playwright単体スクレイピング**       |構造化データ抽出    |JSサイトもOK       |不要             |
|F. **requests + BeautifulSoup**  |静的サイト       |JS非対応          |不要             |
|G. **RSS / 公式API**               |提供サイトのみ     |対応サイト限定        |不要             |

### 3.2 選定指針

```
ログイン必須？ ─Yes─→ B (Operator) または D (拡張機能)
       │
       No
       ↓
JS重い？ ─Yes─→ A (Claude.ai) または E (Playwright)
       │
       No
       ↓
RSS/API? ─Yes─→ G を最優先
       │
       No
       ↓
       → F (requests)
```

### 3.3 実装パターン例：Claude.ai UI操作

```python
from playwright.sync_api import sync_playwright

def fetch_via_claude(urls: list, prompt_template: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./chrome-profile",
            headless=False,
            channel="chrome"
        )
        page = browser.new_page()
        page.goto("https://claude.ai/new")
        
        prompt = prompt_template.format(urls="\n".join(urls))
        page.fill('[data-testid="chat-input"]', prompt)
        page.keyboard.press("Enter")
        
        page.wait_for_selector('[data-is-streaming="false"]', timeout=120000)
        response = page.locator(".prose").last.inner_text()
        
        browser.close()
        return response
```

-----

## 4. ② 差分検知層の選択肢

### 4.1 選択肢一覧

|選択肢                    |検知粒度      |計算コスト|LLMコスト|
|-----------------------|----------|-----|------|
|A. **ハッシュ比較のみ**        |ページ全体の変更有無|極低   |なし    |
|B. **段落単位diff**        |追加・削除段落   |低    |なし    |
|C. **構造化diff (HTML差分)**|DOM単位     |中    |なし    |
|D. **セマンティックdiff**     |意味的な差分    |高    |あり    |

### 4.2 推奨：A + B のハイブリッド

```python
# Step 1: ハッシュで変更有無を判定（変更なしならスキップ）
# Step 2: 変更ありなら段落単位で差分抽出
# Step 3: 差分のみLLMに投入
```

### 4.3 永続化先の選択肢

- SQLiteローカルDB（軽量）
- GitHubリポジトリにスナップショット（履歴自動）
- Google Sheetsの履歴シート（可視性高）

-----

## 5. ③ 構造化層の選択肢

### 5.1 出力フォーマット

|選択肢                              |用途               |検索性|
|---------------------------------|-----------------|---|
|A. **JSON Lines**                |プログラム処理          |中  |
|B. **YAML Frontmatter付きMarkdown**|Obsidian / GitHub|高  |
|C. **CSV**                       |Sheets連携         |高  |
|D. **構造化DB (SQLite/Postgres)**   |クエリ重視            |最高 |

### 5.2 標準ファクトスキーマ（推奨）

```yaml
id: uuid-v4
fact: "命題形式の1文"
entities: [固有名詞のリスト]
category: カテゴリ名
source_url: 取得元URL
source_type: claude_browse | operator | extension | manual
confidence: 0.0-1.0
importance: 1-5
first_seen: ISO8601
last_confirmed: ISO8601
superseded_by: null | id
raw_id: 生データへの参照
```

### 5.3 LLM抽出プロンプトの型

```
以下の差分内容から、独立した事実(ファクト)を抽出してJSON出力してください。
1ファクト = 1命題（「Xは Yである」形式）。
複数の事実が混在する場合は分割してください。

【差分】
{diff}

【出力形式】
[
  {
    "fact": "...",
    "entities": [...],
    "category": "...",
    "importance": 1-5
  }
]
```

-----

## 6. ④ 蓄積層の選択肢

### 6.1 比較表

|                     |全文検索(人)      |AI参照    |通知           |履歴   |自動化|構造化|コスト  |
|---------------------|-------------|--------|-------------|-----|---|---|-----|
|**GitHub**           |✅ Code Search|✅       |✅ Actions    |✅ Git|✅  |△  |プラン内 |
|**Google Drive/Docs**|✅            |✅ Gemini|✅ Apps Script|△ 版履歴|✅  |△  |プラン内 |
|**Google Sheets**    |✅            |✅       |✅ Apps Script|△    |✅  |✅  |プラン内 |
|**Notion**           |✅            |△       |△            |△    |△  |✅  |サブスク別|
|**Obsidian + Git**   |✅            |△       |❌            |✅    |△  |△  |無料   |
|**SQLite (ローカル)**    |△            |△       |❌            |△    |✅  |✅  |無料   |
|**Claude Projects**  |△            |✅       |❌            |❌    |❌  |❌  |プラン内 |

### 6.2 推奨：3層構成

```
[GitHub]            ← ナレッジ実体・履歴の主ストア
   ↓ sync
[Google Sheets]     ← 構造化インデックス・人間用ビュー
   ↓
[Claude Projects]   ← AI自然言語クエリインターフェース
```

### 6.3 GitHubリポジトリ構成例

```
knowledge-repo/
├── facts/
│   ├── company-A.md           # エンティティ別
│   ├── technology-X.md
│   └── market-trends.md
├── raw/
│   └── 2026-05-05/            # 日付別生データ
├── digest/
│   └── weekly-2026-W18.md     # 週次サマリー
├── index.json                 # 全ファクトの構造化インデックス
└── .github/workflows/
    └── pipeline.yml
```

### 6.4 蓄積層の選択指針

- **履歴・差分が重要** → GitHub
- **表形式・集計が重要** → Google Sheets
- **AIに常時参照させたい** → Claude Projects
- **手書きノートと混ぜたい** → Obsidian
- **機密性高い** → ローカルSQLite

-----

## 7. ⑤ 整合性層の選択肢

### 7.1 実行タイミング

|選択肢           |頻度  |用途                |
|--------------|----|------------------|
|A. **取り込み時即時**|毎回  |重複の即時排除           |
|B. **日次バッチ**  |1日1回|矛盾解決・confidence再計算|
|C. **週次グラフ更新**|週1回 |カテゴリ横断の関係性更新      |

### 7.2 LLMバッチプロンプトの型

```
以下のファクト群から:
1. 同一内容を統合
2. 矛盾を検出し、新しい・信頼性の高い方を採用
3. 古いファクトに supersededフラグを立てる

【ファクト一覧】
{facts_json}

【出力】
{
  "consolidated": [...],
  "contradictions": [...]
}
```

### 7.3 安全装置

- 物理削除しない（フラグのみ）
- 統合バッチの結果は別ブランチ → レビュー後マージ
- confidence < 0.5 のものは自動採用しない

-----

## 8. ⑥ 通知層の選択肢

### 8.1 選択肢一覧

|選択肢                                |即時性|モバイル|設定難度|
|-----------------------------------|---|----|----|
|A. **Google Chat Webhook**         |✅  |✅   |易   |
|B. **Gmail (Apps Script)**         |△  |✅   |易   |
|C. **Slack Webhook**               |✅  |✅   |易   |
|D. **Discord Webhook**             |✅  |✅   |易   |
|E. **メール (SMTP)**                  |△  |✅   |中   |
|F. **デスクトップ通知 (notify-send)**      |✅  |❌   |易   |
|G. **iOS/Android Push (Pushover等)**|✅  |✅   |中   |

### 8.2 重要度フィルタの設計

```python
def should_notify(fact):
    if fact.importance >= 4:
        return "immediate"
    if fact.importance == 3:
        return "daily_digest"
    return "weekly_digest"
```

### 8.3 通知の種類

- **即時通知**：importance >= 4 のファクト
- **日次ダイジェスト**：その日の全ファクトサマリー
- **週次レポート**：トレンド・変化のまとめ

-----

## 9. ⑦ 取得層・スケジューラ層の選択肢

### 9.1 スケジューラの選択肢

|選択肢                            |実行場所  |補完機能             |推奨用途    |
|-------------------------------|------|-----------------|--------|
|A. **cron**                    |ローカル  |なし               |簡易用途    |
|B. **systemd timer**           |ローカル  |`Persistent=true`|常時稼働ローカル|
|C. **GitHub Actions**          |クラウド  |リトライ             |リポジトリ連動 |
|D. **Cloud Scheduler / Lambda**|クラウド  |あり               |高可用性    |
|E. **Apps Script Trigger**     |Google|あり               |Sheets連動|

### 9.2 GitHub→ローカル取得の選択肢

|選択肢                                     |即時性 |設定難度|
|----------------------------------------|----|----|
|A. **git pull + cron**                  |数分遅延|易   |
|B. **GitHub Webhook + ngrok**           |即時  |中   |
|C. **GitHub API polling**               |数分遅延|中   |
|D. **GitHub Actions self-hosted runner**|即時  |中   |

-----

## 10. 構成パターン例

### 10.1 パターンA：軽量・公開サイト中心

```
[cron] → [Playwright + Claude.ai UI] → [SQLite] → [Google Chat]
```

- 用途：公開ニュースサイト・公開ドキュメントの監視
- 強み：低コスト・低メンテナンス
- 弱み：ログイン必須サイト不可

### 10.2 パターンB：堅牢・複合ソース統合

```
[GitHub Actions cron]
    ↓
[Playwright] → 公開サイト
[Operator UI] → ログイン必須サイト
    ↓
[差分検知 in Actions]
    ↓
[GitHub commit] → ナレッジ実体
    ↓
[Apps Script] → Google Sheets同期
    ↓
[Google Chat通知 + Claude Projects更新]
```

- 用途：業務監視・複数ソース統合
- 強み：履歴完全・複合ソース対応
- 弱み：構築コスト中

### 10.3 パターンC：ローカル重視・即時性

```
[systemd timer (15min)]
    ↓
[ローカルPlaywright + Claude.ai UI]
    ↓
[ローカルSQLite + Markdown出力]
    ↓
[git push to GitHub] → クラウドバックアップ
    ↓
[GitHub Webhook → Pushover] → モバイル通知
```

- 用途：プライバシー重視・即時通知
- 強み：機密データを外に出さない
- 弱み：常時稼働端末必須

### 10.4 パターンD：Google Workspace完結型

```
[Apps Script Trigger]
    ↓
[UrlFetchApp / 限定的スクレイピング]
    ↓
[Google Sheets蓄積]
    ↓
[Gemini in Workspace で要約]
    ↓
[Gmail / Google Chat通知]
```

- 用途：Workspace内で完結させたい
- 強み：構築簡単・追加ツール不要
- 弱み：JS重いサイト・Operator相当の自律操作不可

-----

## 11. 設計時の注意点

### 11.1 サービス側の制約

- LLMサブスクUIの自動操作はToSで制限される場合あり
- 実行頻度は人間的な間隔（最低15分）に抑える
- アカウント停止リスクを考慮し、複数アカウントは使わない

### 11.2 セレクタ依存の脆弱性

- UI変更でPlaywrightスクリプトが破綻する
- セレクタを設定ファイルに外出し
- 定期的な動作テストを組み込む
- パース失敗時はRaw保存して人間レビューに回す

### 11.3 LLM出力の揺れ

- JSON形式指定でも崩れる場合あり
- パース失敗時のリトライ・フォールバック
- 重要度判定はLLMだけに任せず、ルールベースとの併用

### 11.4 データ整合性

- 物理削除しない（superseded フラグのみ）
- 統合結果はレビュー可能な形で保存
- confidenceの閾値で自動・手動を切り分け

### 11.5 セキュリティ

- ブラウザプロファイルにログイン情報が残る → 暗号化ディスクで保管
- WebhookはHMAC署名検証必須
- GitHub Personal Access Tokenはfine-grained tokenで最小権限

-----

## 12. 実装ステップ推奨順序

1. **最小構成で動かす**：1ソース・1取得・1出力先のみ
1. **差分検知を追加**：ハッシュ比較で重複処理を回避
1. **構造化を導入**：LLMでJSON出力させる
1. **蓄積層を整備**：GitHub or Sheetsへ移行
1. **通知を追加**：重要度フィルタ込みで設計
1. **整合性バッチを追加**：日次でLLMに統合させる
1. **ソースを拡張**：複数サイト・複数手段に展開
1. **取得層を整備**：人間・AI両方からアクセス可能に

-----

## 13. 参考：選択肢決定シート

実際の構築前に、以下を埋める。

```
【プロジェクト名】__________

# ① 収集層
- 主要ソース: __________
- 採用手段: __________
- 取得頻度: __________

# ② 差分検知層
- 検知粒度: __________
- 永続化先: __________

# ③ 構造化層
- 出力形式: __________
- スキーマ: __________

# ④ 蓄積層
- 主ストア: __________
- インデックス: __________
- AIアクセス用: __________

# ⑤ 整合性層
- バッチ頻度: __________
- 安全装置: __________

# ⑥ 通知層
- 即時通知先: __________
- ダイジェスト先: __________
- フィルタ条件: __________

# ⑦ スケジューラ・取得層
- スケジューラ: __________
- ローカル取得方式: __________

# 制約
- 実行ホスト: __________
- 利用サブスク: __________
- 想定データ量: __________
```

-----

## 14. 関連リソース

- Playwright: https://playwright.dev/
- GitHub Actions cron syntax: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule
- Google Apps Script: https://developers.google.com/apps-script
- Google Chat Webhook: https://developers.google.com/chat/how-tos/webhooks
- systemd.timer: https://www.freedesktop.org/software/systemd/man/systemd.timer.html

-----

*本仕様書は LLMブラウザ操作 × ナレッジ蓄積パイプライン構築の参考資料。実装時は要件チェックリスト → 各層の選択 → 構成パターン例の流れで設計する。*