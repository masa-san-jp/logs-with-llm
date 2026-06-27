---
title: "週報：複数デバイスの安全な常時接続と、エージェント常駐・入力検証の勘どころ"
emoji: "🔐"
type: "tech"
topics: ["Tailscale", "systemd", "Telegram", "セキュリティ", "AIエージェント"]
published: true
---

常駐サービスを増やすほど、つまずくのは派手な攻撃ではなく地味な運用の罠でした。今週いちばん象徴的だったのは、同じ Telegram bot トークンを 2 台のホストで同時に使った瞬間に `getUpdates` がぶつかり、`409 Conflict` でゲートウェイが黙る、という類いのハマりどころです。

今週の作業ログは「接続」「常駐」「入力検証」の 3 本でしたが、どれも結局は同じ一点、**最小の入口を、壊れにくく晒す**に収束していました。本稿はその実例をまとめた週報です。

## 1. ポートを開けずに 3 台をつなぐ ― Tailscale + SSH + RDP/RustDesk

対象は MacBook Pro、Windows 10/11 Pro のワークステーション、自宅の Ubuntu GB10 サーバーの 3 台です。これらを Tailscale + SSH + RDP もしくは RustDesk でつなぎます。

3 台を同じ Tailscale アカウント（Google / Microsoft / GitHub / Apple ID のいずれかで認証）に参加させると、安定した Tailscale IP が振られ、ポートフォワーディングが要らなくなります。これが「公開ポートを晒さない」の土台です。

リモートデスクトップは編集（エディション）に依存します。Windows の RDP は Pro / Enterprise / Education でのみ有効なので、仕事用 PC が Home の場合は RustDesk を使い、ポート 21118・固定パスワード・「Direct IP access」で構成します。

SSH は鍵認証に寄せます。Mac で ed25519 鍵を生成し、`ssh-copy-id` で GB10 へ配布、Windows の公開鍵は `~/.ssh/authorized_keys` に追記します。GB10 では systemd で `tailscaled` と `ssh` を有効化し、Windows は `sshd` を自動起動にしておきます。

セキュリティ面の要点は 3 つです。Tailscale で 2FA を有効化すること、公開の 22 / 3389 を晒さないこと、そして使わなくなったデバイスはコンソールから削除すること。入口の数そのものを減らすのが効きます。

## 2. ログアウトしても落ちない常駐ゲートウェイ ― Hermes Agent と「単一トークン」

Hermes の構成は、ASUS Ascent GX10（ARM64・Ubuntu）と macOS 12+ のワークステーションです。GX10 側で Hermes Agent 本体と、Telegram bot を待ち受ける Hermes Gateway を動かします。

bot トークンと、許可する数値の user ID は `~/.hermes/.env` に置き、`chmod 600` で保護します。ゲートウェイは user 権限の systemd ユニット `hermes-gateway.service` として `/home/masa/.local/bin/hermes gateway` を起動し、失敗時は再起動、`systemctl --user enable --now` で有効化します。`sudo loginctl enable-linger $USER` を入れておくと、ログアウト後もサービスが生き続けます。

ここが冒頭の罠の答えです。Mac には Hermes を入れますが、**Gateway は動かしません**。トークンを 1 か所だけで使う運用に保つことで、同時に `getUpdates` が走って `409 Conflict` になるのを避けています。常駐を「冗長化」したくなる気持ちと、トークンの排他利用は別問題でした。

運用面では、`require_mention: true` と `TELEGRAM_ALLOWED_CHATS` でグループでの反応を制御できます。ファイル添付は、ホストのボリュームにアクセスできる場合に `MEDIA:/path/to/file` で渡せます。ベストプラクティスは、`.hermes` ディレクトリを非公開に、`.env` を保護し、トークンを排他利用すること。守りどころは結局ここに戻ってきます。

## 3. 502 で握りつぶさない ― Thug-Fugu の HTTP 検証とオーケストレーション監査

`masa-san-jp/Thug-Fugu` の静的レビューです。設定読み込み・バックエンドアダプタ・オーケストレーション・HTTP サーバー・CLI がきれいに分離されており、オーケストレーションは worker のロールを選んで並行実行し、決定的な merge fallback を当てる構造になっています。

PR 1 では、HTTP リクエスト検証を固くします。具体的には `messages` のチェックを `_validate_chat_completion_request()` に寄せ、形状エラーは現状の「`OrchestrationError` 経由で 502」ではなく、素直に 400 を返すようにします。入力の不正をサーバー側の障害（502）に化けさせない、という地味だが大事な区別です。

ほかの指摘は次の通りです。生のバックエンドエラーをそのまま漏らす P0 リスク、非 localhost ホストへの unsafe bind 警告に関する P1、そしてリクエスト単位の deadline が無いために 1 つの遅い worker が全体のレイテンシを支配しうる点。

ロードマップは、ストリーミングや tool-calling の機能拡張に進む前に、(1) リクエスト形状の強制、(2) debug フラグの裏でのエラー redaction、(3) `--allow-unsafe-bind` のガード、(4) グローバルなオーケストレーション deadline、の順で固める、という優先順位にしました。

## まとめ：境界をまたぐ「統一された検証層」へ

3 つの調査は、同じ設計パターンを描いていました。エッジのデバイスは最小の認証された入口（Tailscale VPN・SSH 鍵・Telegram bot トークン）だけを晒し、systemd 管理の常駐サービス（Hermes Gateway・SSH / RustDesk デーモン）で動かし、厳格な入力検証（Thug-Fugu のリクエストスキーマ）を効かせる。

これらは攻撃面を減らし、障害を分離し、異種のハードウェアにまたがって自律的なワークロードを安全にスケールさせる土台になります。次の一手は、ネットワークとエージェントの境界をまたいで検証層を統一し、コンプライアンスと可観測性を一本化することだと考えています。
