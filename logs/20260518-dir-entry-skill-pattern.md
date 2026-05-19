# Directory Entry Files Skill — INDEX.md (AI) + README.md (Human)

## Context

Long-running projects (especially those with mixed AI/human collaborators) accumulate scattered conventions, log formats, and onboarding rituals. New AI agents starting a session waste time re-discovering structure; new human teammates miss critical operational rules buried in commit history.

Two existing conventions partially address this:

- `README.md` — universally adopted, optimized for human onboarding
- `CLAUDE.md` / `AGENTS.md` — AI-specific instructions, but mixed with project-specific rules and often grow unwieldy

Neither cleanly separates "navigation/index" from "narrative".

## Pattern

Place **two entry files** at every working directory root:

| File | Reader | Primary content |
|---|---|---|
| `INDEX.md` | AI agents | frontmatter, file responsibility map, naming conventions, related skills, latest-state snapshot, urgent alerts |
| `README.md` | Humans | purpose, quickstart table, operational rules, status snapshot, "what NOT to put here" |

Key separation rule: the two files **link** to each other, but do **not duplicate**. Structural information lives in INDEX. Narrative / operational rules live in README. Each file's first line tells the other audience where to go.

## INDEX.md structure (AI-facing)

```markdown
---
type: ai-index
generated: <yyyy-mm-dd>
project: <name>
project_type: <local-repo | gdrive-sync-pj | personal-workspace | etc>
visibility: <PUBLIC | PRIVATE | local-only>
canonical_path: <abs path>
---

# INDEX — AI エージェント向け案内

## エントリポイント（先に読むべき順）
1. <file> — <one-line purpose>
...

## ディレクトリ構造（責務マップ）
| パス | 責務 | 主な形式 |

## ファイル命名・形式の規約

## 関連スキル

## 直近の状態（生成時点のスナップショット）

## 緊急アラート

## このディレクトリで「やってはいけないこと」

## 関連外部リソース
```

The frontmatter is the critical piece — it lets an agent decide in 5 lines whether this directory is in scope, what visibility rules apply, and whether the snapshot is stale.

## README.md structure (human-facing)

```markdown
# <Project Name>

<one-line purpose>

> AI agents should read INDEX.md first.

## 目的
## ディレクトリ構成
## クイックスタート（やりたいこと → コマンド の表）
## ローカル機密境界（ここに置かないもの）
## ステータス（<date> 時点）
## 運用ルール
## メンテナンス
```

The quickstart table is the highest-value section for humans — it converts "what should I do?" into a single column of commands. The status section dates the snapshot so readers know how fresh the rest is.

## Skill implementation

A reusable `/dir-entry [path]` skill that:

1. Examines target directory state (`ls`, detects project type heuristically)
2. Reads existing `README.md` — **preserves** human-authored sections (purpose, license, prohibited content, operational rules) while **regenerating** sections that decay over time (directory tree, status snapshot, recent activity)
3. Generates `INDEX.md` from scratch (machine-friendly, can be regenerated freely)
4. Writes both files, reports diff summary

Project type detection uses simple heuristics:
- `package.json` → Node/JS
- `pyproject.toml` / `requirements.txt` → Python
- path contains `CloudStorage/GoogleDrive-*` → cloud sync workspace
- presence of `operations/log.jsonl` + `handoff/` + `strategy/` → business pipeline structure

## Why this works

- **AI agents get a fast on-ramp**: frontmatter + entry-point list = ~30 seconds to orient
- **Humans get a clean README**: not polluted with machine-only metadata
- **Re-runnable**: regenerate INDEX.md any time without losing human-authored README content
- **Conventions surface**: naming rules, prohibited content, agent-handoff patterns all live in one discoverable place per directory

## Applicable patterns

1. **Split machine-facing vs human-facing docs** — same applies to API docs vs developer guides, schema files vs ER diagrams
2. **Time-stamped state snapshots in long-lived docs** — `generated:` frontmatter + status section make staleness visible without manual nagging
3. **Preserve-and-augment for evolving READMEs** — never blow away human content; only refresh the parts that demonstrably decay
4. **Entry-point ordering instead of flat file lists** — tell readers what to read **first**, not just what exists
5. **Per-directory `INDEX.md` for multi-project repos** — applies recursively to subdirectories that hold their own coherent scope

## Non-goals

- Replace `CLAUDE.md` / `AGENTS.md` at repo root (those carry rules; INDEX is per-directory navigation)
- Auto-update on every file change (intentional manual re-run keeps the snapshot deliberate)
- Generate exhaustive file lists (would defeat the "entry points" purpose)
