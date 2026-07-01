#!/usr/bin/env python3
"""Threads API OAuth 2.0 の初回認可と .env への token 保存。"""

from __future__ import annotations

import argparse
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from threads_oauth import (
    DEFAULT_SCOPES,
    ThreadsOAuthError,
    build_authorize_url,
    exchange_authorization_code,
    exchange_long_lived_token,
    load_oauth_config,
    persist_token_response,
    verify_access_token,
)


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    result: dict[str, str] | None = None
    expected_state: str = ""
    expected_path: str = "/callback"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _set_result(self, value: dict[str, str]) -> None:
        type(self).result = value

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != self.expected_path:
            self.send_error(404, "Not Found")
            return
        params = parse_qs(parsed.query)
        if params.get("error"):
            message = params["error"][0]
            if params.get("error_description"):
                message = f"{message}: {params['error_description'][0]}"
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(message.encode("utf-8"))
            self._set_result({"error": message})
            return
        state = (params.get("state") or [""])[0]
        code = (params.get("code") or [""])[0]
        if state != self.expected_state:
            self.send_error(400, "invalid state")
            self._set_result({"error": "invalid state"})
            return
        if not code:
            self.send_error(400, "missing code")
            self._set_result({"error": "missing code"})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><p>Authorization complete. You can close this tab.</p></body></html>"
        )
        self._set_result({"code": code})


def _extract_code(value: str) -> tuple[str, str]:
    stripped = value.strip().strip('"').strip("'")
    if "code=" in stripped:
        parsed = urlparse(stripped)
        params = parse_qs(parsed.query)
        code = (params.get("code") or [""])[0].strip()
        state = (params.get("state") or [""])[0].strip()
        if not code:
            raise SystemExit("could not find code= in URL")
        return code, state
    if stripped:
        return stripped, ""
    raise SystemExit("empty authorization code")


def _state_file(env_path: Path) -> Path:
    return env_path.parent / ".threads_oauth_state"


def _save_state(env_path: Path, state: str) -> None:
    _state_file(env_path).write_text(state, encoding="utf-8")


def _load_state(env_path: Path) -> str:
    path = _state_file(env_path)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _listen_for_callback(*, host: str, port: int, path: str, state: str) -> str:
    handler = _OAuthCallbackHandler
    handler.expected_state = state
    handler.expected_path = path
    handler.result = None
    server = HTTPServer((host, port), handler)
    server.timeout = 1

    def serve_until_done() -> None:
        while handler.result is None:
            server.handle_request()

    thread = threading.Thread(target=serve_until_done, daemon=True)
    thread.start()
    thread.join(timeout=300)
    server.server_close()
    result = handler.result or {}
    if "error" in result:
        raise ThreadsOAuthError(result["error"])
    code = result.get("code", "").strip()
    if not code:
        raise ThreadsOAuthError("authorization timed out or callback was not received")
    return code


def main() -> None:
    parser = argparse.ArgumentParser(description="Authorize Threads API OAuth 2.0 user context")
    parser.add_argument(
        "--env",
        default=".env",
        help="path to .env file (default: .env)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="print authorize URL instead of opening a browser",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="HTTPS localhost flow: open browser, then paste callback URL (no tunnel)",
    )
    parser.add_argument(
        "--code",
        help="authorization code or full callback URL (skips local callback server)",
    )
    args = parser.parse_args()

    env_path = Path(args.env)
    config = load_oauth_config(env_path=env_path)
    parsed_redirect = urlparse(config.redirect_uri)
    if parsed_redirect.scheme not in ("http", "https") or not parsed_redirect.netloc:
        raise SystemExit(f"invalid THREADS_OAUTH_REDIRECT_URI: {config.redirect_uri}")

    if args.code:
        code, returned_state = _extract_code(args.code)
        expected_state = _load_state(env_path)
        if returned_state and expected_state and returned_state != expected_state:
            raise SystemExit("state mismatch; run --manual again and paste the latest URL")
    elif args.manual:
        state = secrets.token_urlsafe(24)
        _save_state(env_path, state)
        authorize_url = build_authorize_url(
            app_id=config.app_id,
            redirect_uri=config.redirect_uri,
            state=state,
            scopes=DEFAULT_SCOPES,
        )
        print("[oauth] manual mode (no tunnel)", flush=True)
        print("[oauth] redirect URI:", config.redirect_uri, flush=True)
        print("[oauth] scopes:", ",".join(DEFAULT_SCOPES), flush=True)
        print("[oauth] open this URL and approve the app:", flush=True)
        print(authorize_url, flush=True)
        if not args.no_browser:
            webbrowser.open(authorize_url)
        print(
            "[oauth] after approval, copy the full URL from the browser address bar "
            "(SSL error page is OK) and paste below",
            flush=True,
        )
        pasted = input("[oauth] callback URL or code: ").strip()
        code, returned_state = _extract_code(pasted)
        if returned_state and returned_state != state:
            raise SystemExit("state mismatch; run --manual again")
    else:
        host = parsed_redirect.hostname or "127.0.0.1"
        port = parsed_redirect.port or (443 if parsed_redirect.scheme == "https" else 80)
        path = parsed_redirect.path or "/callback"

        state = secrets.token_urlsafe(24)
        authorize_url = build_authorize_url(
            app_id=config.app_id,
            redirect_uri=config.redirect_uri,
            state=state,
            scopes=DEFAULT_SCOPES,
        )

        print("[oauth] waiting for callback on", config.redirect_uri, flush=True)
        print("[oauth] scopes:", ",".join(DEFAULT_SCOPES), flush=True)
        print("[oauth] open this URL in your browser and approve the app:", flush=True)
        print(authorize_url, flush=True)
        if not args.no_browser:
            webbrowser.open(authorize_url)
        print("[oauth] waiting up to 5 minutes for callback...", flush=True)

        code = _listen_for_callback(host=host, port=port, path=path, state=state)
    short_lived = exchange_authorization_code(
        code=code,
        app_id=config.app_id,
        app_secret=config.app_secret,
        redirect_uri=config.redirect_uri,
    )
    short_lived_token = (short_lived.get("access_token") or "").strip()
    user_id = str(short_lived.get("user_id") or "").strip()
    if not short_lived_token:
        raise SystemExit("authorization code exchange did not include access_token")

    long_lived = exchange_long_lived_token(
        short_lived_token=short_lived_token,
        app_secret=config.app_secret,
    )
    access_token = persist_token_response(env_path, long_lived, user_id=user_id)

    user = verify_access_token(access_token)
    username = user.get("username") or "(unknown)"
    print(f"[oauth] authorized as @{username}", flush=True)
    print(f"[oauth] wrote tokens to {env_path}", flush=True)


if __name__ == "__main__":
    main()
