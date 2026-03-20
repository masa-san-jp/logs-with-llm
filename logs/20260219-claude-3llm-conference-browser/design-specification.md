# 設計仕様書：LLM Conference Browser

**バージョン**: 1.0
**作成日**: 2026-03-20
**ステータス**: 設計確定

---

## 1. 概要

### 1.1 プロダクトビジョン

複数のLLMチャットサービスと同時に対話し、LLM同士の意見を交差させながら議論を進めることができるデスクトップアプリケーション。ユーザーは司会者として3つのLLMと「会議」を行い、最終的に議事録として成果を出力できる。

### 1.2 スコープ

本仕様書は以下を対象とする：

- Electronベースのデスクトップアプリケーション（Windows / macOS / Linux）
- 3つのLLMサービスをWebViewで同時表示する画面構成
- 一斉送信・個別送信・クロス送信の各送信機能
- 会話ログのローカル保存
- 議事録の生成・エクスポート機能

以下は本仕様書のスコープ外とする（将来拡張候補）：

- 4ペイン以上への可変化
- API連携モード
- 音声入力

### 1.3 技術スタック

| 項目 | 技術 | バージョン要件 |
|---|---|---|
| アプリケーション基盤 | Electron | v29以上 |
| LLM表示方式 | BrowserView（各LLMサービスのWebインターフェースを直接表示） | - |
| フロントエンド | HTML / CSS / Vanilla JavaScript | - |
| IPC通信 | Electron ipcMain / ipcRenderer | - |
| データ保存 | ローカルファイル（JSON） | - |
| PDF生成 | Puppeteer | v21以上 |

---

## 2. アーキテクチャ

### 2.1 コンポーネント構成

```
┌─────────────────────────────────────────────────────────┐
│ Electron Main Process                                   │
│                                                         │
│  ┌──────────────┐    ┌────────────────────────────────┐ │
│  │ main.js      │    │ BrowserView Manager            │ │
│  │ - Window管理 │    │ - BrowserView x3 (LLM-A/B/C)  │ │
│  │ - IPC処理    │    │ - DOM操作実行（executeJS）      │ │
│  │ - ログ書込み │    │ - 回答ポーリング               │ │
│  └──────┬───────┘    └──────────────┬─────────────────┘ │
│         │                           │                    │
└─────────┼───────────────────────────┼────────────────────┘
          │ ipcMain.handle            │ webContents.executeJavaScript
          │                           │
┌─────────┴───────────────────────────┴────────────────────┐
│ Renderer Process（入力パネル）                            │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ input-panel.html / input-panel.js                │   │
│  │ - 入力欄1（一斉送信・クロス送信）                  │   │
│  │ - 入力欄2〜4（個別送信）                           │   │
│  │ - 議事録生成ボタン                                │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### 2.2 IPC通信設計

Renderer Process から Main Process へ送信するチャンネルと引数：

| チャンネル名 | 送信元 | 引数 | 戻り値 |
|---|---|---|---|
| `send:broadcast` | Renderer | `{ text: string, crossSend: boolean }` | `void` |
| `send:individual` | Renderer | `{ text: string, tabIndex: number }` | `void` |
| `log:get-session` | Renderer | なし | `SessionLog` |
| `minutes:generate` | Renderer | `{ llmTab: number, format: "markdown" \| "pdf" }` | `string`（生成結果） |
| `minutes:export` | Renderer | `{ content: string, format: "markdown" \| "pdf", destPath: string }` | `void` |

### 2.3 データフロー概要

**一斉送信（クロス送信なし）のフロー**:

```
[ユーザー入力] → [Renderer: send:broadcast] → [Main: ipcMain.handle]
    → [BrowserView Manager: 各BrowserViewにDOM操作でテキスト入力・送信]
    → [Main: 会話ログにユーザー発言を記録]
    → [BrowserView Manager: MutationObserverで回答検出]
    → [Main: 会話ログに各LLMの回答を記録]
```

**クロス送信のフロー**:

```
[ユーザー入力] → [Renderer: send:broadcast(crossSend:true)] → [Main]
    → [BrowserView Manager: 各BrowserViewから最新回答テキストを取得]
    → [Main: クロス送信テキストを構成（LLM-A向け、LLM-B向け、LLM-C向け）]
    → [BrowserView Manager: 各BrowserViewに構成済みテキストを入力・送信]
    → [Main: 会話ログ記録]
