---
description: Alias for review_challenge. Review an existing workspace implementation against a base challenge file and generate Markdown reports only
agent: challenge-orchestrator
model: opencode/big-pickle
---

You are executing the `/challenge-reviewer` workflow.

Input base challenge file path: `$ARGUMENTS`

This command is a stable alias for `/review_challenge`.

Use the same rules as `/review_challenge`:
- If `$ARGUMENTS` is empty, print `ERROR: Missing base challenge file path.` and stop.
- If `workspaces/` does not exist or contains no files/folders to evaluate, print `ERROR: Workspace files are required before starting the review process.` and stop without generating any report.
- If the base challenge file cannot be read or does not exist, print `ERROR: Base challenge file does not exist or cannot be read: <path>` and stop.
- Classify the base challenge file as `software_engineering`, `qa_engineering`, or `data_engineering`.
- Invoke `@challenge-reviewer` to review existing workspace content without modifying it.
- Invoke `@challenge-reporter` to generate a Markdown report for `complete_acceptance`, `partial_acceptance`, or `no_acceptance`.
- Assign exactly one grade: `JUNIOR`, `INTERMEDIATE`, or `SENIOR`.

Recommended deterministic helper:
- Run `scripts/review_challenge.py FILE_BASE` for local validation and review session initialization.


Additional v0.6.0 robust review contract:
- Follow three phases: intake, review, report.
- Use `config/review-policy.yaml`.
- Use `MANIFEST.lock.json` and `logs/execution.log` for traceability.
- Generate and complete the acceptance matrix with criterion, evidence, status, severity, and comment.
- Do not mark any criterion as passed without concrete evidence.
- Include numeric score 0-100 plus grade `JUNIOR`, `INTERMEDIATE`, or `SENIOR`.
- With `strict_review: true`, missing README or missing tests/validation evidence prevents `SENIOR`.


Report PDF formatting contract:
- Generate `final-evaluation.md` first.
- Validate Markdown with `scripts/validate_markdown_report.py` before PDF export.
- Convert the validated Markdown to `final-evaluation.pdf` with `scripts/generate_final_pdf.py`.
- PDF output must support rendered tables, clean page breaks, UTF-8/Unicode, professional headings, formatted code blocks, and print-safe margins.


Dynamic FILE_BASE criteria:
- The base challenge document is the source of truth for acceptance criteria.
- During intake, `scripts/review_challenge.py` extracts deliverables, functional acceptance criteria, and technical acceptance criteria from FILE_BASE.
- The generated session criteria are stored in `intake/file-base-extracted-criteria.json` and `review/acceptance-matrix.json`.
- `config/review-policy.yaml` is used as fallback/guardrails only, not as a hardcoded challenge catalog.
- New challenges can be supported without Python changes when FILE_BASE contains clear criteria or deliverables.


Two-dimensional review requirements:
- The review must evaluate both Functional acceptance criteria and Technical acceptance criteria.
- The acceptance matrix must preserve `dimension`, `dimension_label`, and criterion-level evidence for each criterion.
- The final reports must include functional score, technical score, final numeric score, functional grade, technical grade, and final grade.
- The final grade must be based on both dimensions and strict review constraints.
