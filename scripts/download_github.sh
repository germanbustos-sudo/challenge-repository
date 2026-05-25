#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="./workspaces/github_repository"
SUCCESS_MESSAGE="GitHub repository downloaded successfully."
FAILURE_MESSAGE="GitHub repository could not be downloaded."

repo_url="${1:-}"

if [[ -z "$repo_url" ]]; then
  echo "$FAILURE_MESSAGE Missing repository URL."
  exit 2
fi

if [[ "$#" -ne 1 ]]; then
  echo "$FAILURE_MESSAGE Only one repository URL argument is allowed."
  exit 2
fi

if [[ ! "$repo_url" =~ ^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(\.git)?$ ]]; then
  echo "$FAILURE_MESSAGE Invalid GitHub repository URL."
  exit 2
fi

rm -rf -- "$TARGET_DIR"
mkdir -p -- "$(dirname "$TARGET_DIR")"

if git clone --depth 1 -- "$repo_url" "$TARGET_DIR"; then
  if [[ -d "$TARGET_DIR/.git" ]]; then
    echo "$SUCCESS_MESSAGE"
    echo "Target directory: workspaces/github_repository"
    exit 0
  fi
fi

echo "$FAILURE_MESSAGE"
exit 1
