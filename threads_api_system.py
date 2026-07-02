from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import app_paths as paths

API_VERSION = "v1.0"
DEFAULT_API_BASE = "https://graph.threads.net"
REQUEST_INTERVAL_SEC = 0.5
SEARCH_MAX_RESULTS = 25
THREADS_JSON_PREFIX = "threads-api-"
JST = timezone(timedelta(hours=9))

USERNAME_RE = re.compile(r"^@?([A-Za-z0-9._]+)$")


@dataclass(frozen=True)
class FetchTask:
    priority: str
    purpose: str
    instruction: str

    @property
    def is_own_profile(self) -> bool:
        return self.instruction.strip().lstrip("@").lower() == "me"

    @property
    def is_username(self) -> bool:
        if self.is_own_profile:
            return False
        text = self.instruction.strip()
        if text.startswith("http"):
            return False
        match = USERNAME_RE.match(text)
        return match is not None and " " not in text


class ThreadsApiError(RuntimeError):
    pass


class ThreadsApiClient:
    def __init__(self, access_token: str, *, api_base: str = DEFAULT_API_BASE) -> None:
        token = access_token.strip()
        if not token:
            raise ValueError("THREADS_ACCESS_TOKEN is required")
        self._token = token
        self._api_base = api_base.rstrip("/")

    def get_json(self, endpoint: str, params: dict[str, str] | None = None) -> dict:
        merged = dict(params or {})
        merged.setdefault("access_token", self._token)
        query = urllib.parse.urlencode(merged)
        url = f"{self._api_base}/{API_VERSION}/{endpoint}"
        if query:
            url = f"{url}?{query}"
        request = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ThreadsApiError(f"HTTP {exc.code} for {endpoint}: {body}") from exc
        except urllib.error.URLError as exc:
            raise ThreadsApiError(f"request failed for {endpoint}: {exc}") from exc
        time.sleep(REQUEST_INTERVAL_SEC)
        if "error" in payload:
            raise ThreadsApiError(f"API error for {endpoint}: {payload['error']}")
        return payload

    def keyword_search(
        self,
        query: str,
        *,
        limit: int = SEARCH_MAX_RESULTS,
        search_type: str = "RECENT",
    ) -> list[dict]:
        capped = max(1, min(limit, 100))
        fields = "id,text,media_type,permalink,timestamp,username,has_replies,is_quote_post,is_reply"
        payload = self.get_json(
            "keyword_search",
            {
                "q": query,
                "search_type": search_type,
                "limit": str(capped),
                "fields": fields,
            },
        )
        data = payload.get("data")
        return data if isinstance(data, list) else []

    def me_threads(self, *, limit: int = SEARCH_MAX_RESULTS) -> list[dict]:
        capped = max(1, min(limit, 100))
        fields = "id,text,media_type,permalink,timestamp,username,is_quote_post"
        payload = self.get_json(
            "me/threads",
            {
                "limit": str(capped),
                "fields": fields,
            },
        )
        data = payload.get("data")
        return data if isinstance(data, list) else []

    def delete_json(self, endpoint: str) -> dict:
        query = urllib.parse.urlencode({"access_token": self._token})
        url = f"{self._api_base}/{API_VERSION}/{endpoint}?{query}"
        request = urllib.request.Request(url, method="DELETE")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
                payload = json.loads(raw) if raw.strip() else {"success": True}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ThreadsApiError(f"HTTP {exc.code} for DELETE {endpoint}: {body}") from exc
        except urllib.error.URLError as exc:
            raise ThreadsApiError(f"request failed for DELETE {endpoint}: {exc}") from exc
        time.sleep(REQUEST_INTERVAL_SEC)
        if "error" in payload:
            raise ThreadsApiError(f"API error for DELETE {endpoint}: {payload['error']}")
        return payload

    def post_form(self, endpoint: str, data: dict[str, str]) -> dict:
        merged = dict(data)
        merged.setdefault("access_token", self._token)
        body = urllib.parse.urlencode(merged).encode("utf-8")
        url = f"{self._api_base}/{API_VERSION}/{endpoint}"
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ThreadsApiError(f"HTTP {exc.code} for POST {endpoint}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ThreadsApiError(f"request failed for POST {endpoint}: {exc}") from exc
        time.sleep(REQUEST_INTERVAL_SEC)
        if "error" in payload:
            raise ThreadsApiError(f"API error for POST {endpoint}: {payload['error']}")
        return payload

    def me_profile(self) -> dict:
        return self.get_json("me", {"fields": "id,username"})

    def get_media(self, media_id: str, *, fields: str = "id,text,permalink,timestamp") -> dict:
        return self.get_json(media_id, {"fields": fields})

    def thread_replies(self, media_id: str, *, limit: int = 25) -> list[dict]:
        capped = max(1, min(limit, 25))
        fields = "id,text,username,timestamp,hide_status,is_reply"
        payload = self.get_json(
            f"{media_id}/replies",
            {"limit": str(capped), "fields": fields},
        )
        data = payload.get("data")
        return data if isinstance(data, list) else []

    def create_text_container(
        self,
        text: str,
        *,
        reply_to_id: str = "",
        enable_reply_approvals: bool = False,
        reply_control: str = "",
        location_id: str = "",
        share_to_ig_story: str = "",
    ) -> str:
        data: dict[str, str] = {
            "media_type": "TEXT",
            "text": text,
        }
        if reply_to_id:
            data["reply_to_id"] = reply_to_id
        if enable_reply_approvals:
            data["enable_reply_approvals"] = "true"
        if reply_control:
            data["reply_control"] = reply_control
        if location_id:
            data["location_id"] = location_id
        if share_to_ig_story:
            data["share_to_ig_story"] = share_to_ig_story
        payload = self.post_form("me/threads", data)
        creation_id = str(payload.get("id") or "").strip()
        if not creation_id:
            raise ThreadsApiError(f"create container did not return id: {payload}")
        return creation_id

    def publish_container(self, creation_id: str) -> str:
        payload = self.post_form("me/threads_publish", {"creation_id": creation_id})
        media_id = str(payload.get("id") or "").strip()
        if not media_id:
            raise ThreadsApiError(f"publish did not return id: {payload}")
        return media_id

    def manage_reply(self, reply_id: str, *, hide: bool) -> dict:
        return self.post_form(f"{reply_id}/manage_reply", {"hide": "true" if hide else "false"})

    def delete_media(self, media_id: str) -> dict:
        return self.delete_json(media_id)

    def location_search(self, *, query: str = "", latitude: str = "", longitude: str = "") -> list[dict]:
        params: dict[str, str] = {"fields": "id,name,address,city,country"}
        if query:
            params["q"] = query
        if latitude and longitude:
            params["latitude"] = latitude
            params["longitude"] = longitude
        if not query and not (latitude and longitude):
            raise ValueError("location_search requires q or latitude+longitude")
        payload = self.get_json("location_search", params)
        data = payload.get("data")
        return data if isinstance(data, list) else []

    def user_mentions(self, *, limit: int = 10) -> list[dict]:
        capped = max(1, min(limit, 25))
        fields = "id,text,username,timestamp,permalink"
        payload = self.get_json(
            "me/mentions",
            {"limit": str(capped), "fields": fields},
        )
        data = payload.get("data")
        return data if isinstance(data, list) else []

    def media_insights(self, media_id: str, *, metrics: str = "likes,replies,views") -> dict:
        return self.get_json(f"{media_id}/insights", {"metric": metrics})

    def user_insights(self, *, metrics: str = "views") -> dict:
        return self.get_json("me/threads_insights", {"metric": metrics})

    def profile_posts(self, username: str, *, limit: int = SEARCH_MAX_RESULTS) -> list[dict]:
        capped = max(1, min(limit, 100))
        fields = "id,text,media_type,permalink,timestamp,username,is_quote_post"
        payload = self.get_json(
            "profile_posts",
            {
                "username": username.lstrip("@"),
                "limit": str(capped),
                "fields": fields,
            },
        )
        data = payload.get("data")
        return data if isinstance(data, list) else []


def load_access_token() -> str:
    import os

    from runtime_env import bootstrap_runtime_env
    from threads_oauth import get_user_access_token, load_oauth_config

    root = Path(__file__).resolve().parent
    bootstrap_runtime_env(root_dir=root)
    env_path = root / ".env"

    try:
        config = load_oauth_config(env_path=env_path)
    except ValueError:
        config = None

    if config and config.access_token:
        return get_user_access_token(env_path=env_path, refresh_if_needed=True)

    token = os.environ.get("THREADS_ACCESS_TOKEN", "").strip()
    if not token:
        raise ThreadsApiError(
            "THREADS_ACCESS_TOKEN is not set; run threads_oauth_setup.py first"
        )
    return token


def load_api_base() -> str:
    import os

    return os.environ.get("THREADS_API_BASE", DEFAULT_API_BASE).strip() or DEFAULT_API_BASE


def _now_jst_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def _slug(text: str, *, max_len: int = 40) -> str:
    cleaned = re.sub(r"[^\w\u3040-\u30ff\u3400-\u9fff-]+", "-", text.strip(), flags=re.UNICODE)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return (cleaned or "query")[:max_len]


def parse_weekly_suggestion_json(path: Path) -> list[FetchTask]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ValueError(f"tasks must be a non-empty array in {path.name}")

    tasks: list[FetchTask] = []
    for index, item in enumerate(raw_tasks, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"tasks[{index - 1}] must be an object in {path.name}")
        priority = str(item.get("priority") or "").strip()
        purpose = str(item.get("purpose") or "").strip()
        instruction = str(item.get("instruction") or "").strip()
        if not priority or not purpose or not instruction:
            raise ValueError(
                f"tasks[{index - 1}] requires priority, purpose, instruction in {path.name}"
            )
        tasks.append(FetchTask(priority, purpose, instruction))
    return tasks


def _normalize_post(raw: dict, *, captured_at: str, purpose: str, priority: str, source: str) -> dict:
    return {
        "post_id": str(raw.get("id") or ""),
        "text": str(raw.get("text") or ""),
        "username": str(raw.get("username") or ""),
        "permalink": str(raw.get("permalink") or ""),
        "posted_at": str(raw.get("timestamp") or ""),
        "media_type": str(raw.get("media_type") or ""),
        "is_reply": bool(raw.get("is_reply")),
        "captured_at": captured_at,
        "fetch_purpose": purpose,
        "fetch_priority": priority,
        "fetch_source": source,
        "processed": False,
    }


def _fetch_task_posts(client: ThreadsApiClient, task: FetchTask) -> list[dict]:
    captured_at = _now_jst_iso()
    if task.is_own_profile:
        raw_posts = client.me_threads(limit=SEARCH_MAX_RESULTS)
        source = "me_threads"
    elif task.is_username:
        username = task.instruction.strip().lstrip("@")
        raw_posts = client.profile_posts(username, limit=SEARCH_MAX_RESULTS)
        source = "profile_posts"
    else:
        raw_posts = client.keyword_search(task.instruction, limit=SEARCH_MAX_RESULTS)
        source = "keyword_search"
    return [
        _normalize_post(
            raw,
            captured_at=captured_at,
            purpose=task.purpose,
            priority=task.priority,
            source=source,
        )
        for raw in raw_posts
        if raw.get("id")
    ]


def _output_filename(task: FetchTask, index: int) -> str:
    stamp = datetime.now(JST).strftime("%Y%m%d-%H%M%S")
    slug = _slug(task.instruction)
    return f"{THREADS_JSON_PREFIX}{index:02d}-{slug}-{stamp}.json"


def fetch_from_weekly_suggestion(
    *,
    suggestion_path: Path,
    output_dir: Path,
    access_token: str | None = None,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    client = ThreadsApiClient(
        access_token or load_access_token(),
        api_base=load_api_base(),
    )
    tasks = parse_weekly_suggestion_json(suggestion_path)
    written: list[Path] = []

    for index, task in enumerate(tasks, start=1):
        posts = _fetch_task_posts(client, task)
        payload = {
            "fetched_at": _now_jst_iso(),
            "instruction": task.instruction,
            "purpose": task.purpose,
            "priority": task.priority,
            "posts": posts,
        }
        out_path = output_dir / _output_filename(task, index)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(out_path)
        rel = out_path.name
        print(f"[threads_api] wrote {rel} ({len(posts)} posts)", flush=True)

    return written
