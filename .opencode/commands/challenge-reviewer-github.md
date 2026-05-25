---
description: Download a GitHub repository into workspaces and then review it against a base challenge file
agent: challenge-orchestrator
model: opencode/big-pickle
---

You are executing the `/challenge-reviewer-github` workflow.

Arguments: `$ARGUMENTS`

Expected usage:

```text
/challenge-reviewer-github GITHUB_URL FILE_BASE [ATTEMPT_NUMBER] [EMPLOYEE_ID]
```

Purpose:
- This workflow composes two existing orchestrations in strict order.
- Step One: execute `/download_github GITHUB_URL` to download the repository into `workspaces/github_repository`.
- Step Two: only if Step One completes successfully, execute `/challenge-reviewer FILE_BASE` to review the downloaded workspace against the base challenge file.
- This workflow must not solve, fix, rewrite, or modify the challenge implementation after the repository is downloaded.

Parameter validation:
- If `$ARGUMENTS` is empty, print `ERROR: Missing required parameters. Usage: /challenge-reviewer-github GITHUB_URL FILE_BASE [ATTEMPT_NUMBER] [EMPLOYEE_ID]` and stop.
- Parse the first whitespace-delimited value as `GITHUB_URL`.
- Parse the remaining argument text as `FILE_BASE`, preserving spaces when the base file path contains them.
- If `GITHUB_URL` is missing, print `ERROR: Missing GitHub repository URL.` and stop.
- If `FILE_BASE` is missing, print `ERROR: Missing base challenge file path.` and stop.
- Validate that `GITHUB_URL` is an HTTPS GitHub repository URL in one of these formats:
  - `https://github.com/<owner>/<repo>`
  - `https://github.com/<owner>/<repo>.git`
- If URL validation fails, print `ERROR: Invalid GitHub repository URL.` and stop.
- If `FILE_BASE` cannot be read or does not exist, print `ERROR: Base challenge file does not exist or cannot be read: <path>` and stop.

Execution order:
1. Run the same behavior as `/download_github GITHUB_URL`.
2. Confirm that `workspaces/github_repository/.git` exists after download.
3. If the download fails or verification fails, print `ERROR: GitHub repository download failed. Review was not started.` and stop.
4. Run the same behavior as `/challenge-reviewer FILE_BASE`.
5. Confirm that the review generated a Markdown report for complete acceptance, partial acceptance, or no acceptance.
6. Print the download target directory, review session path, acceptance status, grade, and final report path.

Required behavior:
- Downloaded repository content must always be placed under `workspaces/github_repository`.
- The review must evaluate the content under `workspaces/` against the acceptance criteria in `FILE_BASE`.
- Reports must be generated when `workspaces/` contains downloaded files, including:
  - complete acceptance,
  - partial acceptance with failure details,
  - no acceptance with all missing items.
- If `workspaces/` is empty after download, print `ERROR: Workspace files are required before starting the review process.` and stop without generating a report.

Recommended deterministic helper:
- Prefer `scripts/challenge_reviewer_github.py` to validate parameters and execute the two local helper scripts in order.
- The helper internally invokes:
  - `scripts/download_github.py GITHUB_URL`
  - `scripts/review_challenge.py FILE_BASE`

Integration notes:
- This command is intentionally composable and can be used as a prebuilt repository-review step in other orchestrations.
- The existing `/process_challenge`, `/challenge-reviewer`, `/review_challenge`, and `/download_github` commands must remain available and operational.


Optional workspace cleanup:
- To avoid mixing submissions, the deterministic helper supports `--clean-workspaces` or environment variable `CLEAN_WORKSPACES_BEFORE_INTAKE=true`.
- Cleanup is optional and must be limited to the managed `workspaces/` folder.


Report metadata defaults:
- ATTEMPT_NUMBER defaults to `0` when omitted.
- EMPLOYEE_ID defaults to `ABC-123` when omitted.
- The initialized review session must include `final-evaluation.md`, `final-evaluation.json`, and `final-evaluation.pdf`.
