# NDLOCR-Lite 導入ガイド

**日付**: 2026-03-21  
**参照元**: https://lab.ndl.go.jp/news/2025/2026-02-24/ / https://github.com/ndl-lab/ndlocr-lite

-----

## 概要

NDLOCR-Lite は、国立国会図書館（NDL）が CC BY 4.0 ライセンスで公開する日本語 OCR ツールの軽量版。

- **対象資料**: 図書・雑誌などのデジタル化画像（縦書き・横書き混在も対応）
- **入力形式**: CLI は画像ファイル（jpg/png/tiff/tif/jp2/jpeg/bmp）に対応し、GUI はこれらに加えて **PDFファイル** も処理可能
- **最大の特徴**: GPU 不要。ノートパソコン等の一般的な家庭用コンピュータで高速動作
- **対応 OS**: Windows 11 / macOS（Apple M4, Sequoia）/ Linux（Ubuntu 22.04）
- **提供形態**: デスクトップアプリ（GUI）& コマンドライン（CLI）の両方あり
- **最新安定版**: v1.1.2（2025-03-03 リリース）

従来の NDLOCR（ndlocr_cli）は CUDA 対応 GPU を前提とし、Docker 環境が必要だった。NDLOCR-Lite はその制約を撤廃し、手軽に使えることを優先した設計。NDL古典籍OCR-Lite の開発経験を活かして職員が内製。

---

## 技術スタック

| モジュール | 採用技術 |
|----------|---------|
| レイアウト認識 | DEIMv2（DINOv3 ベースのリアルタイム物体検出） |
| 文字列認識 | PARSeq（Permuted Autoregressive Sequence）|
| 読み順整序 | NDLOCR と同一モジュール |
| モデル形式 | PyTorch で学習 → ONNX 変換して推論（onnxruntime） |

GPU が利用できる環境（サーバー等）では `--device cuda` オプションで GPU 推論に切り替えることも可能（ベータ機能）。

---

## 導入方法

### A. デスクトップアプリ（GUI）— 推奨（非エンジニア向け）

1. [Releases ページ](https://github.com/ndl-lab/ndlocr-lite/releases) から OS に合ったファイルをダウンロード
2. **重要**: アプリは日本語（全角文字）を含まないパスに配置すること（全角パスで起動しない場合がある）
3. 解凍して起動するだけ。インストール不要

デスクトップ版には**画面キャプチャモード**があり、ブラウザ上で開いた NDL デジタルコレクション等の画像を、ファイルに保存せずそのままテキスト化できる。  
また、GUI では画像ファイルに加えて **PDFファイル** も入力可能であり、PDF は内部でページ単位の画像に変換したうえでOCR処理される。

### B. コマンドライン（CLI）— pip / uv

**前提**: Python 3.10 以上

なお、CLI は現状 **画像ファイルのみ対応** であり、PDF を直接入力することはできない。

#### pip を使う場合

```bash
git clone https://github.com/ndl-lab/ndlocr-lite
cd ndlocr-lite
pip install -r requirements.txt
cd src
```

ディレクトリ内の画像を一括処理:

```bash
python3 ocr.py --sourcedir 画像ディレクトリ名 --output 出力ディレクトリ名
```

1枚の画像を処理:

```bash
python3 ocr.py --sourceimg digidepo_1287221_00000002.jpg --output tmpdir
```

#### uv を使う場合（推奨）

[uv](https://github.com/astral-sh/uv) を使うと依存関係の管理が楽になり、`ndlocr-lite` コマンドとして使えるようになる。

```bash
git clone https://github.com/ndl-lab/ndlocr-lite
cd ndlocr-lite
uv tool install .
```

インストール後はどこからでも実行可能:

```bash
ndlocr-lite --sourceimg digidepo_1287221_00000002.jpg --output tmpdir
```

---

## 主要オプション一覧

| オプション | 説明 |
|----------|------|
| `--sourcedir <path>` | **CLI用**。画像を含むディレクトリを指定（jpg/png/tiff/tif/jp2/jpeg/bmp を再帰的に処理） |
| `--sourceimg <path>` | **CLI用**。処理する画像ファイルを直接指定 |
| `--output <path>` | OCR 結果の出力先ディレクトリを指定 |
| `--viz True` | 文字認識箇所を青枠で示した画像も出力する |
| `--device cuda` | GPU を使って処理（onnxruntime-gpu が必要、ベータ）|

---

## 出力形式

OCR 結果は XML 形式で出力される（NDLOCR と互換性あり）。テキストだけでなくレイアウト情報（文字領域の座標等）も含まれる。

GUI では設定に応じて TXT / JSON / XML / TEI / PDF などの追加出力も利用できる。

---

## 従来の NDLOCR（ndlocr_cli）との違い

| 比較項目 | NDLOCR-Lite | NDLOCR（ver.2.1） |
|--------|-------------|-----------------|
| GPU | 不要（CPU のみで動作） | CUDA 対応 GPU 必須 |
| 環境構築 | pip install / デスクトップアプリ | Docker ビルドが必要 |
| 対象ユーザー | 一般・研究者・非エンジニア | 大規模処理・エンジニア向け |
| Python 要件 | 3.10 以上（CLI の場合） | Docker 内（ホスト不問）|
| 処理速度 | CPU で高速 | GPU で高速 |
| ライセンス | CC BY 4.0 | CC BY 4.0 |

---

## ユースケース

1. **個人研究・学術利用**: NDL デジタルコレクションの資料からテキストを抽出してコーパス作成
2. **機関内 OCR 処理**: 図書館・研究機関でのデジタル化資料の全文テキスト化
3. **資料横断検索のデータ整備**: XML 出力を活用してレイアウト情報付きの検索インデックスを構築
4. **古典籍・近代文書のデジタル化**: 縦書き文書にも対応するため、明治〜昭和期の資料にも有効

---

## 注意事項・既知の問題

- アプリの配置パスに全角文字が含まれると起動しない場合がある（Windows で特に注意）
- 拡張子の大文字（JPG、PNG 等）は v1.1.1 で修正済み（それ以前では認識しない場合あり）
- ダークモードでの表示問題は v1.1.1 で修正済み
- GPU 対応（`--device cuda`）はベータ機能のため本番利用には注意
- PDF入力は GUI でサポートされるが、内部的には各ページを画像化してからOCR処理する
- CLI は現状 PDF を直接処理できない
- PDF のページ数が多い場合、一時画像の生成により処理時間やディスク使用量が増える可能性がある

---

## 関連リンク

- GitHub リポジトリ: https://github.com/ndl-lab/ndlocr-lite
- 使い方（NDL公式）: https://lab.ndl.go.jp/data_set/ndlocrlite-usage/
- NDL リリースアナウンス: https://lab.ndl.go.jp/news/2025/2026-02-24/
- 従来版（ndlocr_cli）: https://github.com/ndl-lab/ndlocr_cli
- NDL古典籍OCR-Lite: https://github.com/ndl-lab/ndlkotenocr-lite