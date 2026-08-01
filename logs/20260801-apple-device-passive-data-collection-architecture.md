# Mac・iPhone・Apple Watch 自動データ蓄積基盤 設計調査書

作成日: 2026-08-01  
対象: 個人所有のMac、iPhone、Apple Watch  
目的: ユーザーが日常的な入力操作を行わなくても、各デバイスが既に生成・保持している情報と、常駐アプリが取得できる情報を時系列データとして継続蓄積する

---

## 1. 結論

Mac、iPhone、Apple Watchから、操作不要で継続的にデータを蓄積する仕組みは構築できる。

ただし、3デバイスには次の性質差がある。

- **Mac**: 常駐エージェントを動かせるため、作業状態、前面アプリ、アイドル、電源、スリープ、システム負荷などを秒〜分単位で詳細に記録できる。
- **iPhone**: OSがバックグラウンド実行を管理するため、任意の短周期ポーリングはできない。HealthKit、Core Motion、Core Location、Background Tasksなど、OSが許可したイベント駆動・遅延同期型の収集になる。
- **Apple Watch**: 身体活動・健康データの取得に強い。一方で、端末操作時間、前面アプリ、画面操作履歴などの汎用的な利用ログは取得できない。HealthKitを主経路とし、必要な補助情報だけWatchアプリからiPhoneへ同期する。

推奨構成は次のとおりである。

```text
Apple Watch
  ├─ HealthKitへ身体・活動データを記録
  └─ Watchアプリが必要時のみ状態スナップショットを送信
                 │
                 ▼
iPhone Collector
  ├─ HealthKit差分同期
  ├─ Core Motion履歴取得
  ├─ 位置イベント取得
  ├─ バッテリースナップショット
  ├─ Device Activityの限定的集計
  └─ WatchConnectivity受信
                 │
                 ▼
常時稼働サーバー / GX10
  ├─ イベント受信API
  ├─ 原本イベント保存
  ├─ 時系列DB / Parquet
  ├─ 日次・週次集計
  └─ LLM分析・可視化
                 ▲
                 │
Mac Collector
  ├─ 起動・スリープ・復帰
  ├─ 操作中・アイドル
  ├─ 前面アプリ
  ├─ バッテリー・電源
  ├─ CPU・メモリ等
  └─ 開発・ファイル活動
```

この構成では、リアルタイム性を一律に求めない。各イベントに「発生時刻」と「取り込み時刻」を別々に持たせ、後から正しい時系列へ統合する。

---

## 2. 本書における「自動収集」の定義

自動収集を、次の4種類に分ける。

| 区分 | 定義 | 例 |
|---|---|---|
| A. 既存履歴の取得 | OSやアプリが既に蓄積している過去データを読み出す | HealthKitの歩数・心拍・睡眠、Core Motionの歩数履歴、Git履歴 |
| B. OSイベント駆動 | OSが特定イベント発生時にアプリを起動・通知する | HealthKit更新、位置変化、WatchConnectivity受信 |
| C. 常駐観測 | Collectorが継続稼働して状態変化を記録する | Macの前面アプリ、アイドル、電源変化 |
| D. 実行時スナップショット | アプリが実行できた時点の状態だけ記録する | iPhone・Apple Watchのバッテリー残量 |

重要なのは、**OSが画面に表示している情報と、第三者アプリが取得できる情報は同一ではない**という点である。

例えば、iPhoneの「設定」にはスクリーンタイムやバッテリー使用状況が表示されるが、それらすべてを一般アプリが自由な形式で読み出し、外部DBへ転送できるわけではない。

---

## 3. 取得可能性の全体マトリクス

### 3.1 判定記号

| 記号 | 意味 |
|---|---|
| ◎ | 公式APIで安定して取得しやすい |
| ○ | 条件付きで取得可能 |
| △ | スナップショット、推定、限定用途のみ |
| × | 一般アプリ向け公開APIでは取得困難 |

### 3.2 デバイス別概要

| データ領域 | Mac | iPhone | Apple Watch |
|---|---:|---:|---:|
| 起動・稼働時間 | ◎ | △ | △ |
| スリープ・復帰 | ◎ | × | × |
| 画面オン・オフ | ○ | × | × |
| 操作中・アイドル | ◎ | × | × |
| 前面アプリ | ◎ | × | × |
| アプリ利用時間集計 | ◎ | ○・制約大 | × |
| バッテリー残量 | ◎ | ○ | ○ |
| 充電状態 | ◎ | ○ | ○ |
| 歩数・距離 | △ | ◎ | ◎ |
| 心拍・HRV | × | HealthKit経由 | ◎ |
| 睡眠 | × | HealthKit経由 | ◎ |
| 移動状態 | △ | ◎ | ○ |
| 位置・訪問 | △ | ◎・許可必須 | iPhone経由が基本 |
| ファイル変更 | ◎ | アプリ領域のみ | × |
| Git・開発活動 | ◎ | × | × |
| 周囲音の連続録音 | 技術的には可能だが非推奨 | バックグラウンド常時録音は非現実的 | 用途限定 |
| キー入力内容 | 収集可能でも実施非推奨 | × | × |

---

## 4. Apple Watchから自動蓄積できるデータ

## 4.1 中核はHealthKit

HealthKitは、iPhoneとApple Watchの健康・フィットネスデータを集約する公式リポジトリである。ユーザーが明示的に許可したデータ型について、アプリはHealthKitストアから読み出せる。