```

---

## 3. 画面仕様

### 3.1 全体レイアウト

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│              │              │              │              │
│    タブ1     │    タブ2     │    タブ3     │    タブ4     │
│  入力パネル   │   LLM-A     │   LLM-B     │   LLM-C     │
│              │              │              │              │
│  ┌────────┐ │  (例:Claude) │ (例:ChatGPT) │ (例:Gemini)  │
│  │入力欄1 │ │              │              │              │
│  │[一斉]  │ │              │              │              │
│  │☐クロス │ │              │              │              │
│  ├────────┤ │              │              │              │
│  │入力欄2 │ │              │              │              │
│  │[→タブ2]│ │              │              │              │
│  ├────────┤ │              │              │              │
│  │入力欄3 │ │              │              │              │
│  │[→タブ3]│ │              │              │              │
│  ├────────┤ │              │              │              │
│  │入力欄4 │ │              │              │              │
│  │[→タブ4]│ │              │              │              │
│  └────────┘ │              │              │              │
│              │              │              │              │
│ [議事録生成]  │              │              │              │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

- ウィンドウは4ペインに分割（各ペインはリサイズ可能、最小幅 200px）
- タブ1（左端）：入力パネル（常時表示、BrowserView ではなく Renderer Process）
- タブ2〜4：各LLMチャットサービスの BrowserView

### 3.2 入力パネル詳細

#### 入力欄1（一斉送信）

| 要素 | 仕様 |
|---|---|
| テキストエリア | `rows=4`、`placeholder="全LLMに送信するメッセージ"` |
| 一斉送信ボタン | ラベル「一斉送信」、ショートカット Ctrl+Enter |
| クロス送信チェックボックス | ラベル「他LLMの回答を含めて送信（クロス送信）」、デフォルト OFF |

#### 入力欄2〜4（個別送信）

| 要素 | 仕様 |
|---|---|
| テキストエリア | `rows=3`、`placeholder="{LLM名}に送信するメッセージ"` |
| 個別送信ボタン | ラベル「→{LLM名}」、ショートカット Ctrl+Enter（フォーカス中） |

#### 議事録生成ボタン

- パネル最下部に固定配置
- ラベル「議事録を生成」
- 押下でモーダルダイアログを表示（詳細は 4.5 節）

### 3.3 ウィンドウ管理

- 初期ウィンドウサイズ：1440 × 900 px
- 最小ウィンドウサイズ：1024 × 600 px
- 各ペイン幅の比率は `localStorage` に保存し、次回起動時に復元する
- タブ2〜4 の BrowserView は入力パネルの幅に合わせて自動リサイズ

---

## 4. 機能仕様

### 4.1 一斉送信機能

**トリガー**: 入力欄1の一斉送信ボタン押下（またはフォーカス中 Ctrl+Enter）

**処理フロー**:

```
1. 入力欄1のテキストを取得（空の場合は処理中断、UIにバリデーションメッセージ表示）
2. クロス送信チェックボックスの状態を確認
   - OFF → 4.2「通常一斉送信処理」へ
   - ON  → 4.3「クロス送信処理」へ
3. 送信完了後、入力欄1のテキストをクリア
```

**通常一斉送信処理（クロス送信 OFF）**:

```
1. IPC: send:broadcast({ text, crossSend: false }) を Main に送信
2. Main: タブ2〜4 の各 BrowserView に対して DOM 操作
   a. 入力欄セレクタにテキストを挿入（InputEvent を発火）
   b. 送信ボタンをクリック
3. Main: 会話ログに記録
   { sender: "user", target: "all", crossSend: false, content: text }
4. Main: 各 BrowserView で回答監視を開始（4.4 節参照）
```

**エラーハンドリング**:

| エラー | 対処 |
|---|---|
| DOM 操作失敗（セレクタ不一致） | UIにエラートースト表示「{LLM名}への送信に失敗しました。セレクタ設定を確認してください。」 |

### 4.2 個別送信機能

**トリガー**: 入力欄2〜4の個別送信ボタン押下

**処理フロー**:

```
1. 対象テキストエリアのテキストを取得（空の場合は中断）
2. IPC: send:individual({ text, tabIndex }) を Main に送信
3. Main: 対応する BrowserView に DOM 操作（テキスト挿入・送信）
4. Main: 会話ログに記録
   { sender: "user", target: "{LLM名}", crossSend: false, content: text }
