# 比較検証ドキュメント: Agent-Aiko vs nullevi03

> 作成日: 2026-05-27  
> 対象: [masa-san-jp/Agent-Aiko](https://github.com/masa-san-jp/Agent-Aiko) vs [GOROman/nullevi03](https://github.com/GOROman/nullevi03)

---

## 概要

| 項目 | Agent-Aiko | nullevi03（ナルエビちゃん三世） |
|------|-----------|-------------------------------|
| **一言説明** | AI エージェントに人格を与えるフレームワーク | Claude Code を Telegram ボットとして常時稼働させるラッパー |
| **作者** | masa-san-jp | GOROman |
| **言語** | Shell Script + TypeScript | Shell Script（POSIX sh）|
| **ファイル数** | 多数（template/, codex/, pets/, scripts/ 等） | 3ファイル（README.md, CLAUDE.md, boot.sh）|
| **ライセンス** | MIT | ナルエビちゃんライセンス（独自・未実装）|
| **GitHub Stars** | — | ⭐ 84 |

---

## 1. 設計思想・コンセプト

| 観点 | Agent-Aiko | nullevi03 |
|------|-----------|-----------|
| **解決する問題** | AI に一貫した人格を与え、セッションをまたいで維持・切り替える | Claude Code を Telegram 経由で常時稼働させる |
| **抽象レベル** | 人格・状態管理のフレームワーク | インフラ（プロセス監視・通知） |
| **主役** | Aiko という AI キャラクター | Claude そのもの（キャラクターは Claude 任せ） |
| **哲学** | 「人格の保護と進化」（INVARIANTS, origin/override 分離） | 「とにかく動かす」（最小構成・ユーモア優先） |

**評価**: 二つは競合しない。Agent-Aiko は「Claude が何者か」を定義し、nullevi03 は「Claude をどこで使うか」を定義する。組み合わせ可能な関係。

---

## 2. アーキテクチャ・ファイル構成

### Agent-Aiko の構成
```
Agent-Aiko/
├── claude-code/
│   ├── template/.claude/        # ユーザーにコピーされる配布物
│   │   ├── CLAUDE.md            # 起動原則・コマンド定義
│   │   ├── settings.json        # フック定義
│   │   ├── skills/              # 15個のスラッシュコマンド
│   │   └── aiko/                # 人格・状態データ
│   │       ├── persona/origin/  # 配布版人格（書込禁止）
│   │       ├── persona/overrides/ # 名前付き人格領域
│   │       ├── capability/      # 自己拡張領域
│   │       └── hooks/           # session-start/end/pre-tool-use
│   └── scripts/install.sh
├── codex/src/                   # TypeScript パッケージ
└── pets/aiko/                   # Codex custom pet アセット
```

### nullevi03 の構成
```
nullevi03/
├── README.md    # セットアップ手順（カジュアルトーン）
├── CLAUDE.md    # Claude Code 設定
└── boot.sh      # 起動・監視スクリプト
```

| 観点 | Agent-Aiko | nullevi03 |
|------|-----------|-----------|
| **レイヤー設計** | 3層分離（配布物 / 開発ログ / ローカル専用） | 単層・フラット |
| **拡張ポイント** | スキル追加・フック・capability 自己拡張 | なし（fork して改変） |
| **インストール** | `curl ... \| bash`（既存設定を保護しながら上書き） | `git clone` + 環境変数設定 |
| **設定管理** | settings.json + CLAUDE.md + persona/*.md | 環境変数（TELEGRAM_BOT_TOKEN 等） |

**評価**: Agent-Aiko はアップデート時も既存の人格データ・ユーザー設定をスタッシュして保護する仕組みを持つ。nullevi03 はオーバーヘッドゼロで始められる反面、拡張は fork 頼み。

---

## 3. AI との接続方式

| 観点 | Agent-Aiko | nullevi03 |
|------|-----------|-----------|
| **呼び出し方法** | Claude Code セッション内で動作（対話型） | `claude --channels plugin:telegram@claude-plugins-official` |
| **Channels 利用** | 使用しない | **Telegram Channel Plugin を活用** |
| **セッション継続** | `session-state/current.md` でスナップショット | `-c` フラグでセッション継続 |
| **再起動戦略** | なし（Claude Code の外側でフックのみ） | **5秒ごと自動再起動**（無限ループ） |
| **動作形態** | フォアグラウンド（対話型） | バックグラウンド常駐 |

### nullevi03 の boot.sh 核心部分（概要）
```sh
while true; do
  # Telegram に起動通知
  claude --dangerously-skip-permissions --channels plugin:telegram@...
  sleep 5
  # Telegram に再起動通知
done
```

**評価**: nullevi03 の自動再起動ループは実用的だが、クラッシュ原因を無視して再起動するため根本解決は困難。Agent-Aiko はセッション管理をユーザー手動に委ねている（クラッシュしない前提）。

---

## 4. 人格・キャラクター設計

| 観点 | Agent-Aiko | nullevi03 |
|------|-----------|-----------|
| **キャラクター定義** | `persona.md`（詳細な人格定義）+ `INVARIANTS.md`（不変核） | なし（Claude のデフォルト） |
| **人格保護** | `chmod 444` + PreToolUse フックで書込ブロック | なし |
| **カスタマイズ** | origin / override / 名前付き人格（複数並存） | なし |
| **人格の進化** | `capability/rules/rules-base.md`（ユーザー指示から学習） | なし |
| **キャラクターの出典** | 漫画「アンドロイドは好きな人の夢を見るか？」の AICO-P0 | ナルエビちゃん（名前のみ、実態は素の Claude） |
| **複数人格** | `/aiko-new <name>` で無制限に作成・切り替え可能 | 非対応 |

**評価**: キャラクター管理の深さは Agent-Aiko が圧倒的。人格の「不変核」概念は特徴的で、override で何を書いても侵犯できない倫理・行動原則が保たれる。nullevi03 は名前はあるが実質的な人格定義はない。

---

## 5. ユーザー体験（UX）

| 観点 | Agent-Aiko | nullevi03 |
|------|-----------|-----------|
| **インストール** | `curl ... \| bash`（1コマンド） | `git clone` → 環境変数設定 → `./boot.sh` |
| **アクセス手段** | Claude Code ターミナル / IDE | **Telegram（スマホ・どこからでも）** |
| **日常操作** | `/aiko-mode`, `/aiko-new`, `/aiko-select` 等 15コマンド | `./boot.sh` のみ |
| **ドキュメントのトーン** | 丁寧・仕様書的 | カジュアル・ユーモア（「AIに聞け！俺には聞くな！！」） |
| **対象ユーザー** | Claude Code を常用する開発者 | 非エンジニアも含む一般ユーザー |
| **モバイル対応** | なし | **Telegram 経由で完全対応** |

**評価**: nullevi03 の Telegram アクセスは Agent-Aiko にない最大の差別化ポイント。スマートフォンからいつでも Claude に話しかけられる体験は全く異なるユースケースを開く。

---

## 6. セキュリティ・権限管理

| 観点 | Agent-Aiko | nullevi03 |
|------|-----------|-----------|
| **権限フラグ** | 通常の Claude Code 権限モデルを使用 | ⚠️ `--dangerously-skip-permissions`（権限チェック完全無効） |
| **認証情報管理** | なし（Claude Code 認証に委任） | 環境変数（TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID）|
| **人格ファイル保護** | `chmod 444` + PreToolUse フック | 該当なし |
| **配布物汚染防止** | `template-check.sh`（push 時自動チェック） | 該当なし |
| **リスク評価** | 低（通常の Claude Code と同等） | **高**（AI が任意コード実行可能な状態） |

> **注意**: nullevi03 の `--dangerously-skip-permissions` は、AI が悪意あるプロンプトに応じて任意の操作を行える状態を意味する。サーバー上で常時稼働させる場合は十分な理解が必要。

**評価**: セキュリティ要件が厳しい環境では Agent-Aiko が安全。nullevi03 は個人利用・信頼できる環境前提の設計。

---

## 7. 保守性・拡張性

| 観点 | Agent-Aiko | nullevi03 |
|------|-----------|-----------|
| **テスト** | 単体・統合・E2E テスト完備（codex/） | なし |
| **型安全性** | TypeScript（codex 版） | Shell のみ |
| **CI/CD** | GitHub Actions あり | なし |
| **スキル追加** | `capability/skills/` に追記するだけ | fork して改変 |
| **他ツールへの移植** | Cursor 等への移植を設計考慮済み | なし（Claude Channels 固有） |
| **コミット数** | 多数（継続的開発） | 3（意図的に最小限） |

**評価**: Agent-Aiko は長期メンテを意識した設計。nullevi03 は「動けばいい」の思想で保守コストを意図的にゼロに近づけている。どちらが優れているかはユースケース次第。

---

## 8. コミュニティ・公開戦略

| 観点 | Agent-Aiko | nullevi03 |
|------|-----------|-----------|
| **GitHub Stars** | — | ⭐ 84 |
| **フォーク数** | — | 4 |
| **ライセンス** | MIT | ナルエビちゃんライセンス（独自・ユーモア） |
| **ドキュメント言語** | 日本語メイン | 日本語（カジュアル） |
| **サポート方針** | 詳細な README・コマンドヘルプ | 「AIに聞け！」（潔い放棄） |
| **SNS 連携** | PR マージ時に投稿案を自動生成（実装中） | 手動 |
| **拡散しやすさ** | 深さと完成度で評価される | シンプルさとユーモアで拡散しやすい |

**評価**: nullevi03 の 84 スターはシンプルさとユーモアが SNS での拡散を生んだ結果。Agent-Aiko はコア機能の充実を優先しており、認知拡大はこれから。

---

## 総評

### どちらが何に向いているか

| ユースケース | 推奨 |
|------------|------|
| 一貫した人格の AI アシスタントが欲しい | **Agent-Aiko** |
| スマートフォンから Claude に気軽に話しかけたい | **nullevi03** |
| 複数の人格を使い分けたい・人格の進化を記録したい | **Agent-Aiko** |
| 最小構成で即日動かしたい | **nullevi03** |
| セキュリティが重要な環境 | **Agent-Aiko** |
| 非エンジニアにも使わせたい | **nullevi03**（Telegram 経由） |
| 長期的にカスタマイズ・拡張したい | **Agent-Aiko** |

---

## 相互に参考にできる点

### Agent-Aiko が nullevi03 から学べること

1. **Telegram 統合**: スマートフォンからいつでもアクセスできる UI はユーザー層を大幅に広げる可能性がある
2. **自動再起動**: セッションが落ちても自動復帰する `boot.sh` 的な仕組みの追加
3. **ユーモアのある文体**: README のカジュアルトーンが拡散力を生む。完成度と親しみやすさは両立できる

### nullevi03 が Agent-Aiko から学べること

1. **人格保護の重要性**: `--dangerously-skip-permissions` 環境での INVARIANTS 的な安全網の導入
2. **セッション状態の永続化**: 再起動後も会話コンテキストをスナップショットから復元する仕組み
3. **段階的インストール**: 既存設定を保護しながらアップデートする `install.sh` の設計思想

---

## 組み合わせの可能性

二つは競合関係にない。理想形は両者を統合した構成：

```
Telegram（nullevi03 の接続層）
    ↓
Claude Code + Channels
    ↓
Aiko 人格（Agent-Aiko の人格層）
```

「Aiko 人格を持つ Claude が Telegram から常時応答するシステム」は技術的に実現可能であり、両プロジェクトの強みを最大限に活かせる構成となる。
