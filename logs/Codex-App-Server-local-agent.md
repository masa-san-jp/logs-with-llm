# Codex App Server ローカル統合ツール 設計仕様書

| 項目 | 内容 |
|---|---|
| バージョン | 1.0.0 |
| 対象 | 個人ユーザー / ローカル環境専用 |
| 作成日 | 2026-05-05 |
| 想定読者 | 開発者本人および将来の保守担当 |

---

## 1. 概要

### 1.1 目的

個人ユーザーが自身のローカルマシン上で、自身の ChatGPT サブスクリプション（Plus / Pro 等）を活用した独自 AI エージェントアプリを構築できるようにする。Codex CLI に同梱されている `codex app-server` を JSON-RPC 2.0 経由で操作する Node.js クライアントライブラリと、初回セットアップを自動化するスクリプト群を提供する。

### 1.2 達成したいこと

ユーザーが1つのコマンド（`bash setup.sh` または `.\setup.ps1`）を実行するだけで、Codex CLI のインストール、ChatGPT アカウントへの認証、App Server 経由の動作確認、起動ラッパーの生成までが完了する。アプリ開発者は `CodexClient` クラスをインポートするだけで、認証管理・JSON-RPC 通信・ストリーミング応答処理を意識せずに ChatGPT バックエンドへアクセスできる。

### 1.3 スコープ外（やらないこと）

複数ユーザーへのサービス提供、外部ネットワーク経由でのアクセス、商用 API 化、コンテナ化されたデプロイメント、Codex の WebSocket トランスポート（experimental のため）、モバイル環境対応はスコープ外とする。これらは本ツールの設計目標と矛盾するため、必要になった時点で別プロジェクトとして再設計する。

---

## 2. 前提条件と制約

### 2.1 動作環境

| 区分 | 要件 |
|---|---|
| OS | macOS / Linux / Windows |
| Node.js | 18 以上 |
| npm | Node.js に同梱されるもの |
| ネットワーク | OAuth 認証時にブラウザでの ChatGPT へのアクセスが必要 |
| ChatGPT プラン | Plus / Pro / Business / Edu / Enterprise（Codex 利用権を含むプラン） |

### 2.2 公式仕様上の制約

stdio トランスポートは正式サポートだが、WebSocket トランスポートは experimental・unsupported のため本ツールでは採用しない。`chatgpt` managed 認証モードを推奨パスとし、ヘッドレス環境向けに `chatgptDeviceCode` モードをフォールバックとして提供する。`chatgptAuthTokens`（外部トークン注入）は experimental かつトークンリフレッシュをアプリ側で実装する必要があるため使用しない。

### 2.3 利用規約上の制約

OpenAI の利用規約により、ChatGPT サブスクリプションの認証情報を他者と共有することは禁止されている。本ツールは「個人が自身のサブスクで自分のアプリを動かす」用途に限定される。商用サービスや多ユーザー向けプロダクトを構築する場合は、API キー認証への切り替えが必須となる。

### 2.4 セキュリティ上の前提

`~/.codex/auth.json` には ChatGPT のアクセストークンが平文で保存される。このファイルは絶対に Git にコミットしない、ログに含めない、他人と共有しないことを前提とする。本ツールはこの前提が守られる範囲で安全に動作する。

---

## 3. 全体アーキテクチャ

### 3.1 コンポーネント構成

```
┌──────────────────────────────────────────────────────────┐
│  ユーザーアプリ（任意の Node.js コード）                  │
│                                                          │
│   ┌────────────────────────────────────────────────┐     │
│   │  CodexClient (codex-client.js)                 │     │
│   │  - JSON-RPC 2.0 ラッパー                       │     │
│   │  - 認証状態管理                                │     │
│   │  - ストリーミング応答ハンドラ                  │     │
│   └────────────────────────────────────────────────┘     │
└──────────────────────────────────┬───────────────────────┘
                                   │ stdin/stdout (JSON-RPC)
                                   ▼
┌──────────────────────────────────────────────────────────┐
│  codex app-server プロセス（OpenAI 公式バイナリ）         │
│  - OAuth フロー管理                                       │
│  - トークン永続化と自動リフレッシュ                       │
│  - スレッド・ターン管理                                   │
└──────────────────────────────────┬───────────────────────┘
                                   │ HTTPS
                                   ▼
┌──────────────────────────────────────────────────────────┐
│  ChatGPT バックエンド（OpenAI）                           │
│  - 認証されたユーザーのサブスクリプションで推論           │
└──────────────────────────────────────────────────────────┘
```

### 3.2 ファイル構成

