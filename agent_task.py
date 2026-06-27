import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from app_config import AppConfig
from run_agent import ask_agent

FIXED_INSTRUCTIONS_DIR = Path(__file__).resolve().parent / "fixed_instructions"
AGENT_PROMPT_TEMPLATE_PATH = FIXED_INSTRUCTIONS_DIR / "agent_prompt.md"
COMMON_OUTPUT_PATH = FIXED_INSTRUCTIONS_DIR / "common_output.md"
REVIEW_OUTPUT_FILE = "review.json"


class Snapshot:
    """File-level snapshot of work_dir for diff detection and restore."""

    def __init__(self, work_dir, snapshot_dir):
        self.work_dir = work_dir
        self.snapshot_dir = snapshot_dir
        self.manifest = None

    def _build_manifest(self):
        manifest = {}
        for path in sorted(self.work_dir.rglob("*")):
            abs_path = path.resolve().as_posix()
            if path.is_dir():
                manifest[abs_path] = "dir"
                continue
            if path.is_file():
                file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                manifest[abs_path] = f"file:{file_hash}"
        return manifest

    def snapshot(self):
        if self.snapshot_dir.exists():
            shutil.rmtree(self.snapshot_dir)
        shutil.copytree(self.work_dir, self.snapshot_dir)
        self.manifest = self._build_manifest()

    def diff(self):
        if self.manifest is None:
            raise RuntimeError("diff() called before snapshot()")
        current_manifest = self._build_manifest()
        changed_paths = sorted(set(self.manifest.keys()) | set(current_manifest.keys()))
        return [path for path in changed_paths if self.manifest.get(path) != current_manifest.get(path)]

    def restore(self):
        if not self.snapshot_dir.exists():
            raise RuntimeError("cannot restore: snapshot does not exist")
        for path in self.work_dir.iterdir():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        for src in self.snapshot_dir.iterdir():
            dst = self.work_dir / src.name
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)


