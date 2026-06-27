# 1台のマシンで Claude Code を複数アカウント並存させる

Claude Code CLI を使っていると、「個人用」と「会社用」のように複数の Claude アカウントを
同じマシンで使い分けたい場面がある。標準では認証情報が 1 箇所に保存されるため、ログインし直すたびに
前のアカウントが上書きされてしまう。本稿は、設定ディレクトリを分けて **両方ログインしたまま並行運用する**
方法を、仕組み・ソース・使い方の順にまとめる（検証環境: Linux / Claude Code 2.1.173）。

## 仕組み（仕様）

Claude Code は認証情報を設定ディレクトリ配下の `.credentials.json` に保存する。この設定ディレクトリは
環境変数 `CLAUDE_CONFIG_DIR` で切り替えられる。**アカウントごとに別ディレクトリを割り当てれば、
それぞれが独立した認証情報を持ち、互いを上書きしない。**

### 認証情報の保存場所

| OS | デフォルト | `CLAUDE_CONFIG_DIR` 設定時 |
|----|-----------|----------------------------|
| Linux | `~/.claude/.credentials.json` | `$CLAUDE_CONFIG_DIR/.credentials.json` |
| Windows | `%USERPROFILE%\.claude\.credentials.json` | `$CLAUDE_CONFIG_DIR\.credentials.json` |
| macOS | OS の Keychain | Keychain（ファイルには出ない＝後述の注意点参照） |

Linux では `.credentials.json` は権限 `0600`（所有者のみ読み取り可）で保護される。

### 認証方法の優先順位

複数の認証手段が同時に存在する場合、次の順で評価される。

1. 環境変数 `ANTHROPIC_API_KEY`（API キー）
2. 環境変数 `ANTHROPIC_AUTH_TOKEN`（Bearer トークン）
3. `CLAUDE_CONFIG_DIR` 配下の `.credentials.json`（OAuth）
4. デフォルト `~/.claude/.credentials.json`（OAuth）

> `ANTHROPIC_API_KEY` が設定されていると `.credentials.json` は使われない。
> OAuth ベースで複数アカウントを切り替えたい場合は、この変数を `unset` しておく。

### 関連 CLI コマンド

```
claude auth login     # サインイン
claude auth logout    # サインアウト
claude auth status    # 現在の認証状態を表示
```

## ソース（ラッパースクリプト）

毎回 `export CLAUDE_CONFIG_DIR=...` を打つのは面倒なので、2つ目のアカウント専用のラッパーを
PATH の通ったディレクトリ（例: `~/.local/bin/`）に置く。

```bash
#!/bin/bash
# ~/.local/bin/claude-alt
# 2つ目の Claude アカウント専用ランチャー。
# 認証情報を ~/.claude-alt に分離し、デフォルト(~/.claude)と同時に保持する。
export CLAUDE_CONFIG_DIR="$HOME/.claude-alt"
exec claude "$@"
```

```bash
chmod +x ~/.local/bin/claude-alt
```

これで `claude-alt` は常に `~/.claude-alt` を設定ディレクトリとして起動する。
デフォルトの `claude` は今まで通り `~/.claude` を使う。

## 使い方

### セットアップ（2つ目アカウントは初回のみ）

```bash
# 2つ目アカウント用ディレクトリを用意
mkdir -p ~/.claude-alt

# ラッパー経由でログイン（ブラウザ or 表示される URL でサインイン）
claude-alt auth login
```

### 日常運用

```bash
# 1つ目アカウント（デフォルト）
claude

# 2つ目アカウント（別ターミナルで同時に動かせる）
claude-alt
```

両方の `.credentials.json` が別ディレクトリに残るため、**どちらもログインしたまま**になり、
ターミナルごとに別アカウントとして並行作業できる。

### 確認

```bash
claude auth status        # デフォルト側
claude-alt auth status    # 2つ目アカウント側
```

## 注意点（落とし穴）

- **デフォルト側で安易に `claude auth logout` しない。** そのデフォルトの認証情報に依存して動いている
  バックグラウンドのプロセスや常駐エージェントがある場合、ログアウトすると一斉に認証切れになる。
  2つ目アカウントの login/logout は必ずラッパー（`CLAUDE_CONFIG_DIR` を設定した側）で行う。
- **`ANTHROPIC_API_KEY` が環境に残っていると OAuth より優先される。** 複数アカウントを OAuth で
  切り替える運用では `unset ANTHROPIC_API_KEY` しておく。
- **`settings.json` は認証情報と別管理。** `CLAUDE_CONFIG_DIR` を分けると設定ファイルも別になるため、
  2つ目側で必要な設定は別途用意する。
- **macOS は認証情報が Keychain に入る**ため、`CLAUDE_CONFIG_DIR` でファイルを分離する方式が
  そのままは効かない。API キー（`ANTHROPIC_API_KEY`）や `apiKeyHelper` で分ける方法を検討する。
- サブスクリプション種別（Pro / Max / Team / Enterprise）でも OAuth ベースなら同じ方式で分離できる。
  Enterprise の SSO + 管理ポリシー併用時は組織側の設定も確認する。

## まとめ

- 認証情報の置き場は `CLAUDE_CONFIG_DIR` で切り替えられる。アカウントごとにディレクトリを分けるだけで並存できる。
- ラッパースクリプトを 1 本用意すれば、2つ目アカウントをワンコマンドで起動できる。
- 既存のログインに依存する常駐プロセスがある場合、デフォルト側のログアウトに注意する。
