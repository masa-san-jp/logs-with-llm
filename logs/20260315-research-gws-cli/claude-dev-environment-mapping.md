# 開発環境マッピングと役割分担設計

## 前提：環境の整理

```
GitHub（起点・真実の源泉）
├── ローカル開発
│   ├── VSCode + Claude Code（ターミナル / IDE拡張）
│   └── Antigravity（Google製、Gemini 3 Pro / Claude Sonnet 4.6 / GPT-OSS）
└── クラウド開発
    ├── Claude Code Cowork（デスクトップ、ノンエンジニア向けエージェント）
    └── GitHub Copilot（PR・コードレビュー・Issue連携）
```

---

## 各ツールの特性と強みの整理

| ツール | 性格 | 強み | 弱み |
|---|---|---|---|
| **Claude Code (VSCode拡張 / ターミナル)** | コードベース全体を読むエージェント | 大規模コンテキスト・複数ファイル横断・git操作 | 非エンジニアには敷居が高い |
| **Antigravity** | エージェントファーストのIDE。複数エージェントの並列実行 | ブラウザ自動テスト・Agent Manager・成果物のArtifact化 | Geminiがプライマリモデルのため、Claude使用時はレート注意 |
| **Claude Code Cowork** | ファイル・タスク管理の自動化（macOS専用） | ノンエンジニアがエージェント能力を使える・デスクトップ操作 | エンジニアリング作業よりドキュメント・業務自動化向き |
| **GitHub Copilot** | PR・Issue・コードレビューに統合されたアシスタント | リポジトリ文脈でのコードレビュー自動化・CI連携 | コード補完・PR文脈が主、設計レベルの推論は弱い |

---

## このプロジェクト（gws暗黙知抽出）における役割分担

### 役割マップ

```
┌─────────────────────────────────────────────────────────────┐
│  設計・アーキテクチャ決定                                    │
│  → Claude (this chat)                                        │
│  → 設計書をGitHubリポジトリにコミット                        │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  実装フェーズ                                                │
│                                                              │
│  [スクリプト・パイプライン構築]                              │
│  Claude Code (VSCode / ターミナル)                           │
│  - gws収集スクリプトのシェル/Python実装                      │
│  - コンテキストパッケージ生成スクリプト                      │
│  - Claude APIへの送信・応答パース                            │
│  - Sheetsへの書き込み自動化                                  │
│                                                              │
│  [並列タスク処理 / 実験的試行]                               │
│  Antigravity (Agent Manager)                                 │
│  - 複数トピックのLLM分析を並列エージェントで実行            │
│  - ブラウザ自動テスト（Sheets出力の確認など）               │
│  - Artifact（スクリーンショット・実行ログ）で進捗確認        │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  レビュー・CI                                                │
│  GitHub Copilot                                              │
│  - PRのコードレビュー自動化                                  │
│  - スクリプトの品質・セキュリティチェック（APIキー漏洩等）  │
│  - GitHub Actionsでの定期実行（週次ログ収集の自動化）        │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  成果物の配布・活用                                          │
│  Claude Code Cowork                                          │
│  - 暗黙プロセスカタログ（Sheets）からドキュメント自動生成   │
│  - ノンエンジニアメンバーへの分析結果の共有・活用           │
└─────────────────────────────────────────────────────────────┘
```

---

## 実装上の重要な判断

### AntigravityでClaudeを使う場面の絞り込み

AntigravityはGemini 3.1 ProをプライマリモデルとしながらClaude Sonnet 4.6もサポートしている。このプロジェクトでAntigravityを使う場面は以下に絞る：

- **並列エージェントでの実行が有効な場面**：複数のトピッククラスター（例：「予算承認」「採用」「顧客対応」）を並列でLLM分析にかけるとき
- **ブラウザ自動テストが必要な場面**：Sheets出力の確認・Google Workspaceダッシュボードの状態検証

Geminiをプライマリに使い、Claude APIへの直接呼び出しはパイプラインスクリプトに組み込む（Antigravity経由にしない）ほうが、コスト・制御性・再現性の面で優れる。

