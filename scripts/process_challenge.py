#!/usr/bin/env python3
"""Initialize a clean OpenCode challenge workspace.

This helper performs deterministic pre-agent checks for `/process_challenge`:
- validates the input file
- cleans previous workspaces
- classifies the challenge type
- creates a new workspace and manifest

The AI agent workflow continues from the generated manifest.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

VERSION = "0.8.7"
DEFAULT_MAX_REJECTED = 3

ERRORS = {
    "missing_path": "ERROR: Missing challenge file path.",
    "unreadable_file": "ERROR: Challenge file does not exist or cannot be read: {path}",
    "unclassified": "ERROR: Challenge document could not be classified.",
    "workspace_cleanup_failed": "ERROR: Workspace cleanup could not be completed.",
    "workspace_failed": "ERROR: Workspace could not be created.",
}

SPECIALISTS = {
    "software_engineering": "software-specialist",
    "qa_engineering": "qa-specialist",
    "data_engineering": "data-engineering-specialist",
}


def read_text(path: Path) -> str:
    """Best-effort text reader for plain text and PDFs."""
    try:
        if path.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader  # type: ignore
            except Exception:
                return path.name
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages) or path.name
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def classify(text: str) -> str | None:
    """Classify a challenge from its text using explicit role signals."""
    t = text.lower()
    scores = {
        "software_engineering": sum(
            keyword in t
            for keyword in [
                "software engineering",
                "spec-driven",
                "openapi",
                "rest api",
                "user stories",
                "gherkin",
            ]
        ),
        "qa_engineering": sum(
            keyword in t
            for keyword in [
                "qa engineering",
                "test case",
                "regression matrix",
                "manual test",
                "boundary value",
                "equivalence partitioning",
            ]
        ),
        "data_engineering": sum(
            keyword in t
            for keyword in [
                "data engineering",
                "etl",
                "pipeline",
                "star schema",
                "sql database",
                "pandas",
            ]
        ),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else None


def clean_workspaces(workspaces_root: Path) -> None:
    """Remove all previous workspace folders before a new run."""
    workspaces_root.mkdir(parents=True, exist_ok=True)
    for child in workspaces_root.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def create_workspace(src: Path, kind: str, workspace_root: Path) -> Path:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", src.stem).strip("-").lower()[:25]
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = workspace_root / f"{slug}-{ts}"

    for directory in ["input", "implementation", "tests", "review", "reports"]:
        (root / directory).mkdir(parents=True, exist_ok=True)

    shutil.copy2(src, root / "input" / src.name)

    manifest = {
        "orchestrator_version": VERSION,
        "source_file": str(src),
        "classification": kind,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "workspace": str(root),
        "specialist_agent": SPECIALISTS[kind],
        "review_policy": {
            "max_rejected": DEFAULT_MAX_REJECTED,
            "rejection_count": 0,
            "status": "initialized",
            "grade": "N/A",
        },
    }
    (root / "run-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (root / "review" / "rejection-history.json").write_text("[]\n", encoding="utf-8")
    (root / "reports" / "final-evaluation.md").write_text(
        "# Final Challenge Evaluation\n\nStatus: pending OpenCode agent execution.\n",
        encoding="utf-8",
    )
    return root


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print(ERRORS["missing_path"])
        return 2

    src = Path(sys.argv[1]).expanduser().resolve()
    if not src.exists() or not src.is_file():
        print(ERRORS["unreadable_file"].format(path=src))
        return 2

    workspace_root = Path.cwd() / "workspaces"
    try:
        clean_workspaces(workspace_root)
    except Exception:
        print(ERRORS["workspace_cleanup_failed"])
        return 4

    text = read_text(src)
    kind = classify(f"{text}\n{src.name}")
    if not kind:
        print(ERRORS["unclassified"])
        return 3

    try:
        root = create_workspace(src, kind, workspace_root)
    except Exception:
        print(ERRORS["workspace_failed"])
        return 5

    print(
        json.dumps(
            {
                "status": "initialized",
                "classification": kind,
                "specialist_agent": SPECIALISTS[kind],
                "workspace": str(root),
                "max_rejected": DEFAULT_MAX_REJECTED,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
