from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_BASE = "https://graph.threads.net/v1.0"
AUTHORIZE_URL = "https://threads.net/oauth/authorize"
TOKEN_URL = "https://graph.threads.net/oauth/access_token"
LONG_LIVED_URL = "https://graph.threads.net/access_token"
REFRESH_URL = "https://graph.threads.net/refresh_access_token"
DEFAULT_REDIRECT_URI = "https://127.0.0.1:8080/callback"
DEFAULT_SCOPES = (
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
REFRESH_THRESHOLD_DAYS = 7
MIN_TOKEN_AGE_HOURS = 24


class ThreadsOAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class OAuthConfig:
    app_id: str
    app_secret: str
    redirect_uri: str
    access_token: str
    user_id: str
    expires_at: datetime | None
    obtained_at: datetime | None


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _env_value(name: str, *, env_path: Path | None = None) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if env_path is None:
        env_path = Path(".env")
    return _read_env_file(env_path).get(name, "").strip()


def _oauth_token_value(name: str, *, env_path: Path) -> str:
    """Prefer .env over os.environ so refreshed tokens are not masked by stale env."""
    if env_path.is_file():
        value = _read_env_file(env_path).get(name, "").strip()
        if value:
            return value
    return os.environ.get(name, "").strip()


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def update_env_file(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    written: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                written.add(key)
                continue
        new_lines.append(line)
    for key, value in updates.items():
        if key not in written:
            new_lines.append(f"{key}={value}")
    path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
    for key, value in updates.items():
        os.environ[key] = value


def load_oauth_config(*, env_path: Path | None = None) -> OAuthConfig:
    path = env_path or Path(".env")
    app_id = _env_value("THREADS_APP_ID", env_path=path)
    app_secret = _env_value("THREADS_APP_SECRET", env_path=path)
    redirect_uri = _env_value("THREADS_OAUTH_REDIRECT_URI", env_path=path) or DEFAULT_REDIRECT_URI
    access_token = _oauth_token_value("THREADS_ACCESS_TOKEN", env_path=path)
    user_id = _oauth_token_value("THREADS_USER_ID", env_path=path)
    expires_at = _parse_datetime(_oauth_token_value("THREADS_TOKEN_EXPIRES_AT", env_path=path))
    obtained_at = _parse_datetime(_oauth_token_value("THREADS_TOKEN_OBTAINED_AT", env_path=path))
    if not app_id or not app_secret:
        raise ValueError("THREADS_APP_ID and THREADS_APP_SECRET are required")
    return OAuthConfig(
        app_id=app_id,
        app_secret=app_secret,
        redirect_uri=redirect_uri,
        access_token=access_token,
        user_id=user_id,
        expires_at=expires_at,
        obtained_at=obtained_at,
    )


def build_authorize_url(
    *,
    app_id: str,
    redirect_uri: str,
    state: str,
    scopes: tuple[str, ...] = DEFAULT_SCOPES,
) -> str:
    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "scope": ",".join(scopes),
        "response_type": "code",
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def _request_json(
    *,
    url: str,
    method: str = "GET",
    data: dict[str, str] | None = None,
) -> dict:
    body = None
    headers: dict[str, str] = {}
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ThreadsOAuthError(f"request failed ({exc.code}): {detail}") from exc


def exchange_authorization_code(
    *,
    code: str,
    app_id: str,
    app_secret: str,
    redirect_uri: str,
) -> dict:
    return _request_json(
        url=TOKEN_URL,
        method="POST",
        data={
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        },
    )


def exchange_long_lived_token(*, short_lived_token: str, app_secret: str) -> dict:
    query = urllib.parse.urlencode(
        {
            "grant_type": "th_exchange_token",
            "client_secret": app_secret,
            "access_token": short_lived_token,
        }
    )
    return _request_json(url=f"{LONG_LIVED_URL}?{query}")


def refresh_long_lived_token(*, access_token: str) -> dict:
    query = urllib.parse.urlencode(
        {
            "grant_type": "th_refresh_token",
            "access_token": access_token,
        }
    )
    return _request_json(url=f"{REFRESH_URL}?{query}")


def _token_updates(payload: dict, *, user_id: str = "") -> dict[str, str]:
    access_token = payload.get("access_token", "").strip()
    if not access_token:
        raise ThreadsOAuthError("token response did not include access_token")
    expires_in = int(payload.get("expires_in") or 0)
    if expires_in <= 0:
        raise ThreadsOAuthError("token response did not include expires_in")
    now = datetime.now(timezone.utc)
    updates = {
        "THREADS_ACCESS_TOKEN": access_token,
        "THREADS_TOKEN_OBTAINED_AT": now.isoformat(),
        "THREADS_TOKEN_EXPIRES_AT": (now + timedelta(seconds=expires_in)).isoformat(),
    }
    resolved_user_id = (user_id or str(payload.get("user_id") or "")).strip()
    if resolved_user_id:
        updates["THREADS_USER_ID"] = resolved_user_id
    return updates


def persist_token_response(path: Path, payload: dict, *, user_id: str = "") -> str:
    updates = _token_updates(payload, user_id=user_id)
    update_env_file(path, updates)
    return updates["THREADS_ACCESS_TOKEN"]


def _should_refresh_proactively(config: OAuthConfig) -> bool:
    if not config.access_token or config.expires_at is None:
        return False
    now = datetime.now(timezone.utc)
    refresh_after = config.expires_at - timedelta(days=REFRESH_THRESHOLD_DAYS)
    if now < refresh_after:
        return False
    if config.obtained_at is not None:
        min_refresh_at = config.obtained_at + timedelta(hours=MIN_TOKEN_AGE_HOURS)
        if now < min_refresh_at:
            return False
    return True


def _refresh_and_persist(config: OAuthConfig, path: Path) -> str:
    payload = refresh_long_lived_token(access_token=config.access_token)
    return persist_token_response(path, payload, user_id=config.user_id)


def get_user_access_token(*, env_path: Path | None = None, refresh_if_needed: bool = True) -> str:
    path = env_path or Path(".env")
    config = load_oauth_config(env_path=path)
    if not config.access_token:
        raise ValueError("THREADS_ACCESS_TOKEN is not set; run threads_oauth_setup.py first")
    if refresh_if_needed and _should_refresh_proactively(config):
        return _refresh_and_persist(config, path)
    try:
        verify_access_token(config.access_token)
        return config.access_token
    except ThreadsOAuthError as exc:
        if not refresh_if_needed or "me failed (401)" not in str(exc):
            raise
    if refresh_if_needed:
        return _refresh_and_persist(config, path)
    raise ValueError("THREADS_ACCESS_TOKEN is invalid; run threads_oauth_setup.py again")


def verify_access_token(access_token: str) -> dict:
    query = urllib.parse.urlencode(
        {
            "fields": "id,username",
            "access_token": access_token,
        }
    )
    request = urllib.request.Request(f"{API_BASE}/me?{query}")
    try:
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ThreadsOAuthError(f"me failed ({exc.code}): {detail}") from exc
    return payload