Apple Watchが日常的に自動生成し、HealthKitへ保存し得る代表的な情報は次のとおりである。

| 分類 | 代表データ | 過去分 | 継続差分 | 注意点 |
|---|---|---:|---:|---|
| 活動量 | 歩数、歩行・走行距離、アクティブエネルギー | ○ | ○ | iPhone等の複数ソースが混在するため重複処理が必要 |
| アクティビティ | ムーブ、エクササイズ、スタンド | ○ | ○ | 集計値として扱う |
| 心拍 | 心拍数 | ○ | ○ | 一定周期を保証しない |
| 心拍指標 | 安静時心拍数、歩行時平均心拍数、HRV | ○ | ○ | OSが算出する派生値を含む |
| 睡眠 | 就床、睡眠区間、睡眠ステージ | ○ | ○ | Watch装着、設定、機種、OSに依存 |
| 呼吸 | 呼吸数など | ○ | ○ | 取得可否は機種・設定・測定状況に依存 |
| ワークアウト | 種別、開始・終了、距離、エネルギー | ○ | ○ | 手動開始または自動検出後の記録を含む |
| 歩行特性 | 歩行速度、歩幅、左右差等 | ○ | ○ | 対応機種・OS・条件に依存 |
| 音環境 | 環境音レベル、ヘッドフォン音量関連 | ○ | ○ | 設定と権限に依存 |
| その他 | 手首皮膚温、血中酸素等 | 条件付き | 条件付き | 機種、地域、OS、法規制、設定に強く依存 |

### 4.1.1 差分同期方式

HealthKitの同期では、次の組み合わせを基本とする。

1. `HKObserverQuery`で対象データ型の更新を検知する。
2. `HKAnchoredObjectQuery`で前回アンカー以降の追加・削除差分を取得する。
3. 新しいアンカーを端末内へ永続化する。
4. 取得したサンプルをローカルキューへ保存する。
5. 通信可能時にサーバーへ送信する。

`HKObserverQuery`は変更通知であり、変更内容そのものを返す仕組みではない。したがって、差分本体はAnchored Query等で取得する。

HealthKitのバックグラウンド配信は、指定した頻度どおりの時刻に必ず動くタイマーではない。OSが電力、端末状態、データ型などを考慮して実行するため、**発生から同期まで遅延する前提**で設計する。

### 4.1.2 複数ソースの扱い

歩数等は、Apple WatchとiPhoneの双方が同一時間帯のサンプルを生成する可能性がある。単純合算すると過大計上になる。

保存時には最低限、次を保持する。

- HealthKitサンプルUUID
- データ型
- 開始時刻
- 終了時刻
- 値と単位
- `HKSourceRevision`相当のソース情報
- デバイス情報
- メタデータ
- 作成・更新・削除状態

集計時は、HealthKitの統計クエリ、ソース優先順位、時間重複排除などを使い分ける。

## 4.2 Apple Watchのバッテリー

WatchKitから、Apple Watchの現在のバッテリー残量と充電状態を取得できる。

ただし、これは**Watchアプリが実行できた時点の現在値**である。一般アプリがOSの過去のバッテリー推移を一括取得するAPIではない。

取得できる状態例:

- charging
- full
- unplugged
- unknown

推奨する記録タイミング:

- Watchアプリ起動時
- バックグラウンドタスク実行時
- WatchConnectivity送信時
- 充電状態変化をアプリが認識できた時
- ワークアウト開始・終了時

バッテリー履歴を作りたい場合、今後のスナップショットを蓄積して時系列化する。

## 4.3 WatchConnectivityで送れる情報

WatchConnectivityはApple WatchとiPhoneのコンパニオンアプリ間でデータを交換する公式フレームワークである。

用途を次のように分ける。

| API的な考え方 | 用途 |
|---|---|
| 最新状態の置換 | 現在のバッテリー、現在の設定、最新集計 |
| キュー型転送 | 未送信イベント、センサースナップショット |
| 即時メッセージ | 両アプリが到達可能な場合の対話的通信 |
| ファイル転送 | まとまったログや一時ファイル |

Apple Watch側で常時HTTP送信するより、iPhoneを中継ハブにする方が電力・到達性・実装保守性の面で有利である。

## 4.4 Apple Watchから取得困難なデータ

一般アプリ向け公開APIでは、次を前提にしない。

- Apple Watch全体の画面オン時間
- 全アプリの前面表示履歴
- Watch上のアプリ別利用時間
- Digital Crownやタップの全操作履歴
- OS全体のロック・解除履歴
- 正確な装着開始・終了履歴
- 過去のバッテリー残量推移

装着状態は、心拍、歩数、手首関連サンプルの有無などから推定できるが、確定値ではない。推定値には必ず信頼度を持たせる。

---

## 5. iPhoneから自動蓄積できるデータ

## 5.1 HealthKitの集約データ

iPhoneはApple Watchが生成したHealthKitデータを取得・同期する中心端末になる。

iPhone Collectorは、Watchの直接制御を主目的にせず、HealthKitストアへ反映されたデータを差分同期する。これにより、Watchが一時的にiPhoneやネットワークから離れていても、後からデータを回収できる。

## 5.2 Core Motion

Core Motionには、端末が蓄積した歩数・移動距離等の履歴を問い合わせる仕組みがある。

代表例:

- 歩数
- 歩行・走行距離
- 上った階数
- ペース
- ケイデンス
- 移動状態の分類
  - stationary
  - walking
  - running
  - automotive
  - cycling
  - unknown

