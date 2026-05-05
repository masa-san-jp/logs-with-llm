# Claude Code: CLAUDE.md のスリム化と再利用可能スキルへの切り出し

作業日: 2026-05-01（同日午後）
作業者: Aiko エージェント（Claude Sonnet 4.6, override 人格）
目的: 個人運用のエージェント管理リポジトリで、CLAUDE.md に蓄積した手続き的記述を再利用可能なスキル（slash command）として切り出し、CLAUDE.md は「絶対必要なルール」だけを保つ構造に整理する

---

## 背景

午前中の作業で `/sync` `/meta` `/log-push` といった複合コマンドを追加した結果、各エージェントの CLAUDE.md にトリガー検知ルール・手順説明・コマンド詳細が積み上がってきた。180 行を超えた CLAUDE.md もあり、「セッション開始時に読み込む context」としては重い。

設計コンセプトを再確認した：

- **CLAUDE.md** = 絶対必要なルールだけのコンパクトな起動原則
- **skills** = 柔軟に組み合わせ可能な多様なコンテキスト

この方針で再構成した。

---

## 切り出し対象の発見

各 CLAUDE.md を点検し、スキル化候補を 4 つ抽出した。

| 優先度 | 改善箇所 | 削減行数 | 作業コスト |
|---|---|---|---|
| 高 | persona コマンド詳細圧縮 | -50 | 小 |
| 高 | /log-push トリガー検知圧縮 | -64 | 小 |
| 中 | メタエージェント自動起動 → /run-meta-pending | -18 | 中 |
| 低 | 起動シーケンス → /startup | -35 | 中 |
| 追加 | 終了シーケンス → /teardown | -25 | 中 |

判定基準は次の 3 つに絞った：

1. **複数の CLAUDE.md に同じ内容が重複**しているか（重複削減）
2. **手順記述が中身**で、それを Claude が CLAUDE.md とは別経路で読めるか（外出しの安全性）
3. **エージェント固有の核**（役割定義・行動指針・戦術フレームワーク）でないか（CLAUDE.md に残すべきか）

「3」が「No」なら切り出し可能、と判定した。

---

## 設計：スキルの粒度

切り出す側のスキルは、CLAUDE.md からの呼び出しが 1 行で済む粒度にした。

### before（CLAUDE.md 内）

```
## 起動時に必ずやること（順番厳守）
1. `local-workspace/logs/<agent>/_recent.jsonl` の直近エントリを読む
2. `agents/<agent>/rules.json` を読む
3. `agents/<agent>/skills/` と `skills/` のスキル一覧を確認する
4. `local-workspace/input/` の未処理ファイルを確認する
```

### after（CLAUDE.md 内）

```
## 起動時手順

`agents/.claude/skills/startup/SKILL.md` の手順を `<agent>=cfo-fpa` で実行する。
```

CLAUDE.md は「何を・誰として実行するか」だけを残し、「どう実行するか」は SKILL.md に集約する。

---

## トリガー検知ルールの圧縮

`/log-push` のトリガー検知（明示・文脈両対応）は、各 CLAUDE.md に 35 行の詳細列挙がそのまま入っていた。

### before（35 行）

```
## /log-push トリガー検知

### 明示的な起動
- /log-push
- log-push（スラッシュなし）

### 文脈による起動
両方を含む発話：
- セッション終了表現（5 例列挙）
- ログ or push 言及（5 例列挙）

例（起動する）4 件
例（起動しない）3 件

判断に迷う場合は確認質問
```

### after（3 行）

```
## /log-push トリガー検知

明示の `/log-push` または `log-push`（スラッシュなし）に加え、「セッション終了表現」と「ログまたは push の言及」の両方を含む発話で起動。詳細は `.claude/skills/log-push/SKILL.md` 参照。

判断に迷う場合は「`/log-push` を実行しますか？」と 1 行確認してから起動。
```

詳細パターン列挙は SKILL.md の `description` フィールドと本文に移し、トリガー判断のロジック（「両方を含む」「迷ったら確認」）だけを CLAUDE.md に残した。

---

## 結果

### 行数

| ファイル | 圧縮前 | 圧縮後 | 削減 |
|---|---|---|---|
| persona CLAUDE.md | 180 行 | 120 行 | -60 |
| business agents root CLAUDE.md | 72 行 | 29 行 | -43 |
| 業務エージェント 6 件 | 計 -28 行 | | |
| **合計** | | | **約 144 行** |

### 新設スキル

- `/run-meta-pending` — pending マーカー検知 → サブエージェント並列起動 → 後始末
- `/startup <agent>` — 業務エージェントの標準起動シーケンス
- `/teardown <agent> [--peer-review]` — 業務エージェントの標準終了シーケンス

既存スキルは：

- `/sync [pull|push|status]` — GitHub 双方向同期
- `/meta [reviewer|scout|lab|janitor|all]` — メタエージェント手動起動
- `/log-push` — 横断的なログ書き出し + GitHub push

合計 6 スキルで、CLAUDE.md からの参照は 1 行ずつ。

---

