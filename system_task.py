from pathlib import Path

import app_paths as paths
import t_data_system as tds
import threads_api_system as threads_api


class TaskRunner:
    def __init__(
        self,
        *,
        root_dir: Path,
        work_dir: Path,
        stock_dir: Path,
        input_threads_dir: Path,
    ) -> None:
        self.root_dir = root_dir
        self.work_dir = work_dir
        self.stock_dir = stock_dir
        self.input_threads_dir = input_threads_dir

        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.stock_dir.mkdir(parents=True, exist_ok=True)
        self.input_threads_dir.mkdir(parents=True, exist_ok=True)

    def weekly_suggestion_path(self) -> Path | None:
        path = self.work_dir / paths.DATA_SUGGESTION_WEEKLY_FILE
        return path if path.is_file() else None

    def fetch_from_suggestion(self) -> list[Path]:
        suggestion_path = self.weekly_suggestion_path()
        if suggestion_path is None:
            print(
                f"[main] skipping fetch: {paths.DATA_SUGGESTION_WEEKLY_FILE} not found in agent_out/",
                flush=True,
            )
            return []
        return threads_api.fetch_from_weekly_suggestion(
            suggestion_path=suggestion_path,
            output_dir=self.input_threads_dir,
        )

    def ingest_threads_json(self) -> int:
        if not tds.input_has_posts(self.input_threads_dir):
            rel = self.input_threads_dir.relative_to(self.root_dir)
            print(f"[main] skipping INGEST: no posts in {rel}", flush=True)
            return 0
        count = tds.ingest_json_dir(input_dir=self.input_threads_dir, stock_dir=self.stock_dir)
        tds.clear_input_dir(self.input_threads_dir)
        return count

    def mark_all_processed(self) -> None:
        tds.mark_all_processed(self.stock_dir)
