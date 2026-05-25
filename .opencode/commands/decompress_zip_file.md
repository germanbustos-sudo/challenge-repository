---
description: Decompress a local ZIP file into the managed workspaces folder
agent: challenge-orchestrator
model: opencode-go/deepseek-v4-flash
---

You are executing the `/decompress_zip_file` workflow.

ZIP file path: `$ARGUMENTS`

Purpose:
- Decompress exactly one local ZIP archive into the managed `workspaces/` folder.
- This workflow does not solve, review, or modify challenge deliverables.
- User input may provide only the ZIP file path. Never accept or infer a custom destination path.

Fail-fast requirements:
- If `$ARGUMENTS` is empty, print `ZIP file could not be decompressed. Missing ZIP file path.` and stop.
- If more than one ZIP file path is provided, print `ZIP file could not be decompressed. Only one ZIP file path argument is allowed.` and stop.
- Validate that the path exists, is readable, is a file, and is a valid `.zip` archive.
- Use only the fixed target directory: `workspaces/decompressed_zip`.
- Clean only `workspaces/decompressed_zip` before extracting. Never delete any other path.
- Extract the ZIP archive into `workspaces/decompressed_zip`.
- Prevent ZIP Slip/path traversal by rejecting entries that would extract outside `workspaces/decompressed_zip`.
- Verify success by checking that `workspaces/decompressed_zip` contains at least one file or folder.
- On success, show exactly: `ZIP file decompressed successfully.` and then print the target directory.
- On failure, show: `ZIP file could not be decompressed.` plus the reason.

Execution:
- Prefer `scripts/decompress_zip_file.py` as the deterministic local helper.
- On Windows, `scripts/decompress_zip_file.ps1` may be used.
- On Unix-like shells, `scripts/decompress_zip_file.sh` may be used.

Integration:
- This command is prepared as a reusable pre-step for external orchestrations that need local ZIP contents under `workspaces/`.
- Downstream review commands can evaluate the extracted files from `workspaces/decompressed_zip`.


Optional workspace cleanup:
- To avoid mixing submissions, the deterministic helper supports `--clean-workspaces` or environment variable `CLEAN_WORKSPACES_BEFORE_INTAKE=true`.
- Cleanup is optional and must be limited to the managed `workspaces/` folder.
