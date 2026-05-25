# OpenCode Challenge Orchestrator

Version: `0.8.7`

OpenCode Challenge Orchestrator is a portable OpenCode setup for processing, downloading, extracting, reviewing, grading, and reporting Talent Bench-style challenge submissions. It supports ZIP files and GitHub repositories, extracts acceptance criteria from the base challenge document, evaluates functional and technical dimensions independently, applies prompt-injection safeguards, and generates unified Markdown, JSON, HTML, and PDF reports.

## Current architecture

```text
/challenge-reviewer-global
  ├── context boundary guidance (/new)
  ├── clean managed workspace
  ├── intake and parameter validation
  ├── source classification: ZIP FILE or GITHUB URL
  ├── source ingestion: decompress or download
  ├── untrusted-content validation
  ├── prompt-injection scan
  ├── sanitization summary
  ├── security review and decision
  ├── FILE_BASE criteria extraction
  ├── Skills Required extraction
  ├── universal-specialist review
  ├── unified final report rendering
  └── review-session archive
```

The source intake changes by source type, but the review model and final report template are unified for ZIP and GitHub submissions.


## Model configuration

This version keeps the current single-model architecture and migrates the default model from `opencode/big-pickle` to OpenCode Go:

```text
model: opencode-go/deepseek-v4-flash
small_model: opencode-go/deepseek-v4-flash
```

The same model is configured in `opencode.json`, command frontmatter, agent frontmatter, and `config/orchestration.yaml`. Future versions can introduce multi-model routing, but v0.8.7 intentionally keeps the runtime topology unchanged.

Before running reviews, make sure the OpenCode environment is connected to OpenCode Go according to your OpenCode account setup.

## Main capabilities

- Review local ZIP submissions and public GitHub repositories.
- Extract `Functional acceptance criteria` and `Technical acceptance criteria` from `FILE_BASE`.
- Extract agent skills only from the `Skills Required` column, with the role inserted as the first skill.
- Use `universal-specialist` as the primary dynamic reviewer.
- Evaluate two independent dimensions: functional and technical.
- Generate score and grade per dimension, plus final weighted score and grade.
- Apply strict review rules for `SENIOR` eligibility.
- Require concrete evidence for every passed criterion.
- Run prompt-injection and untrusted-content checks before review.
- Generate unified `final-evaluation.md`, `final-evaluation.json`, `final-evaluation.html`, and `final-evaluation.pdf`.
- Publish `employee_id`, `attempt_number`, and `numeric_score` to Google Sheets after final report generation when configured.
- Generate skill extraction reports in Markdown, HTML, and PDF.
- Support Docker execution for consistent OpenCode, Node.js, Python, Playwright, and Chromium runtime behavior.

## Commands

| Command | Purpose |
|---|---|
| `/setup_opencode_environment` | Installs/verifies local dependencies, Playwright MCP, Chromium, and PDF runtime. |
| `/add-google-spreadsheets EMPLOYEE_ID ATTEMPT SCORE` | Appends final review results to Google Sheets columns Employee ID, Attempt, and Score. |
| `/test-google-spreadsheets` | Tests Google Sheets authentication, spreadsheet access, target sheet/range readability, and whether records exist. |
| `/challenge-reviewer-global SOURCE_DATA_REVIEW FILE_BASE [ATTEMPT_NUMBER] [EMPLOYEE_ID]` | Main stateless review workflow. Routes ZIP or GitHub sources to the unified review pipeline. |
| `/challenge-reviewer-zip-file ZIP_FILE_BASE FILE_BASE [ATTEMPT_NUMBER] [EMPLOYEE_ID]` | Decompresses a ZIP into `workspaces/decompressed_zip` and reviews it. |
| `/challenge-reviewer-github GITHUB_URL FILE_BASE [ATTEMPT_NUMBER] [EMPLOYEE_ID]` | Downloads a GitHub repository into `workspaces/github_repository` and reviews it. |
| `/decompress_zip_file ZIP_FILE_BASE` | Decompresses a local ZIP safely into `workspaces/decompressed_zip`. |
| `/download_github GITHUB_URL` | Clones a GitHub repository into `workspaces/github_repository`. |
| `/challenge-reviewer FILE_BASE` | Reviews current `workspaces/` content against `FILE_BASE`; alias-compatible command. |
| `/review_challenge FILE_BASE` | Reviews current `workspaces/` content against `FILE_BASE`. |
| `/process_challenge FILE` | Legacy implementation workflow that solves, tests, supervises, and reports a challenge. |