`CMPedometer`は履歴キャッシュの問い合わせとライブ更新を提供する。`CMMotionActivityManager`は指定期間の活動分類履歴を問い合わせられる。

### HealthKitとの使い分け

| 目的 | 推奨 |
|---|---|
| 長期的な身体活動の正規データ | HealthKit |
| iPhone自身のモーション履歴確認 | Core Motion |
| Watchを含む統合歩数 | HealthKitを基本にする |
| 移動状態の時系列分類 | Core Motion |

HealthKitとCore Motionの歩数を同時に単純加算してはいけない。異なる取得経路として保存し、正規化レイヤーで代表系列を決定する。

## 5.3 Core Location

ユーザーが適切な位置情報権限を与えた場合、iPhoneはバックグラウンドで位置関連イベントを生成できる。

### 取得方式

| 方式 | 特徴 | 電力 | 推奨用途 |
|---|---|---:|---|
| 標準位置更新 | 精度・距離条件を指定して位置更新 | 高くなり得る | ナビゲーション、短時間の詳細経路 |
| Significant-change | 大きな位置変化を低電力で検知 | 低い | 日常移動の粗い記録 |
| Region monitoring | 指定領域への入退場 | 低い | 自宅・職場等の到着・出発 |
| Visit monitoring | 滞在・訪問をイベント化 | 低い | 滞在場所と滞在時間 |

長期常用では、次の組み合わせを推奨する。

1. Significant-changeで大きな移動を検知する。
2. Visitまたはジオフェンスで滞在を記録する。
3. 必要な状況だけ標準位置更新を短時間有効化する。
4. 生の緯度経度から、端末内で「自宅」「職場」「移動中」等へ変換できる場合は、サーバーへ送る精度を落とす。

位置情報は特に機微性が高い。生座標を長期保存するか、意味ラベルだけ保存するかを設計時に決定する。

## 5.4 バッテリー・充電状態

UIKitの`UIDevice`から、iPhoneの現在のバッテリー残量と状態を取得できる。

取得できる状態:

- unplugged
- charging
- full
- unknown

Apple Watchと同様に、一般アプリがiOSの過去のバッテリー統計を自由に読み出す方式ではない。Collectorが実行されたタイミングのスナップショットを保存して履歴を作る。

推奨トリガー:

- アプリ起動・復帰
- バッテリー状態変更通知
- バックグラウンドタスク
- 位置イベント受信
- HealthKit更新受信
- WatchConnectivity受信
- サーバー送信直前

単独で高頻度収集を試みるのではなく、他のバックグラウンドイベントに相乗りさせる。

## 5.5 Device Activity / Screen Time

Device Activityは、アプリやWebサイトの利用状況を扱うプライバシー保護型の仕組みである。スケジュールや利用時間の閾値イベントを監視し、レポート拡張で集計を表示できる。

ただし、次の用途を前提にしてはいけない。

- 現在開いている他社アプリを毎秒取得する
- 全アプリの起動・終了イベントを生ログとして外部送信する
- キーボード入力や画面内容を取得する
- Apple標準スクリーンタイムDBを任意SQLのように一括抽出する

Device Activityは、本基盤の主データソースではなく、次のような補助的な集計に限定する。

- 1日の総利用時間帯
- 選択したアプリ・カテゴリの利用閾値到達
- 端末内レポート
- 集中時間・娯楽時間等の粗いカテゴリ集計

外部サーバーへ送る設計については、API・契約・審査条件を実装時点で再確認し、端末内集計を優先する。

## 5.6 写真ライブラリ

ユーザーが写真アクセスを許可すれば、写真ライブラリから次の文脈情報を取得できる。

- 撮影日時
- 位置情報
- メディア種別
- お気に入り状態
- アルバム所属
- 追加・変更イベント

写真の内容自体を常時クラウド送信する必要はない。まずは、撮影イベントとメタデータだけを行動タイムラインへ統合する。

例:

```json
{
  "event_type": "photo_created",
  "occurred_at": "2026-08-01T15:42:11+09:00",
  "device": "iphone",
  "payload": {
    "media_type": "image",
    "has_location": true,
    "asset_local_id": "local-only-token"
  },
  "sensitivity": "private"
}
```

## 5.7 カレンダー

EventKitへのアクセス許可があれば、次をタイムラインの予定レイヤーとして取得できる。

- 予定タイトル
- 開始・終了
- 場所
- カレンダー
- 参加者情報
- 更新・削除

ただし、カレンダーは「端末が自動観測した事実」ではなく「予定」である。実績データとは分離し、予定と実行を後段で比較する。

## 5.8 iPhoneから取得困難なデータ

一般アプリ向け公開APIでは、次を前提にしない。

- OS全体の画面オン・オフ履歴
- 端末ロック・解除の全履歴
- 現在の他社アプリ名
- 全アプリの前面・背面遷移ログ
- キーボード入力内容
- 通話・メッセージ本文の包括的取得
- Appleマップ内部の「重要な場所」データベースの一括取得
- 設定アプリに表示されるバッテリー使用履歴の自由な抽出
- Wi-Fi SSIDや周辺ネットワークの恒常的な自由取得

---

## 6. Macから自動蓄積できるデータ

Macは本基盤で最も詳細な行動・作業テレメトリーを取得できる。

## 6.1 稼働・電源・画面状態

取得候補:

