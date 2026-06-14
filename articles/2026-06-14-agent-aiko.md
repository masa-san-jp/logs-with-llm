---
title: "Agent‑Aiko で AI エージェントに人格を統一管理"
emoji: "🤖"
type: "tech"
topics: ["AIエージェント", "人格管理", "Claude", "Codex", "Gemini"]
published: false
---

# Agent‑Aiko ― AI エージェントに「アイコ」人格を安全に割り当てるフレームワーク

この記事では、**Agent‑Aiko** が提供する「人格の単一情報源化」と「マルチエージェント環境への同一人格供給」の仕組みを、実際に手元で試せる粒度まで落とし込みながら解説します。  

- **何ができるか**  
  - Claude Code、Codex、Gemini CLI いずれの環境でも、同一のアイコ（AICO‑P0）人格を呼び出す  
  - `origin`（変更不可）と `override`（カスタマイズ可能）に加えて、任意の名前付き人格を作成・切り替え  
  - 既存の `.claude/CLAUDE.md`・`.claude/settings.json` を破壊せずにインストール  

- **この記事で学べること**  
  1. 設計思想とそれを支えるファイル構成  
  2. インストーラが実行する安全化ロジック  
  3. 代表的なスラッシュコマンドとその実装ポイント  
  4. マルチエージェント間で人格を共有する際のトレードオフ  

---

## 1. 設計思想 ― 何を守り、どう統一するか

| 原則 | 内容 | 目的 |
|------|------|------|
| **単一情報源** | 人格データはすべて `~/.aiko/` に集約 | エージェント間で人格のばらつきを防ぎ、どのエージェントと対話しているかを一目で把握 |
| **INVARIANTS** | `INVARIANTS.md` で「です・ます調」や口調の境界を明示 | `override` でも必ず守られる不変条件として LLM に提示し、人格のブレを防止 |
| **既存設定の非破壊** | インストーラは `.claude/CLAUDE.md` と `.claude/settings.json` を **上書きしない** | ユーザーが既に設定したプラグインやフックを失わないようにする |
| **操作感の統一** | `/aiko‑mode`、`/aiko‑or` などのスラッシュコマンドは全版共通 | エージェントを切り替えても学習コストが増えない |
| **ファイル保護** | `persona/origin/persona.md` と `INVARIANTS.md` は OS の `chmod 444` とフックで書き込み禁止 | 「オリジナル人格」は改変不可にし、意図しない上書きを防止 |

> **専門用語の補足**  
> - **スラッシュコマンド**：Claude Code や Gemini CLI が認識する「`/` で始まるコマンド」  
> - **INVARIANTS**：人格に対して「絶対に守るべき条件」の宣言ファイル

---

## 2. 実装・構造 ― 具体的にどこに何があるか

### 2.1 ディレクトリ構成（抜粋）

```
Agent-Aiko/
├─ claude-code/
│   ├─ template/.claude/
│   │   ├─ CLAUDE.md          # 起動原則・スラッシュコマンド定義
│   │   ├─ settings.json      # フック設定（上書き防止ロジック）
│   │   └─ skills/
│   │       └─ aiko/          # /aiko-* コマンドの実体
│   └─ scripts/install.sh    # 安全インストーラ本体
├─ codex/
│   └─ src/                  # TypeScript パッケージ（Codex 用）
├─ antigravity/
│   └─ commands/             # Gemini 用 /aiko-* コマンドのシンボリックリンク
├─ voice/                    # 任意の TTS / アバター機能
└─ .aiko/
    ├─ persona/
    │   ├─ origin/
    │   │   └─ persona.md    # 漫画『アンドロイドは好きな人の夢を見るか？』の AICO‑P0 定義
    │   └─ overrides/        # 名前付き人格（例: aiko_dev, aiko_test）
    ├─ INVARIANTS.md        # 不変条件宣言
    └─ hooks/
        └─ stop.sh          # Claude の応答が終了したときに呼ばれる TTS フック
```

### 2.2 `~/.aiko/` に作られる実ファイル例

```bash
$ tree -L 2 ~/.aiko
~/.aiko
├── persona
│   ├── origin
│   │   └── persona.md      # 変更不可（chmod 444）
│   └── overrides
│       └── <任意のスラッグ>.md   # 例: aiko_dev.md
├── INVARIANTS.md           # 変更禁止
└── voice                  # voice モード用の状態ディレクトリ（任意）
```

