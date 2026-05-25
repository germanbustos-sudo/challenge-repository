#!/usr/bin/env python3
"""Validate the project Playwright MCP configuration and local runtime prerequisites.

This script is intentionally conservative: it validates the OpenCode MCP config
statically by default and checks local command availability without downloading
packages. Use --runtime to also try starting the MCP package help command.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

VERSION = "0.8.7"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Playwright MCP configuration for OpenCode PDF export.")
    parser.add_argument("--runtime", action="store_true", help="Also run a lightweight npx MCP runtime check. May download packages.")
    args = parser.parse_args(argv)

    root = Path.cwd()
    config_path = root / "opencode.json"
    result: dict[str, object] = {
        "status": "valid",
        "validator_version": VERSION,
        "config": str(config_path),
        "checks": [],
        "errors": [],
    }
    checks: list[str] = result["checks"]  # type: ignore[assignment]
    errors: list[str] = result["errors"]  # type: ignore[assignment]

    if not config_path.exists():
        errors.append("opencode.json not found")
    else:
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"opencode.json is not valid JSON: {exc}")
            config = {}
        mcp = config.get("mcp", {}) if isinstance(config, dict) else {}
        playwright = mcp.get("playwright") if isinstance(mcp, dict) else None
        if not isinstance(playwright, dict):
            errors.append("mcp.playwright is missing")
        else:
            if playwright.get("type") != "local":
                errors.append("mcp.playwright.type must be 'local'")
            if playwright.get("enabled") is not True:
                errors.append("mcp.playwright.enabled must be true")
            command = playwright.get("command")
            if command != ["npx", "-y", "@playwright/mcp@latest"]:
                errors.append("mcp.playwright.command must be ['npx', '-y', '@playwright/mcp@latest']")
            else:
                checks.append("mcp.playwright command is configured")
            if int(playwright.get("timeout", 0) or 0) < 30000:
                errors.append("mcp.playwright.timeout should be at least 30000 ms")
            tools = config.get("tools", {}) if isinstance(config, dict) else {}
            if isinstance(tools, dict) and tools.get("playwright*") is True:
                checks.append("playwright MCP tools are enabled")
            else:
                errors.append("tools.playwright* should be true")

    if shutil.which("npx"):
        checks.append("npx is available on PATH")
    else:
        errors.append("npx is not available on PATH; install Node.js/npm")

    if args.runtime and not errors:
        try:
            completed = subprocess.run(
                ["npx", "-y", "@playwright/mcp@latest", "--help"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
                check=False,
            )
            if completed.returncode == 0:
                checks.append("@playwright/mcp runtime help command succeeded")
            else:
                errors.append(f"@playwright/mcp runtime check failed with exit={completed.returncode}: {completed.stdout[-1000:]}")
        except Exception as exc:
            errors.append(f"@playwright/mcp runtime check failed: {exc}")

    if errors:
        result["status"] = "invalid"
        print(json.dumps(result, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
