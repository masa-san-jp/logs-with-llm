**提案ファイル名**: `Stackchan-Arduino-Customization-Handbook.md`

以下が、**完全なマークダウン形式の実践的ドキュメント**です。  
この内容をそのままコピーして、テキストエディタ（VS Code推奨）で新しいファイルを作成し、`Stackchan-Arduino-Customization-Handbook.md` という名前で保存してください。  
初心者でも「もうすぐ届くStackchan」をすぐに動かして、カスタマイズできるよう、**専門用語はすべて説明を入れ、1つ1つの手順を再現性高く**記載しています。

---

# Stackchan Arduino カスタマイズ ハンドブック  
**～ stackchan-arduino で自分だけの可愛いパートナーに進化させる完全ガイド ～**

**作成日**: 2026年5月  
**対象**: Stackchan（CoreS3搭載モデル）をArduino環境でカスタマイズしたい初心者の方  
**著者参考**: hfujikawa77さんのIssue一覧およびコミュニティの最新情報に基づく

## 目次
1. [はじめに](#1-はじめに)  
2. [必要なハードウェアと準備](#2-必要なハードウェアと準備)  
3. [開発環境の整備](#3-開発環境の整備)  
4. [プロジェクトの初期作成](#4-プロジェクトの初期作成)  
5. [基本設定ファイル（YAML）の理解と編集](#5-基本設定ファイルyamlの理解と編集)  
6. [各機能の実装手順（一つずつ丁寧に）](#6-各機能の実装手順一つずつ丁寧に)  
7. [全体の運用管理と注意点](#7-全体の運用管理と注意点)  
8. [トラブルシューティング](#8-トラブルシューティング)  
9. [参照リソース一覧](#9-参照リソース一覧)  

---

## 1. はじめに
StackchanはM5Stack CoreS3を頭部に搭載した可愛いデスクトップロボットです。  
このハンドブックでは、**stackchan-arduino** ライブラリを使って、hfujikawa77さんが実際に取り組んだ以下の機能を一つずつ実現する方法を、**手順書レベル**で解説します。

- 定期発話モード（Cron）
- 音楽に反応して首を振る
- 設定UI（本体画面＋Webサーバー）
- 頭を撫でたときの喜ぶ反応
- 待機中のアイドルLED演出
- 会話履歴の吹き出し表示
- 顔アニメーション（瞬き・口パク・表情）
- サーボ制御の統合
- CoreS3 Push API＋Discord Bot連携
- STT連携でHermes LLM音声会話
- 日本語TTS（ttsQuestV3 Voicevox）
- ビルド環境＋基本疎通確認

これらを**1機能ずつ段階的に追加**できるように記載しています。  
まずは「Basic example」を動かしてから、1つずつ挑戦してください！

---

## 2. 必要なハードウェアと準備
- **本体**: M5Stack CoreS3 + Stackchan本体（サーボ2基、RGB LED、マイク、スピーカー、タッチセンサー搭載）
- **電源**: USB-Cケーブル（データ転送対応）＋安定したACアダプタ（5V/2A以上推奨）
- **microSDカード**（オプション）：音声ファイルや設定保存用（FAT32フォーマット）
- **PC**: Windows / macOS / Linux（VS Codeが動けばOK）
- **注意**: サーボ動作中は無理に手で動かさない（故障の原因）。垂直サーボは5°〜85°以内に制限。

---

## 3. 開発環境の整備
**強く推奨**: VS Code + PlatformIO（ライブラリ管理が簡単でエラー少ない）

### 3-1. インストール手順
1. **VS Code** を公式サイトからインストール  
   https://code.visualstudio.com/
2. VS Codeを開き、左側の拡張機能アイコン（Extensions）をクリック  
   「PlatformIO IDE」を検索してインストール（再起動が必要）
3. **Git** をインストール（まだない場合）  
   https://git-scm.com/

### 3-2. Arduino IDEを使う場合（PlatformIOが苦手な方）
- Arduino IDEをインストール  
- ボードマネージャで「M5Stack」を追加  
- ライブラリマネージャで「M5StackChan」ドライバライブラリをインストール  
（ただし、PlatformIOの方が後述のYAML設定が扱いやすいため推奨）

---

## 4. プロジェクトの初期作成
1. VS Codeを開き、PlatformIOアイコン（左下の蟻みたいなアイコン）をクリック
2. 「New Project」をクリック
3. 以下の設定で作成：
   - **Name**: 任意（例: MyStackchan）
   - **Board**: `m5stack-cores3`（またはStackChan-BSP対応ボード）
   - **Framework**: `Arduino`
4. プロジェクトが作成されたら、**platformio.ini** を以下の内容に編集（正確にコピー）：

```ini
[env:core_s3]
platform = espressif32
board = m5stack-cores3
framework = arduino
monitor_speed = 115200

lib_deps = 
    stack-chan/stackchan-arduino
    m5stack/StackChan-BSP
    M5Unified
    ESP32Servo
    ServoEasing
    ArduinoJson
    YAMLDuino
    SCServo
```

5. **Build**（チェックマークアイコン）をクリック → 成功したらOK
6. CoreS3をUSB接続 → **Upload**（右矢印アイコン）をクリック
7. **Monitor**（プラグアイコン）を開いてシリアルログを確認

**Basic example** を試す：
- `examples/Basic` フォルダのコードを `src/main.cpp` にコピーしてUpload  
- 成功すればStackchanが基本動作（首振り＋音声）します！

---

## 5. 基本設定ファイル（YAML）の理解と編集
設定はすべて **data/yaml/** フォルダ内のYAMLファイルで管理（YAML = 人間が読みやすい設定記述言語）。

- **SC_BasicConfig.yaml**：サーボ角度、Wi-Fi、音量などの基本設定
- **SC_SecConfig.yaml**：Wi-Fiパスワード、APIキーなどの秘密情報（Gitに上げない！）
- **SC_ExConfig.yaml**：自分で追加したい設定

**編集手順**：
1. プロジェクトの `data/` フォルダを作成
2. 上記3ファイルをGitHub（stack-chan/stackchan-arduino）の `data/yaml/` からダウンロードして配置
3. 各ファイルのコメントを読みながら編集（例: Wi-Fi SSIDとパスワード）
4. Upload時に自動でCoreS3のSPIFFS（内部フラッシュメモリ）に書き込まれる

---

## 6. 各機能の実装手順（一つずつ丁寧に）
各機能は**Basic exampleをベースに1つずつ追加**してください。  
コードは `src/main.cpp` に追記し、必要ライブラリをplatformio.iniに追加。

### 6-1. 定期発話モード（Cron）
- ライブラリ追加：`Cron` または `ezTime`
- コード例（簡易）：
  ```cpp
  #include <Cron.h>
  Cron cron;
  void setup() {
    cron.add("0 30 9 * * *", [](){ stackchan.speak("おはようございます！"); });
  }
  ```
- YAMLでスケジュール管理も可能。

### 6-2. マイク入力の音楽に反応して首を振る
- ライブラリ：arduinoFFT
- マイクで音をFFT解析 → リズム成分を抽出し、サーボ角度を同期。

### 6-3. 設定UI（本体画面＋Webサーバー）
- ライブラリ：AsyncWebServerESP32
- 本体画面はLVGLまたはM5Unified UIでタッチ操作  
- WebサーバーでスマホからWi-Fi/APIキー設定。

### 6-4. 頭を撫でたときの喜ぶ反応
- CoreS3のタッチセンサー（Si12T）またはIMUを使用
- イベント発生 → 表情（ハート目）＋喜び声＋首傾げ。

### 6-5. 待機中の低頻度アイドルLED演出
- FastLEDライブラリでWS2812C LEDを低頻度点滅。

### 6-6. 会話履歴を吹き出しで横スクロール表示
- 文字列配列で履歴保持 → LovyanGFXで吹き出し描画。

### 6-7. 顔アニメーション（瞬き・口パク・表情）
- m5stack-avatar または LovyanGFX使用
- TTS再生中に口パク同期、定期的に瞬き。

### 6-8. サーボ制御の統合
- stackchan-arduinoのServoクラス＋Easingで自然な動き。

### 6-9. CoreS3 Push API＋Discord Bot連携
- AsyncWebServerでHTTPエンドポイント作成
- Discord Webhookで外部からテキストPush。

### 6-10. STT連携でHermes LLM音声会話
- Whisper系STT → Hermes LLM → TTSのフロー
- マイク常時監視。

### 6-11. 日本語TTS（ttsQuestV3 Voicevox）
- HTTPでクラウドAPI呼び出し → 音声データ取得・再生
- ずんだもんなどの声も使用可能。

---

## 7. 全体の運用管理と注意点
- **Git管理**：プロジェクトをGitで管理（.gitignoreにSC_SecConfig.yamlを追加）
- **OTA更新**：無線でファームウェア更新（便利）
- **メモリ管理**：ESP32はPSRAM活用、タスク優先度設定
- **電池管理**：Deep Sleep併用、サーボ多用時は発熱注意
- **セキュリティ**：APIキーはSC_SecConfig.yamlに、Webサーバーは認証必須

---

## 8. トラブルシューティング
- **コンパイルエラー** → ライブラリバージョンを固定（platformio.iniに`@バージョン`指定）
- **サーボが動かない** → YAMLの角度範囲を確認
- **音声が出ない** → TTS APIキー確認、スピーカー音量設定
- **Wi-Fi接続失敗** → 2.4GHzのみ対応、SC_SecConfig.yaml再確認
- ログはSerial Monitorで常に確認

---

## 9. 参照リソース一覧（優先度順）
1. **stackchan-arduino**（最重要）  
   https://github.com/stack-chan/stackchan-arduino  
   （README、examples/Basic、YAMLサンプル）
2. **StackChan-BSP**  
   https://github.com/m5stack/StackChan-BSP
3. **M5Stack公式ドキュメント**  
   https://docs.m5stack.com/ja/StackChan  
   https://docs.m5stack.com/ja/arduino/stackchan/program
4. **hfujikawa77さんの活動**  
   X（@hfujikawa77）および関連Issue
5. **mongonta0716さん（ライブラリ作者）**  
   https://github.com/mongonta0716

---

**最後に**  
このハンドブックを印刷するか、PC横に置いて1機能ずつ進めてください。  
Stackchanが届いたら、まずは「Basic example」を動かして喜んであげましょう！  
わからない点が出てきたら、GitHub Issueや#Stackchan ハッシュタグでコミュニティに質問してください。

一緒に可愛いStackchanを育てましょう！ 🐱
