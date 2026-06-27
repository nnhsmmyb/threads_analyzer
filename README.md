**Languages:** [English](README.md) | [日本語](README.ja.md)

# agent_flow

An **experimental sample** for designing workflows upfront and running them reproducibly.

When AI owns both design and execution, each run drifts. **Design** with agent orchestration — explore interactively, then fix task order, review gates, and file constraints in `main.py` and `instructions/`. **Execute** with agent_flow — mechanical checks at each stage, the same path every time.

The example agent runner uses [codex exec](https://developers.openai.com/codex/noninteractive) ([Codex](https://github.com/openai/codex) non-interactive mode; `run_codex.py` launches it). Swap in another agent via `run_agent.ask_agent()`.

## vs orchestration frameworks

Agent orchestration centers on always-on assistants, channel integrations, skills/tools, and multi-agent coordination — spawning sub-agents and coordinating dynamically at runtime.

agent_flow is the opposite — an execution engine for pre-designed flows. No coordination layer or tool stack. Exploration belongs to orchestration; repeatable pipelines belong to agent_flow.

## Run

```bash
python main.py
```

- Output: `agent_out/` (created automatically). On success: `incident_context.md`, `timeline.md`, `hypothesis.md` (and `action_plan.md` when `action_required`)
- Logs: `logs/agent_stdout.log` (reset on start, appended between tasks; `logs/` is also created automatically)
- Requirements: Python 3.10+, `codex exec` available (`codex` on PATH)

## Sample workflow (incident response)

Place input files in `input/inbox/`. Any format works. The repo includes sample files (`incident-memo.md`, etc.) so you can run as-is. For your own reports, drop files in the same directory. If the inbox is empty, nothing runs.

```
inbox present → T001_ingest → T002_timeline → T003_hypothesis
                → T004_action_plan if action_required / skip if monitor_only
```

Each task follows: work → review (`*R.md`) → redo on NG. Unauthorized file changes are restored from a snapshot.

## What to edit

When building your own workflow (task order, branching, instructions, input handling) on top of the framework, edit only the left column. The right column is generic orchestration — leave it alone.


| Edit | Do not edit (framework) |
| ---- | ----------------------- |
| `main.py` — pipeline and parameters | `agent_task.py`, `run_agent.py`, `path_validators.py`, `app_config.py` |
| `instructions/` — `T00x.md` (work) and `T00xR.md` (review) | `fixed_instructions/` |
| `system_task.py` — input checks, etc. | `run_codex.py` (launches `codex exec`; see in-file comments for flags) |


Parameters are constants at the top of `main.py` (`WORK_DIR`, `AGENT_TIMEOUT_SEC`, etc.).

## Framework essentials

- **editable_files**: per task, list files the agent may change under `work_dir`. Other changes are rolled back
  - **editable_files=None**: skip review when there is no deliverable to validate
- **return_status**: read a status value in `main.py` to branch subsequent tasks
- **abort.txt**: agent creates this to abort when the task cannot proceed
- **Write boundary**: writes outside `work_dir` (e.g. inbox) are blocked by the agent sandbox (`codex exec --sandbox workspace-write -C work_dir`). Framework diff validation covers `work_dir` only
  - **Excluded from validation**: dotfiles (e.g. `.hidden`), paths outside `work_dir`
- **Single process**: do not run two flows on the same `work_dir` concurrently (snapshot conflicts)

## Swapping the agent

Implement `AgentRunner` and change the delegate in `run_agent.ask_agent()`. Keep `main.py` and `instructions/` as they are.

```python
def ask_agent(...) -> AgentResult:
    from run_claude import ClaudeRunner
    return ClaudeRunner().run(...)
```

Include settings that restrict writes outside the working directory.