| ファイル | 役割 | 配置 |
|---|---|---|
| `setup.sh` | macOS / Linux 用セットアップ | プロジェクトルート |
| `setup.ps1` | Windows 用セットアップ | プロジェクトルート |
| `codex-client.js` | クライアントライブラリ本体 | プロジェクトルート |
| `example.js` | 使い方サンプル | プロジェクトルート |
| `codex-server.sh` / `codex-server.ps1` | App Server 起動ラッパー（自動生成） | プロジェクトルート |
| `~/.codex/auth.json` | 認証トークン（Codex CLI が自動管理） | ユーザーホーム |

### 3.3 データフロー

初回起動時はセットアップスクリプトが Codex CLI のインストールと OAuth ブラウザフローを実行し、トークンを `~/.codex/auth.json` に保存する。2回目以降のアプリ起動では、`CodexClient.start()` が `codex app-server` を子プロセスとして起動し、既存トークンが自動的に読み込まれる。トークンの有効期限が切れた場合は App Server が自動でリフレッシュする。アプリからの推論リクエストは JSON-RPC で App Server に送られ、App Server が ChatGPT バックエンドに HTTPS で転送し、応答をストリーミングで返す。

---

## 4. セットアップスクリプト仕様

### 4.1 実行ステップ

| Step | 処理 | 失敗時の挙動 |
|---|---|---|
| 1 | Node.js の存在とバージョン確認（18 以上） | エラー終了し、インストール URL を表示 |
| 2 | `npm install -g @openai/codex` | エラー終了 |
| 3 | `codex` コマンドの PATH 解決 | PATH 設定方法を案内して終了 |
| 4 | `codex login status` で既存認証を確認 | 続行 |
| 5 | 未認証なら `codex login`（ヘッドレスなら `--device-auth`） | エラー終了 |
| 6 | App Server を一時起動して `account/read` で認証検証 | 警告表示のみ（致命的でない） |
| 7 | 起動ラッパースクリプト生成 | エラー終了 |
| 8 | 完了メッセージ表示 | - |

### 4.2 ヘッドレス環境の自動検知

`DISPLAY` 環境変数が未設定で、かつ macOS 以外の場合はディスプレイが利用できないと判断し、`codex login --device-auth` を実行する。Windows では PowerShell 環境を前提とし、通常はブラウザフローを使う。

### 4.3 冪等性

スクリプトは何度実行しても安全であることを保証する。Codex CLI が既にインストールされている場合は最新版に更新し、ログイン済みの場合はログインステップをスキップする。生成済みのラッパースクリプトは上書きする。

### 4.4 エラーハンドリング方針

セットアップ中の致命的エラー（Node.js 不足、Codex インストール失敗、ログイン失敗）は即座に終了する。動作確認ステップで App Server との通信に失敗した場合は警告を表示するのみで、ユーザーが手動で `codex login status` を実行できるよう案内する。これは App Server の起動に時間がかかるケースで誤検知しないための設計判断。

---

## 5. CodexClient クラス仕様

### 5.1 責務

CodexClient は EventEmitter を継承し、`codex app-server` 子プロセスへの JSON-RPC 通信、リクエスト ID 管理、レスポンスと通知の振り分け、認証フロー、エージェント実行を担う。アプリ開発者がプロセス管理や JSON-RPC プロトコルを意識せずに済むようにすることが第一目標。

### 5.2 ライフサイクル

`new CodexClient(options)` でインスタンス化、`start()` で App Server プロセスを起動し JSON-RPC ハンドシェイク（initialize → initialized）を行う。利用後は `stop()` で stdin を閉じてプロセスを終了する。1つの CodexClient インスタンスは1つの App Server プロセスに対応する。

### 5.3 コンストラクタオプション

| オプション | 型 | デフォルト | 説明 |
|---|---|---|---|
| `codexHome` | string \| null | null | `CODEX_HOME` 環境変数の上書き値。複数の認証セッションを使い分けたい場合に指定 |

### 5.4 公開メソッド

| メソッド | 戻り値 | 説明 |
|---|---|---|
| `start()` | Promise\<this\> | App Server を起動し、JSON-RPC ハンドシェイクを完了させる |
| `stop()` | void | App Server プロセスを停止する |
| `getAccount()` | Promise\<{authMode, planType, ...}\> | 現在のログイン状態を取得 |
| `startBrowserLogin()` | Promise\<string\> | ブラウザ OAuth を開始し、ユーザーが開くべき authUrl を返す |
| `startDeviceCodeLogin()` | Promise\<{userCode, verificationUrl}\> | デバイスコードフローを開始 |
| `waitForLogin(timeoutMs)` | Promise\<void\> | `account/login/completed` 通知を待機する |
| `logout()` | Promise\<void\> | ログアウト |
| `ask(prompt, onDelta)` | Promise\<{text, threadId}\> | 1ターンのエージェント実行。onDelta でストリーミング受信 |

### 5.5 公開イベント