- システム起動後の経過時間
- Collector起動時刻
- スリープ開始
- スリープ復帰
- 画面スリープ
- 画面復帰
- ログアウト・電源断要求
- 電源アダプター接続・切断
- バッテリー残量
- 残り時間推定
- 低電力警告

主な公式API:

- `ProcessInfo.systemUptime`
- `NSWorkspace`のsleep/wake関連通知
- IOKit `IOPowerSources`

`systemUptime`はRequired Reason APIに該当するため、配布形態によってはPrivacy Manifestで利用理由を宣言する必要がある。

### 推奨イベント

```text
system.boot_observed
system.sleep_started
system.wake_completed
screen.sleep_started
screen.wake_completed
power.ac_connected
power.ac_disconnected
battery.snapshot
collector.started
collector.stopped
collector.heartbeat
```

## 6.2 操作中・アイドル

Core Graphicsのイベントソースから、最後の入力イベントからの経過時間を取得できる。これにより、キーの内容を記録せず、ユーザーが操作中か離席中かを判定できる。

推奨判定例:

| 状態 | 条件例 |
|---|---|
| active | 最終入力から60秒未満 |
| passive | 60秒以上5分未満 |
| idle | 5分以上 |
| away | 15分以上、または画面ロック相当イベント |
| sleeping | システムスリープ中 |

閾値は固定仕様にせず設定可能にする。

保存すべきなのは個々のマウス移動やキーイベントではなく、状態区間である。

```json
{
  "event_type": "presence.interval",
  "occurred_at": "2026-08-01T10:05:00+09:00",
  "ended_at": "2026-08-01T10:47:31+09:00",
  "device": "macbook-pro",
  "payload": {
    "state": "active",
    "threshold_profile": "default-v1"
  }
}
```

## 6.3 前面アプリとアプリ遷移

`NSWorkspace.frontmostApplication`等により、キーボード入力を受ける前面アプリを取得できる。

取得候補:

- アプリ名
- Bundle ID
- PID
- 起動時刻
- 前面化時刻
- 非アクティブ化時刻
- 終了時刻
- 前面滞在時間

アプリ単位であれば比較的低侵襲であり、作業時間の分類に使いやすい。

例:

```json
{
  "event_type": "application.foreground_interval",
  "occurred_at": "2026-08-01T09:12:31+09:00",
  "ended_at": "2026-08-01T09:48:04+09:00",
  "device": "macbook-pro",
  "payload": {
    "bundle_id": "com.microsoft.VSCode",
    "application_name": "Visual Studio Code"
  },
  "sensitivity": "standard"
}
```

### ウィンドウタイトル

アクセシビリティ権限等を使えば、前面ウィンドウのタイトルを取得できる場合がある。しかしタイトルには、顧客名、文書名、URL、メール件名等が含まれる。

初期版では次の順に段階化する。

1. アプリ名のみ
2. 許可リストに含まれるアプリだけウィンドウタイトル取得
3. 端末内でタイトルを分類し、生タイトルを破棄
4. 必要なプロジェクト名等だけ送信

全アプリの生タイトルを無期限保存する設計は避ける。

## 6.4 ファイル活動

MacではFSEvents等を利用し、指定ディレクトリ内のファイルシステム変更を検知できる。

取得候補:

- 作成
- 更新
- 移動
- 名前変更
- 削除
- 対象パス
- 拡張子
- リポジトリ所属

ただし、本文を自動収集する必要はない。まずはメタデータに限定する。

推奨対象:

- Gitリポジトリ
- `Documents`内の指定フォルダ
- 制作物フォルダ
- ログ出力フォルダ

除外対象:

- Keychain関連
- メールデータベース
- ブラウザプロファイル全体
- 認証トークン
- `.env`
- SSH鍵
- パスワード管理データ
- OS内部ディレクトリ

## 6.5 開発活動

Mac上の開発活動は、OS監視だけでなく、各ツールが既に持つ履歴から取得できる。

| データ | 取得源 | 遡及取得 |
|---|---|---:|
| Gitコミット | `.git` | ◎ |
| ブランチ・タグ | `.git` | ◎ |
| Pull Request・Issue | GitHub API | ◎ |
| ターミナルコマンド | shell history | ○ |
| エージェントセッション | Claude Code/Codex等のログ | ○ |
| ビルド・テスト結果 | CI、ローカルログ | ○ |
| ファイル変更 | FSEvents、Git | 将来◎ / 過去△ |
| IDE前面時間 | Mac Collector | 将来◎ |

シェル履歴やエージェントログには機密情報が含まれる可能性がある。生データをそのまま中央DBへ集めず、端末内で秘密情報を除去する。

## 6.6 システムリソース

定期スナップショットとして次を取得できる。

- CPU使用率
- メモリ使用量
- スワップ
- ディスク使用量
- ロードアベレージ
- ネットワーク送受信量
- バッテリー
- 電源ソース
- 実行中プロセスの集計

ただし、個人活動分析の目的では、1秒周期は過剰である。推奨は通常60秒、負荷異常時のみ10秒程度への一時短縮である。

## 6.7 Macで過去分を取得できる可能性がある情報

| データ | 遡及可能性 | 備考 |
|---|---:|---|
| Git履歴 | 高い | コミット以前の未記録作業時間は不明 |
| ファイル作成・更新時刻 | 中 | コピーや同期で時刻が変わる場合がある |
| ブラウザ履歴 | 中 | ブラウザ仕様、権限、履歴削除に依存 |
| shell history | 中 | 設定、複数シェル、履歴保存条件に依存 |
| システムログ | 中 | 保持期間とログポリシーに依存 |
| アプリ前面時間 | 低い | Collector導入前の完全復元は困難 |
| アイドル区間 | 低い | Collector導入前の完全復元は困難 |
| バッテリー推移 | 低い | 今後のスナップショット蓄積が基本 |

