"""リポジトリ直下からの相対パス。"""

from __future__ import annotations

from pathlib import Path

PRODUCTS_DIR = "products"
AGENT_OUT_DIR = "agent_out"
INSTRUCTIONS_DIR = "instructions"
FIXED_INSTRUCTIONS_DIR = "fixed_instructions"
INPUT_THREADS_DIR = "input/threads"
STOCK_DIR = "t_data"
LOGS_DIR = "logs"
TRASH_DIR = "trash"

DATA_SUGGESTION_WEEKLY_FILE = "data_suggestion_weekly.json"
T_INSIGHT_FILE = "t_insight.md"
T_ACCOUNT_FILE = f"{FIXED_INSTRUCTIONS_DIR}/t_account.md"
MARKET_STOCK_FILE = "t_data_market.yaml"

DATA_SUGGESTION_WEEKLY_PATH = f"{AGENT_OUT_DIR}/{DATA_SUGGESTION_WEEKLY_FILE}"
T_INSIGHT_PATH = f"{AGENT_OUT_DIR}/{T_INSIGHT_FILE}"


def resolve(root_dir: Path, relative: str) -> Path:
    return root_dir.resolve() / relative
