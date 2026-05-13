# ローカルマルチエージェント物語生成システム  
～主人公主導のHero's Journey自動生成～

## 1. 背景・元アイデア（ユーザーのX投稿より）
ユーザーは「独自のナラティブを持つ物語の主要キャラクターを瞬時に生成し、そこから人物相関を無限に拡張できる方法」を着想。  

**目標**:  
ローカル環境（Ollamaなど）で、**主人公だけが大まかなジャーニーロードマップを持ち、他のキャラクターは知らずに会話を通じてそれを達成・変化させていく**物語生成システムを構築する。

## 2. 核心的な仮説（Hypothesis）
1. **「場への発言」モデル**が自然な会話を生む  
   1対1直接通信ではなく、共有会話ログ（Blackboard/GroupChat）に対して各エージェントが「これまでの全発言を読んで反応する」方式にすることで、予測不能で有機的な展開が生まれる。

2. **主人公のみロードマップ保有**  
   主人公だけがHero's Journeyの大まかなステージ目標を持ち、他のキャラクターは純粋に「その場の性格・目標・感情」で行動させる。これにより、主人公が「会話という武器でロードマップを攻略する」ダイナミクスが発生する。

3. **小さく始めて拡散させる**  
   最初は固定3ステージ・固定3ターン・最小エージェントで「必ず完結する物語」を生成できる状態にし、徐々にステージ数・キャラクター数・自動分岐・記憶拡張を加えることで、無限拡張性を持たせられる。

4. **完結保証＋改善ループ**  
   強制エンディング＋完結確認エージェントにより、毎回「読める物語」が完成する。人間評価を挟むことで品質が段階的に向上する。

## 3. 設計思想（Design Philosophy）
- **主人公主導（Protagonist-Driven）**: 物語の方向性は主人公の内部ロードマップが握る。他のエージェントは「生きているキャラクター」として振る舞うのみ。
- **共有コンテキスト（Shared Field）**: 全エージェントが同じ会話履歴を読み、反応する。直接的な「指示送信」は避ける。
- **段階的拡張性（Incremental Scalability）**: Phase 0は純Pythonループで1時間以内に動く最小形。以降でAutoGen/LangGraphへ移行し、キャラクター動的生成・並列シーン・ビジュアル連携へ拡散。
- **ローカル完結**: Ollamaのみ使用。外部API依存ゼロ。
- **必ず完結**: ステージ数固定＋強制Ending Generatorで、未完物語を絶対に出さない。
- **人間-in-the-Loop改善**: 各Phase終了時に生成物語を評価し、次の改善点を明確化。
- **再現性と枝分かれ**: 同じシードでも会話次第で異なる展開になるよう、temperature 0.8前後を推奨。

## 4. 開発ロードマップ（全6フェーズ）

### Phase 0: 超最小実験（1日で完成）
- ステージ数: 3固定
- 会話: 各ステージ最大3ターン固定
- エージェント: 主人公＋2名（師匠、凛）
- 実装: 純Pythonループ（AutoGen未使用）
- 完結: 強制Ending Generator
- 目標: とにかく動くものを即生成

### Phase 1: 基本フレーム完成（2〜3日）
- AutoGen GroupChat導入
- ステージ自動遷移（ターン数 or 内容判定）
- ステージ要約引き継ぎ
- 完結確認エージェント追加
- マイルストーン: 8割以上が「完結している」と感じる物語生成

### Phase 2: 柔軟性向上（1週間）
- ステージ数4へ拡張
- サブ目標・分岐メカニズム追加（前ステージ会話で次ステージ初期状況変化）
- 会話ターン数可変
- 記憶要約エージェント導入

### Phase 3: 拡散性・拡張性（2週間）
- 動的キャラクター生成・追加
- サブステージ自動挿入
- ロードマップ動的修正機能
- 並列シーン実験
- ビジュアルプロンプト自動生成準備

