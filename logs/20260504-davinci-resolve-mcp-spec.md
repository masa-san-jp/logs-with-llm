# resolve-mcp-safe — 構築サマリー

> 安全性・信頼性・保守性のベストプラクティスを組み合わせた DaVinci Resolve MCP サーバーを、個人開発成果物として実装した。

成果物：<resolve-mcp-safe.zip>（51 ファイル、約 118 KB）

-----

## 既存実装の課題に対する具体的回答

前回の調査で挙げた問題と、本プロジェクトでの対処を 1:1 で対応させた：

|既存実装の課題                       |本プロジェクトでの対処                                   |
|------------------------------|----------------------------------------------|
|`execute_resolve_code` が無条件で有効|**意図的に実装しない**。Resolve API の特定メソッドのみツール化       |
|破壊的操作と読み取り操作が同じ層              |3 層の権限モデル（safe/standard/full）+ 環境変数で制御        |
|監査ログがない                       |全ツール呼び出しを JSONL で記録（パラメータ・結果・所要時間・セッションID）    |
|入力検証が系統的でない                   |Pydantic v2 で全パラメータをバリデーション                   |
|パストラバーサル対策が不十分                |必須の allowlist + シンボリックリンク解決後の containment チェック|
|リリース署名がない                     |Sigstore で全アーティファクトを署名、SBOM を CycloneDX で同梱   |
|開発者が新ツール追加時に権限を忘れる            |CI ガード（AST スキャン）が `@requires_level` の付け忘れを検出  |

-----

## プロジェクト構成（51 ファイル）

```
resolve-mcp-safe/
├── README.md                  # 利用者向けドキュメント
├── SECURITY.md                # 脆弱性報告ポリシー
├── CONTRIBUTING.md            # 貢献ガイド
├── CHANGELOG.md               # 変更履歴
├── LICENSE                    # MIT
├── pyproject.toml             # 依存定義（バージョン上下限を明示）
├── .pre-commit-config.yaml    # pre-commit フック
├── docs/
│   ├── ARCHITECTURE.md        # レイヤ構成と設計判断
│   ├── THREAT_MODEL.md        # STRIDE による脅威モデル
│   └── AUDIT_GUIDE.md         # 第三者がコードを審査する手順
├── src/resolve_mcp_safe/      # 実装本体（約 1,000 行）
│   ├── server.py              # FastMCP 構築
│   ├── connection.py          # Resolve 接続管理
│   ├── permissions.py         # 権限レベル + デコレータ
│   ├── audit.py               # JSONL 監査ログ
│   ├── validators.py          # Pydantic + パス検証
│   ├── errors.py              # 例外階層
│   ├── tools/                 # 22 ツール
│   └── resources/             # 3 リソース
├── tests/
│   ├── conftest.py
│   └── unit/                  # パーミッション・パス検証・監査の単体テスト
├── scripts/
│   └── check_tools_decorated.py  # CI ガード
└── .github/
    ├── dependabot.yml
    └── workflows/
        ├── ci.yml             # テスト・lint・型・CIガード
        ├── security.yml       # CodeQL・bandit・pip-audit・SBOM
        └── release.yml        # 署名つきリリース
```

-----

## 透明性確保の仕組み（コード審査手続き）

利用者が「この個人プロジェクトを信頼できるか」を独立に検証するための手段を多層で用意：

### 1. リリース完全性の暗号学的検証

```bash
sigstore verify identity \
  --bundle resolve_mcp_safe-0.1.0.whl.sigstore \
  --cert-identity "https://github.com/USERNAME/.../release.yml@refs/tags/v0.1.0" \
  --cert-oidc-issuer "https://token.actions.githubusercontent.com" \
  resolve_mcp_safe-0.1.0.whl
```

→ ビルドが特定タグから GitHub Actions 経由で生成されたことを暗号学的に証明。中間者攻撃や偽配布を検出可能。

### 2. SBOM（CycloneDX）

全リリースに `sbom.cyclonedx.json` を同梱。依存パッケージの完全リストと CVE 照合に使える。

### 3. 静的解析を CI で公開実行

- **CodeQL**：security-extended クエリ
- **Bandit**：Python 固有のセキュリティパターン検出
- **pip-audit**：依存パッケージの既知 CVE スキャン
- **mypy strict**：型整合性
- **ruff (security 含む)**：lint 全般

### 4. AST ベースの CI ガード

