# Docker Setup for OpenCode Challenge Orchestrator

This Docker setup is the recommended way to run the OpenCode Challenge Orchestrator on new machines. The image installs the full runtime during `docker compose build`, including Chromium for PDF generation.

## What the image includes

- OpenCode CLI.
- Node.js, npm and npx.
- Python 3.
- Python Playwright package.
- Node Playwright package.
- Playwright MCP package.
- Chromium browser runtime installed at build time.
- Git, curl, zip and unzip.

The `/setup_opencode_environment` command remains available, but inside Docker it should be treated as a verification command. The browser runtime is installed during image build, not during every review.

## Prerequisites

Install Docker Desktop or Docker Engine with Docker Compose support.

On Windows with Docker Desktop, create this host folder and make sure the drive is shared with Docker:

```text
C:/challenge
```

Put challenge ZIP files and challenge base PDFs in that folder. Inside the container the path is always:

```text
/challenge
```

## Volumes

The Docker Compose service uses these volumes:

```yaml
volumes:
  - .:/app
  - ./.opencode-state:/home/pwuser/.config/opencode
  - ./workspaces:/app/workspaces
  - ./review-sessions:/app/review-sessions
  - ./archived-review-sessions:/app/archived-review-sessions
  - "C:/challenge:/challenge"
```

| Host path | Container path | Purpose |
|---|---|---|
| `.` | `/app` | Project source and OpenCode configuration |
| `./.opencode-state` | `/home/pwuser/.config/opencode` | Persistent OpenCode state/auth/session config |
| `./workspaces` | `/app/workspaces` | Current submission intake and extracted files |
| `./review-sessions` | `/app/review-sessions` | Review outputs and reports |
| `./archived-review-sessions` | `/app/archived-review-sessions` | Archived review sessions |
| `C:/challenge` | `/challenge` | External challenge ZIP/PDF input folder |


## OpenCode Go model

The Docker image ships the runtime dependencies, but OpenCode Go access is still tied to your OpenCode account configuration. The project default model is:

```text
opencode/big-pickle
```

Run `opencode` inside the container and complete `/connect` or your normal OpenCode Go authentication flow if this is the first time using the mounted `.opencode-state` directory.

## Build the image on a new machine

From the project root:

```bash
docker compose build --no-cache
```

The build installs Chromium. No manual `npx playwright install chromium` step should be required.

## Open a shell inside the container

```bash
docker compose run --rm opencode-orchestrator bash
```

## Verify the runtime

Inside the container:

```bash
python3 scripts/validate_setup.py
python3 scripts/check_playwright_mcp.py --runtime
python3 scripts/setup_opencode_environment.py --offline
```

If a prerequisite is missing, the command exits non-zero and prints the exact problem in the console. Rebuild the image with `docker compose build --no-cache` if Chromium is missing.

## Run OpenCode from Docker

Inside the container shell:

```bash
opencode
```

Then run the global reviewer command using container paths:

```text
/challenge-reviewer-global "/challenge/software-engineering.zip" "/challenge/Software Engineering SW Challenge 1_ Spec-Driven Development Basics.pdf" 1 GBUSTOS4339640
```

You can also run non-interactively:

```bash
opencode run "/challenge-reviewer-global \"/challenge/software-engineering.zip\" \"/challenge/Software Engineering SW Challenge 1_ Spec-Driven Development Basics.pdf\" 1 GBUSTOS4339640"
```

## Expected outputs

Reports are written to:

```text
review-sessions/<session>/reports/
```

Expected report artifacts:

```text
final-evaluation.md
final-evaluation.json
final-evaluation.html
final-evaluation.pdf
```

The PDF is generated through Markdown to HTML to Chromium/Playwright PDF export. The Docker image includes Chromium at build time, so the workflow should not fall back to a plain-text PDF and should not require manual browser installation.

## GitHub clone workflow

When this project is cloned from GitHub on a new machine:

1. Clone the repository.
2. Create the host input folder, for example `C:/challenge` on Windows.
3. Place ZIP submissions and challenge PDFs in that folder.
4. Run `docker compose build --no-cache`.
5. Run `docker compose run --rm opencode-orchestrator bash`.
6. Inside the container, run `python3 scripts/validate_setup.py`.
7. Start OpenCode with `opencode` or use `opencode run`.

## Troubleshooting

### Docker cannot mount `C:/challenge`

Create the folder on the host and ensure Docker Desktop file sharing allows the drive.

### PDF generation fails with missing Chromium

Rebuild the image:

```bash
docker compose build --no-cache
```

Then verify:

```bash
docker compose run --rm opencode-orchestrator bash -lc "python3 scripts/check_playwright_mcp.py --runtime && python3 scripts/setup_opencode_environment.py --offline"
```

### OpenCode state is not preserved

The persistent state is mounted at:

```text
./.opencode-state:/home/pwuser/.config/opencode
```

Do not delete `.opencode-state` if you want to preserve OpenCode configuration between container runs.

## Google Sheets dependency note

Starting in v0.8.7, the Docker entrypoint installs project-level Node dependencies inside the mounted `/app` directory if `node_modules/` does not exist. This is required because the project is bind-mounted with `.:/app`, so dependencies created during image build would otherwise be hidden.

This first-run installation enables:

```bash
npm run add-google-spreadsheets -- EMP001 1 86
```

Google credentials are still local-only and must be mounted/provided under:

```text
config/google/sheets.config.json
config/google/service-account.json
```

These files are ignored by Git and Docker context ignore rules.


## Test Google Sheets from Docker

After mounting or copying real Google credentials into `config/google/`, verify access from inside the container:

```bash
npm run test-google-spreadsheets
```

Or run the OpenCode command:

```text
/test-google-spreadsheets
```

This validates authentication, spreadsheet access, target sheet existence, configured range readability, and record presence before the challenge reviewer tries to publish results.
