# 並行ターミナル作業の衝突検知 CLI を設計した — TermGuard

複数のターミナル / Claude Code セッションを開いて並行作業していると、別セッションが同じ `cwd` や同じファイルを編集してしまい、変更が上書きされる事故が起きやすい。これを防ぐための軽量 CLI として **TermGuard** を設計・実装した記録。

## 背景：peer-inbox との棲み分け

同じ「複数ターミナル協調」領域でも目的が違う：

| ツール | 目的 | 通信方向 |
|---|---|---|
| peer-inbox | セッション間の**メッセージ交換**（依頼・通知） | 双方向、明示送信 |
| TermGuard | セッション間の**リソース衝突検知**（事故防止） | 受動、自動検知 |

peer-inbox は「相手に何かを伝える」、TermGuard は「相手が何を握っているか観測して警告する」。

## 設計の核：JSON ファイルだけで状態管理

DB も daemon もサーバープロセスも持たない。各セッションが自分の状態を 1 ファイルとして書き出し、互いに読み合う：

```
~/.termguard/sessions/<uuid>.json
```

ペイロードは以下のような最小構成：

```json
{
  "id": "uuid",
  "name": "api-server",
  "pid": 12345,
  "cwd": "/path/to/project",
  "resources": ["cwd:/path/to/project", "port:3000"],
  "started_at": 1715000000.0,
  "updated_at": 1715000010.0
}
```

これだけで「誰が今どこで作業中か」を全セッションが共有できる。

## 採用したパターン 5 つ

### 1. PID 死活で自動掃除

セッション JSON を読み込むたびに `os.kill(pid, 0)` で生存確認し、死んだセッションのファイルは即削除する：

```python
def is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # 別ユーザー所有でも生きてはいる
    return True
```

クラッシュ放置でゴミセッションが残らない。daemon を持たないツールでは必須のテクニック。

### 2. リソースの正規化（プレフィックス + 絶対パス）

ユーザーが `cwd:.` と書いても `cwd:/abs/path` と書いても同じものを指す必要がある。プレフィックスごとに処理を分岐する：

```python
def normalize_resource(resource: str) -> str:
    if ":" in resource:
        kind, value = resource.split(":", 1)
        if kind in {"cwd", "file", "path"}:
            return f"{kind}:{Path(value).expanduser().resolve()}"
        if kind in {"port", "branch", "build", "job"}:
            return f"{kind}:{value}"
    return f"raw:{resource}"  # 未知プレフィックスはフォールバック
```

`raw:` フォールバックを置くことで、新しいリソース型を後から拡張しても既存呼び出しが壊れない。

### 3. 差分通知（同じ衝突状態は無視）

ポーリングごとに通知を出すと連打になる。**直前と同じ衝突状態なら通知を抑制**する：

```python
last_signature = None
while True:
    conflicts = detect_conflicts(...)
    signature = tuple((other.id, tuple(overlap)) for other, overlap in conflicts)
    if signature != last_signature:
        last_signature = signature
        if conflicts:
            notify(...)
    time.sleep(interval)
```

衝突相手や対象リソースが変わったときだけ通知が飛ぶ。「うるさくないが見落としもしない」を実現する定石。

### 4. 状態ストアは環境変数で差し替え可能

```python
def state_root() -> Path:
    base = os.environ.get("TERMGUARD_HOME")
    if base:
        return Path(base).expanduser()
    return Path.home() / ".termguard"
```

テスト時に `TERMGUARD_HOME=/tmp/test pytest` で隔離できる。CLI ツールに `XXX_HOME` 環境変数を 1 個用意するだけで、テスタビリティとマルチアカウント運用が両立する。

### 5. 通知のフォールバック

macOS の通知は `osascript` でネイティブ表示するが、見つからない環境ではターミナルベルに降格する：

```python
try:
    subprocess.run(["osascript", "-e", script], check=False, ...)
except FileNotFoundError:
    print("\a", end="", file=sys.stderr)
```

`check=False` + `FileNotFoundError` 捕捉で「鳴らせない環境でも落ちない」を保証する。

## サブコマンド設計

| コマンド | 役割 |
|---|---|
| `run -- <cmd>` | コマンドをラップ実行しながら監視（子プロセス管理 + ポーリング） |
| `watch` | コマンドを動かさずターミナルだけ占有予約（エディタ作業など） |
| `status` | 全セッション一覧 + 衝突マトリクス表示 |
| `stop` | セッションカードを手動削除 |

`run` と `watch` を分けたのは、「コマンド実行時の自動衝突検知」と「人間が対話的に作業する区間の予約」が UX として別物だから。

## 適用可能な汎用パターン

- **JSON ファイルだけで状態共有する軽量プロセス間調整** — DB / daemon / サーバーを持たないツールで「誰が今何を握っているか」を共有したいときの最小構成。PID 死活チェックとセットで使う
- **リソース識別子のプレフィックス + 絶対パス正規化** — `kind:value` 形式 + `raw:` フォールバックで、後方互換を保ったまま新リソース型を追加できる拡張点を作れる
- **差分検知による通知抑制** — ポーリング型ツールで「状態が変わった瞬間だけ通知」を実現するには、直前の状態を tuple 化して `last_signature` と比較するだけで十分

## 公開先

- リポジトリ: `github.com/masa-san-jp/termguard`
- ライセンス: MIT
- 対象: macOS（`os.uname()` + `osascript` 前提）
