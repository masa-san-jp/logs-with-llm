# aiko-note/

Aiko の観察日記。日々の気づき・判断・学びを時系列で蓄積する場所。

旧名：`observations/`。2026-06-06 にリネーム。

## ファイル形式

```
aiko-note/
└── YYYYMMDD-aiko-note.jsonl
```

- 1 日 1 ファイル、JSON Lines 形式
- 書き込みは append-only
- Markdown ではなく JSONL：append が安い・部分読みが安い・トークン節約・パース容易

## エントリのスキーマ（5W1H 必須）

```jsonc
{
  "ts":    "2026-06-06T15:30+09:00",         // when（ISO 8601・JST）
  "who":   "masa-san",                        // who（主体・誰が）
  "where": "Agent-Lab/.../telegram/",         // where（場所・どこで）
  "what":  "rules ディレクトリの整備を指示",  // what（何を）
  "how":   "対話で要件確定 → 即実装",         // how（どう・方法）
  "why":   "CLAUDE.md チャネル依存撤去が動機",// why（理由・あれば）
  "tag":   ["telegram","rules"],              // 任意・分類タグ配列
  "refs": [                                    // 任意・URL or path 配列
    "https://github.com/masa-san-jp/Agent-Lab/commit/89209d6"
  ],
  "sent": false                                // bool・Telegram で共有済みか
}
```

必須フィールド：`ts` / `who` / `where` / `what` / `how`。1 つでも欠けたら書かない（未来の自分が解釈不能になる）。

## いつ書くか

- 何か **判断・実装・学び・気づき** があった瞬間
- マサさんとの会話で新しい情報を得たとき
- リポ間で違和感に気づいたとき
- 自分自身の挙動に学びがあったとき

書かないこと：

- 普通の応答（受け答えだけ）
- 重複（既に書いた観察と同じ内容）
- 確証のない推測（書くなら `who: "speculation"` で明示）

## いつ読むか

- Telegram モードのセッション開始時：当日や直近 N 日の note を tail で読む
- マサさんが「最近どうだった？」と聞いたとき：grep / jq で検索
- 同じ問題で迷ったとき：tag / where で絞って検索

## Telegram で共有

各エントリの `sent: false/true` で管理。
書いた直後はデフォルト `false`、マサさんに送ったら `true` に更新。

## 仕様の正本

このファイル（README）はサマリ。正本は Agent-Lab 側にある：

- 仕様：[capability/rules/aiko-note.md](https://github.com/masa-san-jp/Agent-Lab/blob/main/Agent-team/agents/aiko/.aiko/capability/rules/aiko-note.md)
- 関連 TASKS：[Agent-Lab TASKS.md](https://github.com/masa-san-jp/Agent-Lab/blob/main/Agent-team/agents/aiko/.aiko/TASKS.md) の「aiko-note 仕組みの本実装」項目
