# 並列データ収集・統合アーキテクチャ設計書

## ガレージ投資判定システム（関東圏）

-----

## 1. 統合の核心：なぜ「並列収集→融合」が重要か

単一ソースでは以下の問題が発生する：

|問題      |内容                |影響        |
|--------|------------------|----------|
|データ欠損   |アットホームに用途地域が載っていない|台数計算できない  |
|信頼性のバラつき|民間サイトの価格は交渉前の希望価格 |利回りが楽観的すぎる|
|コンフリクト  |公示地価 vs 売出価格が大きく乖離|割高判定を見落とす |
|視点の偏り   |物件情報だけでは需要がわからない  |稼働率の根拠が薄い |

**並列収集→融合により：複数ソースがお互いの欠損・誤りを補完する**

-----

## 2. 信頼度スコア設計

各ソースに固定の信頼度（Reliability Score）を付与し、融合時の重みづけに使う。

```
公的機関ソース（更新頻度は低いが精度高）
├── 国土数値情報 GIS          : 0.98
├── ハザードマップポータル     : 0.96
├── 国交省 不動産取引価格API   : 0.95
├── 国交省 地価公示            : 0.93
├── e-Stat 人口統計            : 0.92
└── 自検協 自動車保有統計      : 0.90

民間ソース（リアルタイム性高いが精度変動）
├── 特P / akippa（賃料相場）   : 0.78
├── 楽待（利回り実績）         : 0.75
└── アットホーム（売地情報）   : 0.72
```

### 信頼度加重平均の適用例（土地価格推定）

```python
# 例：㎡単価の融合
values = {
    "国交省取引価格API": (155_000, 0.95),   # 金額, 信頼度
    "公示地価":         (148_000, 0.93),
    "アットホーム換算": (192_000, 0.72),    # 希望価格なので高め
}

weighted_sum = sum(v * w for v, w in values.values())
weight_sum   = sum(w for _, w in values.values())
fused_price  = weighted_sum / weight_sum
# → 163,400円/㎡（単純平均より公的データ寄り）
```

-----

## 3. コンフリクト検出ロジック

ソース間で同じ項目が食い違う場合、自動でフラグを立てる。

```python
CONFLICT_RULES = {
    # (ソースA, ソースB): (項目名, 許容乖離率)
    ("athome_price",  "reinfolib_price"):  ("㎡単価", 0.20),   # 20%超で警告
    ("ksjgis_zone",   "reinfolib_zone"):   ("用途地域", 0.0),   # 不一致で警告
    ("tokup_rent",    "rakumachi_yield"):   ("想定賃料整合", 0.25),
}

def detect_conflicts(fused_data):
    alerts = []
    for (key_a, key_b), (label, threshold) in CONFLICT_RULES.items():
        val_a = fused_data.get(key_a)
        val_b = fused_data.get(key_b)
        if val_a and val_b:
            gap = abs(val_a - val_b) / val_b
            if gap > threshold:
                alerts.append({
                    "item": label,
                    "gap_pct": round(gap * 100, 1),
                    "action": "現地調査推奨" if gap > 0.30 else "要注意"
                })
    return alerts
```

### コンフリクト時のアクション定義

|乖離率     |対応               |
|--------|-----------------|
|～20%    |公的データを優先採用・ログ記録  |
|20〜30%  |警告フラグ＋レポートに注記    |
|30%超    |スコアを減点＋「現地調査必須」表示|
|用途地域の不一致|処理を一時停止・手動確認を要求  |

-----

## 4. 並列収集の実装パターン

