# OpenMythos リサーチ

## 概要

**OpenMythos** は、Anthropicの非公開モデル「Claude Mythos」のアーキテクチャを、公開論文から理論的に再構築したオープンソース実装。開発者は Kye Gomez（[kyegomez/OpenMythos](https://github.com/kyegomez/OpenMythos)）。

- リリース: 2026年4月
- GitHub Stars: 10,600+（2週間で急伸）
- ライセンス: OSS（PyTorch実装）
- **重要な前提**: 学習済みウェイトは存在しない。あくまでアーキテクチャの仮説実装

---

## Claude Mythosとは

2026年3月末にAnthropicが誤って公開したドラフト資料でその存在が判明した最強モデル。

- Claude Opusの一段上に位置するティア
- Firefoxの脆弱性を**271件**発見（Mozilla社内テスト）
- 32ステップの企業ネットワーク攻撃シミュレーションを完走（史上初のAI）
- 現在は「Project Glasswing」経由で防衛的セキュリティ研究機関限定公開

---

## OpenMythosのアーキテクチャ仮説

### Recurrent-Depth Transformer (RDT)

通常のTransformerが「層を積み重ねる」のに対し、RDTは**同一の重みブロックを繰り返しループ**させる設計。

```
入力
 ↓
[Prelude]     ← 通常のTransformerブロック × N層
 ↓
[Recurrent Block] ← 同一ブロックを T回ループ（重み共有）
 ↓
[Coda]        ← 通常のTransformerブロック × N層
 ↓
出力
```

### 主要コンポーネント

| コンポーネント | 詳細 |
|---|---|
| Attention | MLA（Multi-Latent Attention）or GQA 選択可 |
| FFN | Sparse MoE（ルーテッドエキスパート + 共有エキスパート） |
| ループ安定化 | LoRA Depth Adapter + LayerNorm |
| RoPE | ループインデックスを位置埋め込みに注入（オプション） |

### 効率性の根拠（Parcae論文 2026年4月）

- **770Mパラメータ**のRDTが、通常の**1.3Bパラメータ**Transformerに匹敵
- ループ数と最適トークン数がべき乗則でスケール（予測可能なスケーリング則）
- 推論時のループ数を増やすことで「思考時間」を延長できる

---

## 実際に動かした結果

### インストール

```bash
pip install open-mythos
# Flash Attention 2 使用時（CUDA必須）
pip install flash-attn --no-build-isolation
```

### 基本フォワードパス（CPU, GQA設定）

```python
import torch
from open_mythos.main import MythosConfig, OpenMythos

cfg = MythosConfig(
    vocab_size=1000,
    dim=256,
    n_heads=8,
    n_kv_heads=2,
    max_seq_len=128,
    max_loop_iters=4,
    prelude_layers=1,
    coda_layers=1,
    attn_type="gqa",
    n_experts=8,
    n_shared_experts=1,
    n_experts_per_tok=2,
    expert_dim=64,
    lora_rank=8,
)

model = OpenMythos(cfg)
x = torch.randint(0, 1000, (1, 16))
out = model(x)
```

**実測値:**
- パラメータ数: **1,771,810**（約177万）
- 入力 shape: `[1, 16]` → 出力 shape: `[1, 16, 1000]`

### MLA設定（28Mパラメータ相当）

```python
cfg_mla = MythosConfig(
    vocab_size=32000,
    dim=512,
    n_heads=8,
    n_kv_heads=2,
    max_seq_len=256,
    max_loop_iters=8,
    attn_type="mla",
    kv_lora_rank=128,
    q_lora_rank=256,
    n_experts=16,
    n_shared_experts=2,
    n_experts_per_tok=2,
    expert_dim=128,
)
```

**実測値:**
- パラメータ数: **28,554,754**（約2850万）
- バッチ2、シーケンス長32で正常動作確認

### ループ深度 vs 推論時間（CPU, seq_len=64）

| ループ数 | 推論時間 (ms/forward) |
|:---:|:---:|
| 1 | 62.0 ms |
| 4 | 71.6 ms |
| 8 | 81.8 ms |
| 16 | 111.0 ms |

→ ループを16倍にしても推論コストは約1.8倍。コンピュート効率が良い。

---

## 主要設定パラメータ

| パラメータ | 説明 | デフォルト目安 |
|---|---|---|
| `dim` | 隠れ層の次元数 | 256〜4096 |
| `max_loop_iters` | Recurrent Blockのループ回数 | 4〜32 |
| `prelude_layers` | Preludeの通常Transformer層数 | 1〜4 |
| `coda_layers` | Codaの通常Transformer層数 | 1〜4 |
| `attn_type` | `"mla"` or `"gqa"` | `"mla"` 推奨 |
| `n_experts` | MoEの総エキスパート数 | 8〜64 |
| `n_experts_per_tok` | トークンあたりのTop-Kエキスパート | 2 |
| `lora_rank` | Depth LoRAのランク | 8〜64 |

---

## 注意点・制限

1. **学習済みウェイトなし** — フォワードパスは動くが、実用的な推論はできない
2. **学習スクリプトあり** — `training/` ディレクトリに FineWeb-Edu 向け 3B 学習スクリプトが存在（GPU必須）
3. **RDT訓練の不安定性** — 隠れ状態が指数的に発散しやすい。`lora_rank` と LayerNorm チューニングが重要
4. **Anthropic公式とは無関係** — 推測・仮説実装であり、実際のMythosアーキテクチャとは異なる可能性が高い

---

## 参考リソース

- [GitHub: kyegomez/OpenMythos](https://github.com/kyegomez/OpenMythos)
- [Parcae論文（RDTスケーリング則）](https://arxiv.org/abs/2504.xxxxx)（UC San Diego & Together AI, 2026年4月）
- [PyPI: open-mythos](https://pypi.org/project/open-mythos/)
