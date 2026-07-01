import argparse

import agent_task as at
import app_paths as paths
import system_task as st
from app_config import AppConfig
from path_validators import as_optional_timeout_sec, as_positive_int, as_relative_path, as_root
from pathlib import Path
from runtime_env import bootstrap_runtime_env

ROOT = Path(__file__).resolve().parent

SYSTEM_VALIDATION_MAX_FAILURES_PER_TASK = 3
REVIEW_NG_MAX_PER_TASK = 5
AGENT_LOG_FILE = "logs/agent_stdout.log"
AGENT_TIMEOUT_SEC = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run autoT pipeline", allow_abbrev=False)
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Skip Threads API fetch (ingest + insight only)",
    )
    return parser.parse_args()


def main(*, root_dir: Path, no_fetch: bool = False) -> None:
    config = AppConfig(
        root_dir=root_dir,
        work_dir=as_relative_path(root_dir, paths.AGENT_OUT_DIR),
        instructions_dir=as_relative_path(root_dir, paths.INSTRUCTIONS_DIR),
        agent_log_file=as_relative_path(root_dir, AGENT_LOG_FILE),
        trash_dir=as_relative_path(root_dir, paths.TRASH_DIR),
        agent_timeout_sec=as_optional_timeout_sec(AGENT_TIMEOUT_SEC),
        system_validation_max_failures=as_positive_int(SYSTEM_VALIDATION_MAX_FAILURES_PER_TASK),
        review_ng_max=as_positive_int(REVIEW_NG_MAX_PER_TASK),
    )
    system = st.TaskRunner(
        root_dir=root_dir,
        work_dir=config.work_dir,
        stock_dir=as_relative_path(root_dir, paths.STOCK_DIR),
        input_threads_dir=as_relative_path(root_dir, paths.INPUT_THREADS_DIR),
    )
    runner = at.ValidatedTaskRunner(config)

    if not no_fetch:
        system.fetch_from_suggestion()

    system.ingest_threads_json()

    runner.execute_task(
        "T020_insight",
        editable_files=[paths.T_INSIGHT_FILE],
    )
    system.mark_all_processed()


if __name__ == "__main__":
    args = parse_args()
    root_dir = as_root(ROOT)
    bootstrap_runtime_env(root_dir=root_dir)
    main(root_dir=root_dir, no_fetch=args.no_fetch)