### Phase 4: 品質ループ強化
- ナラティブ監督エージェント常駐
- 自動再生成ループ（低品質時）
- 人間フィードバック記憶機能
- 多ジャンル対応

### Phase 5: 無限拡張・プロダクト化
- キャラクター生成エージェント完全連携
- Web UI（Gradio/Streamlit）
- 長編続き書き機能
- 複数並列生成

**各Phase終了時のルーチン**:
1. 複数物語生成
2. 完結確認エージェント評価
3. 人間が「良かった点・改善点」メモ
4. 次Phase TODO反映

## 5. ステージ定義

### 3ステージ版（Phase 0 用）

```python
STAGES_3 = {
    1: {
        "name": "Setup（日常・呼びかけ）",
        "description": "主人公の平凡な日常を描き、何か異常や呼びかけが起こる。読者に世界観と主人公の性格を紹介。",
        "goal_for_protagonist": "自分の日常に疑問を持ったり、小さな変化の予感を感じさせる。師匠や凛と軽く出会う。",
        "end_condition": "冒険のきっかけ（呼びかけ）が明確になる"
    },
    2: {
        "name": "Confrontation（試練・葛藤）",
        "description": "最初の試練や障害が発生。他のキャラクターとの関係が深まり、対立や協力が生まれる。",
        "goal_for_protagonist": "試練に直面し、逃げたい気持ちや迷いを見せつつ、少し前進する。",
        "end_condition": "最大の壁（Ordealの予感）が見えてくる"
    },
    3: {
        "name": "Resolution（解決・帰還）",
        "description": "試練を乗り越え、変化した姿で日常に戻る（または新しい日常を受け入れる）。",
        "goal_for_protagonist": "成長を実感し、物語を締めくくる。",
        "end_condition": "感情的な決着がつき、テーマが響く終わり方"
    }
}
4ステージ版（Phase 1以降推奨）
STAGES_4 = {
    1: {
        "name": "Ordinary World & Call（日常と呼びかけ）",
        "description": "主人公の普通の生活を描き、冒険への呼びかけ（事件・出会い・予言など）が起こる。",
        "goal_for_protagonist": "日常の不満や欠落を少し感じ、呼びかけに対して興味や拒否反応を見せる。",
        "end_condition": "「行かなければならない」という気持ちが芽生える"
    },
    2: {
        "name": "Trials & Allies（試練と仲間）",
        "description": "最初の試練を経験し、師匠・凛などのキャラクターと関係を築く。世界観を広げる。",
        "goal_for_protagonist": "仲間を得たり、ライバルとぶつかりながら、小さな成功を手に入れる。",
        "end_condition": "本当の大きな試練が近づいていることを実感する"
    },
    3: {
        "name": "Ordeal（最大の試練）",
        "description": "物語のクライマックス。最大の危機・対決・内面的な葛藤が発生。",
        "goal_for_protagonist": "これまでの経験を活かし、死に近い危機を乗り越える（精神的にも）。",
        "end_condition": "主人公が明確に『変わった』と感じる瞬間"
    },
    4: {
        "name": "Return & Resolution（帰還と変容）",
        "description": "試練を終え、成長した姿で元の世界（または新しい世界）に戻る。余韻を残す。",
        "goal_for_protagonist": "得たものを活かし、物語を美しく締めくくる。",
        "end_condition": "テーマが響き、読後感が残る終わり"
    }
}
6. Phase 0 サンプルコード（そのまま実行可能）
import json
import requests
from typing import List, Dict

# ==================== 設定 ====================
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"          # または qwen2.5:7b など
MAX_TURNS_PER_STAGE = 3

# ==================== ステージ定義 ====================
STAGES = {
    1: {"name": "Setup（日常・呼びかけ）", "goal": "日常に疑問を持ち、呼びかけを感じさせる"},
    2: {"name": "Confrontation（試練・葛藤）", "goal": "試練に直面し、少し前進する"},
    3: {"name": "Resolution（解決・帰還）", "goal": "成長を実感し締めくくる"}
}

# ==================== エージェント ====================
class Agent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt

protagonist = Agent(
    name="太郎",
    system_prompt="""あなたは物語の主人公「太郎」です。
現在はステージ{stage}「{stage_name}」です。
ステージの目標: {goal}

他のキャラクターにロードマップを明かさず、自然な会話でこの目標を少しずつ達成してください。
発言は1〜3文程度の自然なものに。"""
)

mentor = Agent(name="師匠", system_prompt="あなたは厳しくも優しい老剣士「師匠」です。口調は少し古風。")
rival = Agent(name="凛", system_prompt="あなたはクールでライバル心の強い少女「凛」です。いつも突っかかる。")

conversation: List[Dict] = []

def call_ollama(agent: Agent, stage: int, history_str: str) -> str:
    stage_info = STAGES[stage]
    prompt = f"""【現在のステージ】{stage}: {stage_info['name']}
目標: {stage_info['goal']}

【これまでの会話】
{history_str}

【あなたの役割】
{agent.system_prompt.format(stage=stage, stage_name=stage_info['name'], goal=stage_info['goal'] if agent.name == "太郎" else "")}

今の発言をしてください。"""
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": "発言してください。"}],
        "stream": False,
        "temperature": 0.85
    }
    
    resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
    return resp.json()["message"]["content"].strip()

def generate_story():
    global conversation
    conversation = []
    print("=== 物語生成開始 ===\n")
    
    for stage in [1, 2, 3]:
        print(f"\n【ステージ {stage}】 {STAGES[stage]['name']}\n")
        if stage == 1:
            conversation.append({"role": "narrator", "content": "ある平凡な村で、青年・太郎は毎日同じ生活を送っていた。"})
        
        for turn in range(MAX_TURNS_PER_STAGE):
            speakers = [protagonist, mentor, rival]
            speaker = speakers[turn % 3]
            history_str = "\n".join([f"{m['role']}: {m['content']}" for m in conversation[-10:]])
            response = call_ollama(speaker, stage, history_str)
            conversation.append({"role": speaker.name, "content": response})
            print(f"{speaker.name}: {response}\n")
        
        if stage < 3:
            conversation.append({"role": "narrator", "content": f"── ステージ{stage}終了、次の展開へ ──"})
    
    # 強制エンディング
    ending_prompt = "これまでの物語を自然に美しく完結させてください。\n\n" + "\n".join([f"{m['role']}: {m['content']}" for m in conversation])
    final = call_ollama(Agent("語り部", "美しい終わり方で物語を完結させる語り部"), 3, ending_prompt)
    conversation.append({"role": "Ending", "content": final})
    print("【Ending】\n" + final)
    
    with open("story_phase0.json", "w", encoding="utf-8") as f:
        json.dump(conversation, f, ensure_ascii=False, indent=2)
    print("\n=== 完了！ story_phase0.json に保存 ===")

if __name__ == "__main__":
    generate_story()
7. 実行手順
	1	Ollama起動 + ollama pull llama3.2（または好みのモデル）
	2	コードを story_phase0.py として保存
	3	python story_phase0.py
8. 今後の拡張ポイント（そのまま次Phaseで実装可能）
	•	AutoGen GroupChatへの移行
	•	ステージ自動遷移判定（内容解析）
	•	動的キャラクター追加
	•	ロードマップ動的更新
	•	ナラティブ監督エージェント
	•	Gradio UI化 など
このドキュメントは一切要約・省略していません。 シニアエンジニアにそのまま渡して議論を進めてください。
---

このMarkdownをそのままコピーして `multi-agent-story-system.md` というファイルに保存すれば、意図が正確に伝わります。  
必要なら追加セクション（具体的なプロンプト例集など）もすぐ追加します！
