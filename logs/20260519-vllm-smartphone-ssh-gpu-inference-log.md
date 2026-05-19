# vLLM起動検証ログ（匿名化版）

## 概要

- 目的: スマートフォンのSSHクライアントから自宅マシンに接続し、GPU上でvLLMを起動してOpenAI互換APIとして利用できるか検証する。
- 参照記事: https://zenn.dev/karaage0703/articles/fcca40c614dffd
- 実施環境: 個人環境のため、ユーザー名、ホスト名、実ディレクトリ、トークン、端末名はすべて匿名化する。
- 匿名化ルール:
  - ユーザー名: `[USER]`
  - ホスト名 / コンピュータ名: `[HOST]`
  - 作業ディレクトリ: `[PROJECT_DIR]`
  - Python仮想環境: `[VENV_DIR]`
  - Hugging Face Token: `[HF_TOKEN]`
  - ローカルパス: 原則として `[PATH]` または `[PROJECT_DIR]` に置換

---

## 1. やろうとしたこと

スマートフォンのSSHクライアントから `[HOST]` に接続し、`vLLM` を起動する。

最終的には以下を確認することを目的とした。

- vLLMサーバーが起動できること
- OpenAI互換API `/v1/models` が応答すること
- `/v1/chat/completions` で推論できること
- 当初試した `gpt-oss-20b` が実用可能か確認すること
- 切り分け用に別モデルでもvLLM自体の正常性を確認すること

---

## 2. 初期セットアップ

### 2.1 `uv` が未導入

最初にPython仮想環境を作成しようとしたが、`uv` コマンドが存在しなかった。

```bash
uv venv -p 3.12 [PROJECT_DIR]/[VENV_DIR]
```

結果:

```text
uv: command not found
```

対応として `snap` で `astral-uv` を導入しようとしたところ、classic confinement が必要という警告が出た。

```text
This revision of snap "astral-uv" was published using classic confinement...
```

対応:

```bash
sudo snap install astral-uv --classic
```

---

### 2.2 Python 3.12 仮想環境の作成

`uv` 導入後、Python 3.12で仮想環境を作成した。

```bash
uv venv -p 3.12 [PROJECT_DIR]/[VENV_DIR]
```

結果:

```text
Using CPython 3.12.3 interpreter
Creating virtual environment
```

Pythonバージョン確認:

```bash
python3.12 --version
```

結果:

```text
Python 3.12.3
```

---

## 3. vLLM custom wheel の導入

### 3.1 `torch==2.10.0+cu130` が見つからない

vLLM custom wheel をインストールしようとしたところ、依存関係解決に失敗した。

```text
No solution found when resolving dependencies:
Because there is no version of torch==2.10.0+cu130
```

原因:

- 指定wheelが `torch==2.10.0+cu130` に依存していた
- 通常のPyPIだけでは該当するPyTorch CUDA 13.0 wheelが解決できなかった

対応:

```bash
uv pip install --torch-backend=cu130 "[VLLM_CUSTOM_WHEEL_URL]"
```

---

### 3.2 `Python.h` が見つからない

続いて `fastsafetensors` のビルド中に失敗した。

```text
fatal error: Python.h: No such file or directory
error: command '/usr/bin/aarch64-linux-gnu-gcc' failed with exit code 1
```

原因:

- Python 3.12 の開発ヘッダが未導入
- C/C++拡張ビルドに必要な環境が不足

対応:

```bash
sudo apt update
sudo apt install -y python3.12-dev build-essential cmake pkg-config
```

---

## 4. 起動スクリプト作成

vLLM起動用に `start-vllm.sh` を作成した。

```bash
cat > [PROJECT_DIR]/start-vllm.sh << 'EOF'
#!/bin/bash
export LD_LIBRARY_PATH=/usr/local/lib/ollama/cuda_v12:/usr/local/cuda/lib64:$LD_LIBRARY_PATH
export VLLM_MXFP4_BACKEND=marlin
export VLLM_MARLIN_USE_ATOMIC_ADD=1
cd [PROJECT_DIR]
source [VENV_DIR]/bin/activate
exec vllm serve "$@"
EOF

chmod +x [PROJECT_DIR]/start-vllm.sh
```

