# 仏教変容プロトコル オブジェクト指向実装仕様書

**バージョン:** 1.0
**対象:** 開発チーム（設計 → 実装 → テスト工程）
**目的:** 個人（`Individual`）を入力として受け取り、認識OSを段階的にアップデートし、最終的に `EnlightenedState` を返す実行可能なシステムを設計する。

-----

## 0. システム概要

本システムは、個人の「苦（`Dukkha`）」を検知・分析し、認識レイヤーの深度に応じて4段階のプロトコル（原始仏教 / 上座部 / 大乗 / 密教）を選択・実行するパイプラインである。各プロトコルは独立したモジュールとして実装され、共通インターフェースを介してオーケストレータ（`LiberationPipeline`）から呼び出される。

### 0.1 アーキテクチャ原則

1. **単一責任原則**: 各プロトコルは特定の認識レイヤーのみに介入する
1. **オープン・クローズド原則**: 新しい宗派プロトコルを追加可能（継承で拡張）
1. **依存性逆転**: 上位モジュールは抽象インターフェース `IProtocol` に依存
1. **状態の不変性**: `Individual` の変容は新しいインスタンスとして返す（関数型的不変性）

### 0.2 レイヤーマッピング

|認識レイヤー                |介入プロトコル|担当クラス                  |
|----------------------|-------|-----------------------|
|L6: 意識（概念）            |原始仏教   |`EarlyBuddhismProtocol`|
|L6精錬: 段階的観察           |上座部    |`TheravadaProtocol`    |
|L7-L8: 末那識 / 阿頼耶識     |大乗     |`MahayanaProtocol`     |
|L9 + 身体: 阿摩羅識 / ハードウェア|密教     |`VajrayanaProtocol`    |

-----

## 1. 入力データモデル: `Individual`

### 1.1 クラス定義

```python
@dataclass
class Individual:
    # --- 静的属性 ---
    id: str
    age: int

    # --- 五蘊（Pañca-skandha）: 構成要素 ---
    skandhas: Skandhas

    # --- 苦の状態 ---
    dukkha_profile: DukkhaProfile

    # --- 執着と渇愛 ---
    attachment_level: float       # 0.0 ~ 1.0 (Upādāna)
    tanha_intensity: float         # 0.0 ~ 1.0 (渇愛強度)

    # --- 深層心理 ---
    alaya_vijnana: AlayaVijnana    # 阿頼耶識（種子ストレージ）
    manas_bias: float              # 末那識によるエゴバイアス 0.0 ~ 1.0

    # --- 進捗状態 ---
    current_stage: Stage           # Enum: PUTHUJJANA, SOTAPANNA, ..., BUDDHA
    three_learnings: ThreeLearnings  # sila/samadhi/panna の完成度
    karma_seeds: List[KarmaSeed]   # 業の種子リスト

    # --- 身体性（密教用） ---
    body_channels: BodyChannels    # 三密の同期状態
```

### 1.2 サブ構造

```python
@dataclass
class Skandhas:
    rupa: float        # 身体
    vedana: float      # 感覚
    samjna: float      # 概念
    samskara: float    # 意志（行）
    vijnana: float     # 識別

@dataclass
class DukkhaProfile:
    four_sufferings: Dict[str, float]   # 生・老・病・死
    eight_sufferings: Dict[str, float]  # +愛別離・怨憎会・求不得・五蘊盛
    despair_unaware: bool               # キルケゴール的無自覚の絶望

@dataclass
class AlayaVijnana:
    seeds: List[KarmaSeed]
    purity_ratio: float  # 0.0=完全汚染 ~ 1.0=完全清浄
    turning_point_reached: bool  # 転依達成フラグ

class Stage(Enum):
    PUTHUJJANA = 0      # 凡夫
    SOTAPANNA = 1       # 預流者
    SAKADAGAMIN = 2     # 一来者
    ANAGAMIN = 3        # 不還者
    ARAHANT = 4         # 阿羅漢
    BODHISATTVA = 5     # 菩薩
    BUDDHA = 6          # 仏
```

-----

## 2. 共通インターフェース: `IProtocol`

