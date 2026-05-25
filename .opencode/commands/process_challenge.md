---
description: Process a challenge file through role classification, implementation, rejection-aware review, grading and Markdown reporting
agent: challenge-orchestrator
model: opencode-go/deepseek-v4-flash
---

You are executing the `/process_challenge` workflow.

Input file path: `$ARGUMENTS`

Fail-fast requirements:
- If `$ARGUMENTS` is empty, print `ERROR: Missing challenge file path.` and stop.
- At the beginning of every execution, clean all working folders under `workspaces/`. If cleanup fails, print `ERROR: Workspace cleanup could not be completed.` and stop.
- If the file cannot be read or does not exist, print `ERROR: Challenge file does not exist or cannot be read: <path>` and stop.
- Read the file and classify it as one of: `software_engineering`, `qa_engineering`, `data_engineering`.
- If classification confidence is low or unsupported, print `ERROR: Challenge document could not be classified.` and stop.
- Create an isolated workspace under `workspaces/<challenge-slug>-<timestamp>/`.
- Copy the input into `input/` and write `run-manifest.json`.
- Route to the matching specialist agent:
  - `software_engineering` -> `@software-specialist`
  - `qa_engineering` -> `@qa-specialist`
  - `data_engineering` -> `@data-engineering-specialist`
- The specialist must implement/develop/test inside the workspace only.
- If implementation fails, print `ERROR: Implementation could not be completed.` and stop.
- Invoke `@challenge-supervisor` for independent review.
- The supervisor must enforce `MAX_REJECTED`, default `3`, and may reject the implementation back to the responsible specialist with observations.
- If the supervisor returns `rejected`, route the work back to the same specialist agent with `review/rework-request.md`, then run the supervisor again.
- Repeat specialist rework and supervisor review until the supervisor returns `accepted` or the rejection count exceeds `MAX_REJECTED`.
- If the rejection count exceeds `MAX_REJECTED`, set status to `cancelled`, print `ERROR: Maximum rejection attempts exceeded. Process cancelled.`, invoke `@challenge-reporter`, and stop after report generation.
- If review fails unexpectedly, print `ERROR: Supervisor review could not be completed.` and stop.
- On accepted review, the supervisor must assign exactly one grade: `JUNIOR`, `INTERMEDIATE`, or `SENIOR`.
- Invoke `@challenge-reporter` to create `reports/final-evaluation.md`, including status, rejection count, grade, observations, and evidence.
- If report generation fails, print `ERROR: Markdown report could not be generated.` and stop.
- End by printing the workspace path, review status, grade, and report path.
