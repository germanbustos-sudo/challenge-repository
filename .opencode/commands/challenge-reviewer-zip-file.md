---
description: Decompress a local ZIP file into workspaces and review it against a base challenge file
agent: challenge-orchestrator
model: opencode/big-pickle
---

You are executing the `/challenge-reviewer-zip-file` composite workflow.

Arguments: `$ARGUMENTS`

Expected usage:

```text
/challenge-reviewer-zip-file ZIP_FILE_BASE FILE_BASE [ATTEMPT_NUMBER] [EMPLOYEE_ID]
```

Purpose:
- Compose `/decompress_zip_file` and `/challenge-reviewer` in a strict fail-fast sequence.
- First decompress the local ZIP archive into `workspaces/decompressed_zip`.
- Then review the extracted workspace content against the base challenge document.
- Do not solve, implement, or modify challenge deliverables.

Required parameters:
- `ZIP_FILE_BASE`: local ZIP archive path from the user's machine.
- `FILE_BASE`: local base challenge document path from the user's machine.

Fail-fast validation:
- If either parameter is missing, print `ERROR: Missing required parameters. Usage: /challenge-reviewer-zip-file ZIP_FILE_BASE FILE_BASE [ATTEMPT_NUMBER] [EMPLOYEE_ID]` and stop.
- If `ZIP_FILE_BASE` does not exist, cannot be read, or is not a `.zip` archive, print a console error and stop.
- If `FILE_BASE` does not exist or cannot be read, print `ERROR: Base challenge file does not exist or cannot be read: <path>` and stop.

Execution order:
1. Step One: run `/decompress_zip_file ZIP_FILE_BASE`.
2. Step Two: only if Step One completes successfully, run `/challenge-reviewer FILE_BASE`.

Workspace rules:
- The decompressed files must be placed under `workspaces/decompressed_zip`.
- The command must not accept or infer a custom extraction destination.
- If ZIP decompression fails, the review must not start.
- If `workspaces/` is empty after decompression, print `ERROR: Workspace files are required before starting the review process.` and stop without generating a report.

Review/report rules:
- Use the same review and report rules as `/challenge-reviewer`.
- Generate reports for complete acceptance, partial acceptance, and no acceptance when workspace content exists.
- Assign exactly one grade: `JUNIOR`, `INTERMEDIATE`, or `SENIOR`.

Recommended deterministic helper:
- Prefer `scripts/challenge_reviewer_zip_file.py` to validate parameters and execute the two local helper scripts in order.
- The helper internally invokes:
  - `scripts/decompress_zip_file.py ZIP_FILE_BASE`
  - `scripts/review_challenge.py FILE_BASE`

Integration notes:
- This command is intentionally composable and can be used as a prebuilt ZIP-review step in other orchestrations.
- Existing commands must remain available and operational: `/process_challenge`, `/review_challenge`, `/challenge-reviewer`, `/download_github`, `/challenge-reviewer-github`, and `/decompress_zip_file`.


Optional workspace cleanup:
- To avoid mixing submissions, the deterministic helper supports `--clean-workspaces` or environment variable `CLEAN_WORKSPACES_BEFORE_INTAKE=true`.
- Cleanup is optional and must be limited to the managed `workspaces/` folder.


Report metadata defaults:
- ATTEMPT_NUMBER defaults to `0` when omitted.
- EMPLOYEE_ID defaults to `ABC-123` when omitted.
- The initialized review session must include `final-evaluation.md`, `final-evaluation.json`, and `final-evaluation.pdf`.