class ValidatedTaskRunner:
    def __init__(self, config: AppConfig):
        self.root_dir = config.root_dir
        self.work_dir = config.work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.instructions_dir = config.instructions_dir
        self.agent_log_file = config.agent_log_file
        self.agent_timeout_sec = config.agent_timeout_sec
        self.system_validation_max_failures = config.system_validation_max_failures
        self.review_ng_max = config.review_ng_max
        self.trash_dir = config.trash_dir
        self.trash_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.trash_run_dir = self.trash_dir / stamp
        self.trash_run_dir.mkdir(parents=True, exist_ok=True)
        rel = self.trash_run_dir.relative_to(self.root_dir)
        print(f"[runner] trash run dir: {rel}", flush=True)
        self.snapshot_dir = self.work_dir.parent / (self.work_dir.name + "_snapshot")
        self.snapshot = Snapshot(self.work_dir, self.snapshot_dir)
        self.agent_log_file.parent.mkdir(parents=True, exist_ok=True)
        self.agent_log_file.write_text("", encoding="utf-8")

        if self.snapshot_dir.exists():
            shutil.rmtree(self.snapshot_dir)

        for meta_file in ("result.json", "review.json", "abort.txt"):
            path = self.work_dir / meta_file
            if path.exists():
                path.unlink()

    def _relative_paths_from_editable_set(self, editable_set: set[str]) -> list[str]:
        work_dir = self.work_dir.resolve()
        return sorted(
            Path(path).relative_to(work_dir).as_posix()
            for path in editable_set
        )

    def _format_editable_files_for_prompt(self, paths: list[str]) -> str:
        if not paths:
            return "(none)"
        return ", ".join(paths)

    def _build_agent_prompt(
        self,
        instruction_path: Path,
        task_id: str,
        editable_paths: list[str],
        retry_message: str | None = None,
    ) -> str:
        if not AGENT_PROMPT_TEMPLATE_PATH.is_file():
            raise RuntimeError(f"agent prompt template not found: {AGENT_PROMPT_TEMPLATE_PATH}")
        if not COMMON_OUTPUT_PATH.is_file():
            raise RuntimeError(f"common output rules not found: {COMMON_OUTPUT_PATH}")

        prompt = AGENT_PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8").strip().format(
            task_id=task_id,
            editable_files=self._format_editable_files_for_prompt(editable_paths),
            common_output_path=COMMON_OUTPUT_PATH.resolve().as_posix(),
            instruction_path=instruction_path.resolve().as_posix(),
        )
        if retry_message is not None:
            retry_section = (
                "This task was sent back for the following reasons. "
                "Address the feedback and redo the task.\n\n"
                f"{retry_message}"
            )
            prompt = f"{retry_section}\n\n{prompt}"
        return prompt

    def _run_agent(
        self,
        instruction_path: Path,
        task_id: str,
        editable_paths: list[str],
        retry_message: str | None = None,
    ):
        prompt = self._build_agent_prompt(
            instruction_path,
            task_id,
            editable_paths,
            retry_message,
        )
        result = ask_agent(
            self.work_dir,
            prompt,
            timeout_sec=self.agent_timeout_sec,
            log_file=self.agent_log_file,
        )
        if result["status"] == "failure":
            raise RuntimeError(f"agent execution failed: {result['message']}")

    def _is_ignored_diff_path(self, path):
        # Dot-prefixed path segments (e.g. .hidden, sub/.cache) are excluded from validation.
        candidate = Path(path).resolve()
        try:
            relative = candidate.relative_to(self.work_dir)
        except ValueError:
            return False
        return any(part.startswith(".") for part in relative.parts)

    def _log(self, task_id, message):
        print(f"[task:{task_id}] {message}", flush=True)

    def _deliverables_label(self, editable_files):
        if not editable_files:
            return ""
        return f" deliverables: {', '.join(editable_files)}"

    def _backup_file_to_trash(self, src: Path) -> None:
        if not src.is_file():
            return
        dest_dir = self.trash_run_dir / "agent_out"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        if dest.exists():
            stem = src.stem
            suffix = src.suffix
            index = 1
            while dest.exists():
                dest = dest_dir / f"{stem}-{index}{suffix}"
                index += 1
        shutil.move(str(src), str(dest))

    def _validate_work_relative_path(self, item: str, *, label: str) -> Path:
        if not isinstance(item, str) or item == "":
            raise ValueError(f"{label} entries must be non-empty strings")
        item_path = Path(item)
        if item_path.is_absolute():
            raise ValueError(f"{label} must be relative paths, not absolute: {item}")
        item_path = (self.work_dir / item_path).resolve()
        if self.work_dir not in item_path.parents:
            raise ValueError(f"{label} must be under WORK_DIR: {item}")
        return item_path

    def _renew_work_files(self, task_id: str, renew_files: list[str]) -> None:
        if not renew_files:
            return

        renewed: list[str] = []
        for item in renew_files:
            path = self.work_dir / item
            if not path.is_file():
                continue
            self._backup_file_to_trash(path)
            renewed.append(item)
        if renewed:
            self._log(task_id, f"renewed: {', '.join(sorted(renewed))}")

    def execute_task(self, task_id, editable_files=None, renew_files=None, return_status=None):
        if not isinstance(task_id, str) or task_id == "":
            raise ValueError("task_id must be a non-empty string")
        self._log(task_id, "task started")

        work_instruction_path = self.instructions_dir / f"{task_id}.md"
        if not work_instruction_path.is_file():
            raise ValueError(f"work instruction not found: {work_instruction_path}")

        review_instruction_path = self.instructions_dir / f"{task_id}R.md"
        if renew_files is None:
            renew_files = []
        if not isinstance(renew_files, list):
            raise ValueError("renew_files must be a list")

        if editable_files is None:
            editable_files = []
        if not isinstance(editable_files, list):
            raise ValueError("editable_files must be a list")

        editable_files = list(dict.fromkeys(editable_files + renew_files))

        skip_review = not editable_files
        if not skip_review and not review_instruction_path.is_file():
            raise ValueError(f"review instruction not found: {review_instruction_path}")

        editable_set = set()
        for item in editable_files:
            item_path = self._validate_work_relative_path(item, label="editable_files")
            editable_set.add(item_path.as_posix())

        self._renew_work_files(task_id, renew_files)

        status_set = None
        if return_status is not None:
            if not isinstance(return_status, list) or len(return_status) == 0:
                raise ValueError("return_status must be a non-empty list")
            status_set = set()
            for status in return_status:
                if not isinstance(status, str) or status == "":
                    raise ValueError("return_status entries must be non-empty strings")
                status_set.add(status)
            editable_set.add((self.work_dir / "result.json").resolve().as_posix())

        review_count = 0
        task_status_value = None

        retry_message = None
        system_violation_count = 0

        # Outer loop: repeat work+review until review passes or review NG limit is reached.
        while True:
            self.snapshot.snapshot()

            # Work phase: run agent and validate file changes until system checks pass.
            while True:
                self._log(task_id, "work started")
                self._run_agent(
                    work_instruction_path,
                    task_id,
                    self._relative_paths_from_editable_set(editable_set),
                    retry_message,
                )
                self._log(task_id, "work finished")

                abort_path = self.work_dir / "abort.txt"
                if abort_path.is_file():
                    reason = abort_path.read_text(encoding="utf-8").strip()
                    if reason == "":
                        reason = "(no reason provided)"
                    raise RuntimeError(f"task aborted: task_id={task_id}, reason={reason}")

                changed_paths = self.snapshot.diff()
                violations = []
                for path in changed_paths:
                    if self._is_ignored_diff_path(path):
                        continue
                    if path not in editable_set:
                        violations.append(f"editable_files violation: {path}")

                if status_set is not None:
                    result_path = self.work_dir / "result.json"
                    if not result_path.is_file():
                        violations.append("result.json was not created")
                    else:
                        try:
                            result_data = json.loads(result_path.read_text(encoding="utf-8"))
                        except json.JSONDecodeError as error:
                            violations.append(f"result.json is not valid JSON: {error}")
                        else:
                            if not isinstance(result_data, dict):
                                violations.append("result.json top-level value must be an object")
                            elif set(result_data.keys()) != {"status"}:
                                violations.append("result.json must contain only the status key")
                            elif result_data["status"] not in status_set:
                                violations.append(
                                    f"result.json status not allowed: {result_data['status']}"
                                )
                            else:
                                task_status_value = result_data["status"]
                                result_path.unlink()

                if violations:
                    system_violation_count += 1
                    self._log(
                        task_id,
                        f"system validation retry ({system_violation_count}/{self.system_validation_max_failures}): {' | '.join(violations)}",
                    )
                    retry_message = "\n".join([f"- {v}" for v in violations])
                    try:
                        self.snapshot.restore()
                    except Exception as error:
                        raise RuntimeError(f"snapshot restore failed: {error}") from error
                    if system_violation_count >= self.system_validation_max_failures:
                        raise RuntimeError(
                            f"system validation limit reached: task_id={task_id}, violations={violations}"
                        )
                else:
                    system_violation_count = 0
                    retry_message = None
                    break

            if skip_review:
                self._log(
                    task_id,
                    f"task finished (review skipped){self._deliverables_label(editable_files)}",
                )
                self._log(task_id, "===============================")
                return task_status_value

            self.snapshot.snapshot()

            # Review phase: run review agent and validate review.json until system checks pass.
            while True:
                self._log(task_id, "review started")
                self._run_agent(
                    review_instruction_path,
                    task_id,
                    [REVIEW_OUTPUT_FILE],
                    retry_message,
                )
                self._log(task_id, "review finished")

                changed_paths = self.snapshot.diff()
                violations = []
                review_json_path = (self.work_dir / "review.json").resolve().as_posix()
                for path in changed_paths:
                    if self._is_ignored_diff_path(path):
                        continue
                    if path != review_json_path:
                        violations.append(f"only review.json may be changed: {path}")

                review_data = None
                review_path = self.work_dir / "review.json"
                if not review_path.is_file():
                    violations.append("review.json was not created")
                else:
                    try:
                        review_data = json.loads(review_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError as error:
                        violations.append(f"review.json is not valid JSON: {error}")
                    else:
                        if not isinstance(review_data, dict):
                            violations.append("review.json top-level value must be an object")
                        elif set(review_data.keys()) != {"result", "reason"}:
                            violations.append("review.json must contain only result and reason keys")
                        elif review_data["result"] not in {"OK", "NG"}:
                            violations.append(f"review.json result not allowed: {review_data['result']}")
                        elif not isinstance(review_data["reason"], str):
                            violations.append("review.json reason must be a string")
                        else:
                            review_path.unlink()

                if violations:
                    system_violation_count += 1
                    self._log(
                        task_id,
                        f"review system validation retry ({system_violation_count}/{self.system_validation_max_failures}): {' | '.join(violations)}",
                    )
                    retry_message = "\n".join([f"- {v}" for v in violations])
                    try:
                        self.snapshot.restore()
                    except Exception as error:
                        raise RuntimeError(f"snapshot restore failed: {error}") from error
                    if system_violation_count >= self.system_validation_max_failures:
                        raise RuntimeError(
                            f"review system validation limit reached: task_id={task_id}, violations={violations}"
                        )
                else:
                    system_violation_count = 0
                    retry_message = None
                    break

            if review_data["result"] == "OK":
                self._log(
                    task_id,
                    f"task finished{self._deliverables_label(editable_files)}",
                )
                self._log(task_id, "===============================")
                return task_status_value
            else:
                review_count += 1
                retry_message = review_data["reason"]
                self._log(
                    task_id,
                    f"review rejected ({review_count}/{self.review_ng_max}): {retry_message}",
                )
                if review_count >= self.review_ng_max:
                    raise RuntimeError(
                        f"review NG limit reached: task_id={task_id}, reason={retry_message}"
                    )
