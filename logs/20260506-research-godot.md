# Godot Engine リサーチ

> 目的: Claude でゲームデザイン → Claude Code で開発 → GodotSteam で Steam リリース

-----

## 1. Godot Engine 概要

### 現在のバージョン

- **最新安定版: Godot 4.6**（2026年1月リリース）
- MIT ライセンス・完全無料・オープンソース
- ロイヤリティなし、収益の何%も取られない
- Windows / macOS / Linux でエディタが動作

### 主な特徴

|項目      |内容                                                   |
|--------|-----------------------------------------------------|
|2D エンジン |独立した2Dエンジン（3Dと同時使用可）、タイルセット・物理・パーティクル対応              |
|3D エンジン |SDF グローバルイルミネーション、GPU パーティクル、Jolt Physics（4.6からデフォルト）|
|スクリプト言語 |GDScript（主力）・C#・C++                                  |
|プラットフォーム|Windows・macOS・Linux・Android・iOS・Web・コンソール            |
|エクスポート  |ワンクリックでマルチプラットフォームエクスポート                             |

### 最近のアップデート履歴

- **4.4**（2025年3月）: Jolt Physics エンジン統合
- **4.5**（2025年9月）: ステンシルバッファ、TileMapLayer 衝突システム改善
- **4.6**（2026年1月）: スタンドアロンライブラリとしてビルド可能、新デフォルトテーマ、Jolt がデフォルト物理エンジンに

### Unity との比較

Unity が 2023年にランタイム課金を発表した後、多数の開発者が Godot に移行。現在は**インディー向けのデファクトスタンダード**的な位置づけになっている。

-----

## 2. スクリプト言語の選択

### GDScript（推奨：シンプルさ優先）

- Python に似た独自言語
- 構文がクリーンで習得が早い
- Godot エディタに完全統合（オートコンプリート・デバッガ）
- LLM（Claude Code）との相性が非常に良い

### C#（推奨：規模が大きい場合）

- .NET 9 対応
- godogen プロジェクト等、Claude Code を使った自律開発では C# を採用するケースも
- Steam / デスクトップ向けには GDExtension 版の GodotSteam が必要（C# 版は公式アセットストアに非対応）

> **結論**: 個人・小規模プロジェクトなら **GDScript** が最適。Claude Code との相性も良好。

-----

## 3. Claude × Godot 開発ワークフロー

### Phase 1: ゲームデザイン（Claude.ai）

Claude と会話形式でゲームデザインを固める。

**推奨する進め方**:

1. ジャンル・コンセプト・ターゲット層の議論
1. コアループ・ゲームメカニクスの設計
1. レベルデザイン・UI/UX の設計
1. GDD（ゲームデザインドキュメント）として出力

-----

### Phase 2: 実装（Claude Code）

**Claude Code が Godot で実際にできること**（実績あり）:

- GDScript コードの生成（ゲームメカニクス・敵AI・UI ロジックなど）
- シーン構造・プロジェクトファイルの構成
- プレースホルダーアセットの生成
- **スクリーンショット撮影 → 視覚的バグ検出 → 自己修正ループ**
- リファクタリング・デバッグ

**重要な特性**: Godot のプロジェクトファイル（`.tscn`・`project.godot` 等）は**人間が読めるテキスト形式**なので、LLM が変更を追跡しやすい。

-----

### 便利なツール・プラグイン

#### Godot MCP サーバー（`godot-mcp`）

Claude Code から Godot エンジンを直接操作できる MCP サーバー。

```json
{
  "mcpServers": {
    "godot": {
      "command": "npx",
      "args": ["@coding-solo/godot-mcp"]
    }
  }
}
```

**できること**:

- エディタの起動・プロジェクトの実行
- シーン作成・ノード追加・スプライト読み込み
- デバッグ出力の取得

#### Godot-Claude-Skills

Claude Code 用のスキルセット。GDScript 生成・アセット管理・レベルデザイン自動化を強化。

