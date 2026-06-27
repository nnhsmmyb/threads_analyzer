#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import IO, Literal, TypedDict


class AgentResult(TypedDict):
    status: Literal["success", "failure"]
    message: str


def _pump_stream(
    stream: IO[str],
    chunks: list[str],
    log_f: IO[str] | None,
    log_lock: threading.Lock | None,
    *,
    tag: str | None = None,
) -> None:
    try:
        for line in stream:
            chunks.append(line)
            if log_f is not None and log_lock is not None:
                with log_lock:
                    if tag:
                        log_f.write(f"[{tag}] ")
                    log_f.write(line)
                    log_f.flush()
    finally:
        stream.close()


class AgentRunner(ABC):
    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    @abstractmethod
    def build_command(self, workdir: Path, prompt: str, **options) -> list[str]:
        pass

    def _run_with_log(
        self,
        cmd: list[str],
        cwd: Path,
        log_path: Path,
        timeout_sec: float | None,
    ) -> tuple[int, str, str]:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_lock = threading.Lock()

        with log_path.open("a", encoding="utf-8") as log_f:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            stdout_chunks: list[str] = []
            stderr_chunks: list[str] = []
            threads = [
                threading.Thread(
                    target=_pump_stream,
                    args=(proc.stdout, stdout_chunks, log_f, log_lock),
                    daemon=True,
                ),
                threading.Thread(
                    target=_pump_stream,
                    args=(proc.stderr, stderr_chunks, log_f, log_lock),
                    kwargs={"tag": "stderr"},
                    daemon=True,
                ),
            ]
            for t in threads:
                t.start()

            try:
                proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                with log_lock:
                    log_f.write(
                        f"\n[{self.agent_name}] timed out after {timeout_sec} seconds\n"
                    )
                    log_f.flush()
                for t in threads:
                    t.join()
                return -1, "", f"{self.agent_name} timed out after {timeout_sec} seconds"

            for t in threads:
                t.join()

        output = "".join(stdout_chunks).strip()
        error = "".join(stderr_chunks).strip()
        return proc.returncode, output, error

    def run(
        self,
        workdir: str | Path,
        prompt: str,
        timeout_sec: float | None = None,
        log_file: str | Path | None = None,
        **options,
    ) -> AgentResult:
        try:
            resolved_workdir = Path(workdir).expanduser().resolve(strict=True)
            if not resolved_workdir.is_dir():
                raise ValueError(f"workdir must be a directory: {resolved_workdir}")
        except (OSError, ValueError) as exc:
            return {"status": "failure", "message": str(exc)}

        cmd = self.build_command(resolved_workdir, prompt, **options)

        if log_file is not None:
            log_path = Path(log_file).expanduser()
            try:
                returncode, output, error = self._run_with_log(
                    cmd, resolved_workdir, log_path, timeout_sec
                )
            except OSError as exc:
                return {"status": "failure", "message": str(exc)}

            if returncode == -1:
                return {"status": "failure", "message": error}

            if returncode != 0:
                return {
                    "status": "failure",
                    "message": output
                    or error
                    or f"{self.agent_name} exited with status {returncode}",
                }
            return {"status": "success", "message": output}

        try:
            proc = subprocess.run(
                cmd,
                cwd=resolved_workdir,
                stdin=subprocess.DEVNULL,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "failure",
                "message": f"{self.agent_name} timed out after {timeout_sec} seconds",
            }

        output = proc.stdout.strip()
        error = proc.stderr.strip()

        if proc.returncode != 0:
            return {
                "status": "failure",
                "message": output
                or error
                or f"{self.agent_name} exited with status {proc.returncode}",
            }

        return {"status": "success", "message": output}


def ask_agent(
    workdir: str | Path,
    prompt: str,
    timeout_sec: float | None = None,
    log_file: str | Path | None = None,
    **options,
) -> AgentResult:
    from run_codex import CodexRunner

    return CodexRunner().run(
        workdir,
        prompt,
        timeout_sec=timeout_sec,
        log_file=log_file,
        **options,
    )
