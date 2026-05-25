---
description: Download a public GitHub repository into the managed workspaces folder
agent: github-downloader
model: opencode-go/deepseek-v4-flash
---

You are executing the `/download_github` workflow.

Repository URL: `$ARGUMENTS`

Purpose:
- Download exactly one public GitHub repository into the managed `workspaces/` folder.
- This workflow does not solve, review, or modify challenge deliverables.
- User input may provide only the repository URL. Never accept or infer a custom destination path.

Fail-fast requirements:
- If `$ARGUMENTS` is empty, print `GitHub repository could not be downloaded. Missing repository URL.` and stop.
- Validate that the URL is an HTTPS GitHub repository URL in one of these formats:
  - `https://github.com/<owner>/<repo>`
  - `https://github.com/<owner>/<repo>.git`
- If validation fails, print `GitHub repository could not be downloaded. Invalid GitHub repository URL.` and stop.
- Use only the fixed target directory: `workspaces/github_repository`.
- Clean only `workspaces/github_repository` before downloading. Never delete any other path.
- Clone the repository into `workspaces/github_repository`.
- Verify success by checking that `workspaces/github_repository/.git` exists.
- On success, show exactly: `GitHub repository downloaded successfully.` and then print the target directory.
- On failure, show: `GitHub repository could not be downloaded.` plus the reason.

Execution:
- Prefer the `github-download-orchestration` skill when available.
- Prefer `scripts/download_github.py` as the deterministic local helper.
- On Windows, `scripts/download_github.ps1` may be used.
- On Unix-like shells, `scripts/download_github.sh` may be used.


Optional workspace cleanup:
- To avoid mixing submissions, the deterministic helper supports `--clean-workspaces` or environment variable `CLEAN_WORKSPACES_BEFORE_INTAKE=true`.
- Cleanup is optional and must be limited to the managed `workspaces/` folder.