---

## 7. 過去分を回収できるデータと、今後しか取れないデータ

## 7.1 過去分を回収しやすい

- HealthKitに保存済みの健康・活動サンプル
- Apple Watchワークアウト
- 睡眠記録
- Core Motionの履歴キャッシュ範囲内の歩数・活動分類
- 写真の撮影日時・位置
- カレンダー予定
- Gitコミット・ブランチ・タグ
- GitHub上のIssue、PR、レビュー、コミット
- ファイルの現在のメタデータ
- shell history
- 保存済みのエージェントログ

## 7.2 今後のCollector導入後にしか正確に取れない

- Macの前面アプリ滞在区間
- Macの操作中・アイドル区間
- Macの画面・スリープ状態の完全な時系列
- iPhone・Watchのバッテリー推移
- 独自定義した訪問・滞在履歴
- iPhoneのバックグラウンドイベント受信履歴
- Watchアプリ固有の実行・同期履歴
- データ同期失敗・再送履歴

---

## 8. データアーキテクチャ

## 8.1 設計原則

1. **原本イベントは追記専用にする**  
   受信後の原本を直接書き換えない。

2. **発生時刻と取り込み時刻を分ける**  
   非同期同期の遅延を吸収する。

3. **取得元を必ず保持する**  
   iPhone歩数とWatch歩数等を区別する。

4. **重複送信を許容し、サーバーで冪等化する**  
   モバイル同期は少なくとも1回配送を基本とする。

5. **生データと派生データを分離する**  
   後から推定ロジックを変更できるようにする。

6. **データごとに機微度を持たせる**  
   保存先、暗号化、保持期間を変える。

7. **欠測をゼロとして扱わない**  
   記録がないことと、活動がないことを区別する。

## 8.2 共通イベントエンベロープ

```json
{
  "schema_version": "1.0.0",
  "event_id": "01J4...ULID",
  "event_type": "health.heart_rate.sample",
  "source_platform": "watchos",
  "source_framework": "healthkit",
  "source_device_id": "watch-personal-01",
  "source_record_id": "healthkit-sample-uuid",
  "occurred_at": "2026-08-01T10:30:00.000+09:00",
  "ended_at": "2026-08-01T10:30:05.000+09:00",
  "observed_at": "2026-08-01T10:38:20.000+09:00",
  "ingested_at": "2026-08-01T10:39:03.120+09:00",
  "timezone": "Asia/Tokyo",
  "sensitivity": "health",
  "confidence": 1.0,
  "payload": {
    "value": 76,
    "unit": "count/min"
  },
  "metadata": {
    "collector_version": "0.1.0"
  }
}
```

### 時刻の意味

| フィールド | 意味 |
|---|---|
| `occurred_at` | 現象が開始した時刻 |
| `ended_at` | 区間終了時刻。点イベントでは省略可 |
| `observed_at` | Collectorがデータを認識した時刻 |
| `ingested_at` | 中央サーバーが受信した時刻 |

## 8.3 イベントIDと冪等性

冪等キーは次を優先する。

1. HealthKit UUID等の公式レコードID
2. 送信元が生成するULID/UUID
3. `device + event_type + occurred_at + payload_hash`

サーバーは同一イベントの再送を成功扱いにし、重複レコードを増やさない。

## 8.4 保存レイヤー

```text
storage/
├─ raw/
│  ├─ healthkit/
│  ├─ core-motion/
│  ├─ location/
│  ├─ mac-activity/
│  └─ device-state/
├─ normalized/
│  ├─ activity/
│  ├─ presence/
│  ├─ work-session/
│  ├─ sleep/
│  └─ location-state/
├─ aggregates/
│  ├─ daily/
│  ├─ weekly/
│  └─ monthly/
└─ reports/
```

推奨形式:

| 用途 | 形式 |
|---|---|
| 端末内送信待ちキュー | SQLite |
| API受信直後 | PostgreSQLまたは追記JSONL |
| 長期保存・再計算 | Parquet |
| 時系列クエリ | PostgreSQL / TimescaleDB / DuckDB |
| ダッシュボード | Grafana、Metabase、自作Web UI |
| LLM入力 | 日次・週次Markdown、構造化JSON |

GX10を常時稼働ハブにする場合、初期段階ではPostgreSQLを必須にせず、`JSONL + Parquet + DuckDB`でも十分に開始できる。

---

## 9. 収集頻度と想定遅延

| データ | 取得方式 | 推奨粒度 | 想定遅延 |
|---|---|---:|---:|
| Mac前面アプリ | イベント通知または短周期確認 | 状態変化時 | 秒単位 |
| Macアイドル | Core Graphics | 15〜30秒確認 | 秒〜30秒 |
| Mac電源 | IOKit通知 | 状態変化時 | 秒単位 |
| Macリソース | ポーリング | 60秒 | 1分以内 |
| Mac heartbeat | 定期 | 30〜60秒 | 1分以内 |
| HealthKit | Observer + Anchored Query | 差分 | 数分〜長時間の場合あり |
| Core Motion履歴 | 定期回収 | 15分〜数時間 | 非同期 |
| Significant location | OSイベント | 位置変化時 | 不定 |
| Visit | OSイベント | 滞在確定後 | 遅延し得る |
| iPhoneバッテリー | 他イベントに相乗り | イベント時 | 不定 |
| Watchバッテリー | Watch実行時 | イベント時 | 不定 |
| WatchConnectivity | キュー転送 | OS判断 | 不定 |
| Device Activity | スケジュール・閾値 | 集計単位 | 不定 |

