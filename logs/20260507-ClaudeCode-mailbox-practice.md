# Claude Code Mailbox ベストプラクティス — 可変台数エージェントチーム向け

## Mailbox の仕組み（前提知識）

Mailbox は IPC でも WebSocket でもなく、**ディスク上の JSON ファイル**。

```
~/.claude/teams/{team-name}/inboxes/{agent-name}.json
```

- エージェントはターン間（think → tool call → result → pause）の「pause」タイミングでのみ受信箱を確認する
- 受信したメッセージは受信側の会話履歴に **user turn として追記** される（＝トークンを永続消費）
- リード（Lead）は全 Teammate の idle 通知・ステータス・broadcast を受け取るため、**最もコンテキストが詰まりやすい**
- コンパクション（~90% 到達時の要約処理）はチーム認識を失わせる既知バグあり

-----

## 可変台数特有の問題

|問題                     |原因                           |
|-----------------------|-----------------------------|
|メッセージが送りっぱなしになる        |受信予定の Teammate が起動していない      |
|リードがチームを「忘れる」          |コンパクション後に Teammate が再起動されていない|
|タスクが永遠に in_progress のまま|タスクオーナーが不在                   |
|broadcast が全員に届かない     |起動数が変わっているのに送信対象が固定          |

-----

## ベストプラクティス

### 1. CLAUDE.md に「現在稼働中のエージェント」を書き込む規約を作る

Mailbox にはルーティングテーブルが存在しない。エージェントは CLAUDE.md とスポーンプロンプトだけを頼りに「誰がいるか」を判断する。

```markdown
## Active Team Members (update on each session start)

| Agent Name    | Role         | File Ownership           |
|---------------|--------------|--------------------------|
| backend-dev   | API 実装      | src/api/                 |
| frontend-dev  | UI 実装       | src/components/          |
| test-runner   | テスト        | tests/                   |

## 不在時のルール
- 上記にいないエージェントには DM を送らない
- 不在エージェントのタスクは lead が再割り当てする
```

セッション開始時に稼働エージェント一覧を CLAUDE.md に反映する運用を **必ず** 習慣化する。

-----

### 2. スポーンプロンプトに「誰が今いるか」を明示する

```
Create an agent team with the following active teammates:
- backend-dev: src/api/ を担当
- frontend-dev: src/components/ を担当

テスト担当は今回不在。テスト関連タスクは backend-dev が兼務する。
```

Teammate は lead の会話履歴を引き継がない。スポーン時の情報だけが初期コンテキスト。

-----

### 3. タスクリスト経由の協調を Mailbox より優先する

Mailbox はメッセージのトークンコストが高く、コンパクション耐性が低い。可能な限りタスクリストの `blockedBy` 依存で協調する。

```
# 悪い例（Mailboxに依存）
backend-dev が API 完成 → frontend-dev に DM「API できました」
frontend-dev がメッセージ受け取ってから着手

# 良い例（タスクリスト依存）
TASK-002: Frontend: UserProfile.jsx 実装
  blockedBy: TASK-001

TASK-001 が complete になると TASK-002 が自動アンブロック
→ DM 不要
```

「90% はタスクリストで解決、10% だけ Mailbox」が適切な比率。

-----

### 4. Mailbox のメッセージは broadcast より direct message を使う

broadcast はチームサイズ × トークンコストで膨らむ。可変台数では「今誰がいるか」次第でコストが変わる。

```
# 悪い例
broadcast: "API スキーマ変更しました"
→ 関係ない Teammate のコンテキストを汚染

# 良い例
DM to frontend-dev: "GET /user のレスポンスに created_at を追加"
```

**broadcast を使って良いケース**：セッション終了宣言・緊急の設計変更・全員に影響するバグ発見

-----

### 5. 重要な情報は必ずファイルに書く（Mailbox に書かない）

コンパクションはファイルを消さないが、メッセージを消す。

