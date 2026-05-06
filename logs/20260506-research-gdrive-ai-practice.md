# Google Drive AI運用ベストプラクティス

-----

## 1. ファイル操作の安全設計

### 絶対に守るルール

|操作  |NG                  |OK                                                  |
|----|--------------------|----------------------------------------------------|
|移動  |copy→delete         |`files.update(addParents / removeParents)` でアトミックに移動|
|削除  |`files.delete` を直接実行|`files.trash` でゴミ箱へ（履歴・共有設定を保持）                     |
|リネーム|新規作成→旧削除            |`files.update(name=...)` で上書き                       |

**copy→deleteを使わない理由**

- ファイルIDが変わる → 共有リンクが全て死ぬ
- リビジョン履歴が消える
- コメント・承認フローが消える
- 共有設定が引き継がれない

### Destructive操作の承認フロー

```
AI → 候補リスト生成（削除・移動対象）
  → 人間が承認
    → 実行（trash使用）
```

AIに直接 `files.delete` を実行させない。承認ステップを必ず挟む。

-----

## 2. フォルダ構造設計

### 基本構造

```
📁 MyDrive/
├── 📄 _INDEX.md              ← ルートインデックス（全体マップ）
├── 📄 _AI_RULES.md           ← ルートレベルのAI行動規範（越権人格）
│
├── 📁 ProjectA/
│   ├── 📄 _ai.md             ← ProjectA専用の交通誘導ルール
│   └── ...
│
├── 📁 ProjectB/
│   ├── 📄 _ai.md
│   └── ...
│
└── 📁 Archive/
    ├── 📄 _ai.md             ← 「読み取り専用。移動・削除禁止」と明記
    └── ...
```

### ルートインデックス（`_INDEX.md`）の内容

```markdown
# Google Drive インデックス

## フォルダ一覧
| フォルダ | 用途 | AIの操作権限 |
|---|---|---|
| /ProjectA | ○○プロジェクト | 読み書き可 |
| /ProjectB | △△プロジェクト | 読み書き可 |
| /Archive  | 過去案件アーカイブ | 読み取りのみ |
| /Private  | AIアクセス禁止 | 禁止 |

## 更新日
YYYY-MM-DD
```

-----

## 3. ai.mdの設計

### 各フォルダのai.mdに必ず書くこと

```markdown
# [フォルダ名] AI操作ガイド

## このファイルについて
- このファイル自体を編集・削除・移動してはいけない
- 読み取り専用の指示書

## 操作権限
- 許可: [具体的な操作を列挙]
- 禁止: このフォルダ外への操作、削除（trash以外）

## フォルダ構成
[このフォルダ内の構成説明]

## 命名規則
[ファイル・フォルダの命名ルール]

## 禁止事項
- copy→deleteによる移動
- files.deleteの直接実行
- このai.mdの変更
```

### ai.md自体を守る工夫

- ファイル名をドット始まりにする（`.ai_rules.md`）→ 一般的なファイル操作で見落としにくい
- ai.mdの冒頭に「このファイルを編集・削除しないこと」を**最初の行**に記載
- Google Driveのファイルに「コメント可・編集不可」の共有設定をかけておく（人間側の誤操作防止も兼ねる）

-----

## 4. 権限境界の設計

### 人格レイヤー

```
_AI_RULES.md（ルート）
  └── 越権人格（事務・整理・横断検索など）
      └── 操作できるフォルダを許可リストで明示

/ProjectA/_ai.md
  └── ProjectA専用人格
      └── /ProjectA 以外には触れない

/Archive/_ai.md
  └── 読み取り専用人格
      └── 書き込み・削除・移動は全て禁止
```

### ルートai.mdの越権人格に書くべき制限

```markdown
## 操作可能フォルダ（許可リスト）
- /ProjectA
- /ProjectB
- /Shared

## 絶対に触れないフォルダ
- /Private
- /Archive（読み取りのみ）

## 横断操作時のルール
1. 操作前に対象フォルダのai.mdを必ず読む
2. 移動はfiles.update(addParents/removeParents)のみ
3. 削除はfiles.trashのみ、files.deleteは使用禁止
4. 操作ログを都度報告する
```

-----

## 5. ログ・監査設計

### AIに操作ログを出力させる

```markdown
## 操作ログフォーマット（AIへの指示）
操作を実行した場合は以下の形式で報告してください：

- 日時: 
- 操作種別: [移動/リネーム/trash/作成]
- 対象: [ファイルID or パス]
- 実行前の状態:
- 実行後の状態:
- 理由:
```

### 定期チェック

- 月1回、`_INDEX.md`と実際のフォルダ構造を突き合わせる
- ゴミ箱を定期確認（AIがtrashした分が溜まる）
- 意図しない共有が発生していないか確認

-----

## 6. Google Drive APIの安全な使い方

### 移動（アトミックに実行）

```python
service.files().update(
    fileId=file_id,
    addParents=new_folder_id,
    removeParents=old_folder_id,
    fields='id, parents'
).execute()
```

### 削除（trashを使う）

```python
# NG
service.files().delete(fileId=file_id).execute()

# OK
service.files().trash(fileId=file_id).execute()
```

### 確認してから実行するパターン

```python
# 1. 対象を検索・リストアップ
# 2. 操作内容を人間に提示
# 3. 承認を得てから実行
# 4. 実行結果をログに記録
```

-----

## まとめ：チェックリスト

- [ ] `files.delete`ではなく`files.trash`を使う
- [ ] 移動は`addParents/removeParents`でアトミックに行う
- [ ] 各フォルダに`_ai.md`を配置する
- [ ] `_ai.md`自体に「このファイルを編集・削除禁止」を明記する
- [ ] ルートに`_INDEX.md`を置き許可フォルダを列挙する
- [ ] AIのdestructive操作に必ず人間の承認ステップを挟む
- [ ] 操作ログを残す運用にする
- [ ] Archiveなど触れてはいけないフォルダを明示的に禁止リストに入れる