#!/usr/bin/env python3
"""Stateless global composite helper for `/challenge-reviewer-global`.

Pipeline implemented:
1. new context boundary (documented for OpenCode TUI; inherent for `opencode run`)
2. clean workspace
3. intake validation
4. classify source as ZIP FILE or GITHUB URL
5. download/decompress through the existing delegate helpers
6. initialize challenge review and extract universal-specialist skills
7. hand off to universal-specialist/reporter agents
8. provide archive command for the review session

The helper is deterministic and fail-fast. It never solves the challenge.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

VERSION = "0.8.7"
USAGE = "Usage: /challenge-reviewer-global SOURCE_DATA_REVIEW FILE_BASE [ATTEMPT_NUMBER] [EMPLOYEE_ID] [PUBLISH_GOOGLE_SHEETS]"
GITHUB_PATTERN = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(\.git)?$")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def fail(message: str, code: int = 1) -> int:
    print(message)
    return code


def log_line(project_root: Path, phase: str, message: str) -> None:
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "challenge-reviewer-global.log").open("a", encoding="utf-8") as log:
        log.write(f"{now()} | {phase} | {message}\n")


def is_valid_github_url(value: str) -> bool:
    value = value.strip().strip('"')
    if not GITHUB_PATTERN.match(value):
        return False
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) == 2


def is_zip_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.suffix.lower() == ".zip"


def clean_workspaces(project_root: Path, force: bool = True) -> None:
    """Clean only the managed workspaces directory to avoid mixing submissions."""
    if not force:
        return
    workspace_root = project_root / "workspaces"
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)


def parse_bool_flag(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return None


def parse_args(argv: list[str]) -> tuple[str, str, Path, str, str, bool] | int:
    args = [arg.strip() for arg in argv[1:] if arg.strip() and arg.strip() != "--clean-workspaces"]
    attempt_number = "0"
    employee_id = "ABC-123"
    publish_google_sheets = True

    # Optional 5th business parameter. Default is true to preserve existing behavior.
    # Supported false values: false, 0, no, n, off.
    if len(args) >= 5:
        maybe_publish = parse_bool_flag(args[-1])
        if maybe_publish is not None:
            publish_google_sheets = maybe_publish
            args = args[:-1]

    if len(args) >= 4:
        attempt_number = args[-2].strip() or "0"
        employee_id = args[-1].strip() or "ABC-123"
        args = args[:-2]
    if len(args) < 2:
        return fail(f"ERROR: Missing required parameters. {USAGE}", 2)

    source_arg = args[0].strip('"')
    base_arg = " ".join(args[1:]).strip().strip('"')

    if is_valid_github_url(source_arg):
        base_path = Path(base_arg).expanduser().resolve()
        if not base_path.exists() or not base_path.is_file():
            return fail(f"ERROR: Base challenge file does not exist or cannot be read: {base_path}", 2)
        return "github", source_arg, base_path, attempt_number, employee_id, publish_google_sheets

    candidates: list[tuple[Path, Path]] = []
    for split_at in range(1, len(args)):
        source_candidate = Path(" ".join(args[:split_at]).strip().strip('"')).expanduser().resolve()
        base_candidate = Path(" ".join(args[split_at:]).strip().strip('"')).expanduser().resolve()
        if is_zip_file(source_candidate) and base_candidate.exists() and base_candidate.is_file():
            candidates.append((source_candidate, base_candidate))

    if candidates:
        source_path, base_path = candidates[0]
        return "zip", str(source_path), base_path, attempt_number, employee_id, publish_google_sheets

    source_path = Path(source_arg).expanduser().resolve()
    if source_arg.lower().endswith(".zip") and (not source_path.exists() or not source_path.is_file()):
        return fail(f"ERROR: ZIP file does not exist or cannot be read: {source_path}", 2)

    return fail("ERROR: INVALID SOURCE. SOURCE_DATA_REVIEW must be a local ZIP file or a GitHub HTTPS repository URL.", 2)


def run_script(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def extract_last_json(text: str) -> dict[str, object]:
    decoder = json.JSONDecoder()
    last: dict[str, object] = {}
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except Exception:
            continue
        if isinstance(obj, dict):
            last = obj
    return last


def main(argv: list[str]) -> int:
    project_root = Path.cwd()
    log_line(project_root, "new", "stateless review boundary requested; use /new in TUI or opencode run for a new execution context")

    parsed = parse_args(argv)
    if isinstance(parsed, int):
        return parsed
    source_type, source_value, base_path, attempt_number, employee_id, publish_google_sheets = parsed

    clean_enabled = os.environ.get("CLEAN_WORKSPACES_BEFORE_INTAKE", "true").lower() not in {"0", "false", "no", "off"}
    clean_workspaces(project_root, force=clean_enabled)
    log_line(project_root, "clean workspace", f"workspaces cleaned={clean_enabled}")
    log_line(project_root, "intake", f"base_file={base_path}")
    log_line(project_root, "classify source", source_type)

    if source_type == "zip":
        delegate = project_root / "scripts" / "challenge_reviewer_zip_file.py"
        delegate_command = "/challenge-reviewer-zip-file"
    else:
        delegate = project_root / "scripts" / "challenge_reviewer_github.py"
        delegate_command = "/challenge-reviewer-github"

    if not delegate.exists():
        return fail(f"ERROR: Delegate helper script was not found for {delegate_command}.", 4)

    result = run_script(delegate, [source_value, str(base_path), attempt_number, employee_id])
    print(result.stdout.rstrip())
    if result.returncode != 0:
        log_line(project_root, "download/decompress", f"failed via {delegate_command} with code {result.returncode}")
        return result.returncode

    delegate_payload = extract_last_json(result.stdout)
    review_session = str(delegate_payload.get("review_session", "pending OpenCode agent execution"))

    # Security gate: workspace content is untrusted input. Scripts create raw evidence only.
    # Quarantine is intentionally deferred until the challenge-security-reviewer validates
    # findings, so scanner false positives cannot block valid reviews prematurely.
    session_arg = [] if not review_session or review_session == "pending OpenCode agent execution" else ["--session", review_session]
    security_steps = [
        ("validate untrusted content", project_root / "scripts" / "validate_untrusted_content.py", [*session_arg]),
        ("scan prompt injection", project_root / "scripts" / "scan_prompt_injection.py", ["--fail-on", "none", *session_arg]),
        ("sanitize workspace content", project_root / "scripts" / "sanitize_workspace_content.py", [*session_arg]),
    ]
    security_results = []
    for phase_name, script_path, script_args in security_steps:
        if not script_path.exists():
            return fail(f"ERROR: Security script is missing: {script_path}", 5)
        sec_result = run_script(script_path, script_args)
        print(sec_result.stdout.rstrip())
        security_results.append({"phase": phase_name, "returncode": sec_result.returncode, "authority": "raw_evidence_only"})
        log_line(project_root, phase_name, f"returncode={sec_result.returncode}; quarantine_decision=deferred_to_security_reviewer")
        if sec_result.returncode != 0:
            security_error = {
                "status": "security_precheck_error",
                "workflow": "challenge-reviewer-global",
                "orchestrator_version": VERSION,
                "phase": phase_name,
                "message": "ERROR: Security precheck script failed to execute. This is an infrastructure error, not a review decision.",
                "review_session": review_session,
                "security_results": security_results,
            }
            print(json.dumps(security_error, indent=2))
            return sec_result.returncode

    security_gate = {
        "status": "security_review_required",
        "workflow": "challenge-reviewer-global",
        "orchestrator_version": VERSION,
        "review_session": review_session,
        "message": "Security scripts completed. Run challenge-security-reviewer before deciding quarantine, fail_review, warn, or continue.",
        "quarantine_decision": "deferred_to_challenge_security_reviewer",
        "security_reports": [
            "security/prompt-injection-report.json",
            "security/untrusted-content-validation.json",
            "security/sanitized-content-summary.json",
        ],
    }
    print(json.dumps(security_gate, indent=2))

    log_line(project_root, "review", f"initialized review_session={review_session}")
    log_line(project_root, "report", "universal-specialist and challenge-reporter agents must complete final reports")

    archive_command = None
    render_report_command = None
    if review_session and review_session != "pending OpenCode agent execution":
        archive_command = f"python scripts/archive_review_session.py \"{review_session}\""
        render_args = "--strict" if publish_google_sheets else "--strict --skip-google-sheets"
        render_report_command = f"python scripts/render_unified_final_report.py \"{review_session}\" {render_args}"
        log_line(project_root, "archive review-session", archive_command)
        log_line(project_root, "report", f"render_command={render_report_command}")

    output = {
        "status": "initialized",
        "workflow": "challenge-reviewer-global",
        "orchestrator_version": VERSION,
        "stateless_context": {
            "open_code_new_required_for_tui": True,
            "recommended_execution": "opencode run \"/challenge-reviewer-global SOURCE_DATA_REVIEW FILE_BASE\"",
            "workspace_cleaned_before_intake": clean_enabled,
        },
        "phases": ["new", "clean workspace", "intake", "classify source", "download/decompress", "security validation", "prompt injection scan", "sanitization", "security reviewer validation", "skill extraction", "universal-specialist review", "report", "archive review-session"],
        "source_type": "ZIP FILE" if source_type == "zip" else "GITHUB URL",
        "source_data_review": source_value,
        "base_file": str(base_path),
        "attempt_number": attempt_number,
        "employee_id": employee_id,
        "publish_google_sheets": publish_google_sheets,
        "delegated_command": delegate_command,
        "review_session": review_session,
        "render_report_command": render_report_command,
        "archive_command_after_report": archive_command,
        "next_agents": ["challenge-security-reviewer", "universal-specialist", "challenge-reporter"],
        "security_decision_rule": "quarantine only after validated critical findings from challenge-security-reviewer",
        "security_results": security_results,
        "final_report_pdf": delegate_payload.get("final_report_pdf", "pending"),
        "agent_skill_profile": delegate_payload.get("agent_skill_profile", "pending"),
        "skill_extraction_report_markdown": delegate_payload.get("skill_extraction_report_markdown", "pending"),
        "skill_extraction_report_html": delegate_payload.get("skill_extraction_report_html", "pending"),
        "skill_extraction_report_pdf": delegate_payload.get("skill_extraction_report_pdf", "pending"),
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