目的:

- CUDA関連ライブラリパスを明示
- vLLM用環境変数を固定
- 仮想環境を有効化して `vllm serve` を実行

---

## 5. スマートフォンSSHクライアント運用

### 5.1 別ターミナル問題

スマートフォンのSSHクライアントから操作していたため、vLLMサーバーを起動したまま別コマンドを実行する方法が必要になった。

対応案:

1. SSHクライアントで同じホストへの新規接続をもう1つ開く
2. 片方をvLLMサーバー起動用、もう片方をcurl確認用にする
3. 代替案として `nohup` でバックグラウンド起動する

バックグラウンド起動例:

```bash
nohup [PROJECT_DIR]/start-vllm.sh [MODEL_NAME] \
  --host 0.0.0.0 \
  --port 8000 \
  > [PROJECT_DIR]/vllm.log 2>&1 &
```

ログ確認:

```bash
tail -f [PROJECT_DIR]/vllm.log
```

---

## 6. `gpt-oss-20b` 起動検証

### 6.1 最初にGGUF repoを指定して失敗

当初、GGUF形式のrepoを `vllm serve` に指定した。

```bash
./start-vllm.sh [GGUF_MODEL_REPO] \
  --host 0.0.0.0 \
  --port 8000
```

結果:

```text
RuntimeError: Cannot find any model weights with `[GGUF_MODEL_REPO]`
```

原因:

- GGUF repoを通常のHugging Face safetensorsモデルとして読み込もうとしていた
- vLLMの通常ロード形式では対象の重みを見つけられなかった

対応:

```bash
./start-vllm.sh openai/gpt-oss-20b \
  --host 0.0.0.0 \
  --port 8000
```

---

### 6.2 tokenizer / vocab取得失敗

`openai/gpt-oss-20b` 起動時に、`openai_harmony` のvocab取得で失敗した。

```text
openai_harmony.HarmonyError:
error downloading or loading vocab file
```

実施した対応:

```bash
uv pip install -U openai-harmony huggingface_hub hf_transfer
```

Hugging Face token設定:

```bash
export HF_TOKEN=[HF_TOKEN]
huggingface-cli login --token "$HF_TOKEN"
```

補足:

- HF tokenは読み取り権限のみで十分
- Write/Admin等は不要

---

### 6.3 tiktoken encodingを手動配置

`openai_harmony` が必要とするtiktoken vocabをローカルに配置し、参照先を明示した。

```bash
mkdir -p [PROJECT_DIR]/tiktoken

curl -L -o [PROJECT_DIR]/tiktoken/o200k_base.tiktoken \
  https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken

curl -L -o [PROJECT_DIR]/tiktoken/cl100k_base.tiktoken \
  https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken

export TIKTOKEN_ENCODINGS_BASE=[PROJECT_DIR]/tiktoken
```

起動スクリプトにも追記した。

```bash
export TIKTOKEN_ENCODINGS_BASE=[PROJECT_DIR]/tiktoken
```

確認:

```bash
python - << 'PY'
from openai_harmony import load_harmony_encoding
enc = load_harmony_encoding("HarmonyGptOss")
print("harmony encoding OK")
PY
```

---

### 6.4 gpt-ossサーバー起動成功

最終的に `gpt-oss-20b` はサーバー起動まで成功した。

確認:

```bash
curl http://localhost:8000/v1/models
```

結果:

```json
{
  "object": "list",
  "data": [
    {
      "id": "openai/gpt-oss-20b",
      "object": "model",
      "owned_by": "vllm"
    }
  ]
}
```

この時点で確認できたこと:

- vLLM API server起動成功
- `/v1/models` 応答あり
- モデルロード自体は成功
- CUDA上で動作

---

## 7. `gpt-oss-20b` 推論時の問題

### 7.1 `/v1/chat/completions` で reasoning は出るが content が空

推論テスト:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-20b",
    "messages": [
      {
        "role": "user",
        "content": "こんにちは。短く自己紹介して"
      }
    ],
    "max_tokens": 128
  }'
