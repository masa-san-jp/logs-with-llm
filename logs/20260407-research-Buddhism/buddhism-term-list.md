# 仏教用語 → 一般用語 → Python命名 対応表

仏教プロトコルを実装可能な形に翻訳するため、各用語を「一般用語」「Python命名（クラス/関数/変数）」「概要」の4カラムで整理する。命名規則はPEP8準拠（クラス=PascalCase、関数=snake_case、定数=UPPER_SNAKE_CASE）。

-----

## 1. 原始仏教：苦の因果プロトコル

### 1-1. 四諦とコア概念

|仏教用語      |一般用語       |Python命名                               |概要                       |
|----------|-----------|---------------------------------------|-------------------------|
|四諦        |因果分析フレームワーク|`class FourTruthsFramework`            |問題の結果・原因・理想・手段を4象限で捉える分析器|
|苦諦        |現状の問題定義    |`def diagnose_current_state()`         |「思い通りにならない」状態を列挙する関数     |
|集諦        |根本原因の特定    |`def identify_root_cause()`            |問題を駆動する真のドライバを抽出         |
|滅諦        |理想状態の定義    |`def define_target_state()`            |問題が解消された後のあるべき姿を設計       |
|道諦        |実行計画       |`def build_action_plan()`              |理想状態への具体的オペレーションを構築      |
|苦（ドゥッカ）   |期待と現実の不整合  |`expectation_reality_gap: float`       |予測値と実測値の乖離を表す指標          |
|渇愛（トリシュナー）|執着駆動の欲求エンジン|`class CravingEngine`                  |エゴを維持・拡張しようとする心理駆動力      |
|行（サンカーラ）  |潜在的形成力・バイアス|`latent_conditioning: dict`            |過去の経験が未来の反応を形成する潜在パラメータ  |
|縁起        |相互依存の因果網   |`class DependencyGraph`                |事象を相互依存ノードとして表現するグラフ構造   |
|無明        |認知バイアス・無自覚 |`cognitive_blind_spot: bool`           |真理への無知状態を示すフラグ           |
|五蘊        |自己を構成する5要素 |`class SelfAggregates`                 |身体・感覚・概念・意志・識別の合成体       |
|五蘊盛苦      |自己実体視による過負荷|`def detect_self_attachment_overload()`|五蘊への執着を検出する関数            |
|涅槃        |最適定常状態     |`NIRVANA_STATE: Final`                 |ノイズに左右されない恒常的平衡          |
|中道        |極端を回避したバランス|`def apply_middle_way()`               |リソース配分を両極端から中央値に寄せる      |

### 1-2. 八正道（実行チェックリスト）

|仏教用語|一般用語        |Python命名                               |概要                |
|----|------------|---------------------------------------|------------------|
|八正道 |行動最適化チェックリスト|`class EightfoldPath`                  |8項目の行動規範を管理するクラス  |
|正見  |正しい認知フレーム   |`def set_correct_worldview()`          |因果律に基づく世界認識を初期化   |
|正思  |思考の浄化       |`def purify_thought()`                 |執着・怒り・害意を除外するフィルタ |
|正語  |通信プロトコルの最適化 |`def sanitize_communication()`         |真実で有益な発話のみを許可     |
|正業  |行動規範の遵守     |`def enforce_ethical_action()`         |倫理制約下での行動実行       |
|正命  |持続可能な生計     |`def maintain_sustainable_livelihood()`|合法的・道徳的な収入源の確立    |
|正精進 |継続的改善       |`def continuous_improvement()`         |善の増進と悪の抑止ループ      |
|正念  |常時モニタリング    |`class Mindfulness`                    |心身状態をリアルタイム監視する観測器|
|正定  |深い集中状態      |`def enter_deep_focus()`               |認知解像度を最大化する集中モード  |
|現観  |直感的覚知イベント   |`on_insight_fired()`                   |因果を直接把握した瞬間のコールバック|

-----

## 2. 上座部仏教：段階的精錬プロトコル

### 2-1. 三学と七清浄

