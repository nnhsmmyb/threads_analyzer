#!/usr/bin/env python3
"""App Review 用: 全 11 permission を順に実行するテスト。"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app_paths as paths
import threads_api_system as api
from review_test.permissions import PERMISSION_DEMOS, REVIEW_SCOPES
from runtime_env import bootstrap_runtime_env
from threads_oauth import load_oauth_config

JST = timezone(timedelta(hours=9))
PUBLISH_WAIT_SEC = 30
RESULT_FILE = "review_test_result.json"
KEYWORD_QUERY = "remote work"
LOCATION_QUERY = "Menlo Park"
TEXT_PUBLISH = "[autoT] App Review publish demo — safe to delete"
TEXT_REPLY = "[autoT] App Review reply demo — safe to delete"
TEXT_DELETE = "[autoT] App Review delete demo — will be removed"
TEXT_IG_SHARE = "[autoT] App Review IG share demo — safe to delete"


def _now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def _step(title: str) -> None:
    print(f"\n[review_test] === {title} ===", flush=True)


def _ok(label: str, detail: str = "") -> dict:
    msg = f"OK: {label}" + (f" ({detail})" if detail else "")
    print(f"[review_test] {msg}", flush=True)
    return {"status": "ok", "label": label, "detail": detail}


def _skip(label: str, detail: str) -> dict:
    print(f"[review_test] SKIP: {label} ({detail})", flush=True)
    return {"status": "skip", "label": label, "detail": detail}


def _fail(label: str, exc: Exception) -> dict:
    print(f"[review_test] FAIL: {label} — {exc}", flush=True)
    return {"status": "fail", "label": label, "detail": str(exc)}


def _run_step(result: dict, key: str, label: str, fn) -> None:
    try:
        result["steps"][key] = fn()
    except Exception as exc:
        result["steps"][key] = _fail(label, exc)


def _wait_publish() -> None:
    print(f"[review_test] waiting {PUBLISH_WAIT_SEC}s...", flush=True)
    for remaining in range(PUBLISH_WAIT_SEC, 0, -5):
        print(f"[review_test]   {remaining}s...", flush=True)
        time.sleep(5 if remaining >= 5 else remaining)


def _publish(
    client: api.ThreadsApiClient,
    text: str,
    *,
    reply_to_id: str = "",
    reply_control: str = "",
    location_id: str = "",
    share_to_ig_story: str = "",
) -> str:
    creation_id = client.create_text_container(
        text,
        reply_to_id=reply_to_id,
        reply_control=reply_control,
        location_id=location_id,
        share_to_ig_story=share_to_ig_story,
    )
    print(f"[review_test]   container_id={creation_id}", flush=True)
    _wait_publish()
    media_id = client.publish_container(creation_id)
    print(f"[review_test]   media_id={media_id}", flush=True)
    return media_id


def run(
    *,
    keyword: str,
    skip_write: bool,
    hide_reply_id: str,
    skip_ig_share: bool,
) -> dict:
    load_oauth_config(env_path=ROOT / ".env")
    client = api.ThreadsApiClient(api.load_access_token(), api_base=api.load_api_base())

    result: dict = {
        "ran_at": _now_jst(),
        "scopes": list(REVIEW_SCOPES),
        "skip_write": skip_write,
        "skip_ig_share": skip_ig_share,
        "steps": {},
    }
    username = ""
    main_post_id = ""
    delete_post_id = ""
    location_id = ""

    print("[review_test] App Review — all permissions", flush=True)
    print("[review_test] scopes:", ",".join(REVIEW_SCOPES), flush=True)
    for perm, apis in PERMISSION_DEMOS:
        print(f"[review_test]   {perm}: {apis}", flush=True)

    if skip_write:
        print("[review_test] --skip-write: 投稿・削除はスキップ", flush=True)
    else:
        print("[review_test] 注意: Threads に投稿・削除を実行します", flush=True)

    _step("threads_basic")
    profile_holder: dict = {}

    def basic_me() -> dict:
        nonlocal username
        profile_holder.update(client.me_profile())
        username = str(profile_holder.get("username") or "")
        return _ok("me", f"@{username}")

    _run_step(result, "threads_basic_me", "me", basic_me)
    posts_holder: list[list[dict]] = []

    def basic_threads() -> dict:
        posts = client.me_threads(limit=5)
        posts_holder.append(posts)
        return _ok("me/threads", f"{len(posts)} posts")

    _run_step(result, "threads_basic_me_threads", "me/threads", basic_threads)

    def basic_media() -> dict:
        posts = posts_holder[0] if posts_holder else []
        if not posts:
            return _skip("media", "no posts")
        media = client.get_media(str(posts[0]["id"]))
        return _ok("media", str(media.get("id") or ""))

    _run_step(result, "threads_basic_media", "media", basic_media)

    _step("threads_keyword_search")

    def keyword_search() -> dict:
        posts = client.keyword_search(keyword, limit=5)
        return _ok("keyword_search", f"{len(posts)} for {keyword!r}")

    _run_step(result, "threads_keyword_search", "keyword_search", keyword_search)

    _step("threads_profile_discovery")

    def profile_discovery() -> dict:
        if not username:
            raise api.ThreadsApiError("username missing from GET /me")
        posts = client.profile_posts(username, limit=5)
        return _ok("profile_posts", f"{len(posts)} for @{username}")

    _run_step(result, "threads_profile_discovery", "profile_posts", profile_discovery)

    _step("threads_manage_mentions")

    def mentions() -> dict:
        items = client.user_mentions(limit=10)
        return _ok("mentions", f"{len(items)} items")

    _run_step(result, "threads_manage_mentions", "mentions", mentions)

    _step("threads_manage_insights")

    def media_insights() -> dict:
        posts = posts_holder[0] if posts_holder else []
        if not posts:
            return _skip("media_insights", "no posts")
        payload = client.media_insights(str(posts[0]["id"]))
        names = [item.get("name") for item in payload.get("data", []) if isinstance(item, dict)]
        return _ok("media_insights", ",".join(str(n) for n in names if n))

    _run_step(result, "threads_manage_insights_media", "media_insights", media_insights)

    def user_insights() -> dict:
        payload = client.user_insights(metrics="views")
        names = [item.get("name") for item in payload.get("data", []) if isinstance(item, dict)]
        return _ok("user_insights", ",".join(str(n) for n in names if n))

    _run_step(result, "threads_manage_insights_user", "user_insights", user_insights)

    _step("threads_location_tagging")

    def location_search() -> dict:
        nonlocal location_id
        locations = client.location_search(query=LOCATION_QUERY)
        if locations:
            location_id = str(locations[0].get("id") or "")
        return _ok("location_search", f"{len(locations)} for {LOCATION_QUERY!r}")

    _run_step(result, "threads_location_tagging_search", "location_search", location_search)

    if skip_write:
        for key, label in (
            ("threads_content_publish", "publish"),
            ("threads_share_to_instagram", "share_to_ig_story"),
            ("threads_manage_replies_publish", "publish_reply"),
            ("threads_read_replies", "read_replies"),
            ("threads_manage_replies_hide", "manage_reply"),
            ("threads_delete", "delete"),
        ):
            result["steps"][key] = _skip(label, "--skip-write")
    else:
        _step("threads_content_publish + location_tagging")

        def publish_main() -> dict:
            nonlocal main_post_id
            main_post_id = _publish(
                client,
                TEXT_PUBLISH,
                reply_control="accounts_you_follow",
                location_id=location_id,
            )
            extra = "reply_control=accounts_you_follow"
            if location_id:
                extra += f", location_id={location_id}"
            return _ok("publish", f"{main_post_id} ({extra})")

        _run_step(result, "threads_content_publish", "publish", publish_main)

        _step("threads_share_to_instagram")

        if skip_ig_share:
            result["steps"]["threads_share_to_instagram"] = _skip(
                "share_to_ig_story", "--skip-ig-share"
            )
        else:

            def ig_share() -> dict:
                media_id = _publish(client, TEXT_IG_SHARE, share_to_ig_story="light")
                return _ok("share_to_ig_story", media_id)

            _run_step(result, "threads_share_to_instagram", "share_to_ig_story", ig_share)

        _step("threads_manage_replies — publish reply")

        def publish_reply() -> dict:
            if not main_post_id:
                raise api.ThreadsApiError("main post missing")
            reply_id = _publish(client, TEXT_REPLY, reply_to_id=main_post_id)
            return _ok("publish_reply", reply_id)

        _run_step(result, "threads_manage_replies_publish", "publish_reply", publish_reply)

        _step("threads_read_replies")

        def read_replies() -> dict:
            if not main_post_id:
                raise api.ThreadsApiError("main post missing")
            replies = client.thread_replies(main_post_id, limit=10)
            return _ok("replies", f"{len(replies)} on {main_post_id}")

        _run_step(result, "threads_read_replies", "read_replies", read_replies)

        _step("threads_manage_replies — hide / unhide")
        if hide_reply_id:

            def hide() -> dict:
                client.manage_reply(hide_reply_id, hide=True)
                return _ok("hide", hide_reply_id)

            _run_step(result, "threads_manage_replies_hide", "hide", hide)

            def unhide() -> dict:
                client.manage_reply(hide_reply_id, hide=False)
                return _ok("unhide", hide_reply_id)

            _run_step(result, "threads_manage_replies_unhide", "unhide", unhide)
        else:
            result["steps"]["threads_manage_replies_hide"] = _skip(
                "hide", "別テスターの返信 ID を --hide-reply-id に指定"
            )
            result["steps"]["threads_manage_replies_unhide"] = _skip("unhide", "requires --hide-reply-id")

        _step("threads_delete")

        def publish_for_delete() -> dict:
            nonlocal delete_post_id
            delete_post_id = _publish(client, TEXT_DELETE)
            return _ok("publish_for_delete", delete_post_id)

        _run_step(result, "threads_delete_publish", "publish_for_delete", publish_for_delete)

        def delete_post() -> dict:
            if not delete_post_id:
                raise api.ThreadsApiError("delete target missing")
            payload = client.delete_media(delete_post_id)
            success = payload.get("success", True)
            return _ok("delete", f"{delete_post_id} success={success}")

        _run_step(result, "threads_delete", "delete", delete_post)

    fails = [k for k, v in result["steps"].items() if v.get("status") == "fail"]
    result["failed_steps"] = fails

    out_dir = ROOT / paths.AGENT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / RESULT_FILE
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[review_test] wrote {out_path.relative_to(ROOT)}", flush=True)
    if fails:
        print(f"[review_test] failed: {', '.join(fails)}", flush=True)
    else:
        print("[review_test] all steps OK", flush=True)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run App Review tests for all 11 Threads permissions")
    parser.add_argument("--keyword", default=KEYWORD_QUERY)
    parser.add_argument("--skip-write", action="store_true", help="投稿・削除をスキップ")
    parser.add_argument("--skip-ig-share", action="store_true", help="Instagram シェア投稿をスキップ")
    parser.add_argument("--hide-reply-id", default="", help="別テスターの返信 ID（hide/unhide 用）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bootstrap_runtime_env(root_dir=ROOT)
    result = run(
        keyword=args.keyword,
        skip_write=args.skip_write,
        hide_reply_id=args.hide_reply_id.strip(),
        skip_ig_share=args.skip_ig_share,
    )
    if result.get("failed_steps"):
        sys.exit(1)


if __name__ == "__main__":
    main()
