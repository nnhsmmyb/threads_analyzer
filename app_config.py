from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    root_dir: Path
    work_dir: Path
    instructions_dir: Path
    agent_log_file: Path
    trash_dir: Path
    agent_timeout_sec: float | None
    system_validation_max_failures: int
    review_ng_max: int