`scripts/check_tools_decorated.py` が全 `@mcp.tool` 関数に `@requires_level` があることを AST で検証。**手動レビューに頼らない構造的保証**。

実行例：

```
$ python3 scripts/check_tools_decorated.py
OK: all @mcp.tool functions have @requires_level.
```

### 5. AUDIT_GUIDE.md

所要 30 分〜1 時間で第三者がコード審査できる手順書を同梱。grep ベースのチェックリスト・テスト実行手順・依存パッケージ検証手順を含む。

### 6. THREAT_MODEL.md

STRIDE 分類で各脅威への対策を明示。「なぜこの設計か」を文書化することで、レビュアーが意図を読み取りやすい。

-----

## 実装した機能（前回調査からの取り込み）

前回挙げた DaVinci Resolve MCP の主要機能を、安全な形で再実装：

### Resources（読み取り専用）

- `resolve://status` — Resolve バージョン・現在ページ
- `resolve://project/current` — プロジェクト情報
- `resolve://timeline/current` — タイムライン情報

### Tools（22 個）

|Level          |ツール                                                                                                                                                                                                                                     |
|---------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|safe           |`get_resolve_version`, `get_current_project`, `list_projects`, `list_timelines`, `get_current_timeline`, `list_media_pool_clips`, `get_media_pool_structure`, `get_render_queue_status`, `list_render_presets`, `get_current_color_clip`|
|standard       |`open_project`, `create_project`, `create_timeline`, `set_current_timeline`, `add_marker`, `create_bin`, `import_media`, `add_to_render_queue`, `add_serial_node`, `apply_lut`                                                          |
|full（要 confirm）|`save_project`, `delete_timeline`, `start_rendering`                                                                                                                                                                                    |

### 提案ワークフローへの対応

前回のワークフロー提案 8 つに対する実装状況：

|ワークフロー               |必要なツール                                  |実装状況                    |
|---------------------|----------------------------------------|------------------------|
|1. バッチインポート＋ビン整理     |`create_bin`, `import_media`            |✅                       |
|2. マーカー一括打ち          |`add_marker`                            |✅                       |
|3. カラーノード自動テンプレート    |`add_serial_node`, `apply_lut`          |✅                       |
|4. レンダーキュー組み立て       |`add_to_render_queue`, `start_rendering`|✅                       |
|5. 台本→タイムライン自動組み     |`create_timeline`, `import_media`       |✅                       |
|6. メタデータ整理           |`list_media_pool_clips`                 |部分的（メタデータ書き込みは v0.2 で予定）|
|7. 納品ファイル検証          |クライアント側で実行                              |クライアント責務                |
|8. CLAUDE.md による設定永続化|クライアント側で実行                              |クライアント責務                |

-----

## 公開時のチェックリスト

実際に GitHub に公開する際の手順：

```
□ GitHub リポジトリ作成（Public）
□ Branch protection ルール設定（main への直接 push 禁止、PR レビュー必須、CI 通過必須）
□ Dependabot を有効化
□ Code scanning（CodeQL）を有効化
□ Secret scanning を有効化
□ Private vulnerability reporting を有効化
□ SECURITY.md のメールアドレスと PGP 鍵フィンガープリントを実値に置換
□ pyproject.toml の作者情報・URL を実値に置換
□ LICENSE の著作権表示を実名に置換
□ uv.lock を生成してコミット（uv lock --upgrade）
□ 初回リリースは v0.1.0 タグを切る → release.yml が自動で署名つき配布
□ README のバッジ URL を実リポジトリパスに更新
```

-----

## 制約事項

正直に列挙：

1. **実機テストは未実施**：本構築はソースコードと CI 設定の整備までで、実際の DaVinci Resolve に接続した end-to-end テストは行っていない。`tests/integration/` 配下に実機テストを追加する作業が公開前に必要。
1. **依存パッケージの完全な lock**：`uv.lock` は実環境で `uv lock` を実行して生成する必要がある。本構築には含めていない。
1. **Resolve API のカバレッジ**：22 ツールは主要操作のみ。samuelgursky 版の 354 ツール相当のカバレッジには至っていない。Issue 駆動でホワイトリストを拡張していく方針。
1. **PGP 鍵**：SECURITY.md にプレースホルダーのみ。実際に運用するなら鍵の生成と公開鍵サーバーへのアップロードが必要。
1. **Windows 実機での動作確認**：CI には Windows runner を含めているが、Resolve 接続部分は実機検証が必要。