```

結果:

```json
{
  "message": {
    "role": "assistant",
    "content": null,
    "reasoning": "..."
  },
  "finish_reason": "length"
}
```

`max_tokens` を増やしても、本文 `content` は `null` のままだった。

```json
{
  "message": {
    "role": "assistant",
    "content": null,
    "reasoning": "..."
  },
  "finish_reason": "stop"
}
```

判断:

- 推論処理自体は走っている
- reasoningは生成されている
- しかしOpenAI互換レスポンスの `content` に本文が入らない
- reasoning parser / Harmony format / chat template 周辺の問題が疑われる

---

### 7.2 `/v1/completions` では出力が崩壊

chat APIではなく completions API を試した。

```bash
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-20b",
    "prompt": "こんにちは。短く自己紹介して",
    "max_tokens": 256
  }'
```

結果:

```text
不自然な日本語、英語混入、意味の崩れた文章が生成された
```

判断:

- gpt-ossのロードや実行自体は成功
- ただし生成品質が正常とは言えない
- tokenizer mismatch、Harmony format、gpt-oss backend対応、custom vLLM buildの互換性問題が疑われる

---

## 8. GPU / CUDA / PyTorch 状態

確認コマンド:

```bash
python - << 'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("cuda:", torch.version.cuda)
print("device count:", torch.cuda.device_count())
if torch.cuda.is_available():
    print("device:", torch.cuda.get_device_name(0))
PY
```

結果の要点:

```text
torch: 2.10.0+cu130
cuda available: True
cuda: 13.0
device count: 1
device: NVIDIA GB10
```

警告:

```text
Found GPU0 NVIDIA GB10 which is of cuda capability 12.1.
Minimum and Maximum cuda capability supported by this version of PyTorch is (8.0) - (12.0)
```

判断:

- CUDAは利用可能
- GPUは認識されている
- PyTorchは動作している
- ただしGB10のCompute Capability 12.1は、当該PyTorch buildの公式サポート範囲外という警告が出ている
- これがgpt-oss不安定性の一因である可能性はあるが、後続のQwen検証によりvLLM環境全体の致命的問題ではないと判断

---

## 9. QwenでvLLM本体を切り分け

`gpt-oss-20b` 固有問題か、vLLM / CUDA / GPU全体の問題かを切り分けるため、別モデルで検証した。

対象モデル:

```text
Qwen/Qwen2.5-7B-Instruct
```

---

### 9.1 残留プロセスによるmemory profiling失敗

最初のQwen起動時に、前のvLLMプロセスまたはGPUメモリ状態の変動により失敗した。

```text
AssertionError:
Error in memory profiling.
Initial free memory ... current free memory ...
This happens when other processes ... release GPU memory while vLLM is profiling during initialization.
```

対応:

```bash
pkill -9 -f vllm
```

必要に応じてGPU使用状況を確認。

```bash
nvidia-smi
```

---

### 9.2 KV cache不足

次に、Qwenのデフォルト最大コンテキスト長が大きく、KV cacheメモリ不足で失敗した。

```text
ValueError:
To serve at least one request with the model's max seq len (32768),
1.75 GiB KV cache is needed,
which is larger than the available KV cache memory.
```

判断:

- テスト目的に対して32k contextは不要
- vLLMはデフォルトで高スループット・長コンテキスト・高並列向けにメモリを確保しようとする
- sanity check用途では `max_model_len` を大幅に下げるべき

---

### 9.3 `gpu-memory-utilization` を高くしすぎて失敗

`--gpu-memory-utilization 0.95` を指定したところ、起動時点の空きVRAMが要求値を下回り失敗した。

```text
ValueError:
Free memory on device cuda:0 (...) on startup is less than desired GPU memory utilization (0.95, ...).
Decrease GPU memory utilization or reduce GPU memory used by other processes.
```

判断:

- GPU総容量の95%をvLLMが使おうとした
- 実際にはOS、driver、display、他プロセス等で既にメモリが使われていた
- テスト目的では0.95は過剰

---

### 9.4 テスト用の軽量設定でQwen起動成功

最終的に、以下のようにテスト向けに軽量化して起動した。

```bash
./start-vllm.sh Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --enforce-eager \
  --max-model-len 1024 \
  --gpu-memory-utilization 0.50
