# はじめに (Getting Started)

## 前提

- GitHubアカウントがあること
- LLM（Claude / Gemini / Grok / ChatGPT など）を利用できること

## セットアップ

### リポジトリをフォークまたはクローン

```bash
git clone https://github.com/masa-san-jp/logs-with-llm.git
cd logs-with-llm
```

### 週次ブログ自動化を使う場合

GitHub Secretsに以下を設定します（`anthropic` バックエンドを使う場合）。

| Secret名 | 説明 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic APIキー |

> デフォルトバックエンド（`github_models`）を使う場合は `GITHUB_TOKEN` が自動提供されるため追加設定不要です。

設定場所: **Settings → Secrets and variables → Actions → New repository secret**

詳細は [週次ブログ自動化](Weekly-Blog-Automation) を参照。

## ログの記録

### 1. LLMと会話する

普段通りLLMとチャットします。

### 2. 議事録を生成する

会話の最後に以下のプロンプトを送ります。

```
意思決定のプロセスを記録しておくために、このチャットの会話の議事録を作って、
マークダウン形式でmdファイルに書き出して。
最終成果物は別のmdファイルで書き出して。
```

### 3. ファイルを保存する

ファイル名の命名規則: `YYYYMMDD-{llm名}-{テーマ}.md`

例:
- `20260201-grok-framework-of-note`
- `20260218-gemini-gws-assistant-bot-design`
- `20260311-claude-research-gws-cli`

`logs/` ディレクトリに保存してコミットします。

```bash
git add logs/20260325-claude-new-feature.md
git commit -m "add: Claude との新機能設計の議事録"
git push
```

## ログの再利用

保存した議事録を別のスレッドや別のLLMに貼り付けて会話を継続できます。

```
（議事録の内容をここに貼り付け）

この話の続きなんだけど、〇〇について詳しく教えて。
```

異なるLLMの視点で同じトピックを深掘りできるのが強みです。

## 次のステップ

- [ログの詳細](Logs) — ディレクトリ構成とファイル形式
- [週次ブログ自動化](Weekly-Blog-Automation) — 毎週自動でブログを生成する
- [プロンプト集](Prompts) — 再利用できるプロンプトテンプレート
