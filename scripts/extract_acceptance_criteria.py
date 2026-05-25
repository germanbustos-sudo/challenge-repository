#!/usr/bin/env python3
"""Extract dynamic acceptance criteria from a FILE_BASE challenge document.

This utility mirrors the session strategy used by review_challenge.py: FILE_BASE is
primary, review-policy.yaml is fallback/guardrails. It is useful for debugging and
integration with other orchestrations.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Import from review_challenge without requiring package installation.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from review_challenge import classify, extract_dynamic_criteria, read_text  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("ERROR: Missing FILE_BASE path.")
        return 2
    path = Path(sys.argv[1]).expanduser().resolve()
    if not path.exists() or not path.is_file():
        print(f"ERROR: FILE_BASE does not exist or cannot be read: {path}")
        return 2
    text = read_text(path)
    role = classify(f"{text}\n{path.name}")
    if not role:
        print("ERROR: Base challenge document could not be classified.")
        return 3
    criteria, extraction = extract_dynamic_criteria(text, role)
    print(json.dumps({"role": role, "extraction": extraction, "criteria": criteria}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
