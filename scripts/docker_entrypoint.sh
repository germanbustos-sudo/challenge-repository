#!/usr/bin/env bash
set -euo pipefail

mkdir -p \
  /home/pwuser/.config/opencode \
  /app/workspaces \
  /app/review-sessions \
  /app/archived-review-sessions

if ! command -v opencode >/dev/null 2>&1; then
  echo "ERROR: opencode CLI is not installed in the Docker image." >&2
  exit 20
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1 || ! command -v npx >/dev/null 2>&1; then
  echo "ERROR: Node.js/npm/npx are required inside the Docker image." >&2
  exit 21
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: Python 3 is required inside the Docker image." >&2
  exit 22
fi


# The project directory is bind-mounted at /app, so node_modules created during
# image build would be hidden. Install project-level Node dependencies on first
# container start so Google Sheets and PDF helper scripts can resolve packages.
if [ -f /app/package.json ] && [ ! -d /app/node_modules ]; then
  echo "Installing project Node dependencies inside the mounted workspace..."
  npm install --no-audit --no-fund
fi

if [ ! -d /ms-playwright ]; then
  echo "ERROR: Playwright browser runtime directory /ms-playwright was not found." >&2
  echo "Rebuild the image with: docker compose build --no-cache" >&2
  exit 23
fi

if ! command -v chromium >/dev/null 2>&1; then
  echo "ERROR: Chromium executable is not available in the Docker image." >&2
  echo "Rebuild the image with: docker compose build --no-cache" >&2
  exit 24
fi

if ! python3 - <<'PY' >/dev/null 2>&1
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    browser.close()
PY
then
  echo "ERROR: Python Playwright cannot launch Chromium." >&2
  echo "Rebuild the image with: docker compose build --no-cache" >&2
  exit 25
fi

exec "$@"
