#!/usr/bin/env python3
"""Publish a completed final-evaluation score to Google Sheets.

This helper reads reports/final-evaluation.json from a review session and calls
`npm run add-google-spreadsheets -- EMPLOYEE_ID ATTEMPT SCORE`.

It intentionally writes only three values to Google Sheets:
- Employee ID -> column 1
- Attempt -> column 4
- Score -> column 7

Google credentials are never printed. The JavaScript command uses
config/google/sheets.config.json and config/google/service-account.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

VERSION = "0.8.7"
ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON report not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def latest_session() -> Path | None:
    sessions = [p for p in (ROOT / "review-sessions").glob("*") if p.is_dir()]
    if not sessions:
        return None
    return max(sessions, key=lambda p: p.stat().st_mtime)


def resolve_session(value: str | None) -> Path:
    if value:
        path = Path(value)
        if not path.is_absolute():
            path = ROOT / path
        return path.resolve()
    session = latest_session()
    if not session:
        raise FileNotFoundError("No review sessions were found.")
    return session.resolve()


def numeric_score(report: dict[str, Any]) -> float:
    for key in ("numeric_score", "final_score", "score"):
        value = report.get(key)
        if value is not None and value != "":
            try:
                return float(value)
            except Exception:
                continue
    raise ValueError("Final numeric score was not found in final-evaluation.json.")


def build_payload(session: Path, dry_run: bool = False) -> dict[str, Any]:
    report_path = session / "reports" / "final-evaluation.json"
    report = read_json(report_path)
    employee_id = str(report.get("employee_id") or report.get("employeeId") or "ABC-123")
    attempt = str(report.get("attempt_number") or report.get("attempt") or "0")
    score = numeric_score(report)
    return {
        "ok": None,
        "dry_run": dry_run,
        "version": VERSION,
        "review_session": str(session),
        "report_path": str(report_path),
        "employee_id": employee_id,
        "attempt": attempt,
        "score": score,
        "command": ["npm", "run", "add-google-spreadsheets", "--", employee_id, attempt, str(score)],
    }


def write_status(session: Path, payload: dict[str, Any]) -> None:
    status_path = session / "integrations" / "google-sheets-publish-status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**payload, "generated_at": now()}
    status_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Publish final-evaluation score to Google Sheets.")
    parser.add_argument("review_session", nargs="?", help="Review session path. Defaults to latest review-sessions/* directory.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the row without calling Google Sheets.")
    args = parser.parse_args(argv[1:])

    try:
        session = resolve_session(args.review_session)
        payload = build_payload(session, dry_run=args.dry_run)
        if args.dry_run:
            payload["ok"] = True
            payload["message"] = "Dry run only. Google Sheets was not updated."
            write_status(session, payload)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0

        result = subprocess.run(
            payload["command"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        payload["ok"] = result.returncode == 0
        payload["returncode"] = result.returncode
        # Do not include raw secrets; add-google-spreadsheets only prints metadata/errors.
        payload["output"] = result.stdout.strip()
        write_status(session, payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return result.returncode
    except Exception as exc:
        payload = {
            "ok": False,
            "version": VERSION,
            "error": str(exc),
            "message": "Google Sheets publishing failed. Configure config/google/sheets.config.json and service-account.json, then retry.",
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
