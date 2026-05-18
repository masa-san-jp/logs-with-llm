結論

Codexのカスタムペットは、基本的に次の2ファイルを ~/.codex/pets/<pet-id>/ に置く構成です。

~/.codex/pets/original-mascot/
├── pet.json
└── spritesheet.webp

OpenAI公式のCodex Appは、Codexスレッドを並列実行できるデスクトップ体験として提供され、Skillsや画像生成もアプリ内で扱えます。カスタムペット制作については、OpenAIの hatch-pet skill が pet.json と spritesheet.webp のパッケージング、スプライトシート検証、QAプレビュー生成を前提にしています。 ￼

提案mdファイル名：20260518-codex-custom-pet-implementation-design.md

⸻

必要な素材

1. キャラクター設計素材

最低限、以下を決めます。

項目	内容
キャラ名	例：Mofu, Circuit-Fox, Ink-Dragon
pet ID	小文字・ハイフン区切り。例：circuit-fox
キャラ説明	pet.json の description に入れる1文
見た目	種族、体型、色、顔、目、尻尾、服、小物
スタイル	ピクセルアート、フラット、3D風、手描き風など
NG要素	ロゴ模倣、既存IP類似、読める文字、複雑すぎる装飾
基準画像	正面または3/4ビューの1枚。以後の全アニメーションの基準にする

OpenAIの hatch-pet skill では、最初に生成・確定したメイン画像を「visual source of truth」、つまり全ポーズの基準画像として扱う設計になっています。 ￼

⸻

2. 実装ファイル

必須

pet.json
spritesheet.webp

hatch-pet skill の出力仕様でも、最終パッケージは ${CODEX_HOME:-$HOME/.codex}/pets/<pet-name>/ 配下に pet.json と spritesheet.webp を置く構成です。 ￼

推奨QA成果物

qa/
├── contact-sheet.png
├── previews/
│   ├── idle.gif
│   ├── running-right.gif
│   └── ...
├── review.json
└── run-summary.json

hatch-pet skill は、単にスプライトシートを作るだけでなく、contact sheet、アニメーションGIF、validation結果、review結果を作って検査する流れを推奨しています。 ￼

⸻

pet.json のコード

最小構成はこれです。

{
  "id": "original-mascot",
  "displayName": "Original Mascot",
  "description": "A calm original companion character for focused coding sessions.",
  "spritesheetPath": "spritesheet.webp"
}

実際の設置先：

mkdir -p ~/.codex/pets/original-mascot
cp spritesheet.webp ~/.codex/pets/original-mascot/spritesheet.webp
cp pet.json ~/.codex/pets/original-mascot/pet.json

pet.json は、ID、表示名、説明、スプライトシートのパスを持つマニフェストとして扱うのが基本です。spritesheetPath は同じフォルダ内の spritesheet.webp を指します。 ￼

⸻

スプライトシート仕様

OpenAIの hatch-pet skill の検査条件では、最終アトラスは以下を満たす前提です。

項目	仕様
形式	PNGまたはWebP。実運用は spritesheet.webp 推奨
サイズ	1536 x 1872
セルサイズ	192 x 208
構造	8列 × 9行
透明	未使用セルは完全透明
QA	contact sheetと各行GIFで確認

この仕様は hatch-pet の最終チェックリストに明記されています。 ￼

計算すると：

横: 192px × 8列 = 1536px
縦: 208px × 9行 = 1872px

⸻

ディレクトリ設計

制作プロジェクトは、Codexに直接置く前に作業ディレクトリを分けるのが安全です。

codex-pet-original-mascot/
├── README.md
├── pet.json
├── assets/
│   ├── reference.png
│   ├── palette.png
│   └── concept.md
├── rows/
│   ├── idle.png
│   ├── running-right.png
│   ├── running-left.png
│   ├── thinking.png
│   ├── working.png
│   ├── success.png
│   ├── error.png
│   ├── sleeping.png
│   └── alert.png
├── frames/
│   ├── idle/
│   ├── running-right/
│   └── ...
├── final/
│   ├── spritesheet.png
│   └── spritesheet.webp
└── qa/
    ├── contact-sheet.png
    ├── previews/
    ├── validation.json
    └── review.json

Codexに認識させる最終配置だけは以下です。

~/.codex/pets/original-mascot/
├── pet.json
└── spritesheet.webp

⸻

実装設計

フェーズ1：キャラクター仕様を固定する

assets/concept.md

