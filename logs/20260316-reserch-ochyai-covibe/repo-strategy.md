# co-vibe カスタムリポジトリ構築戦略

-----

## 方針選択：2つのアプローチ比較

### A. ochyai/co-vibe を fork して管理

```
ochyai/co-vibe (upstream)
        │  git fetch upstream
        │  git merge upstream/main
        ▼
yourname/co-vibe (fork)
  ├── co-vibe.py          ← upstream のまま（触らない）
  ├── covibe-launcher.py  ← 自分の追加ファイル
  ├── .env.example        ← 自分の追加ファイル
  └── ...
```

|          |詳細                                                  |
|----------|----------------------------------------------------|
|**メリット**  |upstream の `co-vibe.py` 更新を `git merge` 1コマンドで取り込める |
|          |GitHub 上で upstream との差分が常に可視化される                    |
|          |Pull Request で upstream にコントリビュートしやすい               |
|**デメリット** |`co-vibe.py` 本体を改変すると毎回マージコンフリクトが発生する               |
|          |fork の制約上、リポジトリを Private にできない場合がある（GitHub Free の場合）|
|**向いている人**|upstream の更新を積極的に取り込みたい / 本体は改変しない方針                |

-----

### B. 独立した新規リポジトリで管理

```
ochyai/co-vibe (参照元)
        │  手動で差分確認・ファイルコピー
        ▼
yourname/my-co-vibe (独立リポジトリ)
  ├── co-vibe.py          ← コピーして自由に改変可能
  ├── covibe-launcher.py  ← 自分の追加ファイル
  ├── .env.example        ← 自分の追加ファイル
  └── ...
```

|          |詳細                                            |
|----------|----------------------------------------------|
|**メリット**  |`co-vibe.py` 本体を自由に改変してもコンフリクトが起きない           |
|          |Private リポジトリにできる（APIキーの .env.example 等を安全に管理）|
|          |リポジトリ名・構成を完全に自分でコントロールできる                     |
|**デメリット** |upstream の更新取り込みは手動（`git diff` で差分確認 → 手動適用）  |
|          |upstream との乖離が気づかないうちに広がりやすい                  |
|**向いている人**|本体も含めて独自改変したい / Private 管理したい                 |

-----

### 判断フローチャート

```
co-vibe.py 本体を改変する予定がある？
  ├── Yes → B（独立リポジトリ）
  └── No
        └── リポジトリを Private にしたい？
              ├── Yes → B（独立リポジトリ）
              └── No → A（fork）推奨
```

**現状（追加要素はアイデア段階・本体改変未定）への推奨**: まず **A（fork）** で始め、本体改変が必要になった時点で B へ移行するのが最もコストが低い。

-----

## 手順書 A：fork で管理する場合

### 1. GitHub で fork を作成

1. https://github.com/ochyai/co-vibe を開く
1. 右上の **Fork** ボタンをクリック
1. リポジトリ名を確認（変更可）→ **Create fork**

### 2. ローカルにクローン・upstream を登録

```bash
# fork したリポジトリをクローン
git clone https://github.com/yourname/co-vibe.git
cd co-vibe

# upstream（ochyai の本家）を登録
git remote add upstream https://github.com/ochyai/co-vibe.git

# リモート確認
git remote -v
# origin   https://github.com/yourname/co-vibe.git (fetch/push)
# upstream https://github.com/ochyai/co-vibe.git   (fetch/push)
```

### 3. 自分の追加ファイルを配置してコミット

```bash
# launcher と .env テンプレートを追加
cp /path/to/covibe-launcher.py .
cp .env.example .env.example.base  # 元テンプレートを保持

# .gitignore に .env を追加（APIキーをコミットしない）
echo '.env' >> .gitignore

# コミット
git add covibe-launcher.py .gitignore
git commit -m "feat: add covibe-launcher.py and update .gitignore"
git push origin main
```

### 4. upstream の更新を取り込む（定期メンテナンス）

```bash
# upstream の最新を取得
git fetch upstream

# 差分を確認してからマージ
git diff main upstream/main -- co-vibe.py

# 問題なければマージ
git merge upstream/main

# コンフリクトがあれば解消してからプッシュ
git push origin main
```

-----

## 手順書 B：独立リポジトリで管理する場合

### 1. GitHub で新規リポジトリを作成

1. https://github.com/new を開く
1. リポジトリ名を入力（例: `my-co-vibe`）
1. **Private** を選択（推奨）
1. **Create repository**

### 2. ochyai のコードを取り込んでローカルにセットアップ

