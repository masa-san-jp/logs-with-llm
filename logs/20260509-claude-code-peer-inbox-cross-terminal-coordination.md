# Claude Code 同士をターミナル間で連携させる方法を調査した — peer-inbox の設計

複数ターミナルで Claude Code を並行起動して作業しているとき、片方の作業が終わったら他方に「レビューして」と頼んだり、並行作業を依頼したりしたい。これを実装するための調査と設計記録。

## 背景：4 つのアプローチを比較

「複数 Claude Code セッション間でメッセージを送り合いたい」というユースケースには、以下の選択肢が存在する：

| 案 | 仕組み | 状況 |
|---|---|---|
| **A. tmux send-keys ベース** | 別 pane の Claude Code に文字列を直接注入 | tmux 必須、要事前セットアップ |
| **B. `claude --remote-control`** | 公式 CLI フラグでセッションを remote 制御 | **詳細調査が必要** |
| **C. `~/.claude/teams/inboxes/` Mailbox** | 第三者ブログで紹介されている設計パターン | **実装の有無を確認が必要** |
| **D. ファイルベース inbox（自前実装）** | 共有ディレクトリ + 手動チェック | 確実、ただし「真の自律」ではない |

A は環境依存、B/C は信頼性ある情報源での裏取りが必要だった。

## 調査結果

### `--remote-control` の実体（公式 docs）

`claude --help` から見つかる `--remote-control [name]` フラグは、**ローカル IPC 用ではない**ことが Anthropic 公式ドキュメントで明確化されている：

> Remote Control は「デスクから携帯へシームレス移行」の UX であり、プロセス間通信ツールではありません

参照：`code.claude.com/docs/en/remote-control.md`

具体的には：
- ローカルマシンの Claude Code プロセスが Anthropic API へポーリング接続を張る
- claude.ai/code（Web）や Claude モバイルアプリからのメッセージを受け取るための機構
- 認証は claude.ai の OAuth セッショントークン
- **同一マシン内の別プロセス間通信は未対応**

なお、`SendUserMessage` ツール（`--brief` フラグで有効化）も同方向の通信用で、ローカル IPC には使えない。

### `~/.claude/teams/inboxes/` Mailbox の実体

第三者ブログで紹介されている "Claude Code Mailbox" パターンは、`~/.claude/teams/{team-name}/inboxes/{agent-name}.json` というファイルベース IPC を前提に書かれている。しかし：

- 当該パスは検証マシン（Claude Code 2.1.133）に**存在しない**
- `claude --help` に `--team` `--mailbox` `--spawn-agent` `--teammate` 系フラグなし
- `TeammateIdle` `TaskCompleted` などのフックも未実装

参照ブログのリンク先が Anthropic 公式 docs ではなくファンサイト（claudefa.st）と Medium であり、**公式機能ではなく将来の構想か、第三者の実装パターン**と推定される。

### 結論：D（ファイルベース inbox 自前実装）が現実解

A（tmux 依存）と D（汎用）を比較し、調査対象環境（macOS Terminal.app 標準）を考慮して D を採用。

## 設計：peer-inbox

### ディレクトリ構造

```
~/Dev-Data/dev-data-local/<project>/shared/peer-inbox/
├── alice/
│   └── inbox.jsonl       ← alice 宛メッセージ（1 行 1 通）
├── bob/
│   └── inbox.jsonl
└── r-d/
    └── inbox.jsonl
```

git 管理外（端末ローカル領域）に配置。1 マシン内のターミナル間通信が前提。

### メッセージ形式（JSONL append-only）

```json
{"ts":"2026-05-08T20:15:33+09:00","from":"alice","to":"bob","message":"PR #42 のレビューお願い","read":false}
```

`read` フラグで既読/未読を区別。append-only なので排他制御不要（並行送信で順序が前後する程度の race のみ）。

### サブコマンド設計

```bash
peer-inbox.sh send <to> "<message>"        # 任意メッセージ
peer-inbox.sh review <to> "<topic>"        # "レビュー依頼: <topic>" テンプレ
peer-inbox.sh done <to> "<what>"           # "完了通知: <what>" テンプレ
peer-inbox.sh parallel <to> "<task>"       # "並行作業依頼: <task>" テンプレ
peer-inbox.sh check                        # 自分の未読を上に表示
peer-inbox.sh mark-read [N]                # 既読化（個別 or 全件）
peer-inbox.sh list                         # 既知 peer + 未読件数
```

