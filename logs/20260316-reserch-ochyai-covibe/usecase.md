# co-vibe ユースケース別導入フロー

> リポジトリ: https://github.com/ochyai/co-vibe  
> バージョン: 2026年3月時点 / MIT License

-----

## 共通セットアップ（全ユースケース必須）

```bash
# 1. クローン
git clone https://github.com/ochyai/co-vibe.git && cd co-vibe

# 2. セットアップウィザード実行（APIキー登録・.env生成）
python3 setup.py

# 3. 起動確認
python3 co-vibe.py
```

`.env` に最低1プロバイダのAPIキーが必要。

```env
ANTHROPIC_API_KEY=sk-ant-...   # 推奨（品質最高）
OPENAI_API_KEY=sk-...          # オプション
GROQ_API_KEY=gsk_...           # オプション（超高速）
```

-----

## UC-1: ターミナルAIペアプログラミング

**対象**: 個人開発者・コーディング補助が目的のユーザー  
**使用戦略**: `auto`（デフォルト）

### フロー

```
要件を自然言語で入力
  → エージェントがタスク複雑度を自動判定
  → simple: Haiku/GPT-mini（高速）
  → normal: Sonnet/GPT-4o（バランス）
  → complex: Opus/o3（高品質）
  → ファイル生成・編集・Bash実行を対話的に実施
  → /undo で直前変更をロールバック可能
```

### 起動コマンド

```bash
# 対話モード（推奨）
python3 co-vibe.py

# ワンショット実行
python3 co-vibe.py -p "FastAPIでCRUDアプリを作って"

# 毎回の確認をスキップ（慣れたユーザー向け）
python3 co-vibe.py -y
```

### 主要スラッシュコマンド

|コマンド      |用途                  |
|----------|--------------------|
|`/undo`   |直前のファイル変更を元に戻す      |
|`/plan`   |プランモード切替（実行前に計画を確認） |
|`/cost`   |現在のトークン使用量・推定コスト確認  |
|`/compact`|コンテキスト圧縮（長時間セッション向け）|

### 注意点

- `-y` フラグなしで起動すると、Bash実行前に毎回確認が入る（安全モード）
- `sudo` / `rm -rf` を含むコマンドは特に慎重に確認する

-----

## UC-2: Deep Web リサーチ

**対象**: 調査・情報収集が目的のユーザー  
**使用戦略**: `strong`（複雑タスクのため最強モデルを指定）

### フロー

```
調査テーマを自然言語で入力
  → エージェントがテーマをサブクエリに自動分解
  → 並列Web検索（WebSearch / WebFetch ツール使用）
  → 各サブクエリの結果を収集・評価
  → 統合レポートを生成・ファイルに出力
```

### 起動コマンド

```bash
# 最強モデルで調査
python3 co-vibe.py --strategy strong

# ワンショットで調査レポート生成
python3 co-vibe.py --strategy strong \
  -p "2025年以降の量子コンピューティング動向を調査してmarkdownレポートにまとめて"
```

### セッション保存・再開

```bash
# 調査セッションを保存して後日再開
python3 co-vibe.py --resume

# セッション一覧を確認
python3 co-vibe.py --list-sessions

# 特定セッションを指定して再開
python3 co-vibe.py --session-id <id>
```

### コスト目安

- Deep Research は複数ターン・大量トークンを消費する
- `/cost` コマンドで随時確認を推奨
- コスト上限が気になる場合は `--strategy fast` で Groq（Llama 3.3 70B）を使用

-----

## UC-3: マルチエージェント並列開発

**対象**: 大規模タスク・並列実行で時間を短縮したい上級ユーザー  
**使用戦略**: `strong` または `auto`

### フロー

```
大きなタスクを入力（例: "このリポジトリ全体をリファクタしてテストを書いて"）
  → オーケストレーターがタスクをサブタスクに分割
  → ワークスティーリングスレッドプールで並列サブエージェントを起動
  → 各エージェントが独立してファイル操作・コマンド実行
  → 結果を統合してオーケストレーターが最終回答を生成
  → /bg でバックグラウンドタスクの進行状況を確認
```

### 起動コマンド

```bash
# 自動許可モード（エージェントが中断なく並列実行）
python3 co-vibe.py -y --strategy strong

# バックグラウンドタスク確認
# 起動後、インタラクティブモードで:
/bg
```

### 推奨プロバイダ構成

```env
# マルチエージェントはトークン消費が多いため複数プロバイダを用意
ANTHROPIC_API_KEY=sk-ant-...  # オーケストレーター用（Opus）
GROQ_API_KEY=gsk_...          # サブエージェント用（Llama 3.3 70B・高速）
```

**重要**: 大きなプロジェクトに対して `-y` を使う場合は必ずGitブランチを切った上で実行する。

```bash
git checkout -b feature/ai-refactor
python3 co-vibe.py -y --strategy strong
```

-----

## UC-4: コスト最適化コーディング（日常タスク）

**対象**: APIコストを抑えたい・応答速度重視のユーザー  
**使用戦略**: `cheap` または `fast`

### 戦略比較

