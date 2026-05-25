#!/usr/bin/env python3
"""Validate final-evaluation.md before converting it to PDF.

The validator is intentionally dependency-free and checks the Markdown structures
that are critical for professional PDF export: headings, fenced code blocks,
tables, required metadata, and report sections.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VERSION = "0.8.7"
REQUIRED_SECTIONS = [
    "Final Challenge Review Report",
    "Summary",
    "Acceptance Matrix",
    "Evidence Log",
    "Anti-False-Positive Validation",
    "Final Recommendation",
]
REQUIRED_METADATA = ["Attempt number", "Employee ID"]


def fail(message: str, code: int = 1) -> int:
    print(json.dumps({"status": "invalid", "error": message}, indent=2))
    return code


def validate_fences(text: str) -> list[str]:
    errors: list[str] = []
    if text.count("```") % 2 != 0:
        errors.append("Unclosed fenced code block detected.")
    return errors


def validate_tables(lines: list[str]) -> list[str]:
    errors: list[str] = []
    for idx, line in enumerate(lines[:-1]):
        if line.strip().startswith("|") and line.strip().endswith("|"):
            next_line = lines[idx + 1].strip()
            if re.fullmatch(r"\|[\s:\-\|]+\|", next_line):
                header_cols = [c.strip() for c in line.strip().strip("|").split("|")]
                sep_cols = [c.strip() for c in next_line.strip().strip("|").split("|")]
                if len(header_cols) != len(sep_cols):
                    errors.append(f"Table separator column count mismatch near line {idx + 1}.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a final-evaluation Markdown report before PDF export.")
    parser.add_argument("markdown_report")
    parser.add_argument("--strict", action="store_true", help="Require all standard report sections.")
    args = parser.parse_args()

    path = Path(args.markdown_report).expanduser().resolve()
    if not path.exists() or not path.is_file():
        return fail(f"Markdown report not found: {path}", 2)
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    errors: list[str] = []
    if not text.strip():
        errors.append("Markdown report is empty.")
    if not re.search(r"^#\s+", text, flags=re.MULTILINE):
        errors.append("Markdown report must contain a level-1 heading.")
    errors.extend(validate_fences(text))
    errors.extend(validate_tables(lines))
    if args.strict:
        lower = text.lower()
        for section in REQUIRED_SECTIONS:
            if section.lower() not in lower:
                errors.append(f"Missing required section: {section}")
        for field in REQUIRED_METADATA:
            if field.lower() not in lower:
                errors.append(f"Missing required metadata field: {field}")
    if errors:
        print(json.dumps({"status": "invalid", "markdown_report": str(path), "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "valid", "markdown_report": str(path), "validator_version": VERSION}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
