# プロジェクト概要: 組織の意思決定プロセス可視化パイプライン
あなたは優秀なシニアエンジニアです。Google Workspace CLI経由で取得したチャットログや行動ログを解析し、LLMを用いて「組織の暗黙知や意思決定のボトルネック」を抽出するデータパイプラインを構築してください。

## 技術スタック
- 言語: Python 3.11+
- データバリデーション・スキーマ定義: Pydantic
- LLM連携: Anthropic SDK (または OpenAI SDK / 任意のLLM API)
- その他: python-dotenv (環境変数管理)

## ディレクトリ構成（推奨）
```text
.
├── core/
│   ├── extractors.py    # Google Workspace CLI/APIからデータを取得する処理
│   ├── processors.py    # PII（個人情報）マスキングやデータクレンジング
│   └── llm_analyzer.py  # LLMへのプロンプト構築と構造化データ抽出
├── schemas/
│   ├── input_models.py  # 生ログのPydanticモデル
│   └── output_models.py # LLMが出力するインサイトのPydanticモデル
├── main.py              # パイプラインの実行エントリーポイント
└── .env                 # APIキーやSpace IDの管理
```

## データスキーマ定義 (Pydantic)
以下のスキーマを schemas/ ディレクトリに実装してください。LLMには Structured Output (Tool calling / JSON mode) を使用し、必ず InsightReport の形式で出力させます。

1. 入力ログのスキーマ (input_models.py)

```Python
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class ChatMessage(BaseModel):
    timestamp: datetime
    author_id: str # 個人を特定しないハッシュ値や "Member_A" などに置換済みであること
    text: str
    thread_id: Optional[str] = None

class SpaceLog(BaseModel):
    space_id: str
    messages: List[ChatMessage]
```

2. 出力インサイトのスキーマ (output_models.py)

```Python
from pydantic import BaseModel, Field
from typing import List

class ActionItem(BaseModel):
    owner: str = Field(..., description="タスクの担当者（推測される場合）")
    task: str = Field(..., description="実行すべきネクストアクション")
    is_pending: bool = Field(..., description="合意が取れておらず宙に浮いているか")

class InsightReport(BaseModel):
    driving_factors: List[str] = Field(..., description="意思決定を前に進めた要因や発言のパターン")
    bottlenecks: List[str] = Field(..., description="議論が停滞した要因（例：特定人物の承認待ち、要件の曖昧さ）")
    implicit_rules: List[str] = Field(..., description="明文化されていないが、メンバー間で前提となっている暗黙のルール")
    improvement_proposals: List[str] = Field(..., description="自動化やプロセス改善に向けた具体的な提言")
    action_items: List[ActionItem] = Field(..., description="抽出された具体的なネクストアクション")
```

## 実装のステップ

エージェントは以下の順序で実装を進めてください。
- schemas/ フォルダを作成し、上記のPydanticモデルを実装する。
- core/processors.py に、ダミーのJSONログ（生のチャットテキスト）を読み込み、個人名を Member_A, Member_B にマスキングして SpaceLog オブジェクトに変換する関数を実装する。
- core/llm_analyzer.py に、SpaceLog を受け取り、LLM APIを呼び出して InsightReport オブジェクトを返す処理を実装する。
- main.py でこれらを結合し、ローカルのダミーデータでテスト実行できるようにする。
