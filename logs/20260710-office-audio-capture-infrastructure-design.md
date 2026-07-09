# オフィス音声収集インフラ設計仕様書

> バージョン: 0.1  
> 日付: 2026-07-10

## 1. 目的

本設計書は、オフィス内で発生する会話を長期的な知識資産として蓄積し、将来的にAIによる暗黙知抽出・業務マニュアル生成・教育コンテンツ生成へ利用できる録音インフラを設計する。

重要な考え方は**AIよりデータを優先する**ことである。

---

# 2. 基本原則

1. 生音声は捨てない
2. AI処理結果はいつでも再生成できる
3. 録音装置とAIを分離する
4. モデル更新前提で設計する
5. 全処理はパイプライン化する

---

# 3. 全体アーキテクチャ

```text
Capture Layer
    ↓
Raw Audio Storage
    ↓
Metadata Layer
    ↓
Speech-to-Text Layer
    ↓
Conversation Layer
    ↓
Knowledge Candidate Layer
    ↓
Knowledge Graph
    ↓
Manual / FAQ / SOP
```

---

# 4. シチュエーション別デバイス

## A. PoC（1〜5人）

|項目|内容|
|---|---|
|推奨|Raspberry Pi 5 + ReSpeaker USB Mic|
|初期費用|2〜5万円|
|運用費|ほぼ0円|
|接続性|★★★★★|
|AI連携|★★★★★|

## B. 小会議室

- Meeting Owl 3
- Jabra Speak2 75
- Poly Sync 60
- Yamaha YVCシリーズ

初期費用: 5〜25万円

---

## C. オープンオフィス

候補

- Shure MXA920
- Sennheiser TeamConnect Ceiling
- Yamaha RM-CG

初期費用

30〜150万円/部屋

---

## D. 個人暗黙知収集

候補

- PLAUD Note
- PLAUD NotePin
- Bee AI
- HiDock
- Sony ICD-TX660

---

# 5. 推奨URL

|メーカー|URL|
|---|---|
|Shure|https://www.shure.com|
|Sennheiser|https://www.sennheiser.com|
|Yamaha UC|https://uc.yamaha.com|
|Jabra|https://www.jabra.com|
|Poly|https://www.hp.com/poly|
|Nureva|https://www.nureva.com|
|Zoom|https://zoomcorp.com|
|TASCAM|https://tascam.com|
|OM SYSTEM|https://explore.omsystem.com|
|Sony|https://www.sony.jp|
|PLAUD|https://jp.plaud.ai|
|HiDock|https://www.hidock.com|
|Bee AI|https://bee.computer|

---

# 6. コスト比較

|構成|初期|月額|運用|
|---|---:|---:|---|
|USBマイク+Pi|2〜5万円|0〜数百円|容易|
|PLAUD|2〜3万円/人|AIプラン次第|容易|
|Meeting Owl|15〜25万円|なし|容易|
|天井マイク|30〜150万円|なし|専門知識必要|

---

# 7. データ保存

```text
data/
 raw_audio/
 processed_audio/
 transcripts/
 conversation_units/
 knowledge_candidates/
 approved_knowledge/
```

命名規則

```
YYYYMMDD-HHMMSS-HHMMSS-room-device.wav
```

---

# 8. メタデータ

必須項目

- recording_id
- room
- device
- start_time
- end_time
- checksum
- duration
- sample_rate
- firmware
- microphone_model

---

# 9. STT

保存項目

- モデル
- モデルバージョン
- プロンプト
- confidence
- 話者ID
- タイムスタンプ

---

# 10. データ品質

保存対象

- 生音声
- 前処理済音声
- transcript
- セグメント
- ナレッジ候補

削除しない。

---

# 11. 将来拡張

- 話者分離
- 感情推定
- 業務フロー抽出
- 知識グラフ
- FAQ生成
- SOP生成
- 教育教材生成

---

# 12. デバイス選定評価軸

- 音質
- 24時間運用
- API
- SDK
- Export
- Linux対応
- USB
- LAN
- PoE
- クラウド依存
- ローカル保存
- 消費電力
- 保守性
- コスト
- AI親和性
- 将来性

---

# 13. 推奨ロードマップ

Phase1
- Raspberry Pi
- USBマイク
- Whisper系STT

Phase2
- 会議室導入
- ナレッジ抽出

Phase3
- 天井マイク
- 全社展開

Phase4
- 知識グラフ
- 自動マニュアル更新

---

# 14. 次に作成すべき成果物

1. デバイス比較表（100〜200機種）
2. 詳細データモデル
3. STTベンチマーク
4. ネットワーク設計
5. セキュリティ設計
6. 法務・プライバシー設計
7. PoC実施計画
8. AIエージェント設計
9. Kubernetes運用設計
10. 運用マニュアル

本仕様書は録音基盤の上位設計とし、詳細設計は各サブシステムごとに分割して管理する。