## Primary command examples

Docker path example:

```text
/challenge-reviewer-global "/challenge/software-engineering.zip" "/challenge/Software Engineering SW Challenge 1_ Spec-Driven Development Basics.pdf" 1 GBUSTOS4339640
```

GitHub example:

```text
/challenge-reviewer-global "https://github.com/example-org/example-repo" "/challenge/Software Engineering SW Challenge 1_ Spec-Driven Development Basics.pdf" 1 ABC123
```

Direct helper example:

```bash
python scripts/challenge_reviewer_global.py "/challenge/software-engineering.zip" "/challenge/Software Engineering SW Challenge 1_ Spec-Driven Development Basics.pdf" 1 GBUSTOS4339640
```

## Agents

| Agent | Role |
|---|---|
| `challenge-orchestrator` | Main command router and workflow coordinator. |
| `universal-specialist` | Primary dynamic reviewer driven by `FILE_BASE`, criteria, and `agent-skill-profile.json`. |
| `challenge-reviewer` | Review support agent for existing workspaces and compatibility flows. |
| `challenge-reporter` | Report generator contract for unified final-evaluation outputs. |
| `challenge-security-reviewer` | Validates security scan findings and controls quarantine decisions. |
| `challenge-supervisor` | Legacy supervisor for `/process_challenge` rejection loops. |
| `github-downloader` | GitHub intake/download support agent. |
| `software-specialist` | Legacy implementation specialist for software challenge solving. |
| `qa-specialist` | Legacy implementation specialist for QA challenge solving. |
| `data-engineering-specialist` | Legacy implementation specialist for data engineering challenge solving. |

## Skills model

The current review flow uses dynamic skills rather than challenge-specific reviewer agents.

The skill extraction rules are:

1. Extract skills only from the `Skills Required` column in `FILE_BASE`.
2. Add the classified role as the first skill, for example `Role: Software Engineering`.
3. Do not treat challenge descriptions, deliverables, resources, time, functional criteria, or technical criteria as skills.
4. Store the result in `review-sessions/<session>/intake/agent-skill-profile.json`.
5. Generate skill reports under `review-sessions/<session>/skills/`.

Generated skill artifacts:

```text
skills/skill-extraction.md
skills/skill-extraction.html
skills/skill-extraction.pdf
review/skill-assessment.md
review/skill-assessment.json
```

## Review dimensions and grading

Every review uses two dimensions:

| Dimension | Meaning |
|---|---|
| Functional acceptance criteria | Business-facing deliverables, features, flows, visible behavior, and required outputs from `FILE_BASE`. |
| Technical acceptance criteria | Architecture, tests, validation, traceability, maintainability, reproducibility, security, and process constraints from `FILE_BASE`. |

Final score is calculated from dimension scores using the configured weighting in `config/review-policy.yaml`.

`SENIOR` requires:

- final numeric score in the senior range,
- functional score above the configured senior threshold,
- technical score above the configured senior threshold,
- complete acceptance,
- strict review pass.

## Unified final report

ZIP and GitHub workflows now use the same report contract:

```text
review-sessions/<session>/reports/
├── final-evaluation.md
├── final-evaluation.json
├── final-evaluation.html
└── final-evaluation.pdf
```

The unified report is generated from:

```text
templates/final-evaluation-unified-template.md
schemas/final-evaluation-unified.schema.json
scripts/render_unified_final_report.py
scripts/generate_final_pdf.py
```

The report includes:

- session metadata,
- source metadata,
- skill extraction summary,
- security assessment,
- dimension summary,
- functional criteria table,
- technical criteria table,
- detailed criteria assessment,
- evidence log,
- skill assessment,
- failed/partial details,
- risks and assumptions,
- final recommendation,
- reference files.

