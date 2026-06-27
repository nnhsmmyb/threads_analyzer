from pathlib import Path


class InputManager:
    def __init__(self, *, input_dir: Path):
        self.input_dir = input_dir

    def has_input(self) -> bool:
        if not self.input_dir.exists():
            return False
        return any(path.is_file() for path in self.input_dir.iterdir())
