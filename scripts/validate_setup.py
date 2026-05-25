#!/usr/bin/env python3
"""Static validation for the OpenCode challenge orchestrator setup."""
from __future__ import annotations
import json
from pathlib import Path

REQUIRED_COMMANDS = [
    "process_challenge.md",
    "review_challenge.md",
    "challenge-reviewer.md",
    "download_github.md",
    "decompress_zip_file.md",
    "challenge-reviewer-github.md",
    "challenge-reviewer-zip-file.md",
    "challenge-reviewer-global.md",
    "setup_opencode_environment.md",
    "add-google-spreadsheets.md",
    "test-google-spreadsheets.md",
]
REQUIRED_AGENTS = [
    "challenge-orchestrator.md",
    "software-specialist.md",
    "qa-specialist.md",
    "data-engineering-specialist.md",
    "challenge-supervisor.md",
    "challenge-reviewer.md",
    "challenge-reporter.md",
    "challenge-security-reviewer.md",
    "universal-specialist.md",
    "github-downloader.md",
    "google-sheets-logger.md",
]
REQUIRED_FILES = [
    "opencode.json",
    "config/orchestration.yaml",
    "config/review-policy.yaml",
    "config/session-policy.yaml",
    "config/security-policy.yaml",
    "config/skill-extraction-policy.yaml",
    "scripts/review_challenge.py",
    "scripts/download_github.py",
    "scripts/decompress_zip_file.py",
    "scripts/challenge_reviewer_github.py",
    "scripts/challenge_reviewer_zip_file.py",
    "scripts/challenge_reviewer_global.py",
    "scripts/archive_review_session.py",
    "scripts/generate_final_pdf.py",
    "scripts/validate_markdown_report.py",
    "scripts/check_playwright_mcp.py",
    "scripts/setup_opencode_environment.py",
    "scripts/setup_opencode_environment.sh",
    "scripts/setup_opencode_environment.ps1",
    "scripts/scan_prompt_injection.py",
    "scripts/sanitize_workspace_content.py",
    "scripts/validate_untrusted_content.py",
    "scripts/extract_agent_skill_profile.py",
    "scripts/render_unified_final_report.py",
    "scripts/publish_review_to_google_sheets.py",
    "src/add-google-spreadsheets.js",
    "src/test-google-spreadsheets.js",
    "src/config.js",
    "config/google/sheets.config.example.json",
    "config/google/service-account.example.json",
    "docs/GOOGLE_SHEETS_INTEGRATION.md",
    "templates/final-evaluation-unified-template.md",
    "schemas/final-evaluation-unified.schema.json",
    "docs/UNIFIED_REPORTING.md",
    "package.json",
    "Dockerfile",
    "docker-compose.yml",
    ".dockerignore",
    ".gitignore",
    ".env.example",
    "docs/DOCKER_SETUP.md",
    "scripts/docker_entrypoint.sh",
]