| イベント名 | 発火タイミング | ペイロード |
|---|---|---|
| `log` | App Server の stderr に出力があったとき | string |
| `parseError` | JSON-RPC メッセージの解析失敗時 | (Error, raw) |
| `error` | プロセスの実行時エラー | Error |
| `exit` | App Server プロセスが終了したとき | exitCode |
| `account/updated` | 認証モード変更時に App Server から通知 | {authMode, planType} |
| `account/login/completed` | ログインフローが完了したとき | {success, error} |
| `turn/delta` | ストリーミング応答の差分受信時 | {threadId, text} |
| `turn/completed` | ターン完了時 | {threadId} |
| `turn/error` | ターン実行エラー時 | {threadId, error} |

### 5.6 内部状態

| プロパティ | 型 | 用途 |
|---|---|---|
| `_msgId` | number | 次に発番する JSON-RPC リクエスト ID |
| `_pending` | Map\<id, {resolve, reject}\> | 応答待ちのリクエスト管理 |
| `_proc` | ChildProcess \| null | App Server 子プロセス |
| `_ready` | boolean | initialize 完了フラグ |

### 5.7 タイムアウト方針

JSON-RPC リクエストは 30 秒で自動タイムアウトする。これは API 呼び出しの応答待ちを想定した値で、ストリーミング応答全体の完了時間ではない（ストリーミングは個別のイベントで管理されるため、全体の所要時間に上限はかからない）。`waitForLogin()` のデフォルトタイムアウトは 120 秒で、ユーザーがブラウザで認証を完了させる時間を確保する。

### 5.8 エラー処理方針

JSON-RPC のレベルでエラーレスポンスが返ってきた場合は、`error.message` を持つ Error オブジェクトを reject する。ターン実行中にエラーが発生した場合は `turn/error` 通知をフックして reject する。プロセスの予期せぬ終了は `exit` イベントで通知し、その時点で実行中のリクエストはタイムアウトで失敗する。

---

## 6. JSON-RPC 通信仕様

### 6.1 トランスポート

stdio を使用する。1メッセージは1行（改行区切り）の JSON 文字列。`jsonrpc: "2.0"` ヘッダはワイヤ上では省略される（Codex 公式仕様に準拠）。

### 6.2 メッセージ種別

リクエストは `id` と `method` を持ち、必ず応答が返る。通知は `method` のみで `id` を持たず、応答は返らない。応答は `id` と `result` または `error` を持つ。

### 6.3 ハンドシェイク

接続直後に必ず以下のシーケンスを実行する。これを省略すると後続のリクエストは失敗する。

```
→ initialize { protocolVersion: "2024-11-05", clientInfo: {name, version} }
← (result)
→ initialized {}   ← 通知（応答なし）
```

### 6.4 主要なメソッド

| メソッド | 種別 | 用途 |
|---|---|---|
| `initialize` | request | プロトコル合意 |
| `initialized` | notify | ハンドシェイク完了通知 |
| `account/read` | request | アカウント情報取得 |
| `account/login/start` | request | ログインフロー開始 |
| `account/login/completed` | notify | ログイン完了通知 |
| `account/logout` | request | ログアウト |
| `thread/create` | request | 新規スレッド作成 |
| `turn/start` | request | エージェント実行開始 |
| `turn/delta` | notify | ストリーミング応答 |
| `turn/completed` | notify | ターン完了 |

---

## 7. 認証設計

### 7.1 認証モード選定

`chatgpt`（ブラウザ OAuth）を第一選択とする。これは Codex CLI 自身がトークンの保存とリフレッシュを担当するため、アプリ側で考慮する点が最小になる。ヘッドレス環境では `chatgptDeviceCode` を使用する。`chatgptAuthTokens` は experimental かつアプリ側でリフレッシュ実装が必要なため採用しない。

### 7.2 トークンライフサイクル

トークンは `~/.codex/auth.json` に Codex CLI が保存する（OS によってはキーリングを使う設定も可能）。アクセストークンが期限切れに近づくと、App Server が自動的にリフレッシュトークンで更新する。アプリ側ではこのライフサイクルを意識する必要がない。

### 7.3 ログインフロー（ブラウザ）

```
[アプリ]                         [App Server]                    [ブラウザ / ChatGPT]
   │                                  │                                  │
   ├─ getAccount() ──────────────────▶│                                  │
   │◀─ {authMode: null} ──────────────┤                                  │
   │                                  │                                  │
   ├─ startBrowserLogin() ───────────▶│                                  │
   │◀─ {authUrl} ─────────────────────┤                                  │
   │                                  │                                  │
   │  [ユーザーが authUrl を開く]                                        │
   │                                  │◀────── OAuth callback ───────────┤
   │                                  │                                  │
   │◀─ account/login/completed ───────┤                                  │
   │◀─ account/updated ───────────────┤                                  │
   │   {authMode: "chatgpt"}          │                                  │
```

