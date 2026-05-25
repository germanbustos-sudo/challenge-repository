#!/usr/bin/env python3
"""Composite helper for `/challenge-reviewer-github`.

It validates two required parameters, downloads a GitHub repository into
workspaces/github_repository, and initializes the review workflow only when the
repository download succeeds.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

VERSION = "0.8.7"
USAGE = "Usage: /challenge-reviewer-github GITHUB_URL FILE_BASE [ATTEMPT_NUMBER] [EMPLOYEE_ID]"
URL_PATTERN = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(\.git)?$")
TARGET_DIR = Path("workspaces") / "github_repository"


def fail(message: str, code: int = 1) -> int:
    print(message)
    return code


def is_valid_github_url(repo_url: str) -> bool:
    if not URL_PATTERN.match(repo_url):
        return False
    parsed = urlparse(repo_url)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) == 2


def parse_args(argv: list[str]) -> tuple[str, Path, str, str] | int:
    if len(argv) < 3:
        return fail(f"ERROR: Missing required parameters. {USAGE}", 2)

    github_url = argv[1].strip()
    attempt_number = "0"
    employee_id = "ABC-123"
    file_args = argv[2:]
    if len(file_args) >= 3:
        attempt_number = file_args[-2].strip() or "0"
        employee_id = file_args[-1].strip() or "ABC-123"
        file_args = file_args[:-2]
    file_base = " ".join(file_args).strip()

    if not github_url:
        return fail("ERROR: Missing GitHub repository URL.", 2)
    if not file_base:
        return fail("ERROR: Missing base challenge file path.", 2)
    if not is_valid_github_url(github_url):
        return fail("ERROR: Invalid GitHub repository URL.", 2)

    base_path = Path(file_base).expanduser().resolve()
    if not base_path.exists() or not base_path.is_file():
        return fail(f"ERROR: Base challenge file does not exist or cannot be read: {base_path}", 2)

    return github_url, base_path, attempt_number, employee_id


def run_script(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def main(argv: list[str]) -> int:
    parsed = parse_args(argv)
    if isinstance(parsed, int):
        return parsed
    github_url, base_path, attempt_number, employee_id = parsed

    project_root = Path.cwd()
    download_script = project_root / "scripts" / "download_github.py"
    review_script = project_root / "scripts" / "review_challenge.py"

    if not download_script.exists():
        return fail("ERROR: download_github helper script was not found.", 4)
    if not review_script.exists():
        return fail("ERROR: review_challenge helper script was not found.", 4)

    download = run_script(download_script, [github_url])
    print(download.stdout.rstrip())
    if download.returncode != 0:
        return fail("ERROR: GitHub repository download failed. Review was not started.", download.returncode)

    target = project_root / TARGET_DIR
    if not (target / ".git").is_dir():
        return fail("ERROR: GitHub repository download failed. Review was not started.", 5)

    review = run_script(review_script, [str(base_path), attempt_number, employee_id])
    print(review.stdout.rstrip())
    if review.returncode != 0:
        return review.returncode

    try:
        review_payload = json.loads(review.stdout)
    except Exception:
        review_payload = {}

    result = {
        "status": "initialized",
        "workflow": "challenge-reviewer-github",
        "orchestrator_version": VERSION,
        "download_target": TARGET_DIR.as_posix(),
        "base_file": str(base_path),
        "attempt_number": attempt_number,
        "employee_id": employee_id,
        "review_session": review_payload.get("review_session", "pending OpenCode agent execution"),
        "classification": review_payload.get("classification", "pending"),
        "next_agents": ["universal-specialist", "challenge-reporter"],
        "required_reports": ["complete_acceptance", "partial_acceptance", "no_acceptance"],
        "final_report_pdf": review_payload.get("final_report_pdf", "pending"),
        "agent_skill_profile": review_payload.get("agent_skill_profile", "pending"),
        "skill_extraction_report_markdown": review_payload.get("skill_extraction_report_markdown", "pending"),
        "skill_extraction_report_html": review_payload.get("skill_extraction_report_html", "pending"),
        "skill_extraction_report_pdf": review_payload.get("skill_extraction_report_pdf", "pending"),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
