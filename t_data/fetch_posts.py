#!/usr/bin/env python3
"""t_data ストックから投稿を取得する。エージェントはこのスクリプト経由のみ参照する。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app_paths as paths
import t_data_system as tds

DEFAULT_STOCK_DIR = ROOT / paths.STOCK_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch posts from t_data stock.")
    parser.add_argument(
        "--file",
        required=True,
        choices=sorted(tds.STOCK_KEYS),
        help="stock category key",
    )
    parser.add_argument("--limit", type=int, required=True, help="1-100")
    parser.add_argument("--unprocessed-only", action="store_true")
    parser.add_argument("--format", choices=("yaml", "json"), default="yaml")
    parser.add_argument("--stock-dir", type=Path, default=DEFAULT_STOCK_DIR)
    args = parser.parse_args()

    payload = tds.fetch_stock(
        args.stock_dir,
        key=args.file,
        limit=args.limit,
        unprocessed_only=args.unprocessed_only,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=120))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