|戦略     |モデル優先順                 |向いているタスク      |
|-------|-----------------------|--------------|
|`cheap`|Haiku → GPT-mini → Groq|単純な質問・短いコード生成 |
|`fast` |Groq → Haiku → GPT-mini|リアルタイム応答が必要な作業|

### 起動コマンド

```bash
# コスト最小化
python3 co-vibe.py --strategy cheap

# 最速レスポンス（Groqが利用可能な場合）
python3 co-vibe.py --strategy fast

# 環境変数で固定（毎回指定不要）
echo 'CO_VIBE_STRATEGY=cheap' >> .env
```

### モデル直接指定

```bash
# Haiku を固定使用
python3 co-vibe.py -m claude-haiku-4-5

# GPT-4o-mini を固定使用
python3 co-vibe.py -m gpt-4o-mini
```

-----

## UC-5: プライベート・オフライン運用（Ollama）

**対象**: APIキーを使いたくない・プライバシー重視・エアギャップ環境  
**使用戦略**: `auto`（Ollamaが自動検出される）

### フロー

```
Ollamaインストール
  → モデルをローカルにpull
  → co-vibe起動時にOllamaが自動検出・プロバイダとして追加
  → 全処理がローカルで完結（外部API通信なし）
```

### セットアップ

```bash
# 1. Ollama インストール（公式サイト: https://ollama.com）
# macOS
brew install ollama

# 2. コーディング向けモデルをpull
ollama pull qwen2.5-coder:7b   # 軽量・高速
ollama pull qwen2.5-coder:32b  # 高品質（GPU推奨）

# 3. Ollamaサービス起動
ollama serve

# 4. co-vibe起動（Ollamaが自動検出される）
python3 co-vibe.py
```

### 確認方法

```bash
# デバッグモードでプロバイダ一覧を確認
python3 co-vibe.py --debug
# バナーにOllamaが表示されれば検出成功
```

### 注意点

- Ollamaのみの場合はAPIキー不要（`.env` にキー不要）
- モデルの品質はクラウドAPIより低い場合がある
- GPU未搭載の場合、32B以上のモデルは動作が遅い

-----

## UC-6: AI研究・エージェント実験基盤

**対象**: エージェント動作の研究・デバッグ・ベンチマークを行う研究者・開発者  
**使用戦略**: `auto` + `--debug`

### フロー

```
--debug フラグで起動
  → 全APIコール・ツール実行・判断ロジックをターミナルにトレース出力
  → <think> ブロックによるモデルの推論過程をリアルタイム表示
  → /cost でターンごとのトークン・コストを測定
  → セッションを保存して後から分析
```

### 起動コマンド

```bash
# デバッグモード（全トレース）
python3 co-vibe.py --debug

# TUIデバッグログをファイルに出力
CO_VIBE_DEBUG_TUI=1 python3 co-vibe.py --debug
# ログ: /tmp/co-vibe-tui-debug.log
```

### プロキシサーバーを利用した外部観測

```bash
# OpenAI互換プロキシとして起動
python3 co-vibe-proxy.py

# 別ツール（Cursor, Continue.devなど）からco-vibeをバックエンドとして利用可能
```

### テスト実行

```bash
# 全840テストを実行
python3 -m pytest tests/ -v

# カテゴリ別に実行
python3 -m pytest tests/test_config.py -v
python3 -m pytest tests/test_client.py -v

# 出力付きで実行
python3 -m pytest tests/ -v -s
```

### 参照ドキュメント

|ファイル                   |内容              |
|-----------------------|----------------|
|`POSITION-PAPER.md`    |設計思想・研究ポジションペーパー|
|`VISION-ROADMAP.md`    |開発ロードマップ        |
|`MULTIAGENT-SURVEY.md` |マルチエージェント実装の調査  |
|`TOOL-SURVEY.md`       |ツール実装の調査        |
|`IMPROVEMENTS.md`      |改善ログ            |
|`DEBUG-IMPROVEMENTS.md`|デバッグ機能の改善ログ     |

-----

## 戦略・プロバイダ選択マトリクス

|ユースケース       |推奨戦略            |推奨プロバイダ           |`-y` フラグ |
|-------------|----------------|------------------|---------|
|ペアプログラミング    |`auto`          |Anthropic         |任意       |
|Deep Research|`strong`        |Anthropic + OpenAI|不要       |
|マルチエージェント    |`strong`        |Anthropic + Groq  |推奨（ブランチ上）|
|日常タスク・コスト重視  |`cheap` / `fast`|Groq + Haiku      |任意       |
|オフライン・プライバシー |`auto`          |Ollama のみ         |任意       |
|研究・実験        |`auto`          |全プロバイダ            |不要       |

-----

## トラブルシューティング早見表

|エラー                         |原因          |対処                              |
|----------------------------|------------|--------------------------------|
|`No API providers available`|APIキー未設定    |`.env` に `ANTHROPIC_API_KEY` を追加|
|`model not found`           |モデル名不正      |`--debug` でバナーのモデル一覧を確認         |
|Ollamaが検出されない               |サービス未起動     |`ollama serve` を実行してから再起動       |
|UIが崩れる                      |TUIレンダリングエラー|`CO_VIBE_DEBUG_TUI=1` でログ確認     |
|セッションが見つからない                |IDが違う       |`--list-sessions` で一覧確認         |