```python
class IProtocol(ABC):
    @abstractmethod
    def diagnose(self, individual: Individual) -> DiagnosisReport:
        """現状分析: 苦諦に相当"""

    @abstractmethod
    def identify_cause(self, individual: Individual) -> CauseReport:
        """原因特定: 集諦に相当"""

    @abstractmethod
    def execute(self, individual: Individual) -> Individual:
        """変容の実行。新しい Individual を返す"""

    @abstractmethod
    def verify(self, before: Individual, after: Individual) -> VerificationResult:
        """KPIに基づく到達度検証"""

    @property
    @abstractmethod
    def target_layer(self) -> ConsciousnessLayer:
        """このプロトコルが介入するレイヤー"""
```

-----

## 3. Protocol 1: `EarlyBuddhismProtocol`（原始仏教）

### 3.1 責務

四諦の因果律に基づき、表層の行動・思考のノイズをデバッグする。

### 3.2 クラス構成

```python
class EarlyBuddhismProtocol(IProtocol):
    def __init__(self):
        self.eightfold_path = EightfoldPath()

    def diagnose(self, ind: Individual) -> DiagnosisReport:
        # 苦諦: 四苦八苦 + 五蘊盛苦の検出
        return DiagnosisReport(
            sufferings=ind.dukkha_profile,
            is_ego_attached=ind.attachment_level > 0.3
        )

    def identify_cause(self, ind: Individual) -> CauseReport:
        # 集諦: 渇愛 + 行 の特定
        return CauseReport(
            primary=ind.tanha_intensity,
            samskara_force=ind.skandhas.samskara
        )

    def execute(self, ind: Individual) -> Individual:
        # 八正道を順次適用
        return self.eightfold_path.apply(ind)
```

### 3.3 八正道モジュール

```python
class EightfoldPath:
    steps = [
        RightView(),         # 正見: 認知OS修正
        RightThought(),      # 正思: 思考最適化
        RightSpeech(),       # 正語: 通信浄化
        RightAction(),       # 正業: 行動規範
        RightLivelihood(),   # 正命: 生計整合
        RightEffort(),       # 正精進: エネルギー配分
        RightMindfulness(),  # 正念: モニタリング
        RightConcentration() # 正定: 集中
    ]

    def apply(self, ind: Individual) -> Individual:
        for step in self.steps:
            ind = step.execute(ind)
        return ind
```

各ステップは `IPathStep` を実装し、具体的な状態変更ロジックを持つ。

### 3.4 KPI

- `tanha_intensity` が 20% 以上減少
- `current_stage` が `PUTHUJJANA` から上位へ遷移可能な閾値に到達

-----

## 4. Protocol 2: `TheravadaProtocol`（上座部仏教）

### 4.1 責務

七清浄の段階的進捗管理により、凡夫から阿羅漢へ精錬する。

### 4.2 クラス構成

```python
class TheravadaProtocol(IProtocol):
    def __init__(self):
        self.seven_purifications = [
            SilaVisuddhi(),           # 戒清浄
            CittaVisuddhi(),          # 心清浄
            DitthiVisuddhi(),         # 見清浄
            KankhaVitaranaVisuddhi(), # 度疑清浄
            MaggamaggaVisuddhi(),     # 道非道智見清浄
            PatipadaVisuddhi(),       # 行道智見清浄
            NanadassanaVisuddhi()     # 智見清浄
        ]
        self.insight_sequence = VipassanaSequence()

    def execute(self, ind: Individual) -> Individual:
        for purification in self.seven_purifications:
            ind = purification.purify(ind)
            if purification.requires_insight:
                ind = self.insight_sequence.run(ind)
        return self._assign_ariya_stage(ind)
```

### 4.3 観智シーケンス（9段階）

```python
class VipassanaSequence:
    insights = [
        UdayabbayaNana(),  # 1. 生滅随観智
        BhangaNana(),       # 2. 壊滅随観智
        BhayaNana(),        # 3. 怖畏智
        AdinavaNana(),      # 4. 過患随観智
        NibbidaNana(),      # 5. 厭離随観智
        MuccitukamyataNana(),  # 6. 脱欲智
        PatisankhaNana(),   # 7. 省察随観智
        SankharupekkhaNana(),  # 8. 行捨智
        AnulomaNana()       # 9. 随順智
    ]

    def run(self, ind: Individual) -> Individual:
        for insight in self.insights:
            ind = insight.observe(ind)
        # 種姓智によるフェーズ移行
        return GotrabhuNana().trigger_transition(ind)
```

