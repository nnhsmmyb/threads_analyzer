from __future__ import annotations

import json
from pathlib import Path

import yaml

import app_paths as paths

MAX_POSTS_PER_FILE = 1000
PROCESSED_FIELD = "processed"
MARKET_FILE = paths.MARKET_STOCK_FILE
STOCK_KEYS = {"market": MARKET_FILE}


def _post_sort_key(post: dict) -> str:
    return str(post.get("posted_at") or post.get("captured_at") or "")


def _load_stock(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _save_stock(path: Path, posts: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(posts, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def ingest_json_dir(*, input_dir: Path, stock_dir: Path) -> int:
    """input/threads/*.json を market ストックへ統合する。"""
    if not input_dir.is_dir():
        return 0

    stock_path = stock_dir / MARKET_FILE
    stock = _load_stock(stock_path)
    by_id = {str(p.get("post_id") or ""): p for p in stock if p.get("post_id")}

    added = 0
    for json_path in sorted(input_dir.glob("*.json")):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        raw_posts = payload.get("posts")
        if not isinstance(raw_posts, list):
            continue
        for raw in raw_posts:
            if not isinstance(raw, dict):
                continue
            post_id = str(raw.get("post_id") or "")
            if not post_id:
                continue
            if post_id in by_id:
                continue
            record = dict(raw)
            record.setdefault(PROCESSED_FIELD, False)
            by_id[post_id] = record
            added += 1

    merged = sorted(by_id.values(), key=_post_sort_key, reverse=True)
    if len(merged) > MAX_POSTS_PER_FILE:
        merged = merged[:MAX_POSTS_PER_FILE]
    _save_stock(stock_path, merged)
    if added > 0:
        print(f"[t_data] ingested {added} post(s) into {MARKET_FILE}", flush=True)
    return added


def input_has_posts(input_dir: Path) -> bool:
    if not input_dir.is_dir():
        return False
    for path in input_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        posts = payload.get("posts")
        if isinstance(posts, list) and posts:
            return True
    return False


def clear_input_dir(input_dir: Path) -> None:
    if not input_dir.is_dir():
        return
    for path in input_dir.iterdir():
        if path.is_file():
            path.unlink()


def mark_all_processed(stock_dir: Path) -> int:
    stock_path = stock_dir / MARKET_FILE
    stock = _load_stock(stock_path)
    updated = 0
    for post in stock:
        if post.get(PROCESSED_FIELD) is False:
            post[PROCESSED_FIELD] = True
            updated += 1
    if updated:
        _save_stock(stock_path, stock)
        print(f"[t_data] marked {updated} post(s) processed", flush=True)
    return updated


def fetch_stock(
    stock_dir: Path,
    *,
    key: str,
    limit: int,
    unprocessed_only: bool = False,
) -> dict:
    if key not in STOCK_KEYS:
        raise ValueError(f"unknown stock key: {key}")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    stock_path = stock_dir / STOCK_KEYS[key]
    stock = _load_stock(stock_path)
    stock = sorted(stock, key=_post_sort_key, reverse=True)

    if unprocessed_only:
        stock = [p for p in stock if p.get(PROCESSED_FIELD) is False]

    selected = stock[:limit]
    return {
        "stock_key": key,
        "total_posts": len(stock),
        "returned": len(selected),
        "posts": selected,
    }
