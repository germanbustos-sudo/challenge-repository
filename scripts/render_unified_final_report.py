#!/usr/bin/env python3
"""Render a unified final-evaluation report for every intake source.

This script is the single deterministic report renderer for ZIP, GitHub,
and future sources. Intake may differ by source, but reporting must not.
It reads the current review session, builds a normalized JSON context,
renders one Markdown template, validates it, writes JSON/HTML, and attempts
HTML-to-PDF via scripts/generate_final_pdf.py.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

VERSION = "0.8.7"
ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "templates" / "final-evaluation-unified-template.md"
SCHEMA_PATH = ROOT / "schemas" / "final-evaluation-unified.schema.json"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def read_text(path: Path, default: str = "") -> str:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        return default
    return default


def normalize_status(value: Any) -> str:
    s = str(value or "pending").strip().lower()
    if "pass" in s or s in {"passed", "success"}:
        return "passed"
    if "partial" in s or "warning" in s:
        return "partial"
    if "fail" in s or "reject" in s:
        return "failed"
    return s or "pending"


def criterion_id(row: dict[str, Any], idx: int) -> str:
    return str(row.get("criterion_id") or row.get("id") or f"AC-{idx:03d}")


def criterion_text(row: dict[str, Any]) -> str:
    return str(row.get("criterion") or row.get("text") or row.get("source_text") or "")


def matrix_rows(session: Path) -> list[dict[str, Any]]:
    matrix = read_json(session / "review" / "acceptance-matrix.json", {})
    rows = matrix.get("criteria") or matrix.get("rows") or []
    if isinstance(rows, dict):
        rows = list(rows.values())
    normalized: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        dim = str(row.get("dimension") or "other").lower()
        if dim not in {"functional", "technical"}:
            section = str(row.get("source_section") or "").lower()
            if "technical" in section:
                dim = "technical"
            elif "functional" in section:
                dim = "functional"
            else:
                dim = "other"
        cid = criterion_id(row, idx)
        normalized.append({
            "id": cid,
            "criterion_id": cid,
            "dimension": dim,
            "dimension_label": "Functional acceptance criteria" if dim == "functional" else "Technical acceptance criteria" if dim == "technical" else "Other criteria",
            "criterion": criterion_text(row),
            "source_section": str(row.get("source_section") or ("Functional acceptance criteria" if dim == "functional" else "Technical acceptance criteria" if dim == "technical" else "")),
            "source_text": str(row.get("source_text") or criterion_text(row)),
            "status": normalize_status(row.get("status")),
            "severity": str(row.get("severity") or "major"),
            "evidence": row.get("evidence") or row.get("evidence_summary") or "pending evidence",
            "comment": str(row.get("comment") or row.get("notes") or ""),
            "evidence_required": row.get("evidence_required") or [],
        })
    return normalized


def score_for(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    values = []
    for row in rows:
        s = normalize_status(row.get("status"))
        if s == "passed":
            values.append(100)
        elif s == "partial":
            values.append(50)
        elif s == "failed":
            values.append(0)
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def grade(score: float | int | None) -> str:
    if score is None:
        return "N/A"
    if score >= 85:
        return "SENIOR"
    if score >= 60:
        return "INTERMEDIATE"
    return "JUNIOR"


def counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "criteria": len(rows),
        "passed": sum(1 for r in rows if normalize_status(r.get("status")) == "passed"),
        "partial": sum(1 for r in rows if normalize_status(r.get("status")) == "partial"),
        "failed": sum(1 for r in rows if normalize_status(r.get("status")) == "failed"),
    }


def md_escape_cell(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        value = "; ".join(map(str, value))
    elif isinstance(value, dict):
        value = "; ".join(f"{k}: {v}" for k, v in value.items())
    s = str(value if value is not None else "")
    s = s.replace("\n", "<br>").replace("|", "\\|")
    return s


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(md_escape_cell(v) for v in row) + " |")
    return "\n".join(out)


def criteria_summary_table(rows: list[dict[str, Any]]) -> str:
    return table(["ID", "Criterion", "Status", "Severity", "Evidence", "Comment"], [
        [r["id"], r["criterion"], r["status"], r["severity"], r.get("evidence", ""), r.get("comment", "")]
        for r in rows
    ]) if rows else "No criteria were extracted for this dimension."


def detail_sections(rows: list[dict[str, Any]]) -> str:
    parts = []
    for r in rows:
        parts.append(f"### {r['id']}: {r['criterion']}\n")
        parts.append(table(["Field", "Detail"], [
            ["Dimension", r.get("dimension_label", "")],
            ["Status", r.get("status", "")],
            ["Severity", r.get("severity", "")],
            ["Source section", r.get("source_section", "")],
            ["Source text", r.get("source_text", "")],
            ["Evidence required", ", ".join(map(str, r.get("evidence_required") or []))],
            ["Evidence", r.get("evidence", "")],
            ["Comment", r.get("comment", "")],
        ]))
        parts.append("")
    return "\n".join(parts).strip() or "No detailed criteria are available."



def _first_non_empty(*values: Any, default: str = "N/A") -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (list, tuple)) and value:
            return "; ".join(str(v) for v in value)
        if isinstance(value, dict) and value:
            return "; ".join(f"{k}: {v}" for k, v in value.items())
        if not isinstance(value, (str, list, tuple, dict)):
            return str(value)
    return default


def _skill_name(item: Any) -> str:
    if isinstance(item, dict):
        return _first_non_empty(
            item.get("skill"),
            item.get("name"),
            item.get("title"),
            item.get("label"),
        )
    return str(item)


def render_skill_assessment(ctx: dict[str, Any], session: Path) -> str:
    """Render section 12 from normalized data, never from free-form agent Markdown."""
    skill_profile = read_json(session / "intake" / "agent-skill-profile.json", {})
    skills = skill_profile.get("skills") or skill_profile.get("agent_skills") or skill_profile.get("domain_skills") or []

    skill_rows: list[list[Any]] = []
    if isinstance(skills, dict):
        skills = list(skills.values())
    if isinstance(skills, list):
        for item in skills:
            if isinstance(item, dict):
                skill_rows.append([
                    _skill_name(item),
                    _first_non_empty(item.get("review_focus"), item.get("review_lens"), item.get("description")),
                    _first_non_empty(item.get("evidence_checked"), item.get("evidence"), default="Derived from acceptance criteria evidence"),
                    _first_non_empty(item.get("evidence_missing"), item.get("missing_or_weak_evidence"), item.get("evidence_missing_weak"), default="See failed and partial criteria"),
                    _first_non_empty(item.get("influenced_dimensions"), item.get("influenced_criteria"), default="Functional, Technical"),
                    _first_non_empty(item.get("risk_notes"), item.get("risk"), default="See risk register"),
                ])
            else:
                skill_rows.append([
                    str(item),
                    "Acceptance criteria traceability",
                    "Derived from acceptance criteria evidence",
                    "See failed and partial criteria",
                    "Functional, Technical",
                    "See risk register",
                ])

    criteria_rows = [[
        r.get("id", ""),
        r.get("dimension_label", ""),
        r.get("criterion", ""),
        r.get("status", ""),
        r.get("evidence", ""),
    ] for r in ctx.get("criteria", [])]

    passed = sum(1 for r in ctx.get("criteria", []) if normalize_status(r.get("status")) == "passed")
    partial = sum(1 for r in ctx.get("criteria", []) if normalize_status(r.get("status")) == "partial")
    failed = sum(1 for r in ctx.get("criteria", []) if normalize_status(r.get("status")) == "failed")

    return (
        "### Skill Assessment Metadata\n\n"
        + table(["Field", "Value"], [
            ["Status", "reviewed"],
            ["Active specialist", ctx.get("reviewer_agent", "N/A")],
            ["Review timestamp", ctx.get("generated_at", "N/A")],
            ["Source profile", "intake/agent-skill-profile.json"],
        ])
        + "\n\n### Domain Skill Lenses\n\n"
        + (table(
            ["Skill", "Review focus", "Evidence checked", "Evidence missing/weak", "Influenced dimensions", "Risk notes"],
            skill_rows,
        ) if skill_rows else "No skill profile was generated.")
        + "\n\n### Criterion-Specific Skills\n\n"
        + (table(
            ["Criterion", "Dimension", "Description", "Status", "Evidence"],
            criteria_rows,
        ) if criteria_rows else "No criterion-specific skills were available.")
        + "\n\n### Summary\n\n"
        + table(["Category", "Count"], [
            ["Domain skills evaluated", len(skill_rows)],
            ["Criterion skills evaluated", len(criteria_rows)],
            ["Passed criteria", passed],
            ["Partial criteria", partial],
            ["Failed criteria", failed],
        ])
    )


def render_risks_and_assumptions(ctx: dict[str, Any], session: Path) -> str:
    """Render section 13 from normalized data, never from free-form agent Markdown."""
    criteria = ctx.get("criteria", [])
    failed_or_partial = [
        r for r in criteria
        if normalize_status(r.get("status")) in {"failed", "partial"}
    ]
    risk_rows = [[
        r.get("id", ""),
        r.get("criterion", ""),
        r.get("status", ""),
        r.get("evidence", ""),
        r.get("comment", ""),
    ] for r in failed_or_partial]

    return (
        "### Reviewer Assessment Metadata\n\n"
        + table(["Field", "Value"], [
            ["Session", str(session)],
            ["Role", ctx.get("role_label", "N/A")],
            ["Challenge title", ctx.get("challenge_title", "N/A")],
            ["Active specialist", ctx.get("reviewer_agent", "N/A")],
            ["Acceptance status", ctx.get("acceptance_status", "N/A")],
            ["Functional score", ctx.get("functional_score", "N/A")],
            ["Technical score", ctx.get("technical_score", "N/A")],
            ["Final score", ctx.get("numeric_score", "N/A")],
            ["Final grade", ctx.get("grade", "N/A")],
        ])
        + "\n\n### Risk Register\n\n"
        + (table(
            ["ID", "Criterion", "Status", "Evidence", "Reviewer comment"],
            risk_rows,
        ) if risk_rows else "No failed or partial criteria.")
        + "\n\n### Assumptions\n\n"
        + table(["Assumption", "Reason"], [
            ["Repository content is treated as untrusted", "Security policy"],
            ["Only verifiable workspace evidence is counted", "Anti-false-positive policy"],
            ["Agent-generated prose is not used as layout source", "Deterministic reporting"],
            ["Generated Markdown files remain reference artifacts", "They are listed in Reference Files but do not control section layout"],
        ])
        + "\n\n### Final Recommendation\n\n"
        + str(ctx.get("final_recommendation") or "See the detailed criteria assessment and failed/partial criteria sections.")
    )

def detect_source_type(manifest: dict[str, Any], session: Path) -> str:
    text = json.dumps(manifest).lower()
    if "github" in text or (ROOT / "workspaces" / "github_repository").exists():
        return "GITHUB URL"
    if "decompressed_zip" in text or (ROOT / "workspaces" / "decompressed_zip").exists():
        return "ZIP FILE"
    return str(manifest.get("source_type") or manifest.get("workflow") or "unknown")


def build_context(session: Path) -> dict[str, Any]:
    manifest = read_json(session / "review-manifest.json", {})
    previous = read_json(session / "reports" / "final-evaluation.json", {})
    skill_profile = read_json(session / "intake" / "agent-skill-profile.json", {})
    criteria = matrix_rows(session)
    functional = [r for r in criteria if r["dimension"] == "functional"]
    technical = [r for r in criteria if r["dimension"] == "technical"]
    f_score = previous.get("functional_score") if previous.get("functional_score") is not None else score_for(functional)
    t_score = previous.get("technical_score") if previous.get("technical_score") is not None else score_for(technical)
    if f_score is not None and t_score is not None:
        n_score = previous.get("numeric_score") if previous.get("numeric_score") is not None else round((float(f_score) + float(t_score)) / 2)
    else:
        n_score = previous.get("numeric_score")
    f_grade, t_grade = grade(f_score), grade(t_score)
    all_counts = counts(criteria)
    if all_counts["criteria"] == 0:
        acceptance = "pending"
    elif all_counts["failed"] == 0 and all_counts["partial"] == 0:
        acceptance = "complete_acceptance"
    elif all_counts["passed"] == 0:
        acceptance = "no_acceptance"
    else:
        acceptance = "partial_acceptance"
    source_type = previous.get("source_type") or detect_source_type(manifest, session)
    role_label = skill_profile.get("role_label") or manifest.get("role_label") or manifest.get("classification") or previous.get("role") or "N/A"
    challenge_title = skill_profile.get("challenge_title") or previous.get("challenge_title") or manifest.get("challenge_title") or manifest.get("classification") or "N/A"
    final_grade = previous.get("grade") or grade(n_score)
    if final_grade == "SENIOR" and (f_score is not None and t_score is not None) and (float(f_score) < 85 or float(t_score) < 85 or acceptance != "complete_acceptance"):
        final_grade = "INTERMEDIATE" if n_score is not None and n_score >= 60 else "JUNIOR"

    dimensions = {
        "functional": {**counts(functional), "score": f_score, "grade": f_grade},
        "technical": {**counts(technical), "score": t_score, "grade": t_grade},
        "overall": {**all_counts, "score": n_score, "grade": final_grade},
    }
    ctx = {
        "schema": str(SCHEMA_PATH.relative_to(ROOT)) if SCHEMA_PATH.exists() else "schemas/final-evaluation-unified.schema.json",
        "generated_at": now(),
        "orchestrator_version": VERSION,
        "workflow_status": previous.get("workflow_status") or manifest.get("status") or "reviewed",
        "acceptance_status": previous.get("acceptance_status") or acceptance,
        "numeric_score": n_score,
        "functional_score": f_score,
        "technical_score": t_score,
        "dimension_scores": {"functional": f_score, "technical": t_score},
        "dimension_grades": {"functional": f_grade, "technical": t_grade},
        "grade": final_grade,
        "attempt_number": str(previous.get("attempt_number") or manifest.get("attempt_number") or "0"),
        "employee_id": str(previous.get("employee_id") or manifest.get("employee_id") or "ABC-123"),
        "source_type": source_type,
        "source_workflow": previous.get("source_workflow") or manifest.get("workflow") or "review_challenge",
        "role": skill_profile.get("role") or manifest.get("classification") or "N/A",
        "role_label": role_label,
        "challenge_title": challenge_title,
        "reviewer_agent": manifest.get("reviewer_agent") or "universal-specialist",
        "dimensions": dimensions,
        "criteria": criteria,
        "evidence_summary": previous.get("evidence_summary") or {},
        "final_recommendation": previous.get("final_recommendation") or "See the detailed criteria assessment and failed/partial criteria sections.",
        "pdf_report": str(session / "reports" / "final-evaluation.pdf"),
    }
    return ctx


def compose_markdown(ctx: dict[str, Any], session: Path) -> str:
    template = read_text(TEMPLATE_PATH, "# Final Challenge Review Report\n\n{{ executive_summary }}\n")
    criteria = ctx["criteria"]
    functional = [r for r in criteria if r["dimension"] == "functional"]
    technical = [r for r in criteria if r["dimension"] == "technical"]
    dims = ctx["dimensions"]

    dimension_summary = table(["Dimension", "Criteria", "Passed", "Partial", "Failed", "Score", "Grade"], [
        ["Functional acceptance criteria", dims["functional"]["criteria"], dims["functional"]["passed"], dims["functional"]["partial"], dims["functional"]["failed"], ctx.get("functional_score"), ctx["dimension_grades"]["functional"]],
        ["Technical acceptance criteria", dims["technical"]["criteria"], dims["technical"]["passed"], dims["technical"]["partial"], dims["technical"]["failed"], ctx.get("technical_score"), ctx["dimension_grades"]["technical"]],
        ["Overall", dims["overall"]["criteria"], dims["overall"]["passed"], dims["overall"]["partial"], dims["overall"]["failed"], ctx.get("numeric_score"), ctx.get("grade")],
    ])

    inventory = read_json(session / "intake" / "workspace-inventory.json", [])
    intake_summary = table(["Property", "Value"], [
        ["Review session", str(session)],
        ["Source type", ctx.get("source_type")],
        ["Criteria source", read_json(session / "intake" / "file-base-extracted-criteria.json", {}).get("extraction", {}).get("source", "dynamic_file_base")],
        ["Workspace inventory count", len(inventory) if isinstance(inventory, list) else "N/A"],
        ["Criteria extraction", "intake/file-base-extracted-criteria.json"],
        ["Agent skill profile", "intake/agent-skill-profile.json"],
    ])

    sec_files = ["security/untrusted-content-validation.json", "security/prompt-injection-report.json", "security/sanitized-content-summary.json"]
    sec_rows = []
    for rel in sec_files:
        data = read_json(session / rel, {})
        status = data.get("status") or data.get("result") or ("present" if (session / rel).exists() else "not generated")
        findings = data.get("findings_count") or data.get("total_findings") or len(data.get("findings", [])) if isinstance(data, dict) else "N/A"
        sec_rows.append([rel, status, findings])
    security_summary = table(["Security artifact", "Status", "Findings"], sec_rows)

    skill_profile = read_json(session / "intake" / "agent-skill-profile.json", {})
    skills = skill_profile.get("skills") or skill_profile.get("agent_skills") or []
    skill_rows = []
    if isinstance(skills, list):
        for item in skills:
            if isinstance(item, dict):
                skill_rows.append([item.get("skill") or item.get("name") or str(item), item.get("description") or item.get("review_focus") or ""])
            else:
                skill_rows.append([str(item), ""])
    skill_summary = table(["Skill", "Description / Review focus"], skill_rows) if skill_rows else "No skill profile was generated."
    skill_summary += "\n\nSkill extraction artifacts: `skills/skill-extraction.md`, `skills/skill-extraction.html`, `skills/skill-extraction.pdf`."

    failed_partials = [r for r in criteria if normalize_status(r.get("status")) in {"failed", "partial"}]
    failed_partial_details = criteria_summary_table(failed_partials) if failed_partials else "No failed or partial criteria."
    evidence_log = table(["Criterion", "Evidence", "Status"], [[r["id"], r.get("evidence", ""), r.get("status", "")] for r in criteria])
    reference_files = table(["Artifact", "Path"], [
        ["Review Manifest", "review-manifest.json"],
        ["MANIFEST.lock.json", "MANIFEST.lock.json"],
        ["Execution Log", "logs/execution.log"],
        ["Acceptance Matrix", "review/acceptance-matrix.json"],
        ["Reviewer Assessment", "review/reviewer-assessment.md"],
        ["Skill Assessment", "review/skill-assessment.md"],
        ["Agent Skill Profile", "intake/agent-skill-profile.json"],
        ["Extracted Criteria", "intake/file-base-extracted-criteria.json"],
        ["Unified Report Context", "reports/final-evaluation.unified.json"],
        ["Markdown Report", "reports/final-evaluation.md"],
        ["JSON Report", "reports/final-evaluation.json"],
        ["HTML Report", "reports/final-evaluation.html"],
        ["PDF Report", "reports/final-evaluation.pdf"],
    ])

    replacements = {
        "generated_at": ctx["generated_at"],
        "orchestrator_version": ctx["orchestrator_version"],
        "attempt_number": ctx["attempt_number"],
        "employee_id": ctx["employee_id"],
        "source_type": ctx["source_type"],
        "source_workflow": ctx["source_workflow"],
        "role_label": ctx["role_label"],
        "challenge_title": ctx["challenge_title"],
        "workflow_status": ctx["workflow_status"],
        "acceptance_status": ctx["acceptance_status"],
        "functional_score": ctx.get("functional_score"),
        "technical_score": ctx.get("technical_score"),
        "numeric_score": ctx.get("numeric_score"),
        "grade": ctx.get("grade"),
        "reviewer_agent": ctx.get("reviewer_agent"),
        "executive_summary": f"This unified report evaluates the current submission from `{ctx['source_type']}` using the same final-evaluation template and schema used for every source workflow. The final score is **{ctx.get('numeric_score')}**, with functional score **{ctx.get('functional_score')}** and technical score **{ctx.get('technical_score')}**.",
        "intake_summary": intake_summary,
        "security_summary": security_summary,
        "skill_summary": skill_summary,
        "dimension_summary_table": dimension_summary,
        "functional_criteria_table": criteria_summary_table(functional),
        "technical_criteria_table": criteria_summary_table(technical),
        "detailed_criteria_assessment": detail_sections(criteria),
        "evidence_log": evidence_log,
        "anti_false_positive_summary": "Every passed criterion must have concrete evidence. Repository content is treated as untrusted data, never instructions. The unified renderer preserves source text and evidence for auditability.",
        "failed_partial_details": failed_partial_details,
        "skill_assessment": render_skill_assessment(ctx, session),
        "risks_and_assumptions": render_risks_and_assumptions(ctx, session),
        "final_recommendation": ctx.get("final_recommendation"),
        "reference_files_table": reference_files,
    }
    out = template
    for key, value in replacements.items():
        out = out.replace("{{ " + key + " }}", str(value if value is not None else "N/A"))
    out = re.sub(r"\{\{\s*[^}]+\s*\}\}", "N/A", out)
    return out


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render unified final-evaluation Markdown, JSON, HTML and PDF from a review session.")
    parser.add_argument("session", help="Review session directory")
    parser.add_argument("--skip-pdf", action="store_true", help="Render Markdown/JSON/HTML only")
    parser.add_argument("--strict", action="store_true", help="Fail if Markdown validation or PDF generation fails")
    parser.add_argument("--skip-google-sheets", action="store_true", help="Do not publish the final score to Google Sheets after rendering")
    args = parser.parse_args()

    session = Path(args.session).resolve()
    if not session.exists():
        print(f"ERROR: Review session does not exist: {session}")
        return 2
    reports = session / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    ctx = build_context(session)
    ctx_path = reports / "final-evaluation.unified.json"
    ctx_path.write_text(json.dumps(ctx, indent=2, ensure_ascii=False), encoding="utf-8")
    md = compose_markdown(ctx, session)
    md_path = reports / "final-evaluation.md"
    json_path = reports / "final-evaluation.json"
    html_path = reports / "final-evaluation.html"
    pdf_path = reports / "final-evaluation.pdf"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps(ctx, indent=2, ensure_ascii=False), encoding="utf-8")
    log = session / "logs" / "execution.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{now()} | report | unified final report rendered from single template/schema\n")

    validator = ROOT / "scripts" / "validate_markdown_report.py"
    if validator.exists():
        val = run([sys.executable, str(validator), str(md_path), "--strict"])
        with log.open("a", encoding="utf-8") as f:
            f.write(f"{now()} | report | markdown validation exit={val.returncode}\n")
            if val.stdout:
                f.write(val.stdout.rstrip() + "\n")
        if val.returncode != 0 and args.strict:
            print(val.stdout)
            return val.returncode

    generator = ROOT / "scripts" / "generate_final_pdf.py"
    if generator.exists():
        cmd = [sys.executable, str(generator), str(md_path), "--json-report", str(json_path), "--html-output", str(html_path), "--output", str(pdf_path), "--attempt-number", ctx["attempt_number"], "--employee-id", ctx["employee_id"]]
        if args.skip_pdf:
            cmd.append("--html-only")
        pdf = run(cmd)
        with log.open("a", encoding="utf-8") as f:
            f.write(f"{now()} | report | unified html/pdf generation exit={pdf.returncode}\n")
            if pdf.stdout:
                f.write(pdf.stdout.rstrip() + "\n")
        if pdf.returncode != 0 and args.strict and not args.skip_pdf:
            print(pdf.stdout)
            return pdf.returncode
    else:
        html_path.write_text("<html><body><pre>" + md.replace("&", "&amp;").replace("<", "&lt;") + "</pre></body></html>", encoding="utf-8")

    google_sheets_status = None
    if not args.skip_google_sheets:
        publisher = ROOT / "scripts" / "publish_review_to_google_sheets.py"
        if publisher.exists():
            publish = run([sys.executable, str(publisher), str(session)])
            google_sheets_status = {
                "returncode": publish.returncode,
                "status_path": str(session / "integrations" / "google-sheets-publish-status.json"),
            }
            with log.open("a", encoding="utf-8") as f:
                f.write(f"{now()} | integration | google sheets publish exit={publish.returncode}\n")
                if publish.stdout:
                    f.write(publish.stdout.rstrip() + "\n")
        else:
            google_sheets_status = {"returncode": 127, "error": "publisher script not found"}

    print(json.dumps({
        "status": "rendered",
        "renderer": "unified_final_evaluation",
        "version": VERSION,
        "session": str(session),
        "markdown_report": str(md_path),
        "json_report": str(json_path),
        "html_report": str(html_path),
        "pdf_report": str(pdf_path),
        "google_sheets_publish": google_sheets_status,
        "schema": str(SCHEMA_PATH),
        "template": str(TEMPLATE_PATH),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
