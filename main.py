import agent_task as at
import system_task as st
from app_config import AppConfig
from path_validators import as_optional_timeout_sec, as_positive_int, as_relative_path, as_root
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SYSTEM_VALIDATION_MAX_FAILURES_PER_TASK = 3
REVIEW_NG_MAX_PER_TASK = 5
WORK_DIR = "agent_out"
INSTRUCTIONS_DIR = "instructions"
INPUT_DIR = "input/inbox"
AGENT_LOG_FILE = "logs/agent_stdout.log"
AGENT_TIMEOUT_SEC = None  # Per-agent-call timeout in seconds. None means no limit.
TRASH_DIR = "trash"


def main():
    root_dir = as_root(ROOT)
    config = AppConfig(
        root_dir=root_dir,
        work_dir=as_relative_path(root_dir, WORK_DIR),
        instructions_dir=as_relative_path(root_dir, INSTRUCTIONS_DIR),
        agent_log_file=as_relative_path(root_dir, AGENT_LOG_FILE),
        trash_dir=as_relative_path(root_dir, TRASH_DIR),
        agent_timeout_sec=as_optional_timeout_sec(AGENT_TIMEOUT_SEC),
        system_validation_max_failures=as_positive_int(SYSTEM_VALIDATION_MAX_FAILURES_PER_TASK),
        review_ng_max=as_positive_int(REVIEW_NG_MAX_PER_TASK),
    )
    runner = at.ValidatedTaskRunner(config)
    input_manager = st.InputManager(
        input_dir=as_relative_path(root_dir, INPUT_DIR),
    )

    if not input_manager.has_input():
        return

    runner.execute_task(
        "T001_ingest",
        editable_files=["incident_context.md"],
    )
    runner.execute_task(
        "T002_timeline",
        editable_files=["timeline.md"],
    )
    response_level = runner.execute_task(
        "T003_hypothesis",
        editable_files=["hypothesis.md"],
        return_status=["action_required", "monitor_only"],
    )
    if response_level == "action_required":
        runner.execute_task(
            "T004_action_plan",
            editable_files=["action_plan.md"],
        )
    else:
        print("[workflow] skipping T004_action_plan (monitor_only)", flush=True)


if __name__ == "__main__":
    main()
