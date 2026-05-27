# リレーショナルDB設計ベストプラクティス  
**状態カラムを避け、イベントログで「事実」を記録する**

**バージョン**: 1.0  
**作成日**: 2026年5月  
**対象**: バックエンドエンジニア、DB設計者、SaaS開発者（初心者〜上級者）  
**目的**: 「status / 退会フラグ / 論理削除」などの状態カラムを安易に作る設計の落とし穴を避け、**監査性・拡張性・不整合耐性を劇的に向上**させる実践的パターンをまとめたドキュメント。

この文書はX投稿（@farstep_ 氏）を起点に、理論・実装例・反証・運用Tipsまで**汎用的に使える形**に整理したものです。  
PostgreSQLを前提に記載していますが、MySQL / SQL Serverなど他のRDBMSにも容易に適用可能です。

---

## 1. 問題提起：よくある「状態カラム」設計の落とし穴

多くのシステムで以下のように設計されます：

```sql
-- よくある悪い例
CREATE TABLE members (
    id          BIGSERIAL PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    status      VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'withdrawn')),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
この設計の問題点
	•	UPDATE で状態を上書きすると過去の履歴が完全に消滅する
	•	「いつ退会したか」「停止→復活の経緯」は追えない
	•	監査・トラブル対応・不正調査で致命的
	•	「論理削除」という言葉は業務現場ではほぼ使われない（和田卓人氏指摘）
本質的なミス 保存すべきは**「状態」ではなく「事実（出来事）」**である。

2. 核心の考え方（理論編）
2.1 Rich Hickey（Clojure作者）の「事実 vs 状態」
	•	事実（Fact）: 不変の出来事（例：「2026-05-26に退会手続きを行った」）
	•	状態（State）: 事実から今この瞬間に導出される情報（例：「現在は退会済み」）
古典的なアナロジー
	•	年齢（age）を保存するな → 生年月日だけ保存せよ
	•	年齢は「生年月日＋現在日付」でいつでも計算可能
2.2 「論理削除」という言葉は業務に存在しない
	•	顧客は「退会してほしい」「停止してほしい」と言う
	•	エンジニアが勝手に「論理削除フラグ」を作るのが問題
2.3 RDBの本質とのミスマッチ
	•	リレーション = 集合（set） → 順序を持たない
	•	状態変化 = 時間軸上の履歴 → 順序が重要

3. 推奨設計（イベントテーブル方式）
3.1 テーブル構成（2テーブル分割）
-- 1. 会員基本情報（不変情報のみ）
CREATE TABLE members (
    id            BIGSERIAL PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    name          VARCHAR(100) NOT NULL,
    birth_date    DATE,
    created_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2. 状態変化専用イベントテーブル（これが核心）
CREATE TABLE membership_events (
    id            BIGSERIAL PRIMARY KEY,
    member_id     BIGINT NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    
    event_type    VARCHAR(50) NOT NULL CHECK (event_type IN (
        'joined',      -- 入会
        'suspended',   -- 停止
        'reactivated', -- 復活
        'withdrawn',   -- 退会
        'banned'       -- BAN（将来的に自由に追加可）
    )),
    
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload       JSONB,                    -- 理由・担当者・補足情報
    created_by    VARCHAR(100),
    created_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 必須インデックス
CREATE INDEX idx_membership_events_member_id ON membership_events(member_id);
CREATE INDEX idx_membership_events_occurred_at ON membership_events(occurred_at);
CREATE INDEX idx_membership_events_member_occurred 
    ON membership_events(member_id, occurred_at DESC);
特徴
	•	event_type は業務用語そのまま → 新しい状態が増えてもALTER TABLE不要
	•	payload（JSONB）で柔軟にメタデータを追加
	•	UPDATEはほぼゼロ（INSERTのみ）
3.2 運用フロー例
-- 入会
INSERT INTO members (...) RETURNING id;
INSERT INTO membership_events (member_id, event_type, payload) 
VALUES (100, 'joined', '{"plan": "premium"}'::jsonb);

-- 停止
INSERT INTO membership_events (member_id, event_type, payload) 
VALUES (100, 'suspended', '{"reason": "未払い"}'::jsonb);
ルール：状態を変更したいときは必ず新しいイベントをINSERTするだけ。

4. 「現在の状態」を取得する方法
4.1 シンプルクエリ
SELECT event_type, occurred_at, payload
FROM membership_events
WHERE member_id = 100
ORDER BY occurred_at DESC
LIMIT 1;
4.2 一覧取得（アクティブ会員）
SELECT m.id, m.name, e.event_type AS current_status
FROM members m
JOIN (
    SELECT member_id, event_type, occurred_at,
           ROW_NUMBER() OVER (PARTITION BY member_id ORDER BY occurred_at DESC) AS rn
    FROM membership_events
) e ON m.id = e.member_id AND e.rn = 1
WHERE e.event_type IN ('joined', 'reactivated')
  AND e.event_type NOT IN ('withdrawn', 'banned');
4.3 パフォーマンス向上策（推奨）
CREATE MATERIALIZED VIEW current_membership_status AS
SELECT member_id, event_type AS status, occurred_at, payload
FROM (
    SELECT member_id, event_type, occurred_at, payload,
           ROW_NUMBER() OVER (PARTITION BY member_id ORDER BY occurred_at DESC) AS rn
    FROM membership_events
) sub
WHERE rn = 1;

-- 定期更新（夜間 or 5分ごと）
REFRESH MATERIALIZED VIEW CONCURRENTLY current_membership_status;

5. 反証と現実的な落としどころ
5.1 主な反論
	•	「状態カラム＋イベントの両方持てばいい」（最も多い声）
	•	「最新状態取得が遅くなる」「JOINが複雑化」
	•	「データ量爆発」「小規模では過剰設計」
	•	「業務担当は単に『ステータス更新して』と言う」
5.2 ケース別おすすめ設計
ケース
おすすめ設計
理由
監査・履歴が法令必須
イベントテーブル中心
完璧な履歴
小規模CRUDアプリ
従来のstatusカラムのみ
シンプル
中規模以上（両方欲しい）
ハイブリッド（status＋events）
現実的最適解
パフォーマンス最優先
status＋トリガーで履歴自動生成
妥協案
実務での最強バランス → membersテーブルに読み取り専用のcurrent_statusカラムを残し、 イベントテーブルは監査・履歴専用にするハイブリッド設計。

6. 運用Tips・ベストプラクティス
	1	最初は重要テーブルだけ適用（会員・契約・注文など）
	2	マイグレーション：既存statusカラムがある場合、1回だけ変換スクリプトを作成
	3	アプリケーション側：トランザクション内で「members INSERT → events INSERT」を1セット
	4	新しい状態追加：event_typeに値を追加するだけ
	5	キャッシュ：最新状態はRedisなどでキャッシュ（任意）
	6	バックアップ：イベントテーブルは追記のみ → 非常に安全

7. 参考文献・出典
	•	元X投稿：https://x.com/farstep_/status/2059407531869675888
	•	Rich Hickey「The Value of Values」
	•	和田卓人氏「論理削除」という言葉は業務に存在しない
	•	イベントソーシング関連文献（CQRS/Event Sourcing）

このドキュメントの使い方
	•	新規プロジェクトの設計資料としてコピー
	•	チーム内レビュー時のチェックリストとして
	•	既存システムのリファクタリング時の判断材料として
必要に応じてSQLを自分のRDBMSに合わせて調整してください。 この設計を導入した現場では「監査が劇的に楽になった」「新機能追加時のDB変更がほぼゼロになった」という声が多数上がっています。
ライセンス：このドキュメントは自由に改変・再配布可能です（クレジット表記推奨）。

最終更新：2026年5月 m