```
# 悪い例
backend-dev → DM → frontend-dev: 
  "レスポンス形式: {token: string, refresh_token: string, expires_in: number}"
# → コンパクション後に消える

# 良い例
backend-dev が docs/api-contract.json に書き出す
frontend-dev が自律的にそのファイルを読む
```

API 仕様・設計決定・共有データは必ず `docs/` 配下に永続化する。CLAUDE.md にそのパスを明記する。

-----

### 6. リードのコンパクション対策

リードは全 Teammate のメッセージを受け取るため最もコンテキストが詰まりやすい。

```bash
# settings.json または環境変数
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80
```

コンパクションを 90% → 80% に前倒しすることで、要約の品質が上がりチーム認識が残りやすくなる。

CLAUDE.md に以下を追記：

```markdown
## Lead の行動規則
- 重要な決定は必ず docs/decisions/ に記録してから Teammate に通知する
- Teammate への通知はファイルパスの共有にとどめる（内容を DM に書かない）
- コンパクション後も teams config を確認し、Teammate 一覧を再確認してから作業再開する
```

-----

### 7. セッション開始時のチェックリスト（可変台数対応）

```markdown
## セッション開始プロトコル（CLAUDE.md に記載）

1. `~/.claude/teams/{team-name}/config.json` を確認し現在の Teammate 一覧を取得
2. CLAUDE.md の Active Team Members セクションを更新
3. 不在 Teammate が担当していたタスクを再割り当て
4. 前回セッションの未読 inbox を確認（`cat ~/.claude/teams/{team-name}/inboxes/*.json`）
5. docs/ 配下の最新ドキュメントを確認してから作業開始
```

-----

### 8. Delegate Mode を常に有効にする

リードが実装作業に入るとコンテキストの消費が加速し、Mailbox 監視の質が落ちる。

```
セッション開始後 → Shift+Tab でデリゲートモードに切り替え
```

リードの役割：タスク割り当て・メッセージルーティング・進捗管理に限定。

-----

### 9. Teammate 数に応じたチーム規模の目安

|同時稼働台数|推奨構成                                        |
|------|--------------------------------------------|
|1 台   |Teammate なし、単一セッション                         |
|2〜3 台 |Lead 1 + Teammate 1〜2。broadcast ほぼ不要        |
|4〜5 台 |Lead 1 + Teammate 3〜4。DM のみ使用、broadcast 原則禁止|
|6 台以上 |フェーズ分割（3台×2フェーズ）を推奨                         |

台数が変わるたびに CLAUDE.md の Active Team Members を更新し、スポーンプロンプトで明示する。

-----

### 10. Hooks で台数変化に自動対応する

```json
// .claude/settings.json
{
  "hooks": {
    "TeammateIdle": {
      "command": "scripts/on-teammate-idle.sh"
    },
    "TaskCompleted": {
      "command": "scripts/on-task-complete.sh"
    }
  }
}
```

`TeammateIdle` フック（exit code 2）でアイドル Teammate に次のタスクを自動アサイン。台数が少ないセッションでは 1 Teammate が複数タスクを連続してこなせる。

-----

## まとめ：可変台数環境での原則

1. **「誰がいるか」を常に CLAUDE.md とスポーンプロンプトに明示する**
1. **協調はタスクリスト優先、Mailbox は例外的な情報伝達のみ**
1. **重要情報はファイルに書く。Mailbox は通知手段、保存手段ではない**
1. **broadcast は最小限。DM が基本**
1. **リードは Delegate Mode で守る。コンパクション閾値を 80% に下げる**
1. **セッション開始時に Teammate 一覧・未読受信箱・タスク状態を必ずリセットする**

-----

## 参考

- [Agent Teams Overview](https://claudefa.st/blog/guide/agents/agent-teams)
- [Advanced Controls](https://claudefa.st/blog/guide/agents/agent-teams-controls)
- [Best Practices](https://claudefa.st/blog/guide/agents/agent-teams-best-practices)
- [Medium: How Claude Code Agents Actually Talk](https://medium.com/@skytoinds/how-claude-code-agents-actually-talk-to-each-other-its-weirder-than-you-think-c070b38c28e0)