### 4.4 KPI（四双八輩マッピング）

```python
def _assign_ariya_stage(self, ind: Individual) -> Individual:
    fetters_cut = ind.get_cut_fetters()
    if {'sakkaya_ditthi', 'vicikiccha', 'silabbata_paramasa'} <= fetters_cut:
        if {'kama_raga', 'vyapada'} <= fetters_cut:
            if len(ind.remaining_asavas) == 0:
                ind.current_stage = Stage.ARAHANT
            else:
                ind.current_stage = Stage.ANAGAMIN
        else:
            ind.current_stage = Stage.SOTAPANNA
    return ind
```

### 4.5 安全機構（種姓智）

`GotrabhuNana.trigger_transition()` は、煩悩の新規流入を遮断する不可逆フラグ `ind.alaya_vijnana.turning_point_reached = True` を立てる。

-----

## 5. Protocol 3: `MahayanaProtocol`（大乗仏教）

### 5.1 責務

主客の実体視を同時解体し、阿頼耶識のレベルで転依（`āśraya-parāvṛtti`）を起こす。

### 5.2 クラス構成

```python
class MahayanaProtocol(IProtocol):
    def __init__(self):
        self.madhyamaka = KamalasilaFourStages()
        self.yogacara = YogacaraEngine()
        self.six_paramitas = SixParamitas()

    def execute(self, ind: Individual) -> Individual:
        ind = self.madhyamaka.deconstruct(ind)   # 主客解体
        ind = self.yogacara.transform_alaya(ind) # 阿頼耶識の転依
        ind = self.six_paramitas.cycle(ind)       # 菩薩道の循環
        return ind
```

### 5.3 中観: カマラシーラ4段階

```python
class KamalasilaFourStages:
    def deconstruct(self, ind: Individual) -> Individual:
        ind = self._usma_murdhan(ind)    # 煖位・頂位: 外界を識と同一視
        ind = self._ksanti(ind)           # 忍位: 唯心への収束
        ind = self._agradharma(ind)       # 世第一法: 不二智
        ind = self._darsanamarga(ind)     # 初地: 無自性の超越
        return ind
```

### 5.4 唯識エンジン

```python
class YogacaraEngine:
    def transform_alaya(self, ind: Individual) -> Individual:
        # 三性の変換: 遍計所執 → 依他起(似有) → 円成実
        for seed in ind.alaya_vijnana.seeds:
            seed = self._purify_seed(seed)
        ind.alaya_vijnana.purity_ratio = self._recalculate_purity(ind)
        ind.manas_bias = max(0.0, ind.manas_bias - 0.5)  # エゴバイアス削減
        if ind.alaya_vijnana.purity_ratio > 0.8:
            ind.alaya_vijnana.turning_point_reached = True  # 転依達成
        return ind
```

### 5.5 六波羅蜜（並行適用サイクル）

```python
class SixParamitas:
    paramitas = [
        Dana(),      # 布施: 余剰リソース循環
        Sila(),      # 持戒: 原則確立
        Ksanti(),    # 忍辱: レイテンシ耐性
        Virya(),     # 精進: 駆動継続
        Dhyana(),    # 禅定: リソース集約
        Prajna()     # 智慧: メタ視座
    ]

    def cycle(self, ind: Individual) -> Individual:
        # 相互干渉する自己組織化ループ
        for _ in range(MAX_ITERATIONS):
            for paramita in self.paramitas:
                ind = paramita.apply(ind)
            if self._is_avaivartika(ind):  # 不退転到達
                break
        return ind
```

-----

## 6. Protocol 4: `VajrayanaProtocol`（密教）

### 6.1 責務

身体（ハードウェア層）を統合し、大日如来との即時同期により `EnlightenedState` へ遷移する。

### 6.2 クラス構成