## Google Sheets result publishing

The orchestrator imports `/add-google-spreadsheets` from the Google Sheets logger integration. After `final-evaluation.json` is generated by the unified renderer, the workflow can publish:

| Report field | Command argument | Spreadsheet column |
|---|---|---|
| `employee_id` | `EMPLOYEE_ID` | Column 1: Employee ID |
| `attempt_number` | `ATTEMPT` | Column 4: Attempt |
| `numeric_score` | `SCORE` | Column 7: Score |

Configuration files live under `config/google/`. Copy `sheets.config.example.json` to `sheets.config.json`, add `service-account.json`, and share the target spreadsheet with the service account email. Local secrets are excluded from Git.

See `docs/GOOGLE_SHEETS_INTEGRATION.md`.

## Security architecture

Workspace files are always treated as untrusted data, never instructions.

Security components:

```text
config/security-policy.yaml
scripts/validate_untrusted_content.py
scripts/scan_prompt_injection.py
scripts/sanitize_workspace_content.py
.opencode/agents/challenge-security-reviewer.md
```

Security behavior:

- Detects prompt injection and context poisoning patterns.
- Distinguishes literal and regex security patterns.
- Delays quarantine until after security-reviewer validation.
- Allows false-positive findings to be marked as non-blocking when validated.
- Generates security artifacts under `review-sessions/<session>/security/`.

## Docker setup

Build the container:

```bash
docker compose build
```

Open a shell with the project mounted:

```bash
docker compose run --rm opencode-orchestrator bash
```

Inside the container, validate the setup:

```bash
python3 scripts/validate_setup.py
python3 scripts/check_playwright_mcp.py --runtime
python3 scripts/setup_opencode_environment.py --verify-only
```

Start OpenCode:

```bash
opencode
```

The compose service mounts:

```yaml
volumes:
  - .:/app
  - ./.opencode-state:/home/pwuser/.config/opencode
  - ./workspaces:/app/workspaces
  - ./review-sessions:/app/review-sessions
  - ./archived-review-sessions:/app/archived-review-sessions
  - "C:/challenge:/challenge"
```

More details are in `docs/DOCKER_SETUP.md`.

## Repository structure

```text
.opencode/
  agents/
  commands/
  plugins/
  skills/
config/
  orchestration.yaml
  review-policy.yaml
  security-policy.yaml
  session-policy.yaml
  skill-extraction-policy.yaml
docs/
  DOCKER_SETUP.md
  UNIFIED_REPORTING.md
examples/
schemas/
  final-evaluation-unified.schema.json
scripts/
templates/
  final-evaluation-unified-template.md
Dockerfile
docker-compose.yml
opencode.json
package.json
README.md
```

## Hooks

No OpenCode hooks are required in the current architecture. Lifecycle behavior is implemented through commands, deterministic helper scripts, agents, and policy files. This keeps the setup portable for local, Docker, and GitHub-cloned executions.

## Runtime directories

The tool creates the following local runtime directories. They are intentionally ignored by Git:

```text
.opencode-state/
workspaces/
review-sessions/
archived-review-sessions/
setup-logs/
```

## GitHub readiness

This repository is prepared to be committed without runtime artifacts. The `.gitignore` excludes generated workspaces, review sessions, archives, state, logs, credentials, temporary files, Python caches, Node dependencies, and local challenge archives.

Before pushing:

```bash
python scripts/validate_setup.py
git status --ignored
```

Do not commit candidate submissions, generated reports, OpenCode local state, secrets, service-account JSON files, or local `.env` files.


## Google Sheets connectivity test

Before enabling automatic publishing in a new environment, run:

```bash
npm run test-google-spreadsheets
```

or from OpenCode:

```text
/test-google-spreadsheets
```

The command validates `config/google/sheets.config.json`, resolves `credentialsFile`, authenticates with Google Sheets, verifies the spreadsheet ID and sheet name, reads the configured range, checks whether rows exist, and reports header compatibility without printing private keys.