本基盤では、同期遅延そのものを障害とみなさず、次の条件で障害判定する。

- Mac heartbeatが一定時間途絶
- iPhone Collectorが24時間以上一度も同期しない
- HealthKitアンカーが進まない
- 送信待ちキューが増加し続ける
- 最古の未送信イベントが規定時間を超える
- 同一データ型の欠測が通常範囲を大きく超える

---

## 10. 派生できる指標

原本データから、次のような高次情報を生成できる。

## 10.1 稼働・作業

- Mac起動時間
- Mac覚醒時間
- 実操作時間
- アイドル時間
- 前面アプリ別時間
- 開発作業時間
- 会議推定時間
- 集中作業区間
- 作業開始・終了時刻
- 深夜作業時間
- 中断回数
- コンテキストスイッチ回数

## 10.2 身体・生活

- 睡眠時間・睡眠ステージ
- 起床推定時刻
- 就床推定時刻
- 歩数・移動距離
- 活動量
- 心拍傾向
- HRV傾向
- ワークアウト時間
- 長時間座位の推定
- 充電・装着パターン

## 10.3 移動・場所

- 自宅滞在時間
- 職場滞在時間
- 移動時間
- 通勤開始・終了
- 訪問先滞在
- 移動手段推定
- 位置ごとの作業時間

## 10.4 統合分析

- 睡眠時間と翌日の集中時間の相関
- HRVと深夜作業の関係
- 運動と作業中断回数の関係
- 会議時間と開発アウトプットの関係
- 場所別の生産性
- Mac利用終了から就寝までの時間
- 起床から最初のMac操作までの時間
- 端末横断の活動タイムライン

派生値には次を付与する。

- 算出ロジックバージョン
- 使用した原本イベント範囲
- 信頼度
- 欠測率
- 再計算日時

---

## 11. 端末横断タイムラインの例

```text
07:04  Apple Watch: 睡眠区間終了
07:11  Apple Watch: 心拍・活動記録再開
07:18  iPhone: 自宅ジオフェンス内で移動開始
07:42  iPhone: 自宅から退出
08:15  iPhone: 職場へ到着
08:22  Mac: スリープ復帰
08:23  Mac: Visual Studio Codeが前面化
08:58  Mac: Google Meetが前面化
09:31  Mac: Google Meet終了、Chromeへ移行
10:04  Mac: 12分間アイドル
10:19  Apple Watch: スタンド記録
12:11  iPhone: 職場から一時退出
12:16  Apple Watch: 歩行距離増加
13:03  Mac: 作業再開
19:42  Mac: 画面スリープ
20:10  iPhone: 自宅到着
23:48  Apple Watch: 睡眠区間開始
```

このタイムラインは、リアルタイムに揃って届く必要はない。翌日までに全イベントが同期され、発生時刻順に再構成できればよい。

---

## 12. プライバシー・セキュリティ設計

## 12.1 原則

- ローカルファースト
- 目的限定
- 最小権限
- データ最小化
- 明示的なオプトイン
- 収集状態の可視化
- 停止・削除が容易
- 生データと公開可能な集計を分離
- 健康・位置・本文データは別暗号鍵または別ストレージ

## 12.2 機微度

| レベル | 例 | 推奨 |
|---|---|---|
| standard | Macの起動、アプリ名、CPU | 通常暗号化、長期保存可 |
| private | ウィンドウタイトル、写真メタデータ、予定 | 制限付き保存、短めの保持期間 |
| location | 緯度経度、訪問履歴 | 強い暗号化、意味ラベル化を検討 |
| health | 心拍、睡眠、HRV | 分離保存、アクセス監査 |
| secret | キー入力、認証情報、本文、音声 | 原則収集しない |

## 12.3 初期版で収集しないもの

- キー入力内容
- クリップボード本文
- メール本文
- チャット本文
- パスワード・トークン
- 画面キャプチャ
- マイク常時録音
- 全ウィンドウタイトル
- 全URL
- 生の位置座標の無期限保存

## 12.4 端末内フィルタ

サーバー送信前に、端末内で次を処理する。

- パス中のユーザー名除去
- URLクエリ文字列除去
- トークン形式の検出・マスク
- `.env`、鍵、認証ファイルの除外
- ウィンドウタイトルの許可リスト処理
- 位置の丸めまたは意味ラベル化
- 生データの機微度付与

---

## 13. 推奨実装構成

## 13.1 iPhone / Apple Watch

技術候補:

- Swift / SwiftUI
- HealthKit
- Core Motion
- Core Location
- BackgroundTasks
- DeviceActivity / FamilyControls（必要な場合のみ）
- WatchConnectivity
- URLSession background transfer
- SQLiteまたはCore Data / SwiftDataによる送信待ちキュー

コンポーネント:

