# Changelog

## v0.8.7

- Migrated the default OpenCode model from `opencode/big-pickle` to `opencode-go/deepseek-v4-flash`.
- Updated `opencode.json`, all command frontmatter, all agent frontmatter, and `config/orchestration.yaml` to use OpenCode Go.
- Kept the existing single-model architecture unchanged for a low-risk migration.
- Updated README and Docker documentation with OpenCode Go model guidance.

## v0.8.4

- Fixed Docker runtime for new machines by installing Python Playwright, Node Playwright, Playwright MCP, and Chromium during `docker compose build`.
- Added a Chromium executable check in the Docker entrypoint.
- Updated Docker documentation so `/setup_opencode_environment` is used as verification inside Docker, not as the primary installer.

## v0.8.3

- Prepared the project structure for GitHub publication.
- Added repository-safe `.gitignore` coverage for OpenCode state, workspaces, review sessions, archives, setup logs, generated reports, Node/Python caches, local archives, and secrets.
- Rewrote `README.md` to describe only the current architecture, commands, agents, dynamic skills, security model, unified reporting, Docker usage, and GitHub readiness.


## v0.8.5

- Migrated the  OpenCode model from `opencode-go/deepseek-v4-flash` to `opencode/big-pickle` .