5. 送信完了後、対象入力欄のテキストをクリア
```

### 4.3 クロス送信機能

**トリガー**: クロス送信チェックボックス ON の状態で一斉送信ボタン押下

**処理フロー**:

```
1. タブ2〜4 の各 BrowserView から最新の回答テキストを取得
   - 回答セレクタで最後の要素を取得
   - 取得できない場合（まだ回答がない）はそのLLMの部分を省略
2. 各LLM向けに送信テキストを構成（下記テンプレート参照）
3. 各 BrowserView に構成済みテキストを入力・送信
4. 会話ログに記録（crossSend: true）
```

**送信テキストテンプレート**（LLM-A 向けの例）:

```
【あなたへの質問】
{ユーザーの入力テキスト}

【他の参加者の意見】
■ {LLM-B名}の回答：
{LLM-Bの最新回答テキスト（設定の maxCrossSendChars 文字まで）}

■ {LLM-C名}の回答：
{LLM-Cの最新回答テキスト（設定の maxCrossSendChars 文字まで）}
```

**長文処理方針**:

設定値 `maxCrossSendChars`（デフォルト: `2000`、`0` で無制限）を上限として、回答テキストを先頭から切り詰める。切り詰めた場合は末尾に `…（省略）` を付加する。

### 4.4 回答監視・取得

Main Process は送信後、各 BrowserView で `MutationObserver` を用いて回答エリアの DOM 変化を監視する。

**監視ロジック（BrowserView 内で `executeJavaScript` により実行）**:

```javascript
// 各BrowserViewで実行
const observer = new MutationObserver(() => {
  const lastResponse = document.querySelector(SELECTOR.responseArea + ':last-child');
  if (lastResponse && !lastResponse.dataset.llmcSent) {
    lastResponse.dataset.llmcSent = '1';
    ipcRenderer.send('response:captured', { tabIndex, text: lastResponse.innerText });
  }
});
observer.observe(document.querySelector(SELECTOR.responseContainer), { childList: true, subtree: true });
```

**タイムアウト**: 送信から **30秒** 以内に回答が取得できない場合、タイムアウトとして以下を実施：

- UIにワーニングトースト「{LLM名}の回答取得がタイムアウトしました」を表示
- 会話ログには `{ sender: "{LLM名}", content: null, timedOut: true }` を記録

### 4.5 会話ログ記録機能

**記録対象**:

- ユーザーの全送信内容（送信先・クロス送信フラグを含む）
- 各LLMの全回答テキスト（タイムスタンプ付き）

**ログファイル保存先**: `{userData}/sessions/{session_id}.json`

（`userData` = Electron の `app.getPath('userData')`）

**JSONスキーマ定義**:

```json
{
  "session_id": "string（UUID v4、必須）",
  "started_at": "string（ISO 8601、必須）",
  "participants": [
    {
      "role": "string（'user' | 'llm'、必須）",
      "name": "string（必須）",
      "tab": "number | null（LLMの場合はタブ番号 2〜4、必須）",
      "service_url": "string | null（LLMの場合はサービスURL、必須）"
    }
  ],
  "messages": [
    {
      "timestamp": "string（ISO 8601、必須）",
      "sender": "string（'user' | LLM名、必須）",
      "target": "string | null（'all' | LLM名 | null、必須）",
      "cross_send": "boolean（必須）",
      "content": "string | null（タイムアウト時は null、必須）",
      "timed_out": "boolean（省略時は false）"
    }
  ]
}
```

**書き込みタイミング**:

- セッション開始時にファイルを新規作成（participants を書き込む）
- メッセージ送受信のたびに `messages` 配列に追記（都度ファイルに書き込む）

**エラーハンドリング**: ファイル書き込みに失敗した場合、UIにエラートースト表示。ログ書き込み失敗はアプリの動作を中断しない。

### 4.6 議事録生成機能

**トリガー**: 議事録生成ボタン押下

**処理フロー**:

```
1. モーダルダイアログを表示：
   - 生成に使用するLLMの選択（タブ2〜4のいずれか）
   - 出力形式の選択（Markdown / PDF）
