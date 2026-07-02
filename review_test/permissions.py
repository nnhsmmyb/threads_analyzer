"""App Review 申請対象の全 permission。"""

from __future__ import annotations

REVIEW_SCOPES: tuple[str, ...] = (
    "threads_basic",
    "threads_content_publish",
    "threads_delete",
    "threads_keyword_search",
    "threads_location_tagging",
    "threads_manage_insights",
    "threads_manage_mentions",
    "threads_manage_replies",
    "threads_profile_discovery",
    "threads_read_replies",
    "threads_share_to_instagram",
)

# permission → デモで叩く API（録画・審査員メモ用）
PERMISSION_DEMOS: tuple[tuple[str, str], ...] = (
    ("threads_basic", "GET /me, GET /me/threads, GET /{media-id}"),
    ("threads_keyword_search", "GET /keyword_search"),
    ("threads_profile_discovery", "GET /profile_posts"),
    ("threads_manage_mentions", "GET /me/mentions"),
    ("threads_manage_insights", "GET /{media-id}/insights, GET /me/threads_insights"),
    ("threads_location_tagging", "GET /location_search, POST /me/threads (location_id)"),
    ("threads_content_publish", "POST /me/threads + POST /me/threads_publish"),
    ("threads_share_to_instagram", "POST /me/threads (share_to_ig_story) + publish"),
    ("threads_manage_replies", "reply_control, publish reply, manage_reply"),
    ("threads_read_replies", "GET /{media-id}/replies"),
    ("threads_delete", "DELETE /{media-id}"),
)