```text
AppleCollectorApp/
├─ Shared/
│  ├─ EventSchema/
│  ├─ LocalQueue/
│  ├─ Crypto/
│  └─ SyncProtocol/
├─ iOS/
│  ├─ HealthKitCollector/
│  ├─ MotionCollector/
│  ├─ LocationCollector/
│  ├─ BatteryCollector/
│  ├─ DeviceActivityCollector/
│  └─ SyncWorker/
└─ watchOS/
   ├─ BatterySnapshot/
   ├─ WatchConnectivitySender/
   └─ BackgroundTaskHandler/
```

## 13.2 Mac

技術候補:

- Swift / AppKit
- ServiceManagement `SMAppService`
- NSWorkspace
- Core Graphics
- IOKit
- FSEvents
- SQLite
- URLSession

コンポーネント:

```text
MacCollector/
├─ AppLifecycleCollector/
├─ SleepWakeCollector/
├─ PresenceCollector/
├─ ForegroundAppCollector/
├─ PowerCollector/
├─ ResourceCollector/
├─ FileEventCollector/
├─ LocalQueue/
└─ SyncWorker/
```

Mac Collectorは、macOS 13以降では`SMAppService`を利用してログイン項目または補助サービスとして登録できる。

## 13.3 GX10サーバー

初期構成:

```text
GX10/
├─ ingestion-api/
│  ├─ authentication
│  ├─ idempotency
│  ├─ schema-validation
│  └─ batch-ingestion
├─ storage/
│  ├─ raw-jsonl
│  ├─ parquet
│  └─ duckdb
├─ processing/
│  ├─ normalization
│  ├─ interval-builder
│  ├─ daily-aggregation
│  └─ anomaly-detection
├─ dashboard/
└─ reports/
```

認証は端末ごとの鍵またはクライアント証明書を使い、Apple IDや端末固有識別子に依存しない独自device IDを発行する。

---

## 14. 段階導入計画

## Phase 0: 取得可否検証

目的: 各APIが実機で期待どおり取得できるか確認する。

実装:

- iPhoneでHealthKit権限取得
- 指定した5〜10種類のHealthKitデータを過去30日分取得
- Anchored Queryのアンカー保存
- Macで前面アプリ、アイドル、sleep/wake、電源をローカルJSONLへ記録
- Watchでバッテリースナップショット取得
- WatchConnectivityでiPhoneへ送信

完了基準:

- 24時間の実機運用でクラッシュしない
- アプリ再起動後も重複なく差分取得できる
- オフライン後に再送できる
- 発生時刻と取り込み時刻が区別される

## Phase 1: 最小実用版

対象データ:

- HealthKit: 歩数、活動量、心拍、HRV、睡眠、ワークアウト
- iPhone: Significant location、Visit、バッテリー
- Watch: バッテリー
- Mac: 前面アプリ、アイドル、sleep/wake、バッテリー、heartbeat

出力:

- 日次タイムライン
- 端末別稼働時間
- Mac実操作時間
- 睡眠時間
- 歩数・活動量
- 自宅・職場・移動の時間

完了基準:

- 7日連続で自動蓄積
- 手動操作なしで翌日レポートが生成される
- 欠測とゼロを区別できる
- 同じイベントの再送で重複しない

## Phase 2: 文脈データ統合

追加:

- カレンダー
- Git / GitHub
- ファイル変更メタデータ
- 許可したアプリのウィンドウ分類
- 写真撮影イベント

成果:

- 予定と実績の比較
- プロジェクト別作業時間
- 会議・開発・管理作業の分類
- 生活・仕事の統合タイムライン

## Phase 3: 分析・自動改善

追加:

- 日次・週次のLLM要約
- 欠測・同期異常検知
- 作業中断パターン
- 睡眠・活動・生産性の相関
- 個人最適な収集頻度制御
- 収集価値の低いデータの停止提案

---

## 15. 最初に実装すべきデータセット

全データを最初から取る必要はない。価値、実現性、電力、プライバシーのバランスから、次の順を推奨する。

### 優先度S

1. Mac sleep/wake
2. Mac active/idle
3. Mac前面アプリ
4. Macバッテリー・電源
5. HealthKit歩数
6. HealthKit心拍
7. HealthKit睡眠
8. HealthKitワークアウト

### 優先度A

9. iPhone Significant location
10. iPhone Visit
11. iPhoneバッテリー
12. Watchバッテリー
13. Core Motion活動分類
14. Macリソース使用量

### 優先度B

15. カレンダー
16. Git / GitHub
17. ファイル変更メタデータ
18. 写真撮影イベント
19. Device Activityの限定集計

### 初期段階では不要

- 常時録音
- キーロギング
- 全URL記録
- 全ウィンドウタイトル
- 高精度GPS常時追跡
- 1秒周期のリソース監視
- Watch上の独自常時センサー処理

---

## 16. MVPの受け入れ基準

MVPは、次を満たした時点で完成とする。

### データ取得

- Macの前面アプリ区間が取得できる
- Macのactive/idle区間が取得できる
- Macのsleep/wakeが取得できる
- Macの電源・バッテリーが取得できる
- HealthKitから過去30日と新規差分が取得できる
- iPhoneの位置変化がバックグラウンドで取得できる
- iPhoneとWatchのバッテリースナップショットが蓄積される

### 同期

- オフライン中も端末内キューへ保存される
- 接続復旧後に自動送信される
- 再送しても重複しない
- 送信失敗を確認できる
- データ欠測を検知できる

### 出力

- 1日分を発生時刻順に表示できる
- Macの操作時間とアイドル時間を算出できる
- 睡眠、歩数、心拍概要を表示できる
- 自宅・職場・移動時間を集計できる
- データの取得元と信頼度を確認できる

