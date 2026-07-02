# review_test — App Review 全 permission テスト

`threads_oauth.DEFAULT_SCOPES` と同じ 11 permission を順に叩く録画・API 成功ログ用プロジェクト。

## Permission 一覧

| Permission | デモ API |
| --- | --- |
| threads_basic | GET /me, /me/threads, /{media-id} |
| threads_keyword_search | GET /keyword_search |
| threads_profile_discovery | GET /profile_posts |
| threads_manage_mentions | GET /me/mentions |
| threads_manage_insights | GET /{media-id}/insights, /me/threads_insights |
| threads_location_tagging | GET /location_search, POST (location_id) |
| threads_content_publish | POST /me/threads + threads_publish |
| threads_share_to_instagram | share_to_ig_story=light |
| threads_manage_replies | reply_control, 返信投稿, manage_reply |
| threads_read_replies | GET /{media-id}/replies |
| threads_delete | DELETE /{media-id} |

## 実行

```bash
# スコープ変更後は OAuth やり直し必須
python3 threads_oauth_setup.py --manual

# 全 permission テスト（投稿・削除あり）
python3 review_test/run.py

# 読み取りのみ
python3 review_test/run.py --skip-write

# IG 連携なし（share_to_instagram スキップ）
python3 review_test/run.py --skip-ig-share

# hide/unhide（別テスターの返信が必要）
python3 review_test/run.py --hide-reply-id <REPLY_ID>
```

成果物: `agent_out/review_test_result.json`

## 録画手順

1. OAuth 同意画面（11 permission すべて表示）
2. `python3 review_test/run.py`
3. ターミナル出力 + `review_test_result.json`

## 注意

- Review 前は keyword_search / profile_posts 等が FAIL することがある（結果 JSON に記録）
- 自分の返信は hide 不可 → `--hide-reply-id` は別テスター用
- location_search は未承認時 `Menlo Park` のみ
- share_to_ig_story は Instagram 連携が必要（なければ `--skip-ig-share`）