|仏教用語    |一般用語       |Python命名                        |概要             |
|--------|-----------|--------------------------------|---------------|
|三学      |到達度KPI三軸   |`class ThreefoldTraining`       |戒・定・慧の3次元で進捗を測定|
|戒（シーラ）  |行動規範の基盤    |`discipline_score: float`       |生活基盤の安定度指標     |
|定（サマディ） |集中力の養成     |`concentration_level: float`    |意識のノイズ除去度      |
|慧（パンニャー）|真理洞察力      |`wisdom_score: float`           |現象の本質を見抜く能力値   |
|七清浄     |7段階進捗マネジメント|`class SevenPurifications(Enum)`|解脱への7つのフェーズ列挙  |
|戒清浄     |基盤構築フェーズ   |`PHASE_1_ETHICAL_BASE`          |行動規範の確立段階      |
|心清浄     |ノイズ除去フェーズ  |`PHASE_2_MENTAL_CLARITY`        |集中によるノイズ削減段階   |
|見清浄     |名色分離フェーズ   |`PHASE_3_NAME_FORM_SPLIT`       |精神と物質を識別する段階   |
|度疑清浄    |因果把握フェーズ   |`PHASE_4_CAUSALITY_CLEAR`       |因果関係への疑問を解消    |
|道非道智見清浄 |正誤識別フェーズ   |`PHASE_5_PATH_DISCRIMINATION`   |正しい道と誤った道を見分ける |
|行道智見清浄  |実行精錬フェーズ   |`PHASE_6_PRACTICE_REFINEMENT`   |観智を深化させる実行段階   |
|智見清浄    |最終到達フェーズ   |`PHASE_7_FINAL_INSIGHT`         |四諦を直接知る出世間智    |

### 2-2. 観智9段階と三遍知

|仏教用語 |一般用語    |Python命名                          |概要               |
|-----|--------|----------------------------------|-----------------|
|観智   |洞察的観察   |`class InsightObserver`           |現象を詳細観察する観測器基底クラス|
|生滅随観智|発生消滅の検出 |`def observe_arising_passing()`   |現象の生滅サイクルを捕捉     |
|壊滅随観智|崩壊面の注視  |`def focus_on_dissolution()`      |実体性を否定する観察       |
|怖畏智  |無依拠の認識  |`def recognize_no_refuge()`       |現象を拠り所なきものと認識    |
|過患随観智|欠陥の発見   |`def detect_defects()`            |現象のリスクと過失を抽出     |
|厭離随観智|離脱欲求の生起 |`def trigger_disenchantment()`    |執着離脱への動機を生成      |
|脱欲智  |解放への志向  |`def seek_liberation()`           |束縛からの離脱を志向       |
|省察随観智|三相での再評価 |`def reassess_three_marks()`      |苦・無常・無我で再観察      |
|行捨智  |平静の確立   |`def establish_equanimity()`      |中立・平等な心的状態を保持    |
|随順智  |四諦への適合  |`def align_with_four_truths()`    |聖者位への接続準備        |
|三遍知  |理解の3深度  |`class ThreeLevelsOfUnderstanding`|個別→共通→執着切断の3段階   |
|知遍知  |個別理解    |`individual_comprehension`        |名色と因果を個別に識別      |
|度遍知  |共通理解    |`universal_comprehension`         |三相を全事象の原理として把握   |
|断遍知  |執着切断    |`attachment_severance`            |誤認識を実効的に捨てる段階    |
|種姓智  |OS切替トリガー|`def trigger_os_migration()`      |凡夫から聖者への不可逆フェーズ移行|

### 2-3. 四双八輩と煩悩

