from pathlib import Path


def as_root(path: Path) -> Path:
    if not isinstance(path, Path):
        raise ValueError("expected a Path")
    resolved = path.expanduser().resolve()
    if not resolved.is_absolute():
        raise ValueError(f"path must be absolute: {resolved}")
    return resolved


def as_relative_path(root_dir: Path, value: str) -> Path:
    if not isinstance(value, str) or value == "":
        raise ValueError("expected a non-empty str")
    relative_path = Path(value)
    if relative_path.is_absolute():
        raise ValueError(f"path must be relative to root_dir: {value}")
    return (root_dir / relative_path).resolve()


def as_positive_int(value: int) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ValueError("expected a positive int")
    return value


def as_optional_timeout_sec(value: int | float | None) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValueError("timeout must be a positive number or None")
    return float(value)
