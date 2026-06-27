#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Literal

from run_agent import AgentRunner

SandboxMode = Literal["workspace-write", "read-only"]


class CodexRunner(AgentRunner):
    def __init__(self, sandbox_mode: SandboxMode = "workspace-write"):
        super().__init__("codex")
        self.sandbox_mode = sandbox_mode

    def build_command(self, workdir: Path, prompt: str, **options) -> list[str]:
        sandbox_mode = options.get("sandbox_mode", self.sandbox_mode)
        return [
            "codex",
            "exec",
            # Do not load $CODEX_HOME/config.toml so runs are reproducible across machines.
            "--ignore-user-config",
            # Do not load user/project execpolicy .rules files.
            "--ignore-rules",
            # Do not persist session rollout files to disk.
            "--ephemeral",
            # Allow running outside a git repository (agent_flow is not always a git worktree).
            "--skip-git-repo-check",
            # Restrict writes to the workspace passed via -C (see Agent approvals & security docs).
            "--sandbox",
            sandbox_mode,
            "-C",
            str(workdir),
            prompt,
        ]
