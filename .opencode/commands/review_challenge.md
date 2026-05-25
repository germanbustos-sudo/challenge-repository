---
description: Review an existing workspace implementation against a base challenge file and generate Markdown reports only
agent: challenge-orchestrator
model: opencode-go/deepseek-v4-flash
---

You are executing the `/review_challenge` workflow.

Input base challenge file path: `$ARGUMENTS`

Purpose:
- This workflow does not solve or modify the challenge implementation.
- It only reviews existing data under `workspaces/`, evaluates compliance against the base challenge document, assigns a level, and generates Markdown reports.

Fail-fast requirements:
- If `$ARGUMENTS` is empty, print `ERROR: Missing base challenge file path.` and stop.
- If `workspaces/` does not exist or contains no files/folders to evaluate, print `ERROR: Workspace files are required before starting the review process.` and stop without generating any report.
- If the base challenge file cannot be read or does not exist, print `ERROR: Base challenge file does not exist or cannot be read: <path>` and stop.
- Read the base challenge file and classify the supervision/review type as one of: `software_engineering`, `qa_engineering`, `data_engineering`.
- If classification confidence is low or unsupported, print `ERROR: Base challenge document could not be classified.` and stop.
- Create a review session folder under `review-sessions/<challenge-slug>-<timestamp>/`.
- Copy the base challenge file into `input/` and write `review-manifest.json`.
- Invoke `@challenge-reviewer` for independent review of the existing `workspaces/` content.
- The reviewer must verify the implementation against the base challenge acceptance criteria and required deliverables.
- The reviewer must assign exactly one acceptance status: `complete_acceptance`, `partial_acceptance`, or `no_acceptance`.
- The reviewer must generate `review/reviewer-assessment.md` for all non-empty workspace outcomes:
  - complete acceptance of acceptance criteria,
  - partial acceptance of acceptance criteria, including failure details,
  - no acceptance of acceptance criteria, including all missing items.
- The reviewer must assign exactly one grade: `JUNIOR`, `INTERMEDIATE`, or `SENIOR`.
- The reviewer must not implement, fix, rewrite, or create missing deliverables for the challenge.
- If reviewer execution fails unexpectedly, print `ERROR: Challenge review could not be completed.` and stop.
- Invoke `@challenge-reporter` to create `reports/final-evaluation.md` inside the review session using the reviewer output.
- The reporter must generate the Markdown report for complete acceptance, partial acceptance, and no acceptance.
- If report generation fails, print `ERROR: Markdown report could not be generated.` and stop.
- End by printing the review session path, classified type, acceptance status, grade, and report path.


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
