# Claude Code: マルチ端末向け自動同期とサブエージェント日次起動の設計

作業日: 2026-05-01
作業者: Aiko エージェント（Claude Sonnet 4.6, override 人格）
目的: 個人運用のエージェント管理リポジトリで、(1) 複数端末間の設定同期、(2) サブエージェントの日次自動起動を、外部スケジューラなしで成立させる

---

## 背景

Claude Code で複数のサブエージェント（業務領域別 4 種＋メタ役 4 種）を運用しているプライベートリポジトリがある。次の 2 つを満たしたい。

1. 自宅・出先・別 PC で同じ設定を共有して使いたい（マルチ端末）
2. メタエージェント（標準化レビュー・社外動向観測・スキル横展開・クリーンアップ）を毎日起動して提案を蓄積させたい

クラウド cron（Anthropic の `/schedule`）は確実だが課金が乗る。ローカル cron は端末オフ時に動かない。Claude Code の hook 機構で完結させられないか検証した。

---

## 設計 1: GitHub 自動同期

### 仕組み

3 層構成：

1. **シェルスクリプト** `agent-sync.sh`
   - `sync` モード（デフォルト）: pull → push → status を順に実行
   - `pull` モード: fast-forward 可能なときだけ自動 pull、ローカル変更があれば skip
   - `push` モード: 対象スコープに変更があれば自動 commit & push
   - `status` モード: 同期状態を表示
2. **hook 設定** `.claude/settings.json`
   - SessionStart: `agent-sync.sh pull`
   - SessionEnd: `agent-sync.sh push`
3. **スラッシュコマンド** `/sync`
   - 任意タイミングで sync を呼ぶ手動コマンド

### 安全機構

- pull がローカル変更を検知したら強制マージしない（`git pull --ff-only`）
- push は対象ディレクトリのみ stage（他ディレクトリの変更には触れない）
- 失敗時も exit 0 でセッション継続を阻害しない（オフライン対応）

### コミットメッセージ規約

自動 commit は `chore(sync): auto-sync ... YYYY-MM-DD HH:MM` で固定し、人間の意図的なコミット（feat / fix / docs）と粒度を区別できるようにした。

### スクリプト要点（抜粋）

```bash
# pull モード
if [ -n "$(git status --porcelain)" ]; then
  echo "ローカル変更があるため pull をスキップ" >&2
  exit 0
fi
if git merge-base --is-ancestor "$LOCAL" "$REMOTE"; then
  git pull --ff-only origin "$BRANCH" --quiet
fi

# push モード
if [ -z "$(git status --porcelain "$SCOPE_PATH")" ]; then
  exit 0  # 何もしない
fi
git add "$SCOPE_PATH"
git commit -m "chore(sync): auto-sync agents $(date '+%Y-%m-%d %H:%M')"
git push origin "$BRANCH"
```

`git rev-parse --show-toplevel` でリポジトリルートを取得し、想定外のリポジトリで実行された場合は何もしない（`basename` 一致チェック）。これでスクリプトの誤発火を防ぐ。

---

## 設計 2: サブエージェントの日次自動起動

### 検討した選択肢

| 案 | 実現性 | コスト | 採否 |
|---|---|---|---|
| クラウド cron（Anthropic の routine） | ◎ | ✗ 課金あり、git 同期セットアップが必要 | 棄却 |
| ローカル cron + `claude -p` | ◯ | ◎ | 端末オフ時に動かない問題あり、棄却 |
| **SessionStart hook + マーカーファイル方式** | ◎ | ◎ | **採用** |

「ユーザーが claude を起動しない＝そもそも分析対象の作業がない」と割り切ることで、SessionStart 同期で十分だと判断した。

### 採用方式：marker file + CLAUDE.md instruction

```
SessionStart hook
  └─ meta-check.sh
       ├─ logs/reviews/.last-run-{role} の更新時刻を確認
       └─ 24h 経過していれば
            logs/reviews/.pending/{role} マーカーを作成

CLAUDE.md（プロジェクト指示）
  └─ pending/ にマーカーがあれば
       対応するサブエージェントを Agent ツールで並列起動
       完了したら last-run 更新 + marker 削除
```

### なぜ二段構えか

Claude Code の hook はシェルスクリプトしか起動できない。`claude -p "/meta reviewer"` を hook 内で呼ぶ案も検討したが、再帰呼び出しになり制御が難しい。「シェルでマーカーを作る」「Claude 本体がマーカーを読んでサブエージェントを起動する」と責務を分離した。

これは原稿執筆で使ったパターンと相似形。本文（実装）と仕様（コメント）を分離し、本文側からは仕様を参照、仕様側はチェックリストとして機能する、という二重化。

### 手動コマンド `/meta`

`/meta` 単独で各メタエージェントの最終起動日時を表示。`/meta <role>` で個別起動、`/meta all` で 4 つ並列起動。

```bash
# 引数なしの状態表示
for role in reviewer scout lab janitor; do
  last=".last-run-$role"
  pending=".pending/$role"
  if [ -f "$last" ]; then
    last_str=$(date -r "$(cat $last)" '+%Y-%m-%d %H:%M')
  else
    last_str="未起動"
  fi
  pend=""
  [ -f "$pending" ] && pend=" (pending)"
  echo "$role: $last_str$pend"
done
```

### .gitignore の判断

`logs/reviews/.pending/` と `.last-run-*` は **端末ローカル状態として gitignore**。

- 端末ごとに独立して動作させる（同期コスト削減）
- 新端末で clone したときは自動的に「全 overdue」状態から始まり、初回起動が走る
- マーカーを共有してしまうと、A 端末で起動 → push → B 端末が pull → 「もう動いた」と判断して起動しない、という穴が空く

---

## 学び・所感

- **Claude Code の hook はサブエージェントを直接起動できない**。だが「マーカーを作って Claude 本体に検知させる」二段階設計で十分実用になる。
- **コスト合理性を最優先するなら、外部スケジューラより SessionStart hook の方が筋が良い**。クラウド cron で月数百円〜数千円が発生する設計を、SessionStart 1 行で代替できる。
- **同期の対象スコープを明示的に絞ること**が重要。`git add .` ではなく `git add Agent-team/agents/` のように対象限定で stage する。これでサブツリー単位の自動同期と、リポジトリ全体の人間操作を共存させられる。
- **マーカー方式は「設計仕様 → 実装」の分離パターンの応用**。原稿レビューでも本文と仕様コメントを二重化したが、メタエージェントでも `.pending` がスペック・Agent 起動が実装、という同じ形が現れた。

---

## 適用可能な汎用パターン

このセッションから抽出した、他のプロジェクトでも使えるパターン：

1. **scope-bound auto-commit pattern**: hook で自動 push する場合、対象ディレクトリを限定して stage する（他の変更を巻き込まない）
2. **two-phase agent invocation**: hook がマーカーを作る → Claude 本体がマーカーを検知してサブエージェントを起動。hook の制約を回避しつつ、宣言的な発火条件を保つ
3. **transient state via gitignore**: 端末ローカルの状態（pending / last-run）は gitignore して各端末が独立計算。同期コスト削減と整合性のトレードオフでは独立計算の方が破綻しにくい

---

参考：
- `git pull --ff-only` の挙動：上流に新コミットがあるが自分は新しいコミットを持っていない場合だけ自動マージ。divergence や untracked changes があれば中止
- Claude Code の hook 仕様：`PreToolUse` / `SessionStart` / `SessionEnd` などのイベントで、シェルコマンドを順次実行できる。matcher で対象ツールを絞り込み可能