```python
import asyncio
import aiohttp
from dataclasses import dataclass
from typing import Any

@dataclass
class SourceResult:
    source_id: str
    data: dict[str, Any]
    reliability: float
    latency_ms: int
    success: bool
    error: str | None = None

async def fetch_all_sources(property_info: dict) -> list[SourceResult]:
    """
    全ソースを並列取得。
    失敗したソースはスキップし、成功分だけで融合する。
    """
    tasks = [
        fetch_reinfolib(property_info),
        fetch_estat(property_info),
        fetch_ksjgis(property_info),
        fetch_hazard(property_info),
        fetch_airia(property_info),
        fetch_athome(property_info),
        fetch_tokup(property_info),
        fetch_rakumachi(property_info),
    ]
    
    # タイムアウト付きで全タスク実行（失敗してもキャンセルしない）
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return [
        r if isinstance(r, SourceResult)
        else SourceResult(source_id="unknown", data={}, reliability=0, 
                         latency_ms=0, success=False, error=str(r))
        for r in results
    ]

async def fetch_reinfolib(prop: dict) -> SourceResult:
    """国交省 不動産取引価格情報API"""
    import time
    start = time.time()
    
    url = "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT001"
    params = {
        "year": "2024",
        "area": prop["prefecture_code"],  # 埼玉=11 など
        "city": prop["city_code"],
        "priceClassification": "01",  # 宅地(土地)
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
    
    latency = int((time.time() - start) * 1000)
    return SourceResult(
        source_id="reinfolib",
        data=parse_reinfolib(data, prop),
        reliability=0.95,
        latency_ms=latency,
        success=True
    )
```

### タイムアウト戦略

```
公的API     : timeout=15s（安定しているが遅い場合あり）
民間スクレイピング: timeout=20s（レンダリング待ちあり）
GISデータ   : timeout=10s（CDNから配信、速い）

部分的な結果での融合：
- 必須ソース（GIS + ハザード）が揃えば処理続行
- 民間ソースは取れた分だけ使う
- 最低4ソース揃わなければ「データ不足」として結果保留
```

-----

## 5. データ正規化レイヤー

各ソースからバラバラで返ってくるデータを共通スキーマに変換する。

```python
# 共通スキーマ（全ソースの出力をここに統一）
UNIFIED_SCHEMA = {
    # 土地情報
    "land": {
        "area_sqm": float,           # 面積（㎡）
        "price_jpy": int,            # 価格（円）
        "price_per_sqm": float,      # ㎡単価
        "address_normalized": str,   # 正規化済み住所
        "lat": float,
        "lng": float,
    },
    # 法規制
    "regulation": {
        "use_zone": str,             # 用途地域
        "building_coverage": float, # 建ぺい率
        "floor_area_ratio": float,  # 容積率
    },
    # リスク
    "risk": {
        "flood_depth_m": float,     # 想定浸水深
        "landslide_risk": bool,
        "tsunami_risk": bool,
    },
    # 需要指標
    "demand": {
        "car_ownership_rate": float, # 世帯あたり保有台数
        "population": int,
        "nearby_parking_count": int, # 500m圏内の競合数
        "avg_nearby_rent": int,      # 近隣月額賃料（円）
    },
}

# 正規化例：住所の統一
def normalize_address(raw: str) -> str:
    """
    「埼玉県さいたま市大宮区○○1-2-3」→ 国土地理院ジオコーダで緯度経度に変換
    複数ソース間で住所表記ゆれを吸収する
    """
    url = f"https://geocoding.gsi.go.jp/geocoding/address/query?q={raw}"
    # ... geocoding処理
```

-----

## 6. ガレージ最適化計算エンジン

融合済みデータを受け取り、投資指標を計算する。

```python
def calculate_garage_metrics(fused: dict) -> dict:
    
    area       = fused["land"]["area_sqm"]
    land_price = fused["land"]["price_jpy"]
    coverage   = fused["regulation"]["building_coverage"]  # 0.6など
    
    # --- 台数計算 ---
    # 普通車: 5.3m × 2.5m = 13.25㎡ + 通路・壁厚 → 約28㎡/台
    # 大型・趣味車: 約40㎡/台
    buildable_area = area * coverage
    
    garage_options = {
        "標準型（普通車）":  {"sqm_per_unit": 28,  "monthly_rent": fused["demand"]["avg_nearby_rent"]},
        "ゆとり型（趣味車）": {"sqm_per_unit": 40,  "monthly_rent": int(fused["demand"]["avg_nearby_rent"] * 1.4)},
        "コンテナ型":        {"sqm_per_unit": 35,  "monthly_rent": int(fused["demand"]["avg_nearby_rent"] * 1.2)},
    }
    
    results = {}
    for plan_name, spec in garage_options.items():
        count = int(buildable_area / spec["sqm_per_unit"])
        build_cost = count * 380_000      # 1台あたり建設費概算
        total_investment = land_price + build_cost
        
        # 稼働率：競合数・人口密度・車保有率から推定
        occupancy = estimate_occupancy(fused)
        
        annual_revenue = count * spec["monthly_rent"] * occupancy * 12
        yield_rate = annual_revenue / total_investment * 100
        payback_years = total_investment / annual_revenue
        
        results[plan_name] = {
            "unit_count":        count,
            "build_cost":        build_cost,
            "total_investment":  total_investment,
            "monthly_revenue":   int(count * spec["monthly_rent"] * occupancy),
            "yield_rate":        round(yield_rate, 2),
            "payback_years":     round(payback_years, 1),
        }
    
    return results

def estimate_occupancy(fused: dict) -> float:
    """自動車保有率・競合数・人口密度から稼働率を推定"""
    base = 0.85
    car_rate   = fused["demand"]["car_ownership_rate"]
    competitor = fused["demand"]["nearby_parking_count"]
    pop        = fused["demand"]["population"]
    
    # 車保有率が高い地域はプラス補正
    base += (car_rate - 1.0) * 0.1
    # 競合が多い地域はマイナス補正
    base -= min(competitor * 0.02, 0.15)
    # 人口密集地はプラス補正
    base += min((pop / 100_000) * 0.03, 0.05)
    
    return max(0.60, min(0.95, base))
```