- GitHub: `Randroids-Dojo/Godot-Claude-Skills`

#### godogen（完全自律開発フレームワーク）

Claude Code + Godot で自律的にゲームを生成するパイプライン。

- C# / .NET 9 + Godot 4 を使用
- 画像生成AI（Gemini・Grok）との連携でアセット自動生成
- GitHub: `htdt/godogen`

-----

## 4. Steam リリース（GodotSteam）

### GodotSteam とは

Valve の **Steamworks SDK** を Godot から使うための GDExtension プラグイン。MIT ライセンス・無料。

**URL**: https://godotsteam.com  
**Codeberg**: https://codeberg.org/godotsteam/godotsteam

### 対応バージョン

|GodotSteam      |対応 Godot      |Steamworks SDK|
|----------------|--------------|--------------|
|最新版（GDExtension）|**Godot 4.4+**|1.64          |
|旧版              |Godot 4.1〜4.3 |1.62          |

対応プラットフォーム: Windows 32/64bit・Linux 32/64bit・Linux ARM64・macOS（Universal）・Android ARM64

### Steamworks で使える主な機能

- Steam 実績・リーダーボード
- クラウドセーブ
- Steam ワークショップ（ユーザー MOD）
- マルチプレイヤー / ロビー
- DRM・価格設定・多言語配信
- プレイテスト機能

### GDExtension 版の注意点

- GDExtension 版は通常の Godot エクスポートテンプレートを使う（GodotSteam 専用テンプレートは不要）
- エディタ上でのオーバーレイ表示は Forward+ レンダラー使用時に制限あり（エクスポート後は問題なし）
- モジュール版と GDExtension 版は**混在不可**

### インストール手順（概要）

1. Godot Asset Store または Codeberg から GodotSteam GDExtension をダウンロード
1. プロジェクトの `addons/` ディレクトリに配置
1. `steam_appid.txt`（Steam App ID を記載）をプロジェクトルートに配置
1. GDScript から `Steam.steamInit()` を呼び出して初期化

```gdscript
func _ready():
    var init = Steam.steamInit()
    if init['status'] == Steam.STEAM_API_INIT_OK:
        print("Steam initialized!")
```

-----

## 5. Steam リリースまでの全体フロー

```
[Claude.ai]
ゲームデザイン議論 → GDD 作成
        ↓
[Claude Code + Godot MCP]
GDScript 生成 → シーン構築 → テスト → バグ修正
        ↓
[Godot エディタ]
最終確認・ビルド（Windows / macOS / Linux）
        ↓
[GodotSteam GDExtension]
Steamworks 機能統合（実績・セーブ・マルチプレイ等）
        ↓
[Steamworks パートナーポータル]
Steam ページ作成 → ビルドアップロード → リリース
```

-----

## 6. Godot の強み（このワークフロー向け）

1. **完全無料・ロイヤリティなし** → Steam 収益を全額受け取れる
1. **テキストベースのプロジェクトファイル** → Claude Code が扱いやすい
1. **GDScript の習得コストが低い** → Claude Code がコード生成しやすい
1. **軽量エディタ** → 低スペック PC でも動作
1. **活発なコミュニティ** → プラグイン・チュートリアルが豊富
1. **GodotSteam が成熟** → Steam 統合が比較的容易

-----

## 7. 参考リンク

|リソース               |URL                                                  |
|-------------------|-----------------------------------------------------|
|Godot 公式           |https://godotengine.org                              |
|Godot ドキュメント       |https://docs.godotengine.org                         |
|GodotSteam 公式      |https://godotsteam.com                               |
|GodotSteam Codeberg|https://codeberg.org/godotsteam/godotsteam           |
|Godot MCP サーバー     |https://github.com/Coding-Solo/godot-mcp             |
|Godot-Claude-Skills|https://github.com/Randroids-Dojo/Godot-Claude-Skills|
|godogen（自律開発）      |https://github.com/htdt/godogen                      |
|Steamworks ドキュメント  |https://partner.steamgames.com/doc/home              |