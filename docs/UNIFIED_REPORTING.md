# Unified Final Evaluation Reporting

Starting in v0.8.7, `final-evaluation` reporting is source-independent.
ZIP, GitHub, and future intake sources must all render through the same
pipeline:

```text
source intake
  -> normalized review session
  -> reports/final-evaluation.unified.json
  -> templates/final-evaluation-unified-template.md
  -> reports/final-evaluation.md
  -> reports/final-evaluation.json
  -> reports/final-evaluation.html
  -> reports/final-evaluation.pdf
```

## Source-independent contract

Only intake is source-specific. Report rendering is not.

Supported sources use the same report renderer:

- `/challenge-reviewer-zip-file`
- `/challenge-reviewer-github`
- `/challenge-reviewer-global`

## Renderer

```bash
python scripts/render_unified_final_report.py "review-sessions/<session>" --strict
```

If Chromium/Playwright is not available while troubleshooting locally:

```bash
python scripts/render_unified_final_report.py "review-sessions/<session>" --skip-pdf
```

This still uses the same template and schema. It only skips PDF export.

## Template and schema

- Template: `templates/final-evaluation-unified-template.md`
- Schema: `schemas/final-evaluation-unified.schema.json`
- Normalized context: `reports/final-evaluation.unified.json`

## Mandatory section order

1. Executive Summary
2. Intake Summary
3. Security Summary
4. Skill Extraction Summary
5. Dimension Score Summary
6. Functional Acceptance Criteria
7. Technical Acceptance Criteria
8. Detailed Criteria Assessment
9. Evidence Log
10. Anti-False-Positive Validation
11. Failed and Partial Criteria Details
12. Skill Assessment
13. Risks and Assumptions
14. Final Recommendation
15. Reference Files

## Rationale

Before v0.8.7, ZIP and GitHub flows could produce different final report
layouts because agents generated source-specific Markdown. v0.8.7 removes
that divergence by making `scripts/render_unified_final_report.py` the single
source of truth for final report rendering.