def main() -> int:
    root = Path.cwd()
    missing = []
    for f in REQUIRED_FILES:
        if not (root / f).exists():
            missing.append(f)
    for f in REQUIRED_COMMANDS:
        if not (root / ".opencode" / "commands" / f).exists():
            missing.append(f".opencode/commands/{f}")
    for f in REQUIRED_AGENTS:
        if not (root / ".opencode" / "agents" / f).exists():
            missing.append(f".opencode/agents/{f}")
    try:
        config = json.loads((root / "opencode.json").read_text(encoding="utf-8"))
        playwright_mcp = config.get("mcp", {}).get("playwright", {})
        if playwright_mcp.get("type") != "local":
            missing.append("opencode.json missing mcp.playwright.type=local")
        if playwright_mcp.get("command") != ["npx", "-y", "@playwright/mcp@latest"]:
            missing.append("opencode.json missing mcp.playwright command")
        if playwright_mcp.get("enabled") is not True:
            missing.append("opencode.json missing mcp.playwright.enabled=true")
        if config.get("tools", {}).get("playwright*") is not True:
            missing.append("opencode.json missing tools.playwright*=true")
    except Exception as exc:
        missing.append(f"opencode.json invalid JSON: {exc}")
    review_policy = (root / "config" / "review-policy.yaml").read_text(encoding="utf-8", errors="ignore") if (root / "config" / "review-policy.yaml").exists() else ""
    for required_text in ["dimension_scoring", "functional", "technical", "Functional acceptance criteria", "Technical acceptance criteria"]:
        if required_text not in review_policy:
            missing.append(f"config/review-policy.yaml missing {required_text}")
    review_script = (root / "scripts" / "review_challenge.py").read_text(encoding="utf-8", errors="ignore") if (root / "scripts" / "review_challenge.py").exists() else ""
    for required_text in ["infer_dimension", "dimension_scores", "functional_score", "technical_score"]:
        if required_text not in review_script:
            missing.append(f"scripts/review_challenge.py missing {required_text}")
    reporter = (root / ".opencode" / "agents" / "challenge-reporter.md").read_text(encoding="utf-8", errors="ignore") if (root / ".opencode" / "agents" / "challenge-reporter.md").exists() else ""
    if "Two-dimensional reporting rules" not in reporter:
        missing.append("challenge-reporter.md missing two-dimensional reporting rules")
    for required_text in ["Unified final-evaluation renderer rules", "render_unified_final_report.py", "final-evaluation.unified.json"]:
        if required_text not in reporter:
            missing.append(f"challenge-reporter.md missing {required_text}")
    universal = (root / ".opencode" / "agents" / "universal-specialist.md").read_text(encoding="utf-8", errors="ignore") if (root / ".opencode" / "agents" / "universal-specialist.md").exists() else ""
    for required_text in ["agent-skill-profile.json", "Skill assessment output", "Functional acceptance criteria", "Technical acceptance criteria"]:
        if required_text not in universal:
            missing.append(f"universal-specialist.md missing {required_text}")
    skill_script = (root / "scripts" / "extract_agent_skill_profile.py").read_text(encoding="utf-8", errors="ignore") if (root / "scripts" / "extract_agent_skill_profile.py").exists() else ""
    for required_text in ["agent-skill-profile.json", "skill-extraction.md", "skill-extraction.html", "skill-extraction.pdf", "extraction_quality"]:
        if required_text not in skill_script:
            missing.append(f"extract_agent_skill_profile.py missing {required_text}")
    review_script_skill = (root / "scripts" / "review_challenge.py").read_text(encoding="utf-8", errors="ignore") if (root / "scripts" / "review_challenge.py").exists() else ""
    for required_text in ["extract_agent_skill_profile.py", "universal-specialist", "agent_skill_profile", "skill_extraction_report_pdf"]:
        if required_text not in review_script_skill:
            missing.append(f"review_challenge.py missing {required_text}")
    docker_compose = (root / "docker-compose.yml").read_text(encoding="utf-8", errors="ignore") if (root / "docker-compose.yml").exists() else ""
    for required_text in [
        ".:/app",
        "./.opencode-state:/home/pwuser/.config/opencode",
        "./workspaces:/app/workspaces",
        "./review-sessions:/app/review-sessions",
        "./archived-review-sessions:/app/archived-review-sessions",
        "C:/challenge:/challenge",
        "opencode-orchestrator",
    ]:
        if required_text not in docker_compose:
            missing.append(f"docker-compose.yml missing {required_text}")
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8", errors="ignore") if (root / "Dockerfile").exists() else ""
    for required_text in ["opencode-ai@latest", "@playwright/mcp@latest", "playwright@1.52.0", "pwuser", "PLAYWRIGHT_BROWSERS_PATH"]:
        if required_text not in dockerfile:
            missing.append(f"Dockerfile missing {required_text}")
    docker_docs = (root / "docs" / "DOCKER_SETUP.md").read_text(encoding="utf-8", errors="ignore") if (root / "docs" / "DOCKER_SETUP.md").exists() else ""
    for required_text in ["docker compose build", "docker compose run --rm opencode-orchestrator bash", "/challenge/software-engineering.zip"]:
        if required_text not in docker_docs:
            missing.append(f"docs/DOCKER_SETUP.md missing {required_text}")
    package_json = (root / "package.json").read_text(encoding="utf-8", errors="ignore") if (root / "package.json").exists() else ""
    for required_text in ["add-google-spreadsheets", "test-google-spreadsheets", "googleapis", "publish-review-to-google-sheets"]:
        if required_text not in package_json:
            missing.append(f"package.json missing {required_text}")
    google_command = (root / ".opencode" / "commands" / "add-google-spreadsheets.md").read_text(encoding="utf-8", errors="ignore") if (root / ".opencode" / "commands" / "add-google-spreadsheets.md").exists() else ""
    for required_text in ["Employee ID", "Attempt", "Score", "npm run add-google-spreadsheets"]:
        if required_text not in google_command:
            missing.append(f"add-google-spreadsheets.md missing {required_text}")
    google_test_command = (root / ".opencode" / "commands" / "test-google-spreadsheets.md").read_text(encoding="utf-8", errors="ignore") if (root / ".opencode" / "commands" / "test-google-spreadsheets.md").exists() else ""
    for required_text in ["spreadsheetId", "sheetName", "records", "npm run test-google-spreadsheets"]:
        if required_text not in google_test_command:
            missing.append(f"test-google-spreadsheets.md missing {required_text}")
    google_test_script = (root / "src" / "test-google-spreadsheets.js").read_text(encoding="utf-8", errors="ignore") if (root / "src" / "test-google-spreadsheets.js").exists() else ""
    for required_text in ["testGoogleSheetsConnection", "spreadsheets.get", "values.get", "hasRecords", "headerMatchesConfiguredColumns"]:
        if required_text not in google_test_script:
            missing.append(f"test-google-spreadsheets.js missing {required_text}")
    google_publish = (root / "scripts" / "publish_review_to_google_sheets.py").read_text(encoding="utf-8", errors="ignore") if (root / "scripts" / "publish_review_to_google_sheets.py").exists() else ""
    for required_text in ["final-evaluation.json", "employee_id", "attempt_number", "numeric_score", "add-google-spreadsheets"]:
        if required_text not in google_publish:
            missing.append(f"publish_review_to_google_sheets.py missing {required_text}")
    renderer = (root / "scripts" / "render_unified_final_report.py").read_text(encoding="utf-8", errors="ignore") if (root / "scripts" / "render_unified_final_report.py").exists() else ""
    for required_text in ["publish_review_to_google_sheets.py", "google_sheets_publish", "--skip-google-sheets"]:
        if required_text not in renderer:
            missing.append(f"render_unified_final_report.py missing {required_text}")

    if missing:
        print("SETUP VALIDATION FAILED")
        for item in missing:
            print(f"- {item}")
        return 1
    print("SETUP VALIDATION PASSED")
    print("Commands, agents, policy, Markdown validation, PDF generation, Playwright MCP configuration, environment setup, prompt-injection security infrastructure, two-dimensional review scoring, Docker runtime setup, universal-specialist skill extraction, unified final-evaluation reporting, Google Sheets append and connectivity-test commands, GitHub-ready ignore rules, and helper scripts are present.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
