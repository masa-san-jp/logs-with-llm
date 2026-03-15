# 議事録：Google Workspace暗黙知抽出システム 設計討議

**日時**：2026-03-16  
**参加者**：プロジェクトオーナー、Claude (Anthropic)  
**次フェーズ担当者への引き継ぎ文書**

---

## 背景・目的

組織全体の活動の中で暗黙的に繰り返されている、個人の感覚や経験に依拠した意思決定・業務プロセスを可視化し、自動化・AIの活用を強力に促進することが最終目的。

そのための手段として、Google WorkspaceのCLI（`gws`）を活用してコミュニケーションログを収集し、LLMにコンテキストとインサイトを発見させるシステムの設計を議論した。

---

## 使用するCLI

**[googleworkspace/cli (gws)](https://github.com/googleworkspace/cli)**

- Drive / Gmail / Calendar / Chat / Sheets / Docs / Admin を単一CLIで操作
- Google Discovery Serviceからリアルタイムにコマンドを構築するRust製
- 全出力がJSON。パイプでjqやPythonに渡せる
- 100以上のAI Agent Skillを内包

```bash
npm install -g @googleworkspace/cli
gws auth setup
gws auth login -s calendar,gmail,chat
```

---

## 設計上の主要な合意事項

### 1. 目的の再定義

「ログの可視化」ではなく**組織の暗黙知グラフの構築**。可視化はゴールではなく最終的な副産物。

### 2. 「可視化から着手」は正しくない

生ログを可視化しても意思決定ログにはならない。LLMへの投入前に**文脈と重みを付与したコンテキストパッケージ**に変換することが必要。正しい処理順序は下記の通り。

```
収集（gws CLI）→ トピッククラスタリング → コンテキストパッケージ生成
→ LLM分析（Claude API）→ 構造化出力 → 可視化・カタログ化
```

### 3. 特定のチャットスペースに絞ってはいけない

暗黙知は複数チャンネルをまたいで分散している。**全ソース横断 → トピック別クラスタリング**が正しい順序。最初から特定スペースに絞ると発見すべき暗黙パターンを事前に消してしまう。

### 4. 収集期間は最低4週間

1週間では週次/月次の固定業務と非定常業務の区別ができない。

### 5. 「重み」の定義

単純な発言数だけでなく、以下の複合指標を使う。

| 重み | 意味 |
|---|---|
| 発言頻度 | 特定トピックへの組織的注目度 |
| スレッド深度（返信数） | 合意形成の困難さ |
| 応答速度 | 組織が暗黙的に付けている優先度 |
| 関与者の多様性 | 組織横断的な問題かどうか |
| 時系列バースト | 制度化されていない定常業務の検出 |
| 会議密度（参加者数×時間） | 議題の重さ |

---

## システムアーキテクチャ

```
Layer 1: Raw Collection（gws CLI）
  Calendar / Gmail（送信済みスレッド）/ Chat（全スペース）→ JSON

Layer 2: Context Assembly
  トピッククラスタリング → 重み算出 → コンテキストパッケージ生成
  発言者ネットワークグラフの構築

Layer 3: LLM Analysis（Claude API）
  暗黙プロセスの命名・構造化
  自動化・AI委譲候補のスコアリング
  組織ネットワークの実態分析

Layer 4: Output
  暗黙プロセスカタログ（Sheets）
  自動化優先順位リスト
```

---

## LLMへの主要プロンプト設計（3種）

**P1：暗黙プロセスの命名**  
トリガー・関与者・判断基準・所要時間・ボトルネックを構造化出力させる。

**P2：自動化・AI委譲可能性スコアリング**  
ルール化可能性・繰り返し性・データ依存性・リスク・関与者数の5軸で0〜10スコアリング。
出力：即時自動化可能 / AIアシスト / プロセス文書化が先決 / 現状維持。

**P3：組織ネットワークの暗黙的構造分析**  
公式組織図に現れない情報ハブ・専門家・影響力の乖離・孤立トピックを検出。

---

## 開発環境と役割分担

| ツール | このプロジェクトでの役割 |
|---|---|
| **Claude (this chat)** | 設計・プロンプト設計・アーキテクチャ判断 → 決定をGitHubにコミット |
| **Claude Code (VSCode / ターミナル)** | 収集・分析・Sheets書き込みスクリプトの実装 |
| **Antigravity (Agent Manager)** | 複数トピッククラスターの並列LLM分析・ブラウザ自動テスト |
| **GitHub Copilot** | PRコードレビュー・CI/CD（GitHub Actions）の品質管理 |
| **Claude Code Cowork** | 分析結果からのドキュメント自動生成・非エンジニアへの配布 |

---

## リポジトリ構成（推奨）

```
.
├── CLAUDE.md                    # Claude Codeへのプロジェクト文脈（最優先で作成）
├── .github/
│   └── workflows/
│       └── weekly_log_analysis.yml   # 週次自動実行（GitHub Actions）
├── scripts/
│   ├── collect_logs.py          # gws CLI呼び出し・収集
│   ├── cluster_topics.py        # トピッククラスタリング・重み算出
│   ├── analyze_with_claude.py   # Claude API呼び出し・応答パース
│   └── write_to_sheets.py       # Sheets書き込み
├── prompts/
│   ├── process_naming.md        # P1プロンプト
│   ├── automation_scoring.md    # P2プロンプト
│   └── network_analysis.md      # P3プロンプト
└── data/                        # .gitignore対象（実データ）
    ├── raw/
    ├── clusters/
    └── analysis/
```

**最初にやること**：CLAUDE.mdを作成してGitHubにコミットする。これがすべての環境で文脈を共有する基盤になる。

---

## 実装ロードマップ

| Week | 作業 | 成果物 |
|---|---|---|
| 1 | gws認証 + 3ソース収集スクリプト作成・実行 | 生ログJSON（4週間分） |
| 2 | トピッククラスタリング + コンテキストパッケージ生成 | topic_clusters.json |
| 3 | LLMプロンプト設計・検証（上位5トピックで試行） | インサイトドラフト |
| 4 | 全トピック適用 + Sheetsカタログ化 | 暗黙プロセスカタログ v1 |
| 5〜 | カタログに基づく自動化実装の優先順位決定 | 自動化ロードマップ |

---

## 認証・セキュリティ注意事項

- OAuth未検証アプリは約25スコープ上限 → `gws auth login -s calendar,gmail,chat` で必要なものだけ指定
- 本番データ（`data/`ディレクトリ）は `.gitignore` で除外必須
- GitHub Actions用の認証情報は `GWS_CREDENTIALS_JSON` と `ANTHROPIC_API_KEY` をSecretsに登録
- 他者の発言ログをAI処理する場合、組織のデータポリシー確認が必要

---

## 参照ドキュメント

- `implicit-knowledge-extraction-design.md`：システム設計詳細（Layer 1〜4、プロンプト全文、コマンド例）
- `dev-environment-mapping.md`：開発環境マッピングと役割分担詳細