### 7.4 セッション再利用

2回目以降のアプリ起動時は `getAccount()` で `authMode` が `null` でないことを確認するだけで、ログインフローはスキップされる。これにより、ユーザーは初回の1度だけブラウザログインすれば、以降はアプリを起動するだけで使える状態になる。

---

## 8. エージェント実行設計

### 8.1 スレッドとターンの概念

スレッドは会話履歴のコンテキスト単位。ターンはスレッド内の1往復（ユーザー入力→エージェント応答）。本ツールの `ask()` メソッドは内部で1スレッド・1ターンを実行する単純なケースをカバーする。複数ターンの会話を扱いたい場合は `thread/create` と `turn/start` を直接呼び出す拡張が必要。

### 8.2 ストリーミング処理

`turn/delta` 通知が応答テキストの差分として連続して送られてくる。CodexClient はこれを集約しつつ、コールバック `onDelta(chunk)` でリアルタイム表示も可能にする。`turn/completed` 通知が来たら最終結果を resolve する。

### 8.3 エラー時の挙動

`turn/error` 通知が来た場合、`ask()` は reject する。CodexClient 側では該当する `threadId` のリスナーを全てクリーンアップしてからエラーを伝播する。

---

## 9. セキュリティ設計

### 9.1 機密情報の取り扱い

`~/.codex/auth.json` および `CODEX_HOME` 配下のファイルは認証トークンを含むため、以下を厳守する。Git リポジトリにコミットしない（プロジェクトの `.gitignore` に追加する）、ログ出力に含めない、他人と共有しない、クラウドストレージに同期しない（自動同期フォルダに置かない）。

### 9.2 ローカル限定の保証

App Server は stdio トランスポートでのみ起動するため、ネットワーク経由でアクセスされることはない。WebSocket リスナーは一切起動しない設計。これによりリモートからの不正アクセスや認証情報の漏洩リスクが構造的に排除される。

### 9.3 子プロセスの権限

App Server 子プロセスは親プロセス（ユーザーアプリ）と同じ権限で動く。これは Codex がローカルファイルシステムにアクセスする必要があるための仕様。アプリ自体を信頼できないコードと同じ権限で動かさないよう注意する。

---

## 10. エラーケースと対処

| ケース | 検出方法 | 対処 |
|---|---|---|
| Node.js 18 未満 | セットアップ時のバージョンチェック | エラー終了しインストール案内 |
| Codex CLI インストール失敗 | npm の終了コード | エラー終了 |
| PATH に codex がない | `which codex` の失敗 | PATH 設定方法を案内して終了 |
| OAuth コールバック失敗 | `codex login` の終了コード | デバイスコードフローへの切替を提案 |
| トークン期限切れ | App Server が自動検出 | 自動リフレッシュ（アプリ側対応不要） |
| リフレッシュトークン無効 | `account/read` で `authMode: null` | 再ログインを促す |
| App Server プロセス停止 | `exit` イベント | アプリ側で再起動するか終了する |
| JSON-RPC タイムアウト | 30 秒経過 | リクエストを reject |
| レート制限超過 | `account/rateLimits/read` で確認可能 | アプリで適切に間隔を空ける |

---

## 11. 制限事項と既知の課題

ChatGPT サブスクリプションには時間あたり・期間あたりのレート制限がある（プランによって異なる）。本ツールは「実質無制限」ではないことを利用者に明示する必要がある。通常の対話的利用なら問題にならないが、バッチ処理や大量並列実行は制限に抵触する可能性が高い。

`account/login/completed` 通知に関するイベント名がドット区切りであるため、EventEmitter の通常の使い方と少し異なる。本クライアントでは通知メソッド名をそのままイベント名として `emit` するため、リスナー登録時もドット区切りで指定する必要がある。

App Server のメソッド名・パラメータ名は Codex CLI のバージョンアップに伴って変更される可能性がある。`codex app-server generate-ts --out ./schemas` で現在のバージョンに対応した TypeScript スキーマを生成できるため、CI で差分検知することを推奨する。

---

## 12. 拡張余地

本仕様は最小限の機能セットに絞っている。今後拡張する場合に検討すべき方向性として、複数ターン会話のサポート、ツール（function calling）の統合、画像入力対応、過去スレッドの再開、レート制限の事前チェック、TypeScript 型定義の追加、テストハーネスの整備が挙げられる。これらは必要が生じた段階で別途設計する。

---

## 13. 参考資料

OpenAI Codex 公式ドキュメント（developers.openai.com/codex/app-server）、Codex GitHub リポジトリ（openai/codex）、JSON-RPC 2.0 仕様（jsonrpc.org/specification）、OAuth 2.0 Device Authorization Grant（RFC 8628）。