# Original Mascot Concept
## Name
Original Mascot
## Personality
Calm, observant, slightly curious, suited for focused coding work.
## Visual Design
- Small fox-like companion
- Rounded silhouette
- Deep navy body
- Cyan accent eyes
- Small scarf
- No readable text
- No logos
- Transparent background
## Animation Requirements
- Identity must remain consistent across every row
- Body size must not pop between frames
- Baseline must stay stable
- Facing direction must be clear
- Character must remain readable at small size

⸻

フェーズ2：スプライト行を作る

9行構成の例です。Codex側の厳密な内部ステート名はバージョン差があり得るため、制作側では「9ステート分を安定して作る」設計にします。

行	状態	内容
1	idle	待機。軽い呼吸、瞬き
2	running-right	右向き移動
3	running-left	左向き移動。右向きの反転で可
4	thinking	考え中。首を傾げる
5	working	作業中。手元や小物が動く
6	success	成功。小さく跳ねる
7	error	エラー。困った表情
8	sleeping	休眠。寝息
9	alert	通知。耳や目が反応

実装上は「行ごとに8フレーム」を作り、最終的に 8 x 9 のアトラスに合成します。

⸻

生成プロンプト例

画像生成で作る場合の基準プロンプトです。

Create a small original coding companion character for Codex Pets.
Character:
- A small fox-like original creature
- Rounded silhouette
- Deep navy fur
- Cyan glowing eyes
- Small charcoal scarf
- Calm and intelligent expression
- No logos, no readable text, no copyrighted character resemblance
Style:
- Clean pixel-art sprite
- Transparent background
- Readable at small desktop overlay size
- Consistent body proportions
- Centered in a 192x208 cell
- Stable baseline across frames
Output:
- 8 animation frames for the requested state
- Even spacing
- No cropping
- No background

行ごとの追加指定：

State: idle.
Action: subtle breathing loop, occasional blink, calm posture.
Keep the same character identity, palette, silhouette, scarf, and face.
State: running-right.
Action: smooth side-facing run cycle to the right.
Keep the same size and baseline across all frames.
State: success.
Action: small celebratory hop with bright but non-text visual effect.
No readable text, no logos.

⸻

アトラス合成スクリプト