### セキュリティ

- 通信が暗号化される
- 端末ごとの認証がある
- 健康・位置データを分離できる
- 収集停止とデータ削除ができる
- キー入力、認証情報、本文を収集しない

---

## 17. 主なリスクと対策

| リスク | 内容 | 対策 |
|---|---|---|
| iOSバックグラウンド遅延 | 任意時刻に実行できない | 発生時刻基準、ローカルキュー、遅延許容 |
| Watch同期遅延 | WatchConnectivityの配送時刻を保証できない | キュー転送、iPhone中継、再送 |
| HealthKit重複 | 複数端末が同種データを生成 | UUID・ソース保持、統計クエリ、正規化 |
| 欠測誤判定 | 記録なしをゼロと判断 | availabilityとcoverageを別管理 |
| バッテリー消費 | GPS・短周期収集 | Significant-change、イベント駆動、動的頻度 |
| 権限拒否 | Health・位置等を取得できない | 機能別権限、縮退動作、状態表示 |
| 機密情報混入 | タイトル・パス・ログに秘密が含まれる | 端末内フィルタ、許可リスト、本文非収集 |
| OS変更 | API挙動や審査条件が変わる | Collectorの疎結合化、OS更新時検証 |
| 長期データ肥大化 | 秒単位ログが増える | 区間化、Parquet、保持期間、集約後削除 |
| 推定の断定化 | 装着・作業等を誤推定 | confidence、推定根拠、原本参照 |

---

## 18. 最終推奨

本構想は、単なる「各端末の稼働時間計測」ではなく、**身体・移動・作業・端末状態を同一時系列へ統合するPersonal Activity Telemetry基盤**として設計すべきである。

中核設計は次の3点である。

1. **Macを詳細な作業センサーにする**  
   前面アプリ、active/idle、sleep/wake、電源を高精度に記録する。

2. **Apple Watchを身体センサーにする**  
   HealthKitに蓄積される活動、心拍、HRV、睡眠、ワークアウトを差分回収する。

3. **iPhoneを移動センサー兼同期ハブにする**  
   HealthKit、Core Motion、Core Location、WatchConnectivityをまとめ、GX10へ非同期送信する。

最初の実装は、Mac CollectorとHealthKit同期から始める。これだけで、作業時間と身体・生活状態の主要部分を操作なしで蓄積できる。位置、Watchバッテリー、Device Activity等は、その後に価値と制約を確認しながら追加する。

---

## 19. Apple公式資料

### HealthKit

- HealthKit overview  
  https://developer.apple.com/documentation/healthkit
- Setting up HealthKit  
  https://developer.apple.com/documentation/healthkit/setting-up-healthkit
- HKObserverQuery  
  https://developer.apple.com/documentation/healthkit/hkobserverquery
- Executing observer queries  
  https://developer.apple.com/documentation/healthkit/executing-observer-queries

### Screen Time / Device Activity

- Device Activity  
  https://developer.apple.com/documentation/deviceactivity
- Screen Time technology frameworks  
  https://developer.apple.com/documentation/screentimeapidocumentation

### Core Motion

- Core Motion  
  https://developer.apple.com/documentation/coremotion
- CMPedometer  
  https://developer.apple.com/documentation/coremotion/cmpedometer
- CMMotionActivityManager  
  https://developer.apple.com/documentation/coremotion/cmmotionactivitymanager

### Core Location

- Core Location  
  https://developer.apple.com/documentation/corelocation
- Significant-change location service  
  https://developer.apple.com/documentation/corelocation/cllocationmanager/startmonitoringsignificantlocationchanges()
- Handling location updates in the background  
  https://developer.apple.com/documentation/corelocation/handling-location-updates-in-the-background

### Background execution

- Background Tasks  
  https://developer.apple.com/documentation/backgroundtasks
- watchOS background execution  
  https://developer.apple.com/documentation/watchkit/background-execution
- Using background tasks on watchOS  
  https://developer.apple.com/documentation/watchkit/using-background-tasks

### WatchConnectivity / Watch battery

- Transferring data with Watch Connectivity  
  https://developer.apple.com/documentation/watchconnectivity/transferring-data-with-watch-connectivity
- WCSession  
  https://developer.apple.com/documentation/watchconnectivity/wcsession
- Apple Watch battery level  
  https://developer.apple.com/documentation/watchkit/wkinterfacedevice/batterylevel
- Apple Watch battery state  
  https://developer.apple.com/documentation/watchkit/wkinterfacedevice/batterystate

### iPhone battery

- UIDevice battery level  
  https://developer.apple.com/documentation/uikit/uidevice/batterylevel
- UIDevice battery state  
  https://developer.apple.com/documentation/uikit/uidevice/batterystate-swift.property

### macOS

- NSWorkspace  
  https://developer.apple.com/documentation/appkit/nsworkspace
- Frontmost application  
  https://developer.apple.com/documentation/appkit/nsworkspace/frontmostapplication
- System uptime  
  https://developer.apple.com/documentation/foundation/processinfo/systemuptime
- CGEventSource  
  https://developer.apple.com/documentation/coregraphics/cgeventsource
- Seconds since last input event  
  https://developer.apple.com/documentation/coregraphics/cgeventsource/secondssincelasteventtype(_:eventtype:)
- IOPowerSources  
  https://developer.apple.com/documentation/iokit/iopowersources_h
- SMAppService  
  https://developer.apple.com/documentation/servicemanagement/smappservice