2. 「生成」ボタン押下で処理開始
3. 選択されたLLMの BrowserView に全会話ログ＋議事録生成プロンプトを送信
4. 回答をプレビューエリアに表示
5. 「エクスポート」ボタン押下でファイル保存ダイアログを表示
6. 指定形式でファイルに保存
```

**議事録生成プロンプトテンプレート**:

```
以下の会議ログを元に、議事録を作成してください。

## 会議ログ
{JSONログの読みやすい形式のテキスト}

## 議事録フォーマット
# 会議議事録
## 基本情報
- 日時：{started_at}
- 参加者：{participants}
## 議題
## 議論の経緯
## 各参加者の主な主張
## 合意事項
## 未解決事項・ネクストアクション
```

**PDF出力**: Puppeteer を使用してMarkdownをHTMLに変換後、PDFとして出力する。

---

## 5. LLMサービス連携仕様

### 5.1 BrowserView 設定

各 BrowserView は以下の設定で生成する：

```javascript
new BrowserView({
  webPreferences: {
    nodeIntegration: false,
    contextIsolation: true,
    sandbox: true,
  }
});
```

### 5.2 DOM 操作仕様

各LLMサービスのDOM操作に必要なセレクタは設定ファイルで管理する（6.1節参照）。

**テキスト入力処理**:

```javascript
// executeJavaScript 内で実行
const inputEl = document.querySelector(SELECTOR.input);
// React/Vueの制御下にある入力欄に対応するためInputEventを使用
const nativeInputSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
nativeInputSetter.call(inputEl, text);
inputEl.dispatchEvent(new InputEvent('input', { bubbles: true }));
```

**送信処理**:

```javascript
// ボタンクリック方式（セレクタが設定されている場合）
document.querySelector(SELECTOR.sendButton).click();
// Enterキー方式（SELECTOR.sendButton が null の場合）
inputEl.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
```

**回答テキスト取得**:

```javascript
const responseEls = document.querySelectorAll(SELECTOR.responseItem);
const lastResponse = responseEls[responseEls.length - 1];
return lastResponse ? lastResponse.innerText : null;
```

### 5.3 デフォルトセレクタ設定

| サービス | input | sendButton | responseItem |
|---|---|---|---|
| claude.ai | `div[contenteditable="true"]` | `button[aria-label="Send Message"]` | `div[data-testid="user-human-turn"], div[data-testid="ai-response"]` |
| chatgpt.com | `#prompt-textarea` | `button[data-testid="send-button"]` | `.group\/conversation-turn` |
| gemini.google.com | `rich-textarea .ql-editor` | `button.send-button` | `.conversation-container .model-response-text` |

> セレクタはサービス側のUI変更で動作しなくなる可能性がある。設定ファイルを編集することで更新可能。

### 5.4 エラー・タイムアウト処理

| 状況 | 処理 |
|---|---|
| セレクタが見つからない | 操作対象LLMのタブにエラー表示＋UIトースト |
| 送信後30秒以内に回答なし | タイムアウトとして処理（4.4節参照） |
| BrowserViewのページロード失敗 | UIにエラー表示「{LLM名}の読み込みに失敗しました。再読み込みしてください。」 |

---

## 6. データ仕様

### 6.1 設定ファイル

**保存先**: `{userData}/config.json`

**JSONスキーマ定義**:

```json
{
  "llms": [
    {
      "tabIndex": "number（2〜4、必須）",
      "name": "string（表示名、必須）",
      "serviceUrl": "string（URL、必須）",
      "selectors": {
        "input": "string（CSSセレクタ、必須）",
        "sendButton": "string | null（nullの場合はEnterキー送信）",
        "responseItem": "string（CSSセレクタ、必須）",
        "responseContainer": "string（MutationObserver の対象、必須）"
      }
    }
  ],
  "crossSend": {
    "maxCrossSendChars": "number（0で無制限、デフォルト2000）",
    "templateFormat": "string（送信テンプレートのカスタム文字列、省略時はデフォルト）"
  },
  "minutes": {
    "defaultFormat": "string（'markdown' | 'pdf'、デフォルト'markdown'）",
    "defaultSaveDir": "string（省略時はDesktop）"
  }
}
```