短縮 alias：`r` / `d` / `p` / `c` / `mr` / `ls`。

### PEER_NAME の自動解決

各セッションの「自分の名前」は環境変数 `PEER_NAME` で指定するが、未設定でも cwd から推定：

```bash
detect_peer_name() {
    [ -n "$PEER_NAME" ] && echo "$PEER_NAME" && return 0
    case "$(basename "$PWD")" in
        cfo-fpa|hr|logi-ops|...) echo "$(basename "$PWD")"; return 0 ;;
        Aiko*) echo "aiko"; return 0 ;;
    esac
    return 1
}
```

業務エージェント用ディレクトリで Claude を起動した時に自動的にそのエージェント名を採用する。Aiko 系の各バリアント（`Aiko-Mesugaki`、`Aiko-or` など）は単に `aiko` として正規化。

### macOS 通知連携

送信時に受信側スクリーンに通知：

```bash
osascript -e "display notification \"new message from $PEER_NAME\" \
  with title \"@$to peer-inbox\" sound name \"Glass\""
```

これだけで「気づかせる」部分は解決する。Linux/Windows では通知だけ機能しないが、inbox 本体は動く。

### スキル化（Claude Code SKILL.md）

`/peer-inbox` スラッシュコマンドとして TRIGGER パターンを定義：

```yaml
description: "TRIGGER: ユーザーが「<peer> にレビュー依頼」「<peer> に完了通知」
  「メッセージ届いてる？」「受信箱見て」「既読にして」のような自然文を発した
  場合、または /peer-inbox を明示入力した場合。SKIP: /agent-call（subprocess
  1 ターン委譲）、外部チャネル（Slack/Discord）。Examples - bob にレビュー依頼
  出して, 受信箱見て, alice に完了通知"
```

これでユーザーは Aiko に対して「bob にレビュー依頼出して」と日本語で頼むだけで、Aiko が `peer-inbox.sh review bob "..."` を Bash 経由で実行する。

## 制約と限界

正直に列挙：

- **真の自律ではない**：受信側は手動で `check` を走らせる必要がある。macOS 通知が attention hook
- **macOS 限定の通知**：`osascript` 依存。他 OS は別実装が必要
- **1 マシン内**：複数マシンに跨る場合は別の sync チャネル必要
- **append-only**：全削除や履歴整理は別ツール必要

## 既存ツールとの差別化

既に存在する subprocess 1 ターン委譲（`agent-call.sh`）とは目的が違う：

| ツール | スコープ | 同期/非同期 | 用途 |
|---|---|---|---|
| `agent-call.sh` | Claude → 別 Claude（subprocess） | 同期 1 ターン | 即答が欲しい |
| `peer-inbox.sh` | **生きてる別ターミナル** | **非同期 file-based** | 作業依頼・連絡 |

両方を共存させ、「即答 vs 後で気づいて読む」のニーズを使い分ける。

## 適用可能な汎用パターン

1. **公式機能の調査は公式 docs 一次ソースで裏取り**：`--help` の短い説明文だけでは挙動が分からないことが多い。フラグが「何のため」「どこに繋がるか」は公式ドキュメントを当たる。第三者ブログの「設計パターン」記事は実装の有無が不明確な場合があり、`claudefa.st` のような名前のサイトは Anthropic 公式ではない可能性を念頭に置く

2. **「真の自律」を諦めて非同期＋通知のハイブリッドに倒す**：プロセス間 live IPC は OS・端末・権限で複雑化しがち。ファイル append + OS 通知の組み合わせは「気づいたら読む」UX で 80% の価値を実装コスト 20% で取れる

3. **PEER_NAME のような identity を cwd から自動推定する**：人間が使うツールでも、明示設定の手間を減らすため「カレントディレクトリの規約から推定 → なければエラー」のレイヤーを挟むと UX が大幅に改善する

4. **スラッシュコマンド化で日本語自然文 → CLI コマンドのマッピングを作る**：SKILL.md の TRIGGER パターンに `「bob にレビュー依頼」「受信箱見て」` のような発話パターンを書いておくと、Claude Code セッションがそれを認識してバックグラウンドで CLI を叩く。ユーザーは CLI 構文を覚えなくても自然言語だけで運用できる
