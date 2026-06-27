Follow these rules strictly.

- Create or update **only** the editable files listed in the task prompt. Do not create, modify, or delete any other file in the workspace (including other tasks' deliverables). Reading other files for reference is allowed.
- Exception: when the task instruction explicitly requires stopping with `abort.txt`, you may create `abort.txt` in the workspace root (`./`).
- Write all deliverables in the same language as the task instruction.
- Always persist deliverables by creating or updating the specified files.
- Output printed to stdout is not treated as a deliverable.
- When JSON is required, printing to stdout is meaningless. Always save to the specified file.
- If you determine the task cannot be completed given the available information or input files, create `abort.txt` with the reason and stop.
  - Place `abort.txt` in the workspace root (`./`).
  - For **review tasks** (tasks that output `review.json`), do not create `abort.txt`. If undecidable, output `{"result":"NG","reason":"..."}` in `review.json` instead.
