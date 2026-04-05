# 調査報告書：Google Workspace CLI（googleworkspace/cli）を用いた週次レポート自動化と、管理者向け可視化・監視のベストプラクティス

- 調査日: 2026-03-10
- 対象リポジトリ: `googleworkspace/cli`（repo ID: 1171026502）
- 想定利用者: Google Workspace 利用者／管理者（300名規模、外部共有は一部許可）
- 出力形式: Markdown（ローカル保存）
- タイムゾーン: JST固定
- 週次区切り: 月曜開始（JST）

---

## 1. エグゼクティブサマリ（結論）

### 1.1 週次レポート自動化（個人〜チーム用途）
Google Workspace CLI（以下 `gws`）は、Google の Discovery Service を実行時に参照して Workspace API のコマンド体系を動的に構築する設計であり、Calendar/Chat を含む複数サービスのAPIを **同一CLIで横断的に呼び出す**ことができる。([github.com](https://github.com/googleworkspace/cli))

そのため、以下は「取得 → 正規化 → 集計 → Markdown化」というパイプラインで実現可能性が高い：

- 一定期間のカレンダー情報（日時・参加者・タイトル・説明）を取得して週次レポート化
- 自分が参加している Chat スペース群を対象に、一定期間のメッセージを収集し、自分の発言を抽出してレポート化
- 指定スペースの会話履歴を取得し、スレッド単位に整理してレポート化
- 上記レポート同士（Calendar×Chat）を突合して包括レポート化（例：会議前後の発言量、会議参加者の発言の偏り等）

ただし、Chat の「履歴取得（messages.list）で時間フィルタやスレッド情報がどの程度取れるか」は API 仕様に依存するため、実運用前に `gws schema` によるスキーマ確認が必須、という結論になった。([github.com](https://github.com/googleworkspace/cli))

### 1.2 管理者視点（組織全体監視）
「組織全体の“本文”レベルの監視」は、一般に権限・同意・スコープ（sensitive/restricted）などの壁があり、個人用途より難易度が上がる。

そのため、管理者の生産性向上・監査・可視化の目的では、以下の方針が実務的：

- **監視の主軸を監査ログ（Admin Reports/Drive監査など）に置く**
- “全部読む”ではなく、目的別に **KPI→アラート→調査導線（Runbook）** の三段構えで運用負荷を下げる
- 外部共有が「一部許可」の場合は、許可パターンを固定して **例外のみ可視化** する

---

## 2. 対象ツール（googleworkspace/cli）の概要

### 2.1 ツールの位置づけ
`gws` は「Google Workspace API を横断的に扱うCLI」で、静的なコマンド一覧を持たず、Google の Discovery Service を実行時に参照してコマンド体系を生成する。Workspace API 側にエンドポイント／メソッドが追加されると CLI 側が自動的に拾える思想である。([github.com](https://github.com/googleworkspace/cli))

### 2.2 特徴（調査で重要だった点）
- **構造化JSON出力**を前提とし、パイプで `jq` 等に流して集計しやすい([github.com](https://github.com/googleworkspace/cli))
- `--help` でリソース／メソッド単位のヘルプを提供([github.com](https://github.com/googleworkspace/cli))
- `--dry-run`（書き込み系操作の事前確認）をサポート([github.com](https://github.com/googleworkspace/cli))
- 自動ページング（`--page-all`）をサポートし、NDJSONとしてストリーミング可能([github.com](https://github.com/googleworkspace/cli))
- どのAPIでも **`gws schema <service>.<resource>.<method>`** でリクエスト/レスポンスのスキーマを内省できる([github.com](https://github.com/googleworkspace/cli))
- Chat を含む複数サービス（Drive/Gmail/Calendar/Sheets/Docs/Chat/Admin等）を1つのCLIで扱う設計([github.com](https://github.com/googleworkspace/cli))

### 2.3 READMEに明示された例（調査根拠）
README上で、Chat送信（`chat spaces messages create`）やスキーマ内省（`gws schema ...`）、ページング（`--page-all`）が明示されている。([github.com](https://github.com/googleworkspace/cli))

---

## 3. 週次レポート自動化の要件整理と実現方針

### 3.1 要件（ユーザー提示）
1. 一定期間のカレンダーの日時、参加者、タイトル、説明を取得して報告書を作る
2. 一定期間のチャット上での自分の発言（複数チャットにまたがる）を全て取得して報告書を作る
3. 指定したチャットスペースでの一定期間の会話履歴（スレッドも含む）を取得して報告書を作る
4. 上記報告書同士を見比べて包括的なレポートを作る

### 3.2 JST固定・月曜開始の週次区切り
- 週次の期間は **月曜00:00（JST）〜翌週月曜00:00（JST）** の半開区間として扱う方針とした
- 実行環境は Mac/Windows を想定し、OS差に応じて週次の `timeMin/timeMax` を生成する（コードの再現例は本報告書では省略）

---

## 4. 個人・チーム用途（自分が参加している範囲）での実現性評価

### 4.1 Calendar：期間内イベント取得→レポート化
- `gws` は Calendar API を扱える（READMEの範囲でも Calendar が明示され、Workspace横断の対象として扱われる）([github.com](https://github.com/googleworkspace/cli))
- 実現方針：
  - `events.list` を `timeMin/timeMax` で期間指定
  - `fields`（フィールドマスク）で必要項目（summary/description/attendees/start/end等）に絞り、レスポンス肥大化を防ぐ
  - JSON → 集計（`jq`やスクリプト）→ Markdown化

### 4.2 Chat：スペース横断で自分の発言を収集
- `gws` は Chat API を扱い、少なくとも READMEでは Chat へのメッセージ作成（create）が例示されている([github.com](https://github.com/googleworkspace/cli))
- 実現方針（現実的な二段階）：
  1) `spaces.list` で自分が参加するスペース一覧を取得  
  2) 各スペースの `messages.list` でメッセージを取得し、送信者情報（メール等）で “自分の発言” を抽出して集約
- 重要な不確実性：
  - `messages.list` が **時間範囲フィルタ**を持つか
  - スレッド情報（thread）をどのフィールドで取得できるか
  - 取得の粒度（ページング／最大件数）と実運用負荷
- 上記は API 仕様依存なので、`gws schema chat.spaces.messages.list` 等で確認が必要という結論になった。([github.com](https://github.com/googleworkspace/cli))

### 4.3 Chat：指定スペースの会話履歴（スレッド含む）
- 取得→スレッド単位の整理は、概ね次の設計で実現可能：
  - `messages.list` でメッセージ列を取得
  - `thread` 相当の識別子（スキーマ確認が必要）でグルーピング
  - Markdown化（スレッド→時系列）
- ここでも `gws schema` によるフィールド特定が前提になる。([github.com](https://github.com/googleworkspace/cli))

### 4.4 Calendar×Chat の包括レポート（突合）
- 方針：データを共通スキーマへ正規化して突合する
  - Calendarイベント：`{source:"calendar", start, end, title, attendees[], description, link}`
  - Chat発言：`{source:"chat", time, space, thread, sender, text}`
- 例：会議前後の一定時間における発言量／会議参加者の発言の偏り／会議リンクと関連スレッドの結び付け等

---

## 5. 管理者視点（組織全体監視）の見通しと現実的アプローチ

### 5.1 組織全体の“本文監視”はハードルが上がる
- 個人スコープと異なり、管理者視点で全社横断の Chat 本文を網羅的に取得するには、一般に権限・同意・スコープ等の設計が必要になる
- そのため、監査・可視化の目的は “本文収集” よりも **監査ログ中心**で設計する方が運用負荷が下がりやすい

### 5.2 生産性向上のための運用原則（監査・可視化）
- 「全部見る」ではなく **KPI→アラート→調査導線（Runbook）** を整備
- 300名規模では、週次で “上位N件＋急上昇＋例外” を出す運用が現実的
- 外部共有が一部許可なら、許可パターンを固定して **例外のみを可視化**（例外レビューに運用を寄せる）

---

## 6. 管理者の生産性を向上させるベストプラクティス（関心領域別）

前提：ユーザー数300まで／外部共有は一部許可／レポートはローカルMarkdown。

### 6.1 アカウントアクティビティ：セキュリティ
**日次（5分）**で見る項目を固定し、詳細調査は例外時だけにする。
- ログイン異常（深夜帯、短時間に多地点、失敗急増）
- 特権アカウント（管理者）の操作イベント
- 外部共有の急増
- 大量ダウンロード・大量閲覧の兆候（可能な範囲で）

加えて、一次対応のRunbook（テンプレ）を整備し、属人性を排除する。

### 6.2 アカウントアクティビティ：生成AIの活用
- AIは「判断」ではなく「作業の置換」に使う（週次レポート要約、アラート一次切り分け、手順書からのチェックリスト生成）
- ただし AI 出力は誤り得るため、制裁や重大判断の根拠にしない（監査ログ・管理画面で裏取り）
- 重要情報の境界は、共有・IRM・DLP等のルールとセットで整備する（外部共有がある組織では特に重要）

### 6.3 どんなドキュメントが作成され、会社全体でどんな活動が行われているか
- Inventory（棚卸し）と Activity（活動）を分けて設計すると、運用が整理される
- 共有ドライブ中心に寄せるほど、可視化・権限管理・引継ぎが容易になる（マイドライブ偏重は監視・統制コスト増）

### 6.4 ハブ文書の可視化（利用者数／アクセス頻度／更新頻度）
ハブの定義を3指標に固定する：
- Reach（利用者数）
- Velocity（更新頻度）
- Risk（共有リスク：外部共有・公開リンク）

週次で「上位20件＋急上昇」のみを提示し、全件分析を避ける（300名規模ではこれが回る）。

### 6.5 共有ドライブ（共有フォルダ）ごとの活動可視化
共有ドライブ単位に “活発さ” と “危険度” のKPIを分ける。
- 活発さ：編集数、閲覧数、アクティブユーザー
- 危険度：外部共有追加、公開リンク化、ダウンロード増

外部共有が一部許可の場合、許可先ドメイン・許可ドライブ・期限付き共有等のルールを先に固定し、例外のみレビュー対象にする。

### 6.6 長時間労働リスク軽減（時間外・深夜活動可視化）
- 個人監視に直行せず、まず部署・グループ単位の傾向から始める
- 深夜帯（例：22:00–05:00 JST）の編集イベントの“増加・急増”に絞って提示する
- 施策（会議設計、承認フロー、通知設計、テンプレ化/自動化）に接続する形でレポートを作る

---

## 7. 週次レポート（ローカルMarkdown）テンプレ案

週次（JST・月曜開始）で、以下のようなローカルフォルダ構成が運用しやすい。

- `reports/YYYY-MM-DD_to_YYYY-MM-DD/`
  - `00_summary.md`（重要トピック3点、今週の対応、来週のフォロー）
  - `01_security_accounts.md`（ログイン異常、特権アカウント）
  - `02_drive_overview.md`（作成/編集/共有変化の概況）
  - `03_drive_hub_docs.md`（ハブ文書Top20＋急上昇）
  - `04_shared_drives_activity.md`（共有ドライブ別の活発度）
  - `05_external_sharing_exceptions.md`（許可パターン外の外部共有のみ）
  - `06_after_hours_risk.md`（深夜活動の傾向・急増）

---

## 8. 重要な注意点・制約（調査で確認された事項）

- `gws` は Discovery Service を参照してコマンド体系を動的に構築するため、API仕様に応じてコマンドの可用性・パラメータが変わり得る。([github.com](https://github.com/googleworkspace/cli))
- Chat については、送信（create）がREADMEで例示される一方、履歴取得の「時間範囲指定」「スレッド情報」「横断検索」の実現性は API 仕様依存であり、`gws schema` による確認が必須という結論になった。([github.com](https://github.com/googleworkspace/cli))
- 監視設計は “本文を全量収集” ではなく、監査ログ中心・例外検知中心に寄せる方が、管理者の運用負荷とリスク（過剰収集）を下げられる。

---

## 9. 次のアクション（推奨）

1) Chat/Calendar について、`gws schema` で以下を確認し、取得可能なフィルタ・フィールドを確定する  
   - `calendar.events.list/get`
   - `chat.spaces.list`
   - `chat.spaces.messages.list/get`

2) 外部共有が「一部許可」のため、許可パターン（許可ドメイン、許可共有ドライブ、期限付き共有等）を決め、週次レポートで “例外のみ” を列挙する運用にする

3) 週次レポートは「上位N件＋急上昇＋例外」に絞り、毎回全件集計を避けて継続可能な負荷にする（300名規模向け）

---

## 付録：調査で参照した一次情報
- GitHub: googleworkspace/cli（README・リポジトリ概要）([github.com](https://github.com/googleworkspace/cli))