|仏教用語    |一般用語      |Python命名                        |概要            |
|--------|----------|--------------------------------|--------------|
|凡夫      |未到達ユーザー   |`class OrdinaryUser`            |聖者位未達成の主体     |
|聖者      |到達済みユーザー  |`class NobleUser`               |預流者以上の階位に達した主体|
|預流者     |Lv1到達者    |`class StreamEnterer(NobleUser)`|三結を断った初期聖者    |
|一来者     |Lv2到達者    |`class OnceReturner(NobleUser)` |欲貪・瞋恚を希薄化した聖者 |
|不還者     |Lv3到達者    |`class NonReturner(NobleUser)`  |五下分結を断滅した聖者   |
|阿羅漢     |Lv4最終到達者  |`class Arahant(NobleUser)`      |全煩悩を滅尽した究極状態  |
|煩悩      |心理的ノイズ    |`class MentalDefilement`        |認知を汚染する心理作用   |
|漏（āsava）|流入ノイズ     |`defilement_inflow: Stream`     |システムへの新規ノイズ流入 |
|有漏      |ノイズ保持状態   |`has_residual_noise: bool`      |既存ノイズを保持している状態|
|無漏      |ノイズ遮断状態   |`is_noise_sealed: bool`         |新規ノイズ流入を遮断した状態|
|三結      |初期削除対象バグ3種|`INITIAL_BUGS = [...]`          |有身見・疑・戒禁取     |
|サンガ     |実践コミュニティ  |`class PracticeCommunity`       |修行者の共同体       |
|三蔵      |三層ドキュメント体系|`class Tipitaka`                |律・経・論の3カテゴリ   |

-----

## 3. 大乗仏教：主客同時解体プロトコル

### 3-1. 空と中観

|仏教用語        |一般用語      |Python命名                      |概要               |
|------------|----------|------------------------------|-----------------|
|空（śūnyatā）  |実体なき関係性   |`class Emptiness`             |固有実体の非存在を表すプリミティブ|
|人法二無我       |主体・客体の両面否定|`def deny_self_and_object()`  |主客双方の実体性を否定      |
|中観          |両極否定のロジック |`class MadhyamakaLogic`       |有無両極端を排する論理エンジン  |
|戯論（prapañca）|言語による概念拡張 |`verbal_proliferation: list`  |言語が生む不要な概念インフレ   |
|相依性         |相互依存関係    |`def is_mutually_dependent()` |要素間の依存を判定        |
|色即是空        |現象=関係性    |`def phenomena_to_relations()`|実体を関係性へ変換        |
|空即是色        |関係性=現象    |`def relations_to_phenomena()`|関係性から現象を生成       |
|不二智         |主客非分離の認識  |`class NonDualCognition`      |二項対立を超えた認識モード    |

### 3-2. 唯識と八識

|仏教用語                |一般用語       |Python命名                        |概要              |
|--------------------|-----------|--------------------------------|----------------|
|唯識                  |認識論的一元論    |`class CognitionOnlyModel`      |世界を認識の産物として扱うモデル|
|八識                  |認識の8レイヤー   |`class EightConsciousnessLayers`|感覚から深層ストレージまでの階層|
|前五識                 |5感覚入力      |`sensory_inputs: tuple`         |視聴嗅味触の生データ      |
|意識                  |概念化層       |`class ConceptualLayer`         |言語によるラベリング処理    |
|末那識                 |エゴ層        |`class EgoLayer`                |自我執着を生む無意識層     |
|阿頼耶識                |ローカルストレージ  |`class StorehouseConsciousness` |経験と種子を蓄積する深層DB  |
|阿摩羅識                |クラウド接続層    |`class UniversalConsciousness`  |個を超えた根源への接続層    |
|種子（bīja）            |潜在的傾向データ   |`class Seed`                    |未来の行動を生む潜在パターン  |
|薫習                  |経験の書き込み    |`def imprint_experience()`      |行為を種子として蓄積する処理  |
|三性                  |存在の3モード    |`class ThreeNatures(Enum)`      |実存の3つの性質列挙      |
|遍計所執性               |妄想された実体    |`DELUSIONAL_CONSTRUCT`          |言語により錯認された主客対立  |
|依他起性                |縁起的発生      |`DEPENDENTLY_ARISEN`            |因縁により生起する現象流    |
|円成実性                |ありのままの真実   |`PERFECTED_NATURE`              |妄想を排した後の真実      |
|転依（āśraya-parāvṛtti）|認識基盤の切替    |`def transform_base()`          |汚染された基盤を純粋なものへ変換|
|似有                  |シミュレートされた現実|`simulated_reality: bool`       |仮措定された依他起性の仕様   |

