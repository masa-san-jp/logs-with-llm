# Claude Code & Codex オーケストレーション ベストプラクティス

-----

## 目次

1. [スプリットペイン監視環境の構築](#1-スプリットペイン監視環境の構築)
1. [フックによる品質ゲートの強制](#2-フックによる品質ゲートの強制)
1. [プラン承認ワークフローの確立](#3-プラン承認ワークフローの確立)
1. [SKILL.md メタデータチューニング](#4-skillmd-メタデータチューニング)
1. [役割ベースのスキルバンドル設計](#5-役割ベースのスキルバンドル設計)
1. [ハイブリッド・モデルルーティングの実装](#6-ハイブリッドモデルルーティングの実装)

-----

## 前提知識：2つのオーケストレーションモデルの違い

|観点       |Codex サブエージェント    |Claude Code エージェントチーム            |
|---------|------------------|---------------------------------|
|協調モデル    |中央集権型（ハブ＆スポーク）    |分散型（ピア・ツー・ピア）                    |
|タスク割り当て  |親エージェントからの直接ディスパッチ|共有タスクリストからの自律取得                  |
|エージェント間通信|不可（親のみと通信）        |Mailbox/SendMessage 経由で可能        |
|状態保存場所   |クラウド側スレッドメモリ      |ローカルファイルシステム (`~/.claude/tasks/`)|
|排他制御     |API/クラウドインフラ側で管理  |ローカルのファイルロック機構                   |
|最適ユースケース |独立した並列タスク、バッチ処理   |相互依存のある複雑なリファクタリング               |

-----

## 1. スプリットペイン監視環境の構築

### 目的

Claude Code のエージェントチームは複数の独立プロセスとしてローカルで稼働する。各エージェントの動作を同時に視認し、必要時に Human-in-the-loop で介入できる環境が運用品質の前提条件となる。

### 実装手順

#### Step 1: tmux のセットアップ

```bash
# tmux のインストール（macOS）
brew install tmux

# 新しいセッションを作成
tmux new-session -s claude-team

# ペインを分割（例：3エージェントの場合）
# 水平分割
tmux split-window -h

# さらに垂直分割
tmux split-window -v

# ペイン間の移動
# Ctrl+b → 矢印キー
```

#### Step 2: iTerm2 Python API を使う場合（macOS）

```python
# ~/.config/iterm2/scripts/claude_monitor.py
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    # タブを作成してエージェントごとにペインを分割
    tab = await window.async_create_tab()
    session = tab.current_session

    # チームリード用ペイン
    await session.async_send_text("claude --team lead\n")

    # チームメイト1用ペイン
    new_session = await session.async_split_pane(vertical=True)
    await new_session.async_send_text("claude --team member1\n")

    # チームメイト2用ペイン
    new_session2 = await session.async_split_pane(vertical=False)
    await new_session2.async_send_text("claude --team member2\n")

iterm2.run_until_complete(main)
```

#### Step 3: 共有タスクリストの確認コマンド

```bash
# エージェントチームのタスクリスト確認（Ctrl+T でも表示可能）
cat ~/.claude/tasks/{team-name}/tasks.json | jq '.[] | {id, status, assignee}'

# リアルタイム監視
watch -n 2 "cat ~/.claude/tasks/{team-name}/tasks.json | jq '.[] | {id, status}'"
```

#### Step 4: Codex の場合（config.toml で並列数制御）

```toml
# ~/.codex/config.toml
[agents]
max_threads = 6        # 並列サブエージェント数（デフォルト6）
max_depth = 3          # 再帰的エージェント呼び出しの最大深度
```

### 確認ポイント

- 各ペインで個別のエージェントログが流れていること
- タスクのステータス（`pending` → `in_progress` → `completed`）が更新されていること
- 特定ペインにクリックして入り込み、手動でスキルを呼び出せること

-----

## 2. フックによる品質ゲートの強制

### 目的

エージェントが自律的にタスクを完了宣言する前に、Linting・静的解析・テストを自動で走らせ、品質基準を満たさないタスクの完了を物理的に阻止する。終了コード 2 を返すスクリプトが品質ゲートのトリガーとなる。

### 実装手順

#### Step 1: フック設定ファイルの作成（Claude Code）

```bash
# プロジェクトディレクトリに hooks ディレクトリを作成
mkdir -p .claude/hooks
```

```json
// .claude/hooks/task_completed.json
{
  "hook": "TaskCompleted",
  "script": ".claude/hooks/quality_gate.sh",
  "blocking": true
}
```

#### Step 2: 品質ゲートスクリプトの作成

```bash
#!/bin/bash
# .claude/hooks/quality_gate.sh

set -e

TASK_FILE="$1"
TASK_ID=$(jq -r '.id' "$TASK_FILE")
CHANGED_FILES=$(jq -r '.changed_files[]' "$TASK_FILE" 2>/dev/null || echo "")

echo "=== Quality Gate: Task $TASK_ID ==="

# 1. Linting チェック
if echo "$CHANGED_FILES" | grep -q "\.ts\|\.js"; then
    echo "Running ESLint..."
    npx eslint $CHANGED_FILES
    if [ $? -ne 0 ]; then
        echo "GATE FAILED: ESLint errors detected"
        exit 2  # 終了コード2でタスク完了を阻止
    fi
fi

# 2. テストカバレッジチェック
if echo "$CHANGED_FILES" | grep -q "\.ts\|\.js"; then
    echo "Running test coverage check..."
    COVERAGE=$(npx jest --coverage --coverageReporters=json-summary 2>/dev/null \
        | jq '.total.lines.pct')

    if (( $(echo "$COVERAGE < 80" | bc -l) )); then
        echo "GATE FAILED: Coverage $COVERAGE% is below 80%"
        exit 2  # 終了コード2でタスク完了を阻止
    fi
fi

# 3. 型チェック（TypeScript）
if echo "$CHANGED_FILES" | grep -q "\.ts"; then
    echo "Running type check..."
    npx tsc --noEmit
    if [ $? -ne 0 ]; then
        echo "GATE FAILED: TypeScript errors detected"
        exit 2
    fi
fi

echo "=== Quality Gate: PASSED ==="
exit 0  # 正常終了でタスク完了を許可
```

```bash
chmod +x .claude/hooks/quality_gate.sh
```

#### Step 3: Codex の場合（サブエージェント設定ファイル）

```toml
# .codex/agents/quality-reviewer.toml
[agent]
model = "gpt-5.3-codex"
model_reasoning_effort = "high"
sandbox_permissions = ["read-only"]

[hooks]
on_complete = ".codex/hooks/quality_gate.sh"
blocking = true
```

#### Step 4: フックに渡すエラーログの設定

```bash
# .claude/hooks/quality_gate.sh の末尾に追加
# ゲート失敗時のフィードバックをエージェントに返す
if [ $EXIT_CODE -eq 2 ]; then
    cat << EOF > "$TASK_FILE.feedback"
品質ゲートが失敗しました。以下を修正して再提出してください：

エラー内容：
$(cat /tmp/quality_gate_errors.log)

修正要件：
- テストカバレッジ 80% 以上
- ESLint エラー 0 件
- TypeScript コンパイルエラー 0 件
EOF
fi
```

### 確認ポイント

- `exit 2` が返るとエージェントにタスクが差し戻されること
- エラーログがエージェントのコンテキストに正確に渡されること
- `exit 0` で正常にタスクが完了ステータスに移行すること

-----

## 3. プラン承認ワークフローの確立

### 目的

データベーススキーマ変更・認証ロジック・決済処理など、破壊的・高リスクなタスクに対して、エージェントを「読み取り専用プランモード」で強制起動させ、実装計画がチームリードに承認されるまでコード変更を禁止する。

### 実装手順

#### Step 1: 高リスクタスクの判定条件を定義

```json
// .claude/config.json
{
  "plan_required_patterns": [
    "migration",
    "schema",
    "auth",
    "payment",
    "DELETE FROM",
    "DROP TABLE",
    "security",
    "credential"
  ],
  "plan_approval_criteria": [
    "テストコードが含まれていること",
    "ロールバック手順が記載されていること",
    "影響範囲のファイルリストが記載されていること"
  ]
}
```

#### Step 2: プランモードでエージェントを起動するスクリプト

```bash
#!/bin/bash
# spawn_with_plan.sh - 高リスクタスクを読み取り専用プランモードで起動

TASK_DESCRIPTION="$1"
TEAM_NAME="$2"

# 高リスクパターンの検出
RISK_PATTERNS=("migration" "schema" "auth" "payment" "DROP" "DELETE")
IS_HIGH_RISK=false

for pattern in "${RISK_PATTERNS[@]}"; do
    if echo "$TASK_DESCRIPTION" | grep -qi "$pattern"; then
        IS_HIGH_RISK=true
        break
    fi
done

if [ "$IS_HIGH_RISK" = true ]; then
    echo "高リスクタスク検出 → プランモードで起動"
    # --plan-mode: コード変更を禁止し、計画書の作成のみ許可
    # --require-approval: リードの承認なしに実行フェーズに移行不可
    claude --team "$TEAM_NAME" \
           --plan-mode \
           --require-approval \
           --task "$TASK_DESCRIPTION"
else
    claude --team "$TEAM_NAME" \
           --task "$TASK_DESCRIPTION"
fi
```

#### Step 3: チームリードの自律承認基準を設定

```markdown
<!-- .claude/TEAM_LEAD_INSTRUCTIONS.md -->
# チームリードの承認ルール

チームメイトからプラン承認リクエストを受け取った場合、以下の基準で評価すること：

## 承認条件（全て満たすこと）
1. **テストコード**: 変更対象のユニットテスト・統合テストが計画に含まれていること
2. **ロールバック手順**: 変更を元に戻す具体的な手順が記載されていること
3. **影響ファイルリスト**: 変更されるファイルが網羅的に列挙されていること
4. **副作用の分析**: 依存コンポーネントへの影響が分析されていること

## 却下時の対応
条件を満たさない場合は、不足している項目を明記したフィードバックと共に計画を差し戻すこと。
承認も却下も自律的に判断してよい。人間への確認は不要。
```

#### Step 4: Codex のサブエージェント計画強制設定

```toml
# .codex/agents/high-risk-worker.toml
[agent]
model = "gpt-5.4"
sandbox_permissions = ["read-only"]  # 書き込み禁止

[developer_instructions]
"""
このエージェントはコードを変更する前に必ず実装計画書を作成し、
オーケストレーターの承認を得ること。
計画書には以下を含めること：
1. 変更するファイルの完全なリスト
2. テスト戦略
3. ロールバック手順
"""

[hooks]
before_write = "require_plan_approval"
```

### 確認ポイント

- 高リスクキーワードを含むタスクが自動でプランモードに振り分けられること
- チームリードが承認基準を満たさない計画を自律的に差し戻せること
- 承認前にファイル書き込みが物理的に阻止されること

-----

## 4. SKILL.md メタデータチューニング

### 目的

スキルの自律的な選択精度はフロントマターの `description` フィールドの記述精度に依存する。本文の詳しさより、`description` のトリガー条件の正確さがスキル発動率を決定する。不適切なスキルのロードを防ぎ、トークン消費を最適化する。

### SKILL.md の基本構造

```
/skills/
  your-skill/
    SKILL.md          # メタデータ（L1）+ 手順（L2）
    scripts/          # 実行スクリプト（L3）
    references/       # APIドキュメント等（L3）
    assets/           # テンプレート（L3）
```

### 実装手順

#### Step 1: 悪い description の例（発動しない）

```yaml
---
name: database-migration
description: "データベースのマイグレーションを行います。"
---
```

**問題点**: トリガー条件が曖昧、三人称でない、キーワードが不足

#### Step 2: 良い description の例（正確に発動する）

```yaml
---
name: database-migration
description: |
  このスキルは、以下の条件に該当する場合に使用される：
  - ユーザーがデータベーススキーマの変更、テーブルの追加・削除・変更を要求する場合
  - "migration"、"マイグレーション"、"スキーマ変更"、"ALTER TABLE"、"CREATE TABLE" という
    キーワードがタスクに含まれる場合
  - Prisma、Sequelize、Alembic、Flyway などの ORM/マイグレーションツールの操作が必要な場合
  このスキルは SQL の直接実行やアプリケーションコードの変更には使用しない。
---
```

**改善点**: 三人称、トリガーキーワードを網羅、除外条件を明記

#### Step 3: description の最適な記述パターン

```yaml
---
name: {スキル名}
description: |
  このスキルは、以下の条件に該当する場合に使用される：
  - [ユースケース1]: [具体的なトリガーワードや状況]
  - [ユースケース2]: [具体的なトリガーワードや状況]
  - [ユースケース3]: [具体的なトリガーワードや状況]
  このスキルは [除外ケース] には使用しない。
  関連キーワード: [keyword1], [keyword2], [keyword3]
---
```

#### Step 4: description の文字数・品質チェックスクリプト

```bash
#!/bin/bash
# validate_skills.sh - スキルのメタデータ品質を検証

SKILLS_DIR="${1:-~/.claude/skills}"

for skill_file in "$SKILLS_DIR"/*/SKILL.md; do
    SKILL_NAME=$(dirname "$skill_file" | xargs basename)
    DESC_LENGTH=$(grep -A 20 "^description:" "$skill_file" | wc -c)
    HAS_TRIGGER=$(grep -c "場合に\|以下の条件\|when\|if" "$skill_file" || true)
    HAS_EXCLUSION=$(grep -c "使用しない\|not used\|exclude" "$skill_file" || true)

    echo "--- $SKILL_NAME ---"
    echo "  説明文字数: $DESC_LENGTH (推奨: 200-1024文字)"
    echo "  トリガー条件: $([ $HAS_TRIGGER -gt 0 ] && echo '✓' || echo '✗ 要追加')"
    echo "  除外条件: $([ $HAS_EXCLUSION -gt 0 ] && echo '✓' || echo '△ 推奨')"

    if [ $DESC_LENGTH -lt 100 ]; then
        echo "  ⚠️  説明が短すぎます。トリガー条件を追加してください。"
    fi
    if [ $DESC_LENGTH -gt 1024 ]; then
        echo "  ⚠️  説明が長すぎます（上限1024文字）。簡潔にしてください。"
    fi
done
```

#### Step 5: Codex でのスキル管理

```bash
# パブリックリポジトリからスキルをインストール
$skill-installer install https://github.com/org/codex-skills/database-migration

# スキルの一時無効化（削除せずに無効化）
# ~/.codex/config.toml に追加
[[skills.config]]
path = "~/.codex/skills/database-migration/SKILL.md"
enabled = false

# スキルの明示的呼び出し（エージェントの自律選択を上書き）
# プロンプト内で $ プレフィックスを使用
$database-migration スキーマにユーザーロールテーブルを追加
```

### 確認ポイント

- 関連タスクで意図したスキルが自動ロードされること
- 無関係なタスクでスキルが誤ってロードされないこと
- スキルのメタデータのみで 30〜100 トークン程度の消費に収まること

-----

## 5. 役割ベースのスキルバンドル設計

### 目的

マルチエージェント環境で各エージェントに全スキルを持たせると推論のブレとコンテキスト混乱が発生する。エージェントの役割ごとに必要最小限のスキルのみをロードする「役割ベースのバンドル」を強制し、専門性を物理的に担保する。

### スキルバンドルの設計パターン

```
team/
  lead/
    .claude/skills/
      orchestration/    # タスク分割・割り当て
      code-review/      # レビュー基準
      plan-approval/    # 計画承認ロジック
  security-reviewer/
    .claude/skills/
      vuln-scanner/     # 脆弱性診断スクリプト
      owasp-checker/    # OWASP チェックリスト
      secret-detector/  # シークレット漏洩検知
  doc-writer/
    .claude/skills/
      style-guide/      # 文書スタイルガイド
      api-doc/          # API ドキュメントテンプレート
  backend-dev/
    .claude/skills/
      db-migration/     # DB マイグレーション
      api-design/       # REST/GraphQL 設計
      test-gen/         # テストコード生成
```

### 実装手順

#### Step 1: ロール定義ファイルの作成

```json
// .claude/team-roles.json
{
  "roles": {
    "lead": {
      "skills_path": ".claude/skills/lead/",
      "model": "claude-opus-4-7",
      "description": "タスク分割、計画承認、品質管理を担当"
    },
    "security-reviewer": {
      "skills_path": ".claude/skills/security/",
      "model": "claude-opus-4-7",
      "description": "セキュリティレビュー専任。コード変更は行わない"
    },
    "doc-writer": {
      "skills_path": ".claude/skills/docs/",
      "model": "claude-sonnet-4-6",
      "description": "ドキュメント作成専任"
    },
    "backend-dev": {
      "skills_path": ".claude/skills/backend/",
      "model": "claude-sonnet-4-6",
      "description": "バックエンドの実装担当"
    }
  }
}
```

#### Step 2: ロール別起動スクリプト

```bash
#!/bin/bash
# spawn_agent.sh - ロールに応じたスキルバンドルでエージェントを起動

ROLE="$1"
TASK="$2"
TEAM_NAME="$3"

# team-roles.json からスキルパスを読み込む
SKILLS_PATH=$(jq -r ".roles[\"$ROLE\"].skills_path" .claude/team-roles.json)
MODEL=$(jq -r ".roles[\"$ROLE\"].model" .claude/team-roles.json)

if [ -z "$SKILLS_PATH" ]; then
    echo "Error: 未定義のロール '$ROLE'"
    exit 1
fi

echo "ロール '$ROLE' のエージェントを起動..."
echo "  スキルパス: $SKILLS_PATH"
echo "  モデル: $MODEL"

claude --team "$TEAM_NAME" \
       --role "$ROLE" \
       --skills-path "$SKILLS_PATH" \
       --model "$MODEL" \
       --task "$TASK"
```

#### Step 3: Codex のサブエージェント定義ファイルでのスキル指定

```toml
# .codex/agents/security-reviewer.toml
[agent]
model = "gpt-5.3-codex"
model_reasoning_effort = "high"
sandbox_permissions = ["read-only"]  # セキュリティレビュアーは書き込み禁止

[skills]
# セキュリティ関連スキルのみをロード
paths = [
    "~/.codex/skills/vuln-scanner/SKILL.md",
    "~/.codex/skills/owasp-checker/SKILL.md",
    "~/.codex/skills/secret-detector/SKILL.md"
]

[developer_instructions]
"""
あなたはセキュリティレビュー専任エージェントです。
コードの変更は一切行わず、脆弱性の検出と報告のみを担当します。
"""
```

#### Step 4: Mailbox を使ったエージェント間の情報共有（Claude Code）

```bash
# バックエンドエージェントがAPI仕様をフロントエンドエージェントに通知する例
# Claude Code の SendMessage ツールを呼び出す想定のスクリプト

cat << 'EOF' > .claude/hooks/notify_api_change.sh
#!/bin/bash
# API 仕様変更時にフロントエンドエージェントに通知

CHANGED_FILE="$1"

if echo "$CHANGED_FILE" | grep -q "api/"; then
    # Mailbox 経由でフロントエンドエージェントに通知
    claude send-message \
        --to "frontend-dev" \
        --message "API仕様が更新されました: $CHANGED_FILE を確認し、フロントエンドの型定義を更新してください"
fi
EOF
chmod +x .claude/hooks/notify_api_change.sh
```

### 確認ポイント

- 各エージェントが自分のロール外のスキルをロードしていないこと
- Mailbox 経由のメッセージが適切なエージェントに届いていること
- セキュリティレビュアーが `read-only` モードで動作していること

-----

## 6. ハイブリッド・モデルルーティングの実装

### 目的

Claude Code の高精度推論と Codex の高速並列処理を組み合わせ、タスクの性質に応じて最適なモデルに処理を委譲する。WarpGrep などの Codex MCP サーバーをClaude Code チームのワーカーとして外部呼び出しすることで、トークン効率と出力品質を同時に最大化する。

### ルーティング判断基準

|タスクタイプ        |推奨エンジン           |理由               |
|--------------|-----------------|-----------------|
|アーキテクチャ設計・レビュー|Claude Opus 4.7  |深い推論、自己検証ループ     |
|セキュリティ審査      |Claude Opus 4.7  |競合状態等の潜在バグ検出     |
|大規模コード検索      |Codex (WarpGrep) |60%の時間削減、トークン汚染なし|
|CI/CD パイプライン構築|Codex            |シェルコマンド並列実行で圧倒的速度|
|依存関係の一括更新     |Codex            |パターンマッチング型の定型処理  |
|ドキュメント生成      |Claude Sonnet 4.6|コスト効率と品質のバランス    |

### 実装手順

#### Step 1: ルーティング設定ファイルの作成

```json
// .claude/routing.json
{
  "rules": [
    {
      "pattern": ["search", "grep", "find", "探索", "検索"],
      "engine": "codex",
      "skill": "warpgrep",
      "reason": "大規模コード検索はCodexのWarpGrepが最適"
    },
    {
      "pattern": ["architecture", "design", "アーキテクチャ", "設計"],
      "engine": "claude-opus",
      "reason": "深い設計判断はClaude Opusが必要"
    },
    {
      "pattern": ["ci", "pipeline", "deploy", "script", "bash"],
      "engine": "codex",
      "reason": "シェル操作はCodexのTerminal-Benchスコアが優秀"
    },
    {
      "pattern": ["security", "auth", "vulnerability", "セキュリティ"],
      "engine": "claude-opus",
      "reason": "競合状態等の潜在バグ検出にはClaude Opusの自己検証が必須"
    }
  ],
  "default": "claude-sonnet"
}
```

#### Step 2: ルーティングスクリプトの実装

```bash
#!/bin/bash
# route_task.sh - タスクを適切なエンジンにルーティング

TASK="$1"
ROUTING_CONFIG=".claude/routing.json"

# ルーティングルールの評価
ENGINE=$(python3 << EOF
import json, sys

with open("$ROUTING_CONFIG") as f:
    config = json.load(f)

task = """$TASK""".lower()

for rule in config["rules"]:
    for pattern in rule["pattern"]:
        if pattern.lower() in task:
            print(rule["engine"])
            sys.exit(0)

print(config["default"])
EOF
)

echo "タスクを '$ENGINE' にルーティング: $TASK"

case "$ENGINE" in
    "codex")
        # Codex CLI 経由で実行
        codex --model gpt-5.3-codex "$TASK"
        ;;
    "claude-opus")
        claude --model claude-opus-4-7 "$TASK"
        ;;
    "claude-sonnet")
        claude --model claude-sonnet-4-6 "$TASK"
        ;;
    *)
        echo "Error: 未知のエンジン '$ENGINE'"
        exit 1
        ;;
esac
```

#### Step 3: Claude Code から Codex WarpGrep を外部ツールとして呼び出すスキル

```yaml
---
name: codex-search
description: |
  このスキルは、以下の条件に該当する場合に使用される：
  - 大規模リポジトリ（1万行以上）でのコード検索が必要な場合
  - "grep"、"検索"、"find usages"、"どこで使われている" というキーワードがある場合
  - Codex の WarpGrep を使って高速検索を行う場合
  このスキルはコード変更には使用しない。検索・探索専用。
---

# Codex WarpGrep 経由の高速コード検索

## 使用方法

検索クエリを受け取り、Codex CLI 経由で WarpGrep を起動する。
結果のファイルパスと行範囲のみをコンテキストに返す（コンテキスト汚染を防ぐ）。

## 実行手順

1. 検索クエリを整理する
2. Codex CLI を呼び出す
3. 結果のファイルパスと行番号のみを返す（生のコード内容は含めない）
```

```bash
#!/bin/bash
# skills/codex-search/scripts/warpgrep.sh
# Codex WarpGrep を呼び出して検索結果のロケーションのみを返す

QUERY="$1"
REPO_PATH="${2:-.}"

echo "=== Codex WarpGrep 検索: $QUERY ==="

# Codex CLI 経由で WarpGrep を起動
RESULT=$(codex --skill warpgrep \
               --query "$QUERY" \
               --repo "$REPO_PATH" \
               --output-format "locations-only" \
               2>/dev/null)

# ファイルパスと行範囲のみを出力（コード本文は含めない）
echo "$RESULT" | jq -r '.results[] | "\(.file):\(.start_line)-\(.end_line)"'

echo "=== 検索完了（コード本文はコンテキストに含めない） ==="
```

#### Step 4: トークンコストのモニタリング設定

```bash
#!/bin/bash
# monitor_tokens.sh - エンジン別のトークン消費量を記録

LOG_FILE="~/.claude/token_usage.jsonl"

log_usage() {
    ENGINE="$1"
    TASK_TYPE="$2"
    TOKENS="$3"

    echo "{\"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \
          \"engine\": \"$ENGINE\", \
          \"task_type\": \"$TASK_TYPE\", \
          \"tokens\": $TOKENS}" >> "$LOG_FILE"
}

# 日次サマリーの表示
show_daily_summary() {
    echo "=== 本日のトークン使用量 ==="
    cat "$LOG_FILE" | jq -r 'select(.timestamp | startswith("'"$(date +%Y-%m-%d)"'")) |
        .engine' | sort | uniq -c | sort -rn
}
```

### 確認ポイント

- コード検索タスクが Codex にルーティングされ、メインコンテキストが汚染されないこと
- 設計・セキュリティタスクが Claude Opus にルーティングされること
- 月次のトークン消費が適切なエンジン分散により最適化されていること

-----

## まとめ：プラクティスの優先順位

|優先度 |プラクティス              |効果                |
|----|--------------------|------------------|
|🔴 必須|スプリットペイン監視環境        |エージェント挙動の可視化と介入能力 |
|🔴 必須|フックによる品質ゲート         |低品質コードの自動阻止       |
|🟡 重要|プラン承認ワークフロー         |高リスク変更の破壊的影響の防止   |
|🟡 重要|SKILL.md メタデータチューニング|トークン効率と正確なスキル発動   |
|🟢 推奨|役割ベースのスキルバンドル       |推論の専門化とコンテキスト混乱の排除|
|🟢 推奨|ハイブリッドモデルルーティング     |コスト最適化と品質の両立      |