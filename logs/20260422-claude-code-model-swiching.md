# Claude Code モデル切り替え運用 仕様設計書

## 1. 目的

プロジェクトの性質（機密性、複雑性）やコスト、用途に応じて、Anthropic APIモデルとローカルLLMを効率的かつ安全に切り替えて運用するための標準手法を定義する。

-----

## 2. 運用パターン別仕様

### パターンA：プロジェクト別自動切り替え（direnv）

**用途:** プロジェクトごとに「このリポジトリはローカルLLM限定」「このリポジトリはSonnet固定」と厳密に固定したい場合。

**構成ファイル:** `.envrc`（各プロジェクトのルートに配置）

```bash
# .envrc

# モデルの指定
export CLAUDE_CODE_MODEL="claude-sonnet-4-5"

# ローカルLLMを使用する場合のみ以下を有効化
# export ANTHROPIC_BASE_URL="http://localhost:11434/v1"
# export ANTHROPIC_API_KEY="ollama"

# 思考モードをデフォルトにする場合（オプション）
# export CLAUDE_CODE_THINKING="true"
```

> **注意:** `.envrc` は `direnv allow` を実行しないと有効化されない。初回セットアップ時に忘れずに実行すること。

-----

### パターンB：タスク別ショートカット（Alias）

**用途:** 開発者の判断でタスクの重さに応じてグローバルにモデルを使い分けたい場合。

**構成ファイル:** `~/.zshrc` または `~/.bashrc`

|コマンド     |対象モデル                  |用途                  |
|---------|-----------------------|--------------------|
|`c-pro`  |Claude Sonnet（最新）      |複雑なリファクタリング、新規機能実装  |
|`c-think`|Claude Sonnet（Thinking）|難解なバグ調査、アルゴリズム設計    |
|`c-fast` |Claude Haiku（最新）       |誤字修正、テストコードの量産（低コスト）|
|`c-local`|Qwen2.5-Coder（ローカル）    |機密ロジックの修正、オフライン作業   |

```bash
alias c-pro='claude --model claude-sonnet-4-5'
alias c-think='claude --model claude-sonnet-4-5 --thinking'
alias c-fast='claude --model claude-haiku-4-5'
alias c-local='ANTHROPIC_BASE_URL=http://localhost:11434/v1 ANTHROPIC_API_KEY=ollama claude --model qwen2.5-coder:32b'
```

> **Tips:** エイリアス追加後は `source ~/.zshrc`（または `.bashrc`）で即時反映できる。

-----

### パターンC：チーム共有コマンド（Makefile）

**用途:** チーム全体で同じモデル設定を共有し、個人の環境変数設定に依存させたくない場合。

**構成ファイル:** `Makefile`（プロジェクトルート）

```makefile
.PHONY: chat chat-thinking chat-local

# 標準（Sonnet）
chat:
	@claude --model claude-sonnet-4-5

# 思考重視
chat-thinking:
	@claude --model claude-sonnet-4-5 --thinking

# ローカルLLM（開発機でOllamaが動いている前提）
chat-local:
	@ANTHROPIC_BASE_URL=http://localhost:11434/v1 \
	ANTHROPIC_API_KEY=ollama \
	claude --model qwen2.5-coder:32b
```

> **Tips:** `make chat` のように短いコマンドで呼び出せるため、CI/CDスクリプトへの組み込みにも向いている。

-----

### パターンD：対話型セレクター（Wrapper Script）

**用途:** 起動時にその都度、対話形式で最適なモデルを選びたい場合。

**構成ファイル:** `claude-selector.sh`（パスの通った場所に配置）