**初期値（デフォルト config.json）**:

```json
{
  "llms": [
    {
      "tabIndex": 2,
      "name": "Claude",
      "serviceUrl": "https://claude.ai",
      "selectors": {
        "input": "div[contenteditable=\"true\"]",
        "sendButton": "button[aria-label=\"Send Message\"]",
        "responseItem": "div[data-testid=\"ai-response\"]",
        "responseContainer": "div[data-testid=\"chat-messages\"]"
      }
    },
    {
      "tabIndex": 3,
      "name": "ChatGPT",
      "serviceUrl": "https://chatgpt.com",
      "selectors": {
        "input": "#prompt-textarea",
        "sendButton": "button[data-testid=\"send-button\"]",
        "responseItem": ".group\\/conversation-turn",
        "responseContainer": "main"
      }
    },
    {
      "tabIndex": 4,
      "name": "Gemini",
      "serviceUrl": "https://gemini.google.com",
      "selectors": {
        "input": "rich-textarea .ql-editor",
        "sendButton": "button.send-button",
        "responseItem": ".model-response-text",
        "responseContainer": ".conversation-container"
      }
    }
  ],
  "crossSend": {
    "maxCrossSendChars": 2000,
    "templateFormat": ""
  },
  "minutes": {
    "defaultFormat": "markdown",
    "defaultSaveDir": ""
  }
}
```

### 6.2 ファイル保存パス仕様

| データ | パス |
|---|---|
| 設定ファイル | `{userData}/config.json` |
| 会話ログ | `{userData}/sessions/{session_id}.json` |
| エクスポートした議事録 | ユーザー指定パス（デフォルト: `{Desktop}/{session_id}_minutes.md` 等） |

---

## 7. エラーハンドリング一覧

| エラー種別 | 発生箇所 | 対処 | ユーザー通知 |
|---|---|---|---|
| DOM操作失敗（セレクタ不一致） | BrowserView Manager | 処理中断（他LLMへの送信は継続） | トースト表示 |
| 回答取得タイムアウト（30秒） | BrowserView Manager | タイムアウト記録、監視終了 | ワーニングトースト |
| BrowserViewロード失敗 | Main Process | 再読み込みボタンを表示 | エラーオーバーレイ |
| ログファイル書き込み失敗 | Main Process | エラーログ出力（コンソール）、動作継続 | トースト表示 |
| 議事録生成失敗 | Main Process | モーダルにエラー表示 | モーダル内エラーメッセージ |
| config.json 読み込み失敗 | Main Process | デフォルト設定で起動 | 起動時ダイアログ |

---

## 8. 制約・前提条件

- **ログイン認証**: 各LLMサービスへのログインはユーザーが各WebView内で手動で行う。アプリはログイン情報を管理しない。
- **DOM構造変更リスク**: 各LLMサービスのDOM構造変更により動作しなくなる可能性がある。`config.json` のセレクタを更新することで対応する。セレクタ更新はアプリ内の設定画面、またはファイルの直接編集で行う。
- **同時送信の順序保証**: タブ2→3→4の順に送信するが、LLMの回答タイミングはサービス側の処理速度に依存するため保証しない。
- **オフライン動作**: 各LLMサービスへのアクセスにはネットワーク接続が必要。オフライン時はWebViewがエラーページを表示する（アプリ側での特別な処理なし）。
- **対応OS**: Windows 10以上、macOS 12以上、Ubuntu 22.04以上

---

## 9. 今後の拡張候補

- ペイン数の可変化（3ペイン〜5ペイン対応）
- API連携モード（WebView表示ではなくAPI経由で各LLMと通信）
- 会議テンプレート機能（ブレスト、意思決定、レビューなど用途別プロンプト）
- セッション履歴管理（過去の会議一覧・検索・再開）
- 音声入力対応
- リアルタイム要約パネル（会議中に議論のサマリーを常時表示）
- 設定画面UI（config.json の GUIエディタ）

---

*本仕様書は `desing-speculation.md`（構想段階メモ）を元に作成した実装向け設計仕様書である。実装時に詳細な技術検証の結果を反映して適宜更新すること。*