## メタエージェント並走

CLAUDE.md スリム化と並行して、未消化だった日次メタエージェント 4 件（reviewer / scout / lab / janitor）を初めて並列起動した。Agent ツールで `subagent_type=<role>` 指定で 4 件同時実行。

結果（合計 20 findings、24 backlog タスク起票）：

- **reviewer**：6 findings（high 2 / med 1 / low 3）。ログフォーマット異常 2 件が high
- **scout**：4 findings。SDK の新ベータ機能（永続メモリ）と MCP 仕様 PR 2 件
- **lab**：5 findings + 2 extractions。複数エージェントに散在する「spec-before-action」骨格を共通化提案
- **janitor**：5 findings、削除実行は禁止のため提案のみ。リポジトリサイズ 0.57MB

並列実行の所要時間は約 35 分（最長エージェント基準）。順次実行だったら 80 分以上かかっていたはず。

---

## 学び・所感

### 「定義」と「手続き」を分離する

CLAUDE.md には **「私は何者か・どの基準で判断するか」** だけを書く。**「どうやって実行するか」** は別ファイルに切り出す。これが context window の節約と保守性の両立に効く。

エージェント定義は変わらない。手続きは変わる（ファイルパスが変わる、ステップが増える）。**変動率が違うものを同じファイルに置かない**。

### スキル化の閾値

すべての手続きをスキルにすべきではない。次の場合だけスキル化した：

- **複数の CLAUDE.md に重複**している（重複削減）
- **行数が 5 行以上**（CLAUDE.md に直接書くと context が膨らむ）
- **将来も使う**（一度きりの作業はスキル化しない）

5 行以下の単発手続きは CLAUDE.md にそのまま残した方が、参照のオーバーヘッドが上回る。

### マニフェスト的な序文

各スキルファイルの先頭に description（YAML frontmatter）を入れる仕様は、Claude にとっても便利だが、人間が読むときの目印にもなる。

```yaml
---
name: startup
description: Run the standard startup procedure for a business agent...
---
```

「このスキルが何をするか」を 1 文で書く制約が、作る側にも使う側にも判断のショートカットを提供する。

---

## 適用可能な汎用パターン

このセッションから抽出した、他のプロジェクトでも使えるパターン：

1. **definition-vs-procedure pattern**：エージェント／システムの「定義」（ID・役割・基準）と「手続き」（手順・コマンド・トリガー）を別ファイルに分ける。前者は安定、後者は変動するため、混在させると保守コストが膨らむ
2. **trigger detection delegation**：トリガー検知のキーワード列挙は SKILL.md の description に集約し、CLAUDE.md には判断ロジック（「両方を含む」「迷ったら確認」）だけを残す。これで誤発火条件の調整が SKILL.md 内で完結する
3. **parallel sub-agent fanout**：独立した分析タスク（reviewer / scout / lab / janitor）は単一の親セッションから並列起動する。順次実行に対し所要時間 1/N、コンテキスト分離もできる

---

参考：
- Claude Code skills 仕様：`.claude/skills/<name>/SKILL.md` に description（YAML frontmatter）+ 本文。`description` の文言が Claude のスキル選択に直接影響する
- Agent ツールの並列起動：単一の AI message 内で複数の Agent tool_use を含めると並列実行される

---

## 実装状況追記（2026-05-05 確認）

このログで提案した内容は **すべて実装済み**。

| 項目 | 状態 |
|---|---|
| `/run-meta-pending` スキル | ✅ `agents/.claude/skills/run-meta-pending/` |
| `/startup` スキル | ✅ `agents/.claude/skills/startup/`（grant 用拡張も対応済み） |
| `/teardown` スキル | ✅ `agents/.claude/skills/teardown/` |
| `/sync` `/meta` `/log-push` 既存スキル | ✅ 同ディレクトリに存在 |
| business agents root CLAUDE.md スリム化 | ✅ 29 行（log の目標通り） |
| 業務エージェント 6 件のスリム化 | ✅ 58〜87 行（cfo-fpa 77 / hr 59 / logi-ops 87 / marke-sales 75 / pr-brand 58 / r-d 74） |
| Aiko CLAUDE.md スリム化 | ✅ 23 行 |

なお、log 作成後に追加された **grant エージェント** にも同パターンを適用：

- 206 行 → 128 行（**-38%**）
- 圧縮内訳：ディレクトリ構成（33→2 行、`docs/SPEC-INDEX.md` 参照）、起動時手順（11→7 行、`/startup grant` ＋固有3手順）、使うスキル一覧（34→11 行、grant 固有のみ）、設計上の制約（24→10 行、5項目ヘッドライン＋docs 参照）、終了時手順（7→7 行、`/teardown grant` ＋固有処理）
- 保持：Phase 1/2 起動主体、データ分離原則、抽象タイトル運用、端末ごとの動作モード（grant の核は変更なし）
- `/startup` SKILL.md 側に「grant エージェントは Phase 確認や local-bindings 存在確認を追加で行う」という拡張ポイントが事前に明記されていたため、追加スキル作成は不要だった