### 3-3. 華厳と菩薩道

|仏教用語|一般用語       |Python命名                     |概要                  |
|----|-----------|-----------------------------|--------------------|
|事事無礙|全要素の無障害相互作用|`class FullMeshInteraction`  |全ノードが相互貫入するネット構造    |
|相入  |作用の相互流入    |`def mutual_function_flow()` |他要素への作用浸透           |
|相即  |存在の相互重合    |`def mutual_identity()`      |存在そのものの相互置換         |
|有力  |主導的作用      |`dominant_force: float`      |全体を主導する作用値          |
|無力  |受動的作用      |`passive_force: float`       |主導に従属する作用値          |
|菩薩  |自他救済型エージェント|`class Bodhisattva`          |自己解脱と他者救済を両立するエージェント|
|菩提心 |覚醒への動機     |`awakening_motivation: float`|真理追求のドライバ変数         |
|大悲  |普遍的救済意志    |`universal_compassion: float`|全対象への救済志向           |
|方便  |手段の柔軟な選択   |`def select_skillful_means()`|状況適応型の手段選択器         |

### 3-4. 六波羅蜜

|仏教用語|一般用語    |Python命名                        |概要                |
|----|--------|--------------------------------|------------------|
|六波羅蜜|菩薩の6行動原則|`class SixPerfections`          |自己組織化サイクルを回す6メソッド |
|布施  |リソース分配  |`def give_resources()`          |余剰を他者へ分配する関数      |
|持戒  |原則の維持   |`def maintain_principles()`     |アイデンティティを環境ノイズから防護|
|忍辱  |逆境耐性    |`def endure_adversity()`        |システム停止を防ぐ耐性レイヤ    |
|精進  |継続駆動    |`def sustain_effort()`          |最短経路での継続的実行       |
|禅定  |リソース集中  |`def concentrate_resources()`   |注意リソースを一点集約       |
|智慧  |メタ視座の獲得 |`def acquire_meta_perspective()`|統合的な本質把握          |

-----

## 4. 密教：身体統合即時プロトコル

### 4-1. 三密と即身成仏

|仏教用語      |一般用語        |Python命名                      |概要             |
|----------|------------|------------------------------|---------------|
|即身成仏      |現状態での即時変容   |`def instant_transformation()`|漸進モデルを排した即時同期関数|
|三密        |3チャネル同期プロトコル|`class ThreefoldSync`         |身体・言語・精神の同時同期  |
|身密        |身体チャネル      |`body_channel: Mudra`         |印による身体エネルギー同期  |
|口密        |言語チャネル      |`speech_channel: Mantra`      |真言による振動同期      |
|意密        |精神チャネル      |`mind_channel: Visualization` |観念による認識同期      |
|印（Mudra）  |身体的シグナチャ    |`class Mudra`                 |手指形状による身体プロトコル |
|真言（Mantra）|音声的パスワード    |`class Mantra`                |特定周波数を持つ音声コード  |
|加持        |双方向同期プロセス   |`def bidirectional_sync()`    |源泉と主体の相互浸透処理   |
|加         |源泉からの注入     |`def inject_from_source()`    |源泉の働きを主体へ注入    |
|持         |主体による受容     |`def receive_with_awareness()`|注入を自覚的に保持      |
|阿字（A-ji）  |解体的プリミティブ   |`DECONSTRUCTIVE_PRIMITIVE`    |既存概念を解体する否定記号  |
|邪気        |感情的過積載      |`emotional_overload: float`   |蓄積された外来ノイズ量    |

### 4-2. 曼荼羅と灌頂