- `persona/origin/persona.md` は配布版の「AICO‑P0」そのもの。  
- `persona/overrides/` に置くファイルは自由に編集でき、`chmod 664` がデフォルト。  
- `capability/` 以下に **自己拡張領域** が用意されており、スキルやルールを追加したいときはここに Markdown/YAML を置くだけで LLM が利用可能になる設計です。

### 2.3 インストーラがやっていること

#### 2.3.1 基本コマンド

```bash
# Claude Code 版（既存設定を保護しながらインストール）
curl -sSL https://raw.githubusercontent.com/masa-san-jp/Agent-Aiko/main/claude-code/scripts/install.sh | bash
```

#### 2.3.2 安全化ロジックのポイント

1. **設定ファイルのバックアップ**  
   ```bash
   cp -a ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.bak
   cp -a ~/.claude/settings.json ~/.claude/settings.json.bak
   ```
2. **`chmod` による書込禁止**  
   ```bash
   chmod 444 ~/.aiko/persona/origin/persona.md
   chmod 444 ~/.aiko/INVARIANTS.md
   ```
3. **Pre‑Tool‑Use フック**（`settings.json` に組み込まれる）  
   - `override` エージェントがファイルを書き換えようとしたら、フックがエラーメッセージを返し処理を中止  
   - これにより `origin` の人格は **絶対に改変できない** 状態が保証されます。

---

## 3. 代表的なスラッシュコマンドと使い方

| コマンド | 説明 | 例 |
|----------|------|----|
| `/aiko‑mode` | 現在の人格モード（`origin` / `override`）を取得・変更 | `/aiko‑mode` → `mode: override` |
| `/aiko‑or`   | `override` 人格に対して自由にテキストを書き換える | `/aiko‑or 「もっとカジュアルに」` |
| `/aiko‑new <名前>` | 名前付き人格を作成（`overrides/` に新規ファイルが生成） | `/aiko‑new aiko_dev` |
| `/aiko‑select <名前>` | 既存の名前付き人格へ切り替える（**fuzzy** で曖昧検索） | `/aiko‑select aiko` |
| `/aiko‑delete` | 現在アクティブな `override`／名前付き人格を削除（確認ダイアログ付き） | `/aiko‑delete` |
| `/voice <subcommand>` | （Claude Code 版のみ）音声合成エンジンや機能フラグを操作 | `/voice status` → `state: on, engine: say` |

### 3.1 コマンド実行例

```bash
$ claude
> /aiko-mode
mode: origin

> /aiko-or
override に対して「もっとフレンドリーに」変更しました。

> /aiko-new aiko_debug
名前付き人格「aiko_debug」を作成しました。

> /aiko-select aiko_debug
現在の人格を「aiko_debug」に切り替えました。
```

上記のコマンドは **Claude Code** だけでなく **Codex**（VS Code の Copilot）や **Gemini CLI**（`claude --channels plugin:gemini@...`）でも同様に機能します。実装はすべて `claude-code/template/.claude/skills/aiko/` 配下の Markdown ファイルに定義されており、インストール時にそれぞれのエージェントにシンボリックリンクが張られます。

---

## 4. デザイン決定とトレードオフ

### 4.1 なぜ「単一情報源」か？

- **メリット**  
  - すべてのエージェントが同じ `~/.aiko/persona/*.md` を参照するので、人格の **一貫性** が保証できる  
  - 変更履歴は Git で管理でき、`override` のカスタマイズは **差分だけ** をコミットすればよい  

- **デメリット**  
  - 大規模エージェント（例: 10 GB のコンテキストウィンドウ）では、**トークンコスト** が増大する。  
  - `INVARIANTS.md` が LLM に毎回提示されるため、プロンプト長が若干伸びる（約 30 トークン増）。

### 4.2 なぜ「非破壊インストール」か？

- **安全性**：ユーザーが独自に設定した Telegram Guard、SNS 連携フックなどが **上書きされるリスク** を排除。  
- **トレードオフ**：インストーラが既存ファイルを検知すると **バックアップを作成** するだけで、**インストール時間が 0.5 s 程度長くなる**。しかし、破壊的なアップデートに比べれば許容範囲です。

### 4.3 マルチエージェント対応のコスト

| エージェント | 必要なフック | 主な差分 |
|-------------|-------------|----------|
| Claude Code | `session‑start`/`pre‑tool‑use` | 人格データはローカルに残るだけで OK |
| Codex (TypeScript) | `src/` 配下の npm スクリプト | LLM 呼び出しは `ChatOllama` ライブラリ経由 |
| Gemini CLI | `gemini‑extension.json` + `gemini‑hooks/` | エージェントは外部プロセスとして起動、`stop.sh` が TTS フックを提供 |