```bash
# ochyai のコードをクローン（一時的）
git clone https://github.com/ochyai/co-vibe.git
cd co-vibe

# origin を自分のリポジトリに切り替え
git remote remove origin
git remote add origin https://github.com/yourname/my-co-vibe.git

# upstream も参照用に登録しておく
git remote add upstream https://github.com/ochyai/co-vibe.git

# 自分のリポジトリにプッシュ
git push -u origin main
```

### 3. 追加ファイルを配置してコミット

```bash
cp /path/to/covibe-launcher.py .
echo '.env' >> .gitignore

git add covibe-launcher.py .gitignore
git commit -m "feat: add covibe-launcher.py"
git push origin main
```

### 4. upstream の更新を手動で確認・取り込む

```bash
# upstream の更新を確認
git fetch upstream
git log upstream/main --oneline -10   # 最近のコミットを確認
git diff main upstream/main -- co-vibe.py  # co-vibe.py の差分を表示

# 取り込む場合（本体を改変していない場合）
git checkout upstream/main -- co-vibe.py
git commit -m "chore: update co-vibe.py from upstream"
git push origin main

# 本体を改変している場合は手動で差分を適用する
```

-----

## 複数端末への環境再現

### リポジトリのセットアップ（新しい端末で実行）

```bash
# リポジトリをクローン
git clone https://github.com/yourname/co-vibe.git  # または my-co-vibe
cd co-vibe

# .env を作成（APIキーは各端末で個別入力）
cp .env.example .env
nano .env
```

### .env の内容（各端末で設定する項目）

```env
# ── APIキー（各端末で個別に設定・絶対にコミットしない）──
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...         # 任意
GROQ_API_KEY=gsk_...          # 任意

# ── デフォルト戦略（端末ごとに変えてもよい）──
CO_VIBE_STRATEGY=auto

# ── デバッグ（研究用端末では1に）──
CO_VIBE_DEBUG=0
```

### Ollama モデルの再現（新しい端末で実行）

Ollama 自体のモデルはリポジトリで管理できないため、セットアップスクリプトで pull するのが現実的。

```bash
# setup-ollama.sh としてリポジトリに含めておく
#!/bin/bash
# 使用するモデルをここに列挙して管理する
MODELS=(
  "qwen2.5-coder:7b"
  # "qwen2.5-coder:32b"  # GPU推奨
)

echo "Ollama モデルをセットアップします..."
for model in "${MODELS[@]}"; do
  echo "pulling: $model"
  ollama pull "$model"
done
echo "完了"
```

```bash
# 新しい端末でのセットアップ手順
git clone https://github.com/yourname/co-vibe.git && cd co-vibe
cp .env.example .env && nano .env       # APIキーを入力
bash setup-ollama.sh                    # Ollamaモデルを pull
python3 covibe-launcher.py              # 起動
```

-----

## リポジトリに含めるファイル構成（推奨）

```
co-vibe/
  ├── co-vibe.py              # upstream のファイル（基本触らない）
  ├── co-vibe-proxy.py        # upstream のファイル
  ├── co-vibe.sh              # upstream のファイル
  ├── covibe-launcher.py      # ★ 自分の追加ファイル
  ├── setup-ollama.sh         # ★ 自分の追加ファイル（Ollamaモデル管理）
  ├── .env.example            # ★ 自分が編集したテンプレート（キーなし）
  ├── .gitignore              # .env を除外していること必須
  ├── README.md               # 自分用の使い方メモを追記してもよい
  └── tests/                  # upstream のまま
```

### .gitignore の必須項目

```gitignore
# APIキー（絶対にコミットしない）
.env

# Python キャッシュ
__pycache__/
*.pyc

# セッションデータ（端末ごとに異なる）
.co-vibe-sessions/
*.session
```

-----

## 方針変更：fork → 独立リポジトリへの移行

fork で始めて後から独立に切り替えたくなった場合の手順。

```bash
# 1. GitHub の Settings → 一番下 → "Unlink fork" 相当の操作はできないため
#    新規リポジトリを作成して push し直す

# 2. 新規リポジトリを作成（GitHub UI で）

# 3. 既存の fork ローカルのリモートを変更
cd co-vibe
git remote set-url origin https://github.com/yourname/my-co-vibe.git
git push -u origin main

# 4. upstream は残しておく（更新確認用）
git remote -v
# origin   https://github.com/yourname/my-co-vibe.git
# upstream https://github.com/ochyai/co-vibe.git
```