```

設定意図:

- `--enforce-eager`
  - CUDA graph captureを無効化し、初期化を安定化
- `--max-model-len 1024`
  - テスト用途に必要十分なコンテキスト長へ縮小
- `--gpu-memory-utilization 0.50`
  - vLLMが過剰にGPUメモリを予約しないよう抑制

起動結果:

```text
Started server process
Waiting for application startup.
Application startup complete.
```

---

## 10. Qwen推論テスト成功

テスト:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [
      {
        "role": "user",
        "content": "こんにちは。短く自己紹介して"
      }
    ],
    "max_tokens": 64
  }'
```

結果:

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "こんにちは！私はQwenと呼ばれ、Alibaba Cloudによって作られたアシスタントです。質問や話題について詳しく知りたいことがあれば何でもお聞きください！",
        "reasoning": null
      },
      "finish_reason": "stop"
    }
  ]
}
```

判断:

- vLLMサーバーは正常
- OpenAI互換APIは正常
- tokenizerは正常
- GPU推論は正常
- CUDA / FlashAttention / PyTorch環境は少なくともQwenでは実用可能
- 問題は `gpt-oss-20b` 固有と判断できる

---

## 11. 最終結果

### 成功したこと

- スマートフォンSSHクライアントから `[HOST]` に接続し、vLLMを操作できた
- Python 3.12仮想環境を作成できた
- vLLM custom wheelをインストールできた
- CUDA 13.0 / PyTorch環境でGPUを認識できた
- vLLM API serverを起動できた
- `/v1/models` が応答した
- Qwenモデルで `/v1/chat/completions` の正常推論に成功した

---

### 失敗または保留になったこと

- `gpt-oss-20b` はサーバー起動までは成功
- しかし `chat/completions` では `reasoning` のみ出て `content` が `null`
- `completions` では文章品質が崩壊
- `gpt-oss-20b` は現時点ではこの環境・このvLLM custom buildでは実用不可と判断

---

## 12. 残課題

### 12.1 gpt-ossを使い続ける場合

追加調査が必要な領域:

- vLLM custom buildとgpt-ossの互換性
- `openai_harmony` のバージョン整合性
- reasoning parser / Harmony format の処理
- tokenizer / chat template の整合性
- GB10 / Compute Capability 12.1への正式対応状況
- PyTorch CUDA 13.0 buildの対応範囲

考えられる対応:

```text
最新のvLLM nightly / torch nightly / openai_harmony最新版で再検証する
```

または:

```text
vLLMではなく transformers / SGLang / llama.cpp 等の別backendを試す
```

---

### 12.2 実用優先の場合

現時点で正常動作が確認できたQwenを使う。

推奨起動例:

```bash
./start-vllm.sh Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --enforce-eager \
  --max-model-len 1024 \
  --gpu-memory-utilization 0.50
```

用途に応じて後から調整する項目:

- `--max-model-len`
- `--gpu-memory-utilization`
- `--enforce-eager` を外すかどうか
- systemd常駐化
- `nohup` / `tmux` / `screen` での運用
- Open WebUI / Continue / Cline / OpenAI互換クライアントへの接続

---

## 13. 結論

今回の作業で、vLLM環境そのものは正常に構築できた。

一方で、当初目的だった `gpt-oss-20b` は以下の理由により実用段階に達しなかった。

```text
モデルロードと推論処理自体は動くが、OpenAI互換API上でcontentが返らず、
completionsでも生成品質が崩れるため。
```

最終的な切り分け結果:

```text
vLLM / CUDA / GPU / API は正常。
gpt-oss-20b + 現在のvLLM custom build の組み合わせが不安定。
```

当面の実用方針:

```text
Qwen/Qwen2.5-7B-Instruct をvLLMで運用し、
gpt-oss系は別backendまたは新しいvLLM/PyTorch環境で再検証する。
```