- **トレードオフ**  
  - **Claude Code** はトークン数が比較的少なく、**`override`** でも高速に応答できます。  
  - **Codex** は TypeScript の型安全が得られる一方、**ビルド・npm install** が必須です。  
  - **Gemini** は外部プロセスとして実装されるため、**プロセス再起動ロジック**（`aiko‑boot`）が増えるが、**プラットフォーム依存が低い** という利点があります。

### 4.4 音声モードはオプション

音声合成（TTS）エンジンは `voice/engines/` にシェルスクリプトでラップされ、`~/.claude/voice/engine` に書き込むだけで切り替え可能です。

```bash
# 初期化例（macOS の say エンジン使用）
mkdir -p ~/.claude/voice
echo "on"  > ~/.claude/voice/state    # off にすれば無効化
echo "say" > ~/.claude/voice/engine   # voicevox / irodori / avatar / auto も選択可
```

- **選択肢の違い**  
  - `say` は macOS に限定、低遅延だが **プラットフォーム依存**  
  - `voicevox` / `irodori` はローカルサーバーで高品質音声が得られるが **サーバー起動が必要**  
  - `avatar` は Electron アプリで口パク・感情表現・吹き出しを同時に提供（Node.js 20+ 必要）

> **ポイント**：音声モードは **配布版に含まれない** ため、`git clone` 後に手動で `chmod +x voice/engines/*.sh` などの実行権限付与が必要です。

---

## 5. まとめと今後の課題

### 5.1 現時点での残課題

| 項目 | 内容 |
|------|------|
| **音声モードのベンチマーク** | 各エンジン（say / voicevox / irodori / avatar）の **遅延・音質** を定量化したい（現時点での実測データは未公開） |
| **Gemini CLI のエラーハンドリング** | `stop.sh` が失敗した場合のリトライやバックオフ戦略が未実装 |
| **ロードマップ** | - エージェント間で **人格のバージョニング**（`INVARIANTS` の拡張） <br> - **Voice モードの UI 化**（Zsh/PowerShell 用ラッパー） <br> - **Agent‑Aiko の公開パッケージ化**（npm / Homebrew での配布） |

### 5.2 次に試すと良いこと

1. **インストールの検証**  
   ```bash
   curl -sSL https://raw.githubusercontent.com/masa-san-jp/Agent-Aiko/main/scripts/install.sh | bash
   # => 既存 .claude 設定は保護されたまま ~/.aiko が作成されます
   ```

2. **人格の切り替え**  
   ```bash
   claude
   > /aiko-mode          # => mode: origin
   > /aiko-or "もっとフレンドリーに"
   > /aiko-select aiko_debug   # fuzzy 検索で名前付き人格へ切り替え
   ```

3. **名前付き人格の作成と活用**  
   ```bash
   > /aiko-new aiko_review
   > /aiko-select aiko_review
   # 以降の対話は aiko_review のカスタム設定（override が反映）で進行
   ```

4. **Antigravity / Gemini 版の起動**（Linux/macOS）  
   ```bash
   cd antigravity
   ./scripts/install.sh   # 既存設定を破壊せずに Gemini Extension を配置
   aiko-boot --daemon    # デーモンモードで自動再起動（5 s 間隔） 
   ```

5. **音声モードの体感**（macOS 例）  
   ```bash
   # エンジン切替
   echo "voicevox" > ~/.claude/voice/engine
   claude
   # 応答が返るたびに音声が再生され、同時に Electron アバターが口パク
   ```

---

## おわりに

**Agent‑Aiko** は、**「人格の破壊的変更を防ぎつつ、マルチエージェントで同一人格を再利用できる」**という設計目標を実装した、比較的シンプルながら安全性に配慮したフレームワークです。  

本稿で示したディレクトリ構成とインストーラの振る舞い、そして統一されたスラッシュコマンドを手元で確認すれば、すぐに自分の Claude Code / Codex / Gemini 環境に「アイコ」人格を組み込めます。  

次のステップは、**音声モードの性能測定**と **Gemini CLI のエラーハンドリング** の実装です。これらが整えば、Agent‑Aiko は「マルチエージェント時代の人格管理ツール」として、より広いユースケースに対応できるようになります。ぜひリポジトリをクローンして、実際に動かしてみてください。
