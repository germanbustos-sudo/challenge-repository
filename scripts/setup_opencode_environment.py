#!/usr/bin/env python3
"""Bootstrap and verify the local OpenCode challenge orchestrator environment.

This setup is intended for machines that obtain this project from a GitHub
repository or a ZIP archive. It installs/verifies the dependencies required for
professional PDF generation:
- Node.js/npm/npx
- Playwright npm package
- Playwright Chromium runtime
- Playwright MCP package availability
- HTML to PDF export smoke test

If any prerequisite cannot be installed or verified, the script exits non-zero
and prints a clear console error. It never creates a plain-text fallback PDF.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime
from pathlib import Path

VERSION = "0.8.7"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class SetupLog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.log_dir = root / "setup-logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / "setup-opencode-environment.log"
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        line = f"[{_now()}] {message}"
        self.lines.append(line)
        print(message)
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def _run(command: list[str], log: SetupLog, *, timeout: int = 300, allow_fail: bool = False) -> subprocess.CompletedProcess[str]:
    log.write("$ " + " ".join(command))
    try:
        completed = subprocess.run(
            command,
            cwd=log.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Command not found: {command[0]}. {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(command)}") from exc

    output = completed.stdout.strip()
    if output:
        for line in output.splitlines()[-80:]:
            log.write("  " + line)
    if completed.returncode != 0 and not allow_fail:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {' '.join(command)}")
    return completed


def _which_or_error(binary: str, install_hint: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise RuntimeError(f"{binary} was not found on PATH. {install_hint}")
    return path


def _ensure_package_json(root: Path, log: SetupLog) -> None:
    package_json = root / "package.json"
    if package_json.exists():
        log.write("package.json found; using project dependency manifest.")
        return
    log.write("package.json not found; creating a minimal project manifest for Playwright runtime dependencies.")
    package_json.write_text(json.dumps({
        "name": "opencode-challenge-orchestrator",
        "version": VERSION,
        "private": True,
        "description": "Runtime dependencies for OpenCode challenge orchestrator PDF generation.",
        "scripts": {
            "setup:pdf": "playwright install chromium",
            "verify:pdf": "node scripts/verify_playwright_pdf_runtime.mjs"
        },
        "devDependencies": {
            "playwright": "^1.44.0",
            "@playwright/mcp": "latest"
        }
    }, indent=2) + "\n", encoding="utf-8")


def _install_npm_dependencies(log: SetupLog, offline: bool) -> None:
    if offline:
        log.write("Offline mode enabled; skipping npm install.")
        return
    if (log.root / "package-lock.json").exists():
        log.write("package-lock.json found; running npm install for reproducible local dependencies.")
        _run(["npm", "install", "--no-audit", "--no-fund"], log, timeout=600)
    else:
        log.write("package-lock.json not found; running npm install and creating lockfile if needed.")
        _run(["npm", "install", "--no-audit", "--no-fund"], log, timeout=600)


def _install_chromium(log: SetupLog, offline: bool) -> None:
    if offline:
        log.write("Offline mode enabled; skipping Chromium installation.")
        return
    log.write("Installing/verifying Playwright Chromium runtime. This is required for final-evaluation.pdf.")
    _run(["npx", "playwright", "install", "chromium"], log, timeout=900)


def _write_pdf_smoke_test(root: Path) -> Path:
    script = root / "scripts" / "verify_playwright_pdf_runtime.mjs"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(textwrap.dedent(r'''
        import { chromium } from 'playwright';
        import { mkdirSync, writeFileSync, existsSync, statSync } from 'node:fs';
        import { resolve } from 'node:path';
        const outDir = resolve('setup-logs');
        mkdirSync(outDir, { recursive: true });
        const htmlPath = resolve(outDir, 'pdf-runtime-smoke-test.html');
        const pdfPath = resolve(outDir, 'pdf-runtime-smoke-test.pdf');
        writeFileSync(htmlPath, `<!doctype html><html><head><meta charset="utf-8"><style>body{font-family:Arial,sans-serif} table{border-collapse:collapse} th,td{border:1px solid #999;padding:6px}</style></head><body><h1>PDF Runtime Smoke Test</h1><p>UTF-8: áéíóú ñ ✓</p><table><tr><th>Key</th><th>Value</th></tr><tr><td>Status</td><td>OK</td></tr></table></body></html>`, 'utf8');
        const browser = await chromium.launch({ headless: true });
        const page = await browser.newPage();
        await page.goto('file://' + htmlPath.replaceAll('\\', '/'), { waitUntil: 'networkidle' });
        await page.pdf({ path: pdfPath, format: 'Letter', printBackground: true, preferCSSPageSize: true });
        await browser.close();
        if (!existsSync(pdfPath) || statSync(pdfPath).size < 1000) {
          throw new Error('PDF smoke test did not create a valid PDF file.');
        }
        console.log(JSON.stringify({ status: 'pdf_runtime_ok', pdf: pdfPath }));
    ''').strip() + "\n", encoding="utf-8")
    return script


def _verify_runtime(log: SetupLog) -> None:
    _run(["node", "--version"], log, timeout=60)
    _run(["npm", "--version"], log, timeout=60)
    _run(["npx", "--version"], log, timeout=60)
    _run(["npx", "playwright", "--version"], log, timeout=120)
    # The MCP help command may download the MCP package when not cached, but setup has installed it as a dev dependency.
    _run(["npx", "@playwright/mcp", "--help"], log, timeout=180)
    _write_pdf_smoke_test(log.root)
    _run(["node", "scripts/verify_playwright_pdf_runtime.mjs"], log, timeout=180)


def _verify_opencode_config(log: SetupLog) -> None:
    _run([sys.executable, "scripts/check_playwright_mcp.py", "--runtime"], log, timeout=240)
    _run([sys.executable, "scripts/validate_setup.py"], log, timeout=120)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install and verify OpenCode PDF runtime dependencies.")
    parser.add_argument("--offline", action="store_true", help="Do not install dependencies; only verify what already exists.")
    parser.add_argument("--skip-install", action="store_true", help="Alias for --offline.")
    args = parser.parse_args(argv)

    root = Path.cwd()
    log = SetupLog(root)
    offline = bool(args.offline or args.skip_install)
    result: dict[str, object] = {
        "status": "pending",
        "setup_version": VERSION,
        "root": str(root),
        "platform": platform.platform(),
        "offline": offline,
        "log": str(log.log_path),
    }

    log.write("Starting OpenCode environment setup.")
    log.write("This setup is safe for projects cloned from GitHub or extracted from ZIP files.")
    try:
        _which_or_error("node", "Install Node.js LTS from https://nodejs.org/ and retry.")
        _which_or_error("npm", "Install Node.js/npm and retry.")
        _which_or_error("npx", "Install Node.js/npm and retry.")
        _ensure_package_json(root, log)
        _install_npm_dependencies(log, offline)
        _install_chromium(log, offline)
        _verify_runtime(log)
        _verify_opencode_config(log)
        result["status"] = "ready"
        result["message"] = "OpenCode environment is ready. Playwright MCP and Chromium PDF runtime are available."
        log.write("SETUP COMPLETED: OpenCode environment is ready.")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        result["message"] = "SETUP FAILED. Resolve the console error above before running /challenge-reviewer-global if PDF output is required."
        log.write("SETUP FAILED: " + str(exc))
        print(json.dumps(result, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
