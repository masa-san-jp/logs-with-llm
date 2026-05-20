# 既存パイプラインに「2 つ目のカレンダー source」を contract 違反せずに足す

## 結論

AI エージェント用のデータパイプラインに、**既存ソースを壊さず別系統のデータソースを並列で足す**ときのデザインパターンの記録。

題材は Google Calendar：

- 既存：workspace 主アカウントの Calendar を GAS が API で取り込み → `inbox/calendar/<YYYY-MM>.json`
- 追加：API で繋がない別アカウントの Calendar を、手動 `.ics` export 経由で取り込みたい

このときに陥りがちな「既存スロットに第二アカウントを混ぜ込む」案を採らず、**別 source として並列追加**することで pipeline 規約（`bound_to` 制約）を守ったまま拡張する。

ファイル名は `20260519-calendar-external-second-source-pattern.md`。

---

## 前提となる pipeline 規約（AGENT_CONTRACT.yaml）

データ取り込み側で AI が触る規約のうち、本件で効くのは以下：

```yaml
source_bindings:
  rules:
    - source: calendar
      bound_to: workspace.drive_account
      note: "workspace の Drive アカウントの calendar しか取り込まない"

source_modes:
  calendar: { mode: canonical, partition: monthly_by_start_time }

fetch_policy:
  per_source:
    calendar:
      window:
        backward_days: 7
        forward_days: 365
```

つまり「**`inbox/calendar/` は workspace 主アカウント専用のスロット**」というガバナンス境界が contract レベルで宣言されている。ここに API 認証も権限も異なる別アカウントのデータを混ぜ込むのは「同じ名前の source に複数 origin を詰める」ことになり、後で取り込みエージェント・読み出し側 skill の両方が複雑化する。

---

## 設計判断（5 点）

### 1. 既存 source への追加ではなく、別 source として並列に置く

| 案 | 評価 |
|---|---|
| 既存 `calendar` に第二アカウントを足す（`bound_to` を配列化など） | ❌ contract の本来の意味（workspace 専用）が壊れる |
| **別 source `calendar_external` を作って並列に置く** | ✅ 採用。contract 上のガバナンス境界が綺麗に分かれる |

選定理由：

- **OAuth 認証問題を回避**：別アカウント API を叩こうとすると別 OAuth スコープが必要。手動 export なら認証拡張は不要
- **ガバナンス上の意図的分離**：「個人領域は AI パイプラインに半透膜で接続する」という方針を contract に表現できる
- **将来の origin 追加コストが低い**：iCloud / Outlook なども同じパターンで `calendar_external/<origin>/` として並べるだけ

### 2. 投入経路を既存 source 配下の subdir に統一する

これは設計を 1 度組み直した点。

最初の案：投入先 = `inbox/calendar_external/<origin>/_raw/*.ics`

→ 「ユーザー視点で .ics 関連が `calendar_external` 側に集まってしまい、既存 `calendar/` を見たユーザーが『他の場所もあるのか』を毎回思い出す必要がある」と判明。

確定案：投入先 = **`inbox/calendar/_raw/*.ics`**

```
inbox/calendar/
├── 2026-05.json …                            ← GAS が書く（不可侵）
└── _raw/                                      ← 手動 .ics 投入専用
    ├── 20260519-gmail-personal.ics
    └── 20260519-workspace-snapshot.ics
```

ポイント：

- **アンダースコア prefix の subdir** は AGENT_CONTRACT で既に「システム制御用」の規約として確立済み（`_meta/` `_config/` `_scripts/` と同じ）。GAS は `_raw/` を見ない
- 出力 JSON は引き続き `calendar_external/<origin>/<YYYY-MM>.json` に書く → contract の `bound_to` 制約は破らない
- ユーザー視点では「カレンダー関連は全部 `inbox/calendar/` を見ればよい」になり、迷子が消える

### 3. ファイル名規約で origin を自動判定する

ファイル名規約：**`<YYYYMMDD>-<origin>.ics`**

例：`20260519-gmail-personal.ics`

スクリプト側：

```python
KNOWN_ORIGINS = {
    "gmail-personal",
    "workspace-snapshot",
}
FILENAME_RE = re.compile(r"^(?P<date>\d{8})-(?P<origin>[a-z0-9][a-z0-9-]*)\.ics$")
```

- 規約違反 → exit=4 で停止しエラーメッセージに **期待形式と KNOWN_ORIGINS を併記**
- 未知 origin → 同様に停止
- ユーザーは投入時にファイル名を rename するだけ。コードに認証情報や個別アカウント情報を書かなくて済む

### 4. 個別アカウントのメアドは文書のどこにも書かない

DESIGN.md / contract / skill 定義 / コード / memory のすべてで、個別アカウントのメアドは抽象名（`gmail-personal` / `workspace-snapshot`）に置換する。

- AI が触る文書は将来 git 履歴・他リポへの転載・PR ベース共有などで広範に拡散する
- contract に「`workspace.drive_account` 以外のアカウント」「個人 Gmail カレンダー」のような **相対的記述**を採用すると、メアドが入り込む隙間が無くなる
- 例外は `workspace.drive_account` block 本体と、Drive Desktop マウントポイントの物理パス（システム命名なので削除不可）のみ

### 5. PEP 723 inline metadata + `uv run --script` でスクリプト 1 本完結に

