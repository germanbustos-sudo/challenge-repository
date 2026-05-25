#!/usr/bin/env python3
"""Decompress one local ZIP file into workspaces/decompressed_zip."""
from __future__ import annotations

import os
import shutil
import sys
import zipfile
from pathlib import Path

TARGET_DIR = Path("workspaces") / "decompressed_zip"
SUCCESS_MESSAGE = "ZIP file decompressed successfully."
FAILURE_MESSAGE = "ZIP file could not be decompressed."


def fail(reason: str, code: int = 1) -> int:
    print(f"{FAILURE_MESSAGE} {reason}")
    return code


def ensure_safe_target(project_root: Path, target: Path) -> Path:
    workspace_root = (project_root / "workspaces").resolve()
    resolved_target = target.resolve()
    if resolved_target != workspace_root and workspace_root not in resolved_target.parents:
        raise ValueError("Refusing to use a target directory outside workspaces/.")
    return resolved_target


def safe_extract(zip_path: Path, target: Path) -> None:
    target_resolved = target.resolve()
    with zipfile.ZipFile(zip_path, "r") as archive:
        bad_file = archive.testzip()
        if bad_file is not None:
            raise ValueError(f"ZIP integrity check failed at entry: {bad_file}")

        members = archive.infolist()
        if not members:
            raise ValueError("ZIP archive is empty.")

        for member in members:
            member_name = member.filename.replace("\\", "/")
            if member_name.startswith("/") or member_name.startswith("../") or "/../" in member_name:
                raise ValueError(f"Unsafe ZIP entry detected: {member.filename}")
            destination = (target / member.filename).resolve()
            if destination != target_resolved and target_resolved not in destination.parents:
                raise ValueError(f"Unsafe ZIP entry outside target directory: {member.filename}")

        archive.extractall(target)


def has_extracted_content(target: Path) -> bool:
    return target.exists() and target.is_dir() and any(target.iterdir())


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
        return fail("Missing ZIP file path." if len(args) < 1 else "Only one ZIP file path argument is allowed.", 2)

    zip_arg = args[0].strip().strip('"')
    if not zip_arg:
        return fail("Missing ZIP file path.", 2)

    zip_path = Path(zip_arg).expanduser().resolve()
    if not zip_path.exists() or not zip_path.is_file():
        return fail(f"ZIP file does not exist or cannot be read: {zip_path}", 2)
    if zip_path.suffix.lower() != ".zip":
        return fail(f"Input file is not a .zip archive: {zip_path}", 2)
    if not zipfile.is_zipfile(zip_path):
        return fail(f"Input file is not a valid ZIP archive: {zip_path}", 2)

    project_root = Path.cwd()
    try:
        clean_workspaces_if_requested(project_root, argv)
        target = ensure_safe_target(project_root, project_root / TARGET_DIR)
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

        safe_extract(zip_path, target)

        if not has_extracted_content(target):
            return fail("Extraction verification failed: no files or folders were created.")

        print(SUCCESS_MESSAGE)
        print(f"Target directory: {TARGET_DIR.as_posix()}")
        return 0
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