```python
class VajrayanaProtocol(IProtocol):
    def __init__(self):
        self.abhiseka = Abhiseka()          # 灌頂（参入儀礼）
        self.three_mysteries = ThreeMysteries()
        self.goso_joshingan = GosoJoshingan()
        self.mandala = DualMandala()

    def execute(self, ind: Individual) -> Individual:
        if not self.abhiseka.is_initiated(ind):
            ind = self.abhiseka.initiate(ind)
        ind = self.three_mysteries.synchronize(ind)
        ind = self.goso_joshingan.execute(ind)
        return ind
```

### 6.3 三密の同期

```python
class ThreeMysteries:
    def synchronize(self, ind: Individual) -> Individual:
        ind = KayaGuhya().apply(ind, mudra=ind.current_mudra)     # 身密
        ind = VagGuhya().apply(ind, mantra=ind.current_mantra)    # 口密
        ind = ManoGuhya().apply(ind, visualization="a_ji")        # 意密
        assert ind.body_channels.is_synchronized(), "三密同期失敗"
        return ind
```

### 6.4 五相成身観（5段階の厳密なステートマシン）

```python
class GosoJoshingan:
    stages = [
        Stage1_CittaPrativedham("Om cittaprativedham karomi"),
        Stage2_Bodhicittopadayam("Om bodhicittam utpadayami"),
        Stage3_TisthaVajra("Om tistha vajra"),
        Stage4_Vajratmako("Om vajratmako 'ham"),
        Stage5_SarvatathagataUnion("Om yatha sarvatathagatas tatha 'ham")
    ]

    def execute(self, ind: Individual) -> Individual:
        for stage in self.stages:
            ind = stage.visualize(ind)
            if not stage.verify(ind):
                raise VisualizationFailedException(stage)
        return self._mark_as_buddha(ind)
```

### 6.5 出力

`ind.current_stage = Stage.BUDDHA`、`EnlightenedState` の属性を具備。

-----

## 7. オーケストレータ: `LiberationPipeline`

### 7.1 クラス定義

```python
class LiberationPipeline:
    def __init__(self):
        self.protocols: Dict[ConsciousnessLayer, IProtocol] = {
            ConsciousnessLayer.L6_SURFACE: EarlyBuddhismProtocol(),
            ConsciousnessLayer.L6_REFINED: TheravadaProtocol(),
            ConsciousnessLayer.L7_L8_DEEP: MahayanaProtocol(),
            ConsciousnessLayer.L9_BODY: VajrayanaProtocol()
        }

    def run(self, individual: Individual) -> EnlightenedState:
        # 1. 初期診断
        depth = self._assess_depth(individual)

        # 2. レイヤー順次適用（浅い層から深い層へ）
        current = individual
        for layer in ConsciousnessLayer.ordered_from(depth):
            protocol = self.protocols[layer]
            diagnosis = protocol.diagnose(current)
            cause = protocol.identify_cause(current)

            previous = current
            current = protocol.execute(current)

            verification = protocol.verify(previous, current)
            if not verification.passed:
                raise ProtocolFailedException(layer, verification)

        return EnlightenedState.from_individual(current)

    def _assess_depth(self, ind: Individual) -> ConsciousnessLayer:
        if ind.attachment_level < 0.2:
            return ConsciousnessLayer.L9_BODY
        elif ind.manas_bias < 0.3:
            return ConsciousnessLayer.L7_L8_DEEP
        elif ind.tanha_intensity < 0.5:
            return ConsciousnessLayer.L6_REFINED
        else:
            return ConsciousnessLayer.L6_SURFACE
```

-----

## 8. 例外設計

```python
class KlesaException(Exception):
    """煩悩に起因する例外の基底クラス"""

class AttachmentOverflowException(KlesaException):
    """執着が閾値超過（Upādāna オーバーフロー）"""

class TanhaRuntimeError(KlesaException):
    """渇愛による実行時エラー"""

class AvidyaException(KlesaException):
    """無明（真理への無知）"""

class ProtocolFailedException(Exception):
    """プロトコル検証失敗"""

class VisualizationFailedException(Exception):
    """観想の成立失敗（密教用）"""
```

### 例外ハンドリング戦略