-----

## 7. Claude APIによる最終評価生成

計算結果をそのまま渡し、投資判断コメントを自動生成する。

```python
import anthropic

def generate_investment_report(fused: dict, metrics: dict, conflicts: list) -> str:
    
    client = anthropic.Anthropic()
    
    prompt = f"""
以下は関東圏の土地物件の統合分析データです。
ガレージ投資として適切かどうかを評価してください。

## 物件概要
{fused["land"]}

## 規制情報
{fused["regulation"]}

## リスク情報
{fused["risk"]}

## 需要指標
{fused["demand"]}

## ガレージ計画別試算
{metrics}

## データ品質アラート
{conflicts if conflicts else "コンフリクトなし"}

## 出力形式
- 総合評価（S/A/B/C）と理由（3行以内）
- 最も推奨するガレージプランと根拠
- 投資判断上の最大リスク（2点）
- 追加調査が必要な項目（あれば）
"""
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text
```

-----

## 8. 実装フロー（まとめ）

```
1. ユーザーが検索条件を入力
   └ エリア（市区町村）・予算・最低面積

2. 物件URLリストをアットホームからスクレイピング
   └ 各物件の住所・面積・価格を取得

3. 物件ごとに並列データ取得ジョブを起動
   └ asyncio.gather で8ソース同時実行

4. 正規化レイヤーで共通スキーマに変換
   └ 住所のジオコーディング（国土地理院API）

5. コンフリクト検出
   └ ソース間の食い違いをフラグ化

6. 信頼度加重融合
   └ 公的データ優先・民間は補完として利用

7. ガレージ計算エンジン実行
   └ 3プラン（標準・ゆとり・コンテナ）の利回り試算

8. Claude API で投資評価レポート生成

9. CSV / Notion に出力
   └ ソートキー：品質スコア × 利回り
```

-----

## 9. 品質スコア計算式

```python
def calculate_quality_score(results: list[SourceResult]) -> float:
    """
    取得できたソースの信頼度平均 × 必須ソース充足率
    """
    required_sources = {"ksjgis", "hazard", "reinfolib"}
    
    achieved = {r.source_id for r in results if r.success}
    required_ratio = len(required_sources & achieved) / len(required_sources)
    
    avg_reliability = sum(r.reliability for r in results if r.success) / len(results)
    
    score = avg_reliability * required_ratio * 100
    return round(score, 1)

# スコア目安
# 90点以上：信頼度高い → そのまま投資判断に使える
# 70〜89点：注意が必要な項目あり → 警告表示
# 70点未満：データ不足 → 手動補完を推奨
```

-----

## 10. 技術スタック

|役割      |ライブラリ / サービス               |
|--------|---------------------------|
|並列HTTP  |`aiohttp` + `asyncio`      |
|スクレイピング |`playwright` (JS対応)        |
|GISデータ処理|`geopandas` + `shapely`    |
|データ変換   |`pandas`                   |
|住所正規化   |国土地理院 ジオコーディングAPI          |
|AI評価    |`anthropic` SDK            |
|出力      |`pandas → CSV` / Notion API|
|定期実行    |GitHub Actions (cron)      |