取り込みスクリプト（.ics → JSON）は本来なら venv を切って `pip install icalendar recurring-ical-events` する流れだが、**venv ディレクトリ自体を作らない**選択肢がある：

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "icalendar>=5.0",
#     "recurring-ical-events>=2.1",
# ]
# ///
"""script body..."""
```

- shebang + PEP 723 metadata block で依存を宣言
- 初回実行で `uv` がキャッシュに解決（手元の計測で 14ms）。2 回目以降はもっと速い
- `./script.py` 1 発で走る。venv の活性化・忘却・腐敗が一切起きない
- 他人に渡すときも「`uv` だけ入れて `./script.py` を叩く」で済む

特に AI エージェントが書き散らかすツールスクリプト（取り込み・変換・検証）には強くフィットする。

---

## 実装の要点

### .ics 取り込みの核

```python
import icalendar
import recurring_ical_events

cal = icalendar.Calendar.from_ical(ics_path.read_bytes())

today = datetime.now(TZ).date()
win_start = today - timedelta(days=BACKWARD_DAYS)
win_end = today + timedelta(days=FORWARD_DAYS)

# RRULE をウィンドウ内に展開してから処理
expanded = recurring_ical_events.of(cal).between(win_start, win_end)

for comp in expanded:
    status = str(comp.get("STATUS", "")).lower()
    if status == "cancelled":
        continue
    # UID + DTSTART(suffix) で展開後の個別オカレンスを unique 化
    event_id = f"{comp['UID']}_{comp['DTSTART'].dt.strftime('%Y%m%dT%H%M%S')}"
    ...
```

ハマりどころ：

- **RRULE 展開**を忘れると週次・月次イベントが原本 1 件分しか入らない
- 展開後の各オカレンスは元の `UID` をそのまま持つ → `UID` だけでは ID が衝突する → DTSTART suffix を付ける
- 終日イベント (`DTSTART;VALUE=DATE`) は `date` 型で来るので `datetime` 前提のコードは TypeError。型分岐必須
- TZ は `LAST-MODIFIED` などが UTC で来るので、Asia/Tokyo に正規化する

### 出力スキーマは既存と互換に揃える

差分は 2 フィールドだけ：`source: "calendar_external"`, `origin: "<name>"`。

これで、読み出し側 skill は **読み込み先のループに 1 行足すだけ**で両 source を吸収できる：

```
1. inbox/calendar/<YYYY-MM>.json
2. inbox/calendar_external/*/<YYYY-MM>.json   ← 追加
```

共通スキーマ変換時に `raw._origin = <origin>` を付与しておけば、後段でフィルタも識別もできる。

### 異常系の防御

ガード対象：

- 規約違反ファイル名（`badname.ics`）→ exit=4
- 未知 origin（`20260519-unknown-origin.ics`）→ exit=4・既知 origin 一覧を提示
- empty `_raw/` ディレクトリ → exit=3

ユーザーが正しい場所に正しいファイル名で置かなければ取り込みは行われない。誤投入で混入する事故を構造的に潰す。

---

## 動作確認

ダミー .ics 1 本 + 実 .ics（workspace 主アカウントの export を別 origin として）1 本でテスト：

| ケース | 結果 |
|---|---|
| 単発イベント・終日・RRULE 展開（6 回繰り返し）・cancelled 除外 | 全パス |
| TZ 正規化（UTC → JST + 9h） | パス |
| 月別バケット（start 月で分割） | パス |
| 既存 JSON との merge（フル export 前提・空エンベロープ上書き含む） | パス |
| 未知 origin / 規約違反ファイル名 → exit=4 | パス |

`uv run --script` の初回実行で 8 パッケージを 14ms で解決して走った。venv 不要。

---

## 適用可能な汎用パターン

### Pattern 1: contract 制約を破らずに 2nd source を並列追加する

既存の `source_bindings.X.bound_to = Y` が宣言されているとき、別 origin のデータを足したい場合は **`X_external` という別 source を並列に作る**。

- 既存 source の意味（=  境界）は壊れない
- 出力スキーマだけ既存と互換に揃えれば、読み出し側 skill は最小改修で両系統を吸収できる
- 将来 origin が増えても `X_external/<新-origin>/` を並べるだけ。差分は YAML 1 ブロックと辞書 1 行

### Pattern 2: アンダースコア prefix subdir で既存スロットと衝突せずに subdomain を切る

`inbox/<source>/` などの取り込みスロットに、別経路の生データを共存させたいとき：

- `inbox/<source>/_raw/`  のように **アンダースコア prefix の subdir** を切る
- 自動取込スクリプト（GAS 等）はトップレベルファイルだけを処理するように既に書かれているケースが多く、`_raw/` は無視される
- `_meta/` `_config/` `_scripts/` などのシステム制御用 prefix と同じ視覚的シグナル

ユーザー視点では「関連ファイルは全部 `inbox/<source>/` を見ればよい」になり、subdir 違いで散らばらない。

### Pattern 3: PEP 723 inline metadata + `uv run --script` で venv 不要のスクリプト 1 本完結

AI が書き散らかすツールスクリプト（取り込み・変換・検証・1 回限りバッチ）には特に効く：

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["icalendar>=5.0", "recurring-ical-events>=2.1"]
# ///
```

- venv ディレクトリの作成・activate・腐敗・複数バージョン共存などの面倒が消える
- 渡す側は `uv` だけ前提にすれば済む
- 受け取った側は `./script.py` を叩くだけ
- 依存はスクリプト先頭で完結する → コードレビュー時に依存と本体を 1 ファイルで読める

requirements.txt / pyproject.toml / Pipfile を **作らずに済むケース**が広範に存在する。
