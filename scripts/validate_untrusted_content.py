#!/usr/bin/env python3
"""Validate untrusted workspace files before an LLM review.

This detects oversized files, invalid names, binary masquerading, and suspicious HTML/JS.
It does not execute candidate code.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

VERSION = "0.8.7"
MAX_FILE_BYTES = 5 * 1024 * 1024
SUSPICIOUS_SUFFIXES = {".exe", ".dll", ".scr", ".ps1", ".bat", ".cmd"}
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".html", ".py", ".js", ".ts", ".sql", ".csv"}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def looks_binary(path: Path) -> bool:
    try:
        data = path.read_bytes()[:4096]
    except Exception:
        return False
    return b"\x00" in data


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate untrusted workspace content.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--workspace", default="workspaces")
    parser.add_argument("--session", default=None)
    parser.add_argument("--fail-on-critical", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    workspace = (root / args.workspace).resolve()
    if not workspace.exists():
        print(f"ERROR: Workspace directory not found: {workspace}")
        return 2
    findings = []
    total_files = 0
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        total_files += 1
        rel = str(path.relative_to(root))
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            findings.append({"severity": "high", "type": "oversized_file", "path": rel, "size_bytes": size})
        if path.suffix.lower() in SUSPICIOUS_SUFFIXES:
            findings.append({"severity": "medium", "type": "executable_or_script_file", "path": rel})
        if path.suffix.lower() in TEXT_SUFFIXES and looks_binary(path):
            findings.append({"severity": "critical", "type": "binary_masquerading_as_text", "path": rel})
        if path.suffix.lower() in {".html", ".htm"}:
            text = path.read_text(encoding="utf-8", errors="replace")[:200000].lower()
            if "<script" in text:
                findings.append({"severity": "high", "type": "html_contains_script", "path": rel})
            if "http://" in text or "https://" in text:
                findings.append({"severity": "medium", "type": "html_external_resource_reference", "path": rel})
    highest = "none"
    rank = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    for f in findings:
        if rank[f["severity"]] > rank[highest]:
            highest = f["severity"]
    report = {
        "status": "completed",
        "validator_version": VERSION,
        "generated_at": now(),
        "workspace": str(workspace),
        "total_files": total_files,
        "finding_count": len(findings),
        "highest_risk": highest,
        "findings": findings,
    }
    out = root / "security" / "untrusted-content-validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.session:
        session_out = Path(args.session).resolve() / "security" / "untrusted-content-validation.json"
        session_out.parent.mkdir(parents=True, exist_ok=True)
        session_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if args.fail_on_critical and highest == "critical":
        return 20
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
