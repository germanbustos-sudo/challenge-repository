#!/usr/bin/env python3
"""Download one public GitHub repository into workspaces/github_repository."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

TARGET_DIR = Path("workspaces") / "github_repository"
SUCCESS_MESSAGE = "GitHub repository downloaded successfully."
FAILURE_MESSAGE = "GitHub repository could not be downloaded."
URL_PATTERN = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(\.git)?$")


def fail(reason: str, code: int = 1) -> int:
    print(f"{FAILURE_MESSAGE} {reason}")
    return code


def is_valid_github_url(repo_url: str) -> bool:
    if not URL_PATTERN.match(repo_url):
        return False
    parsed = urlparse(repo_url)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) == 2


def ensure_safe_target(project_root: Path, target: Path) -> Path:
    workspace_root = (project_root / "workspaces").resolve()
    resolved_target = target.resolve()
    if resolved_target != workspace_root and workspace_root not in resolved_target.parents:
        raise ValueError("Refusing to use a target directory outside workspaces/.")
    return resolved_target


def clean_workspaces_if_requested(project_root: Path, argv: list[str]) -> None:
    requested = os.environ.get("CLEAN_WORKSPACES_BEFORE_INTAKE", "").lower() in {"1", "true", "yes", "on"} or "--clean-workspaces" in argv
    if not requested:
        return
    workspace_root = project_root / "workspaces"
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--clean-workspaces"]
    if len(args) != 1:
        return fail("Missing repository URL." if len(args) < 1 else "Only one repository URL argument is allowed.", 2)

    repo_url = args[0].strip()
    if not repo_url:
        return fail("Missing repository URL.", 2)
    if not is_valid_github_url(repo_url):
        return fail("Invalid GitHub repository URL.", 2)

    project_root = Path.cwd()
    clean_workspaces_if_requested(project_root, argv)
    target = ensure_safe_target(project_root, project_root / TARGET_DIR)

    try:
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--", repo_url, str(target)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode != 0:
            return fail(f"git clone exited with code {result.returncode}. {result.stdout.strip()}")

        if not (target / ".git").is_dir():
            return fail("Clone verification failed: .git directory was not found.")

        print(SUCCESS_MESSAGE)
        print(f"Target directory: {TARGET_DIR.as_posix()}")
        return 0
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
