---
description: Install and verify OpenCode environment dependencies, including Playwright MCP and Chromium PDF runtime
agent: challenge-orchestrator
model: opencode/big-pickle
---

You are executing `/setup_opencode_environment`.

Purpose:
- Prepare a freshly downloaded or GitHub-cloned OpenCode challenge orchestrator project.
- Install and verify dependencies required for professional PDF report generation.
- Ensure the configured Playwright MCP server and local Chromium runtime can generate `final-evaluation.pdf` from `final-evaluation.html`.

Arguments: `$ARGUMENTS`

Supported optional flags:
- `--offline`: do not install dependencies; only verify the local environment.
- `--skip-install`: alias for `--offline`.

Execution contract:
1. Validate that Node.js, npm, npx, Python, and project files are available.
2. Ensure a project-level `package.json` exists for reproducible setup after GitHub clone or ZIP extraction.
3. Install npm dependencies when not running in offline mode.
4. Install Playwright Chromium runtime when not running in offline mode.
5. Validate `opencode.json` Playwright MCP configuration.
6. Validate MCP runtime availability.
7. Run a Chromium PDF smoke test that renders an HTML page with UTF-8 text and a table into PDF.
8. Write setup logs to `setup-logs/setup-opencode-environment.log`.
9. If any prerequisite cannot be installed or verified, stop and print a clear console error.

Required command:

```bash
python scripts/setup_opencode_environment.py $ARGUMENTS
```

Windows alternative:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_opencode_environment.ps1
```

Linux/macOS alternative:

```bash
bash scripts/setup_opencode_environment.sh
```

Fail-fast rules:
- If Node.js/npm/npx is missing, stop and print the installation requirement.
- If npm cannot download dependencies, stop and print the npm failure.
- If Chromium cannot be installed, stop and print the Playwright failure.
- If the PDF smoke test fails, stop and print the failure.
- Never mark the setup as ready unless Chromium PDF export succeeds.

Success condition:
- Console output must include `SETUP COMPLETED: OpenCode environment is ready.`
- The JSON result must have `status: ready`.

Operational note:
- Run this command once after downloading or cloning the project, before `/challenge-reviewer-global`, when PDF output is required.