- `KlesaException` は前段プロトコルへロールバックし、再実行
- 3回連続失敗時は一段階浅いプロトコルから再開
- 種姓智到達後は `KlesaException` の発生頻度が構造的に低下する

-----

## 9. 出力: `EnlightenedState`

```python
@dataclass(frozen=True)
class EnlightenedState:
    individual_id: str
    final_stage: Stage                # 通常 Stage.ARAHANT 以上
    three_learnings_completed: bool
    alaya_purity: float               # 1.0 が理想
    turning_point_achieved: bool      # 転依フラグ
    embodied_synchronization: bool    # 三密同期フラグ
    executed_protocols: List[str]
    execution_log: List[LogEntry]

    @classmethod
    def from_individual(cls, ind: Individual) -> "EnlightenedState":
        return cls(...)
```

-----

## 10. 実行フロー図

```
Individual (入力)
    │
    ▼
[LiberationPipeline.run()]
    │
    ▼
┌─────────────────────────┐
│ _assess_depth()         │ ← 介入レイヤー判定
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ EarlyBuddhismProtocol   │ ← L6 表層
│  diagnose → execute     │
└─────────────────────────┘
    │ verify OK
    ▼
┌─────────────────────────┐
│ TheravadaProtocol       │ ← L6 精錬
│  7清浄 → 9観智          │
└─────────────────────────┘
    │ verify OK
    ▼
┌─────────────────────────┐
│ MahayanaProtocol        │ ← L7-L8 深層
│  中観 → 唯識 → 六波羅蜜 │
└─────────────────────────┘
    │ 転依達成
    ▼
┌─────────────────────────┐
│ VajrayanaProtocol       │ ← L9 + 身体
│  灌頂 → 三密 → 五相成身観│
└─────────────────────────┘
    │
    ▼
EnlightenedState (出力)
```

-----

## 11. テスト仕様

### 11.1 ユニットテスト

- 各プロトコルの `diagnose/execute/verify` を独立検証
- `EightfoldPath` の各ステップが冪等であること
- `VipassanaSequence` が9段階を順序通りに実行すること
- `YogacaraEngine` が `purity_ratio` を単調増加させること

### 11.2 統合テスト

- 4段階のパイプラインが `Individual → EnlightenedState` を完遂すること
- 例外発生時のロールバック動作
- 種姓智到達後の不可逆性検証

### 11.3 回帰テスト

- 凡夫（`Stage.PUTHUJJANA`）からの典型的遷移パス
- 既に上座部到達済み個体を大乗から開始するパス
- 密教のみ単独適用の失敗ケース（前段の基盤なし）

### 11.4 受入基準

|項目    |基準                               |
|------|---------------------------------|
|苦の減少率 |tanha_intensity 80%以上削減          |
|転依達成率 |alaya_vijnana.purity_ratio >= 0.8|
|ステージ到達|final_stage >= Stage.ARAHANT     |
|実行ログ  |全プロトコルが順序通り記録されていること             |

-----

## 12. 開発工程への引継ぎ事項

1. **フェーズ1**: `Individual` 及び関連データ構造の実装とバリデーション
1. **フェーズ2**: `IProtocol` インターフェースと `EarlyBuddhismProtocol` の実装
1. **フェーズ3**: `TheravadaProtocol` と観智シーケンスの実装
1. **フェーズ4**: `MahayanaProtocol`（中観・唯識・六波羅蜜）の実装
1. **フェーズ5**: `VajrayanaProtocol`（三密・五相成身観）の実装
1. **フェーズ6**: `LiberationPipeline` の統合とE2Eテスト

### 依存関係

- 各プロトコルは前段プロトコルの完了を前提としない（`_assess_depth` が適切なエントリポイントを決定）
- ただし密教の単独実行は論理的に許可されるが、前段の基盤がない場合は `VisualizationFailedException` で即座に失敗する設計とする

### 拡張ポイント

- 新しい宗派（例: 浄土教、禅）は `IProtocol` を実装することで追加可能
- KPI 閾値は設定ファイル（`protocol_thresholds.yaml`）から注入
- 瞑想セッションの時間軸シミュレーションは別レイヤー（`TemporalSimulator`）として分離

-----

**以上を実装仕様とする。**