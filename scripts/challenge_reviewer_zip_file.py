#!/usr/bin/env python3
"""Composite helper for `/challenge-reviewer-zip-file`.

It validates two required parameters, decompresses a ZIP file into
workspaces/decompressed_zip, and initializes the review workflow only when the
ZIP decompression succeeds.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

VERSION = "0.8.7"
USAGE = "Usage: /challenge-reviewer-zip-file ZIP_FILE_BASE FILE_BASE [ATTEMPT_NUMBER] [EMPLOYEE_ID]"
TARGET_DIR = Path("workspaces") / "decompressed_zip"


def fail(message: str, code: int = 1) -> int:
    print(message)
    return code


def parse_args(argv: list[str]) -> tuple[Path, Path, str, str] | int:
    args = [arg.strip() for arg in argv[1:] if arg.strip()]
    attempt_number = "0"
    employee_id = "ABC-123"
    if len(args) >= 4:
        attempt_number = args[-2].strip() or "0"
        employee_id = args[-1].strip() or "ABC-123"
        args = args[:-2]
    if len(args) < 2:
        return fail(f"ERROR: Missing required parameters. {USAGE}", 2)

    # Support quoted paths and best-effort unquoted paths with spaces by finding
    # a valid ZIP path prefix and a valid base challenge path suffix.
    candidates: list[tuple[Path, Path]] = []
    for split_at in range(1, len(args)):
        zip_candidate = Path(" ".join(args[:split_at]).strip().strip('"')).expanduser().resolve()
        base_candidate = Path(" ".join(args[split_at:]).strip().strip('"')).expanduser().resolve()
        if zip_candidate.exists() and zip_candidate.is_file() and zip_candidate.suffix.lower() == ".zip":
            if base_candidate.exists() and base_candidate.is_file():
                candidates.append((zip_candidate, base_candidate))

    if candidates:
        zip_path, base_path = candidates[0]
        return zip_path, base_path, attempt_number, employee_id

    # More specific diagnostics for normal quoted two-argument usage.
    zip_path = Path(args[0].strip('"')).expanduser().resolve()
    base_path = Path(" ".join(args[1:]).strip().strip('"')).expanduser().resolve()

    if not zip_path.exists() or not zip_path.is_file():
        return fail(f"ERROR: ZIP file does not exist or cannot be read: {zip_path}", 2)
    if zip_path.suffix.lower() != ".zip":
        return fail(f"ERROR: ZIP input file is not a .zip archive: {zip_path}", 2)
    if not base_path.exists() or not base_path.is_file():
        return fail(f"ERROR: Base challenge file does not exist or cannot be read: {base_path}", 2)

    return zip_path, base_path, attempt_number, employee_id


def run_script(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def target_has_content(project_root: Path) -> bool:
    target = project_root / TARGET_DIR
    return target.exists() and target.is_dir() and any(target.iterdir())


def main(argv: list[str]) -> int:
    parsed = parse_args(argv)
    if isinstance(parsed, int):
        return parsed
    zip_path, base_path, attempt_number, employee_id = parsed

    project_root = Path.cwd()
    decompress_script = project_root / "scripts" / "decompress_zip_file.py"
    review_script = project_root / "scripts" / "review_challenge.py"

    if not decompress_script.exists():
        return fail("ERROR: decompress_zip_file helper script was not found.", 4)
    if not review_script.exists():
        return fail("ERROR: review_challenge helper script was not found.", 4)

    decompression = run_script(decompress_script, [str(zip_path)])
    print(decompression.stdout.rstrip())
    if decompression.returncode != 0:
        return fail("ERROR: ZIP file decompression failed. Review was not started.", decompression.returncode)

    if not target_has_content(project_root):
        return fail("ERROR: ZIP file decompression failed. Review was not started.", 5)

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
        "workflow": "challenge-reviewer-zip-file",
        "orchestrator_version": VERSION,
        "decompression_target": TARGET_DIR.as_posix(),
        "zip_file": str(zip_path),
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
