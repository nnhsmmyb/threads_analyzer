"""PATH と .env の読み込み。"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

_BOOTSTRAPPED = False


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


def _load_dotenv(*, root_dir: Path) -> None:
    for env_path in (root_dir / ".env", Path.cwd() / ".env"):
        if not env_path.is_file():
            continue
        for key, value in _read_env_file(env_path).items():
            os.environ.setdefault(key, value)
        return


def bootstrap_runtime_env(*, root_dir: Path | None = None) -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    if root_dir is None:
        root_dir = Path(__file__).resolve().parent
    _load_dotenv(root_dir=root_dir)
    _BOOTSTRAPPED = True


def resolve_command(name: str, *, root_dir: Path | None = None) -> str:
    bootstrap_runtime_env(root_dir=root_dir)
    path = shutil.which(name)
    if path is None:
        raise FileNotFoundError(f"command not found: {name!r}")
    return path