Pillowで frames/<state>/*.png から 1536x1872 のスプライトシートを作る例です。

from pathlib import Path
from PIL import Image
CELL_W = 192
CELL_H = 208
COLS = 8
ROWS = 9
STATES = [
    "idle",
    "running-right",
    "running-left",
    "thinking",
    "working",
    "success",
    "error",
    "sleeping",
    "alert",
]
ROOT = Path("codex-pet-original-mascot")
FRAMES_DIR = ROOT / "frames"
FINAL_DIR = ROOT / "final"
FINAL_DIR.mkdir(parents=True, exist_ok=True)
atlas = Image.new("RGBA", (CELL_W * COLS, CELL_H * ROWS), (0, 0, 0, 0))
for row, state in enumerate(STATES):
    state_dir = FRAMES_DIR / state
    frame_paths = sorted(state_dir.glob("*.png"))
    if len(frame_paths) != COLS:
        raise ValueError(f"{state}: expected {COLS} frames, got {len(frame_paths)}")
    for col, frame_path in enumerate(frame_paths):
        img = Image.open(frame_path).convert("RGBA")
        if img.size != (CELL_W, CELL_H):
            fitted = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
            img.thumbnail((CELL_W, CELL_H), Image.Resampling.LANCZOS)
            x = (CELL_W - img.width) // 2
            y = CELL_H - img.height
            fitted.alpha_composite(img, (x, y))
            img = fitted
        atlas.alpha_composite(img, (col * CELL_W, row * CELL_H))
png_path = FINAL_DIR / "spritesheet.png"
webp_path = FINAL_DIR / "spritesheet.webp"
atlas.save(png_path)
atlas.save(webp_path, "WEBP", lossless=True, quality=100)
print(f"Saved: {png_path}")
print(f"Saved: {webp_path}")

⸻

pet.json 生成スクリプト

import json
from pathlib import Path
PET_ID = "original-mascot"
DISPLAY_NAME = "Original Mascot"
DESCRIPTION = "A calm original companion character for focused coding sessions."
pet = {
    "id": PET_ID,
    "displayName": DISPLAY_NAME,
    "description": DESCRIPTION,
    "spritesheetPath": "spritesheet.webp",
}
out_dir = Path("codex-pet-original-mascot")
(out_dir / "pet.json").write_text(
    json.dumps(pet, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(out_dir / "pet.json")

⸻

インストールスクリプト

macOS/Linux想定です。

#!/usr/bin/env bash
set -euo pipefail
PET_ID="original-mascot"
SOURCE_DIR="codex-pet-original-mascot"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
PET_DIR="$CODEX_HOME/pets/$PET_ID"
mkdir -p "$PET_DIR"
cp "$SOURCE_DIR/pet.json" "$PET_DIR/pet.json"
cp "$SOURCE_DIR/final/spritesheet.webp" "$PET_DIR/spritesheet.webp"
echo "Installed Codex pet:"
echo "$PET_DIR"

⸻

QA設計

自動チェック

最低限、以下を検証します。

from pathlib import Path
from PIL import Image
import json
PET_DIR = Path.home() / ".codex" / "pets" / "original-mascot"
PET_JSON = PET_DIR / "pet.json"
SPRITESHEET = PET_DIR / "spritesheet.webp"
errors = []
if not PET_JSON.exists():
    errors.append("pet.json not found")
if not SPRITESHEET.exists():
    errors.append("spritesheet.webp not found")
if PET_JSON.exists():
    data = json.loads(PET_JSON.read_text(encoding="utf-8"))
    for key in ["id", "displayName", "description", "spritesheetPath"]:
        if key not in data:
            errors.append(f"missing key: {key}")
if SPRITESHEET.exists():
    img = Image.open(SPRITESHEET).convert("RGBA")
    if img.size != (1536, 1872):
        errors.append(f"invalid spritesheet size: {img.size}, expected (1536, 1872)")
if errors:
    print("NG")
    for e in errors:
        print("-", e)
    raise SystemExit(1)
print("OK")

目視チェック

重点は以下です。

観点	NG例
同一性	行ごとに別キャラに見える
サイズ	フレームごとに拡大縮小して見える
ベースライン	足元が上下に跳ねすぎる
方向	右走り・左走りが逆
透明背景	白背景や色背景が残る
可読性	小さく表示すると潰れる
権利	既存キャラ、商標、ロゴに似すぎる

hatch-pet skill でも、決定的なバリデーションだけでは不十分で、contact sheetとGIFプレビューを目視QAし、種族、体型、顔、配色、小物、シルエットの一貫性を確認するよう求めています。 ￼

⸻

Codexに依頼する場合の実用プロンプト

Codex App内で作らせるなら、以下のように依頼すると実装まで通りやすいです。

Codexのカスタムペットを作ってください。
要件:
- pet ID: original-mascot
- displayName: Original Mascot
- description: A calm original companion character for focused coding sessions.
- スタイル: 読みやすいピクセルアート
- キャラクター: 紺色の小さな狐型オリジナルキャラクター、シアンの目、小さなチャコール色のスカーフ
- 既存IP、ロゴ、読める文字は禁止
- 透明背景
- 192x208セル、8列x9行、最終spritesheetは1536x1872
- final/spritesheet.webp を生成
- pet.json を生成
- contact-sheet.png と各行GIFプレビューを作ってQA
- 問題なければ ~/.codex/pets/original-mascot/ に pet.json と spritesheet.webp を配置
成果物:
- ~/.codex/pets/original-mascot/pet.json
- ~/.codex/pets/original-mascot/spritesheet.webp
- qa/contact-sheet.png
- qa/previews/*.gif
- qa/validation.json

Codex Appは画像生成をスレッド内で扱えるため、UIアセット、背景、イラスト、スプライトシート、プレースホルダー制作に使えると公式ドキュメントで説明されています。 ￼

⸻

推奨実装方針

最短で作る場合

1. キャラ基準画像を1枚作る
2. 9状態 × 8フレームを生成
3. 1536x1872 の spritesheet.webp に合成
4. pet.json を作る
5. ~/.codex/pets/<pet-id>/ に置く
6. Codex Appの Settings > Appearance > Pets で選択する

品質重視の場合

1. キャラクター仕様書を作る
2. 基準画像を固定する
3. idle と running-right を先に検証する
4. 問題なければ残り7行を生成する
5. running-left は running-right の反転で作る
6. 自動検証
7. contact sheet確認
8. GIFプレビュー確認
9. 最終配置

⸻

注意点

* spritesheet.webp は透明対応・ロスレスWebPで保存する。
* 未使用セルがある場合は完全透明にする。
* 生成画像に文字、ロゴ、UI、既存キャラクター風の造形を入れない。
* 1フレームごとにキャラの顔・体型・色が変わると、ペットとしての一貫性が崩れる。
* アニメーションは派手さより「小さく表示して認識できること」を優先する。
* Codex Appやペット機能は更新が速い領域なので、実装時点のCodexバージョンで表示確認する。公式Codex IDE/Appは現在も機能更新が続いており、アプリ・IDE・CLIで共有される設定や機能もあります。 ￼