### GitHub Actionsへの接続（定期自動実行）

週次でログを収集・分析を回す場合、以下の構成が自然：

```yaml
# .github/workflows/weekly_log_analysis.yml
name: Weekly Log Analysis

on:
  schedule:
    - cron: '0 9 * * MON'  # 毎週月曜9時

jobs:
  collect-and-analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install gws CLI
        run: npm install -g @googleworkspace/cli
      
      - name: Setup credentials
        env:
          GWS_CREDENTIALS: ${{ secrets.GWS_CREDENTIALS_JSON }}
        run: |
          mkdir -p ~/.config/gws
          echo "$GWS_CREDENTIALS" > ~/.config/gws/credentials.json
      
      - name: Collect logs
        run: python scripts/collect_logs.py
      
      - name: Run LLM analysis
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python scripts/analyze_with_claude.py
      
      - name: Write to Sheets
        run: python scripts/write_to_sheets.py
```

Claude Codeの `@github` 連携を使えば、このワークフローファイル自体の生成・修正もチャットから指示できる。

### CLAUDE.md によるプロジェクト文脈の固定

Claude CodeはCLAUDE.mdファイルを使ってコーディング規約・アーキテクチャ決定・プロジェクト固有の要件を記述し、セッションをまたいで一貫した実装を保証する。

このプロジェクトのCLAUDE.mdに記載すべき内容：

```markdown
# CLAUDE.md

## プロジェクト概要
Google Workspaceのコミュニケーションログから組織の暗黙知を抽出するシステム。
gws CLIでデータ収集 → Pythonでコンテキストパッケージ生成 → Claude APIで分析 → Sheetsに書き込み。

## 重要な設計原則
- 生ログを直接LLMに渡さない。必ずtopic_clustersを経由する
- Gmail/Chat/Calendarの3ソースを必ず横断する（単一ソースに絞らない）
- 分析プロンプトはprompts/ディレクトリで管理し、スクリプトにハードコードしない

## ディレクトリ構造
scripts/
  collect_logs.py      # gws CLI呼び出し
  cluster_topics.py    # トピッククラスタリング
  analyze_with_claude.py  # Claude API呼び出し
  write_to_sheets.py   # Sheets書き込み
prompts/
  process_naming.md    # 暗黙プロセスの命名プロンプト
  automation_scoring.md
  network_analysis.md
data/
  raw/                 # gws出力JSON（gitignore対象）
  clusters/            # クラスタリング結果
  analysis/            # LLM分析結果

## 認証
- gws認証：~/.config/gws/credentials.json（ローカル）/ GitHub Secrets（CI）
- Anthropic API key：環境変数 ANTHROPIC_API_KEY
- 本番データはdataディレクトリに保存し、.gitignoreで除外すること
```

---

## Coworkの活用範囲の明確化

Claude Code Coworkはノンエンジニア向けのデスクトップツールで、ファイル整理・ドキュメント生成・タスク管理の自動化に特化している。

このプロジェクトでのCoworkの役割：
- エンジニアリングタスク（スクリプト実装）には使わない
- **暗黙プロセスカタログができた後**に、そのカタログをもとにした業務マニュアル・引き継ぎドキュメントの自動生成に使う
- 分析結果を非エンジニアメンバーと共有するためのサマリードキュメント作成

---

## ツール選択のデシジョンガイド

```
タスクが来たとき → どのツールを使うか？

コードベース全体を理解した上でスクリプトを書く / リファクタリングする
  → Claude Code (VSCode拡張 or ターミナル)

複数の独立した分析タスクを同時に走らせたい
  → Antigravity (Agent Manager で並列実行)

PRを出す / コードレビューしてもらう / CIに組み込む
  → GitHub Copilot

分析結果からドキュメントを作る / 非エンジニアに配布する
  → Claude Code Cowork

設計を考える / アーキテクチャを議論する / プロンプトを設計する
  → Claude (this chat) → 決定をGitHubにコミット
```
