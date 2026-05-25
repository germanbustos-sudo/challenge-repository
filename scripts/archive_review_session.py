#!/usr/bin/env python3
"""Archive a review session for traceability.

This helper creates a ZIP archive under archived-review-sessions/ for a completed
or initialized review session. It is deterministic and does not modify challenge
implementation files.
"""
from __future__ import annotations

import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path

VERSION = "0.8.7"


def fail(message: str, code: int = 1) -> int:
    print(message)
    return code


def main(argv: list[str]) -> int:
    if len(argv) < 2 or not argv[1].strip():
        return fail("ERROR: Missing review session path. Usage: python scripts/archive_review_session.py REVIEW_SESSION_PATH", 2)

    session = Path(argv[1]).expanduser().resolve()
    if not session.exists() or not session.is_dir():
        return fail(f"ERROR: Review session path does not exist or is not a directory: {session}", 2)

    project_root = Path.cwd().resolve()
    archive_root = project_root / "archived-review-sessions"
    archive_root.mkdir(parents=True, exist_ok=True)

    safe_name = session.name[:80]
    archive_path = archive_root / f"{safe_name}.zip"
    counter = 1
    while archive_path.exists():
        archive_path = archive_root / f"{safe_name}-{counter}.zip"
        counter += 1

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(session.rglob("*")):
            if item.is_file():
                zf.write(item, arcname=str(Path(session.name) / item.relative_to(session)))

    audit = {
        "status": "archived",
        "orchestrator_version": VERSION,
        "archived_at": datetime.now().isoformat(timespec="seconds"),
        "review_session": str(session),
        "archive_path": str(archive_path),
    }
    (session / "logs").mkdir(parents=True, exist_ok=True)
    with (session / "logs" / "execution.log").open("a", encoding="utf-8") as log:
        log.write(f"{audit['archived_at']} | archive | {archive_path}\n")
    print(json.dumps(audit, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