|仏教用語  |一般用語      |Python命名                            |概要              |
|------|----------|------------------------------------|----------------|
|曼荼羅   |宇宙構造マップ   |`class Mandala`                     |宇宙の構造を可視化したマップ  |
|胎蔵界曼荼羅|慈悲原理マップ   |`class WombRealmMandala(Mandala)`   |理・慈悲の展開構造       |
|金剛界曼荼羅|智慧原理マップ   |`class DiamondRealmMandala(Mandala)`|智慧と作用の体系        |
|両部不二  |2マップの統合   |`def unify_dual_mandalas()`         |慈悲と智慧を統合する関数    |
|大日如来  |宇宙根源インスタンス|`COSMIC_ROOT: Singleton`            |全存在の源泉シングルトン    |
|灌頂    |初期化セレモニー  |`def initialize_practitioner()`     |修行者を曼荼羅へ参入させる初期化|
|阿闍梨   |認定インストラクタ |`class CertifiedMaster`             |プロトコル伝授権限を持つ指導者 |

### 4-3. 五相成身観

|仏教用語      |一般用語     |Python命名                      |概要               |
|----------|---------|------------------------------|-----------------|
|五相成身観     |5段階同化プロセス|`class FiveStepIdentification`|大日如来との同化5ステップ    |
|通達菩提心     |菩提心の検知   |`def detect_awakening_mind()` |阿頼耶識奥底の月輪を朧月として観察|
|月輪        |清浄心の可視化体 |`moon_disc: VisualObject`     |菩提心を表す円形シンボル     |
|修菩提心      |菩提心の精錬   |`def refine_awakening_mind()` |月輪を16分割で満月へ完成    |
|成金剛心      |智慧の顕現    |`def manifest_diamond_mind()` |月輪中に金剛杵を出現させる    |
|金剛杵（Vajra）|不壊の智慧体   |`class VajraScepter`          |鋭利かつ不壊な智慧シンボル    |
|証金剛身      |全身への浸透   |`def pervade_body()`          |金剛性を身体全体へ拡張      |
|入我        |源泉の自己流入  |`def source_enters_self()`    |大日如来が主体へ流入する処理   |
|我入        |自己の源泉流入  |`def self_enters_source()`    |主体が大日如来へ流入する処理   |
|仏身円満      |完全同化状態   |`class FullyMergedState`      |個体境界が消滅した合一状態    |
|法爾瑜伽      |無我の大我状態  |`NATURAL_YOGA_STATE: Final`   |エゴ消去後に立ち上がる普遍主体  |

-----

## 5. 使用ガイドライン

### 5-1. クラス階層の設計イメージ

```python
# 基底プロトコル
class BuddhistProtocol(ABC):
    @abstractmethod
    def diagnose(self): ...
    @abstractmethod
    def intervene(self): ...

# 各段階の実装
class PrimitiveBuddhism(BuddhistProtocol): ...  # 四諦+八正道
class Theravada(BuddhistProtocol): ...           # 七清浄+観智
class Mahayana(BuddhistProtocol): ...            # 空+唯識+六波羅蜜
class Vajrayana(BuddhistProtocol): ...           # 三密+五相成身観
```

### 5-2. 介入レイヤーによる使い分け

|問題の深度    |選択すべきクラス           |主要メソッド                                    |
|---------|-------------------|------------------------------------------|
|表層の行動ノイズ |`PrimitiveBuddhism`|`EightfoldPath` の各メソッド                    |
|段階的な精神精錬 |`Theravada`        |`InsightObserver` の9段階                    |
|深層の認知バイアス|`Mahayana`         |`transform_base()` + `SixPerfections`     |
|身体統合全方位  |`Vajrayana`        |`ThreefoldSync` + `FiveStepIdentification`|

### 5-3. 命名規則のポリシー

- **抽象概念** → クラス名（PascalCase）: `Emptiness`, `DependencyGraph`
- **プロセス・動作** → 関数名（snake_case）: `purify_thought()`, `transform_base()`
- **状態・指標** → 変数名（snake_case）: `concentration_level`, `defilement_inflow`
- **不変の到達点** → 定数（UPPER_SNAKE_CASE）: `NIRVANA_STATE`, `COSMIC_ROOT`

-----

この対応表を参照することで、抽象的な仏教概念を実装可能な関数・クラス・変数として扱うことが可能になり、プロトコルの再現性と検証可能性が大幅に向上する。