```bash
#!/bin/bash

echo "--- Claude Code Brain Selector ---"
PS3='使用するモデルを選択してください: '
options=("Sonnet (Standard)" "Sonnet (Thinking)" "Haiku (Fast)" "Ollama (Local)" "Quit")

select opt in "${options[@]}"
do
    case $opt in
        "Sonnet (Standard)")
            unset ANTHROPIC_BASE_URL
            claude --model claude-sonnet-4-5
            break ;;
        "Sonnet (Thinking)")
            unset ANTHROPIC_BASE_URL
            claude --model claude-sonnet-4-5 --thinking
            break ;;
        "Haiku (Fast)")
            unset ANTHROPIC_BASE_URL
            claude --model claude-haiku-4-5
            break ;;
        "Ollama (Local)")
            export ANTHROPIC_BASE_URL="http://localhost:11434/v1"
            export ANTHROPIC_API_KEY="ollama"
            claude --model qwen2.5-coder:32b
            break ;;
        "Quit")
            exit ;;
        *) echo "無効な選択です $REPLY";;
    esac
done
```

配置後に実行権限を付与する:

```bash
chmod +x claude-selector.sh
# PATH が通っている場所に移動（例）
mv claude-selector.sh ~/.local/bin/cs
```

-----

## 3. セキュリティに関する注意事項

1. **APIキーの管理:** ローカルLLMを使用する場合でも、Claude Codeの仕様上 `ANTHROPIC_API_KEY` の環境変数が要求される場合がある。その際は `ollama` などのダミー文字列を入れ、本物のキーを漏洩させないよう注意すること。
1. **Base URLのリセット:** ローカルLLMからクラウドAPIに切り替える際は、必ず `ANTHROPIC_BASE_URL` を `unset` するか空にすること（誤ってローカル設定のままクラウドにリクエストを送らないため）。
1. **gitignore:** direnv を使う場合、個人のAPIキーを含んだ `.envrc` は必ず `.gitignore` に追加すること。
   
   ```gitignore
   # .gitignore
   .envrc
   ```
1. **ローカルLLMの起動確認:** パターンB・C・Dでローカルモデルを使う前に、Ollamaが起動しているか確認すること。未起動のままだと接続エラーになる。
   
   ```bash
   ollama list   # 利用可能なモデルを確認
   ollama serve  # 未起動の場合は起動
   ```

-----

## 4. 推奨される使い分け基準

|シチュエーション     |推奨パターン|コマンド例               |
|-------------|------|--------------------|
|日常的なコーディング   |パターンB |`c-pro`             |
|社外秘コード・個人開発  |パターンA |direnv でローカルLLMを強制  |
|複雑なバグの解決     |パターンB |`c-think`           |
|軽作業・コスト節約    |パターンB |`c-fast`            |
|CI/CDや自動スクリプト|パターンC |`make chat`         |
|チームでモデルを統一したい|パターンC |Makefile を共有        |
|その都度モデルを選びたい |パターンD |`cs`（wrapper script）|

-----

## 5. パターン選択フローチャート

```
開始
 │
 ├─ チーム開発？
 │   └─ Yes → パターンC（Makefile）
 │
 ├─ 機密コードを扱う？
 │   └─ Yes → パターンA（direnv + ローカルLLM）
 │
 ├─ 毎回モデルを選びたい？
 │   └─ Yes → パターンD（Wrapper Script）
 │
 └─ それ以外 → パターンB（Alias）が最も手軽
```

-----

## 6. モデル文字列リファレンス（2025年時点）

|モデル                |文字列                        |備考       |
|-------------------|---------------------------|---------|
|Claude Sonnet 4.5  |`claude-sonnet-4-5`        |現行スタンダード |
|Claude Haiku 4.5   |`claude-haiku-4-5-20251001`|高速・低コスト  |
|Claude Opus 4.5    |`claude-opus-4-5`          |最高性能     |
|Qwen2.5-Coder（ローカル）|`qwen2.5-coder:32b`        |Ollama 経由|


> **注意:** モデル文字列は変更される場合がある。最新の文字列は [Anthropic ドキュメント](https://docs.anthropic.com) を参照すること。