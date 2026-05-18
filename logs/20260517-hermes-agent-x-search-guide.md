# Hermes Agent + xAI Grok で X (Twitter) 検索を使う完全ガイド
**APIキー不要・X Premiumサブスクだけで高度なX検索が可能**

**ファイル名**: `hermes-agent-x-search-guide.md`

---

## 概要
Hermes Agent（Nous Researchのオープンソース自己改善型エージェント）にxAI GrokのOAuth認証を連携させることで、**X Premiumのサブスクリプションを直接利用**してXポスト検索が行えます。APIキー取得や追加料金は一切不要です。

これにより、エージェント内でリアルタイムのX検索ツール（`x_search` / `x_keyword_search` など）が使用可能になります。

---

## インストール（初回のみ）

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
インストール後、hermes コマンドが使用可能になります。

設定手順
1. Grok (xAI) プロバイダーでログイン
hermes model
	•	xAI Grok OAuth (SuperGrok Subscription) を選択
	•	ブラウザが開いたら accounts.x.ai でXアカウントにログイン（X PremiumティアでOK）
	•	アクセス承認 → トークンが自動保存されます
2. X検索ツールを有効化（重要）
hermes tools
	•	🐦 X (Twitter) Search に移動 → Spaceキー で有効化
	•	保存して終了
3. 動作確認
hermes doctor

基本的な使い方
hermes --tui
または hermes で起動後、自然言語で指示します。

ユースケース例
1. 最新トレンド・ニュース収集
指示例:
最近のAIニュースをXで検索して、重要なポストを5件まとめて日本語で教えて
期待される動作: エージェントが自動でx_keyword_searchやセマンティック検索を使い、リアルタイム情報を取得・要約
2. 特定ユーザーの監視
指示例:
@npaka123 の直近10件のポストを検索して、技術関連のものをリストアップ
3. ハッシュタグ・キーワード調査
指示例:
#HermesAgent OR #Grok で話題になっている投稿を検索し、ポジティブ・ネガティブの反応を分析して
4. 競合・市場調査
指示例:
"Claude 4" OR "Gemini 2.5" に関するX上の反応を、過去24時間で検索してレポート作成
5. イベントリアルタイム追跡
指示例:
WWDC 2026 関連のポストをライブ検索して、主要発表を時系列でまとめて
6. 自己改善型エージェントとしての活用
Hermesは検索結果を記憶し、次のタスクに活用可能：
先ほど検索したAIニュースをもとに、今日の技術ブログ記事のネタを3つ提案して

便利コマンド
コマンド
用途
hermes model
モデル/プロバイダー切り替え
hermes tools
ツール有効化・無効化
hermes doctor
診断・トラブルシューティング
hermes auth logout xai-oauth
再ログインしたい場合
hermes --tui
TUIモードで起動

注意点
	•	X検索はX Premiumのレート制限に準拠します
	•	ヘッドレス環境（サーバー）では --no-browser オプション + SSHポートフォワードで認証可能
	•	検索精度はGrokのモデル性能に依存（現在はGrok 4系が最高性能）

参考リンク
	•	Hermes Agent 公式ドキュメント
	•	xAI Grok × Hermes 統合発表
	•	Nous Research GitHub

作成日: 2026年5月 
