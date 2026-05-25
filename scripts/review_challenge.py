#!/usr/bin/env python3
"""Initialize a deterministic OpenCode challenge review session.

This helper supports the review pipeline phases:
1. intake: validate FILE_BASE and workspace data
2. review: initialize acceptance matrix and evidence requirements
3. report: initialize final Markdown/JSON report targets

It does not solve the challenge. It creates immutable traceability files for the
agents to complete: review-manifest.json, MANIFEST.lock.json, logs/execution.log,
review/acceptance-matrix.md, review/reviewer-assessment.md, and reports targets.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

VERSION = "0.8.7"

ERRORS = {
    "missing_path": "ERROR: Missing base challenge file path.",
    "empty_workspaces": "ERROR: Workspace files are required before starting the review process.",
    "unreadable_file": "ERROR: Base challenge file does not exist or cannot be read: {path}",
    "unclassified": "ERROR: Base challenge document could not be classified.",
    "review_session_failed": "ERROR: Review session could not be created.",
}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_text(path: Path) -> str:
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
    t = text.lower()
    scores = {
        "software_engineering": sum(k in t for k in ["software engineering", "spec-driven", "openapi", "rest api", "user stories", "gherkin"]),
        "qa_engineering": sum(k in t for k in ["qa engineering", "test case", "regression matrix", "manual test", "boundary value", "equivalence partitioning"]),
        "data_engineering": sum(k in t for k in ["data engineering", "etl", "pipeline", "star schema", "sql database", "pandas"]),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else None


def workspace_has_data(root: Path) -> bool:
    return root.exists() and root.is_dir() and any(root.iterdir())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_inventory(root: Path, limit: int = 5000) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    if not root.exists():
        return items
    for p in sorted(root.rglob("*")):
        if len(items) >= limit:
            break
        try:
            rel = p.relative_to(root).as_posix()
            if p.is_file():
                items.append({"path": rel, "type": "file", "size": p.stat().st_size, "sha256": sha256_file(p)})
            elif p.is_dir():
                items.append({"path": rel, "type": "directory"})
        except Exception:
            continue
    return items


def normalize_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[\s•●○\-*]+", "", line)
    line = re.sub(r"^\d+[\.)]\s*", "", line)
    return re.sub(r"\s+", " ", line).strip()


def split_candidate_items(block: str) -> list[str]:
    """Extract bullet-like criteria from a text block while preserving meaning."""
    # PDF extractors sometimes collapse bullets into one physical line. Normalize
    # common bullet markers into line boundaries before parsing.
    block = re.sub(r"\s+[•●○]\s+", "\n● ", block)
    block = re.sub(r"\s+-\s+", "\n- ", block)
    items: list[str] = []
    current: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line:
            if current:
                items.append(normalize_line(" ".join(current)))
                current = []
            continue
        is_bullet = bool(re.match(r"^(?:[•●○\-*]|\d+[\.)])\s+", line))
        is_table_row = line.startswith("|") and line.endswith("|")
        if is_table_row:
            cells = [normalize_line(c) for c in line.strip("|").split("|")]
            cells = [c for c in cells if c and not set(c) <= {"-", ":"}]
            if len(cells) >= 2 and cells[0].lower() not in {"functional acceptance criteria", "technical acceptance criteria"}:
                for cell in cells:
                    if len(cell) >= 12:
                        items.append(cell)
            continue
        if is_bullet:
            if current:
                items.append(normalize_line(" ".join(current)))
            current = [line]
        elif current:
            current.append(line)
    if current:
        items.append(normalize_line(" ".join(current)))
    filtered = []
    banned_prefixes = ("level skills required", "resources time", "document identifier", "revision history")
    for i in items:
        low = i.lower()
        if len(i) < 12 or low.startswith(banned_prefixes):
            continue
        filtered.append(i)
    return filtered


def extract_section(text: str, start_patterns: list[str], stop_patterns: list[str]) -> str:
    """Extract a plain-text section.

    This helper is intentionally conservative. Side-by-side acceptance criteria
    tables are handled by extract_side_by_side_acceptance_sections(), because
    PDF text extraction often collapses both column headers into one line.
    """
    lines = text.splitlines()
    start_idx: int | None = None
    for idx, line in enumerate(lines):
        lowered = re.sub(r"\s+", " ", line.lower()).strip()
        if any(p in lowered for p in start_patterns):
            # Avoid using the combined table header as a normal section start.
            if "functional acceptance criteria" in lowered and "technical acceptance criteria" in lowered:
                continue
            start_idx = idx + 1
            break
    if start_idx is None:
        return ""
    end_idx = len(lines)
    for idx in range(start_idx, len(lines)):
        lowered = re.sub(r"\s+", " ", lines[idx].lower()).strip()
        if any(p in lowered for p in stop_patterns):
            end_idx = idx
            break
    return "\n".join(lines[start_idx:end_idx])


TECHNICAL_START_PATTERNS = [
    # Software engineering
    "the spec is consistent", "code structure follows", "no extra features", "no \"extra features\"",
    "basic input validation", "the project has at least one", "the readme documents", "the repository has a clean commit",
    "commit history clearly", "tests follow arrange-act-assert", "no production code exists", "line coverage is at least",
    "at least two refactors", "no flaky", "spec documents exist before code", "a /prompts folder", "a planning file",
    "the codebase has a clear separation", "basic input validation", "each agent has a clear", "the handoff format",
    "tests written by", "the reviewer agent", "the comparison report uses", "the codebase keeps clean architecture",
    "prompts are stored", "tool schemas are strongly typed", "api keys", "model names", "environment-specific values",
    "an eval script", "retry/backoff", "the code separates", "clear separation of concerns",
    # QA engineering
    "each test case has", "equivalence partitioning", "a decision table", "priority and severity", "the regression matrix is sortable",
    "the test suite includes", "charters follow", "session sheets separate", "bug reports include", "findings are mapped",
    "ai assistance", "findings are prioritized", "authentication is handled", "json schema validations", "variables and secrets",
    "tests assert", "negative tests", "the collection is versioned", "selectors prefer", "waits use", "fixtures isolate",
    "secrets are read", "the ci job uploads",
    # Data engineering
    "the pipeline is idempotent", "connection strings", "logging captures", "data types in the db", "the repo includes a basic data dictionary",
    "unit tests cover", "indexes are added", "window functions", "query plans", "each table has", "naming conventions",
    "the report explains which model", "index creation is justified",
]


def looks_like_technical_start(item: str) -> bool:
    normalized = normalize_line(item).lower().strip(" -•●")
    normalized = re.sub(r"\s+", " ", normalized)
    return any(normalized.startswith(pattern) or pattern in normalized[:120] for pattern in TECHNICAL_START_PATTERNS)


def extract_side_by_side_acceptance_sections(text: str) -> tuple[str, str, dict[str, object]]:
    """Extract functional/technical criteria from collapsed two-column PDF text.

    Talent Bench challenge PDFs often contain a two-column table with the headers
    "Functional acceptance criteria" and "Technical acceptance criteria" on the
    same visual row. PDF extraction collapses the table into a linear stream. In
    that situation, the source-of-truth split is not keyword inference per item;
    instead we identify the combined header and split the following bullet list
    at the first technical-column criterion.
    """
    compact = re.sub(r"\s+", " ", text)
    header = re.search(r"Functional\s+acceptance\s+criteria\s+Technical\s+acceptance\s+criteria", compact, re.IGNORECASE)
    if not header:
        return "", "", {"side_by_side_detected": False}

    after = compact[header.end():]
    stop = re.search(
        r"(?:\bSW\s+Challenge\s+\d+|\bQA\s+Challenge\s+\d+|\bDE\s+Challenge\s+\d+|\bDocument\s+identifier\b|\bRevision\s+History\b)",
        after,
        re.IGNORECASE,
    )
    if stop:
        after = after[:stop.start()]

    items = split_candidate_items(after)
    split_idx: int | None = None
    for idx, item in enumerate(items):
        if looks_like_technical_start(item):
            split_idx = idx
            break

    if split_idx is None:
        # If the table was detected but the boundary was not, keep the old safe
        # behavior: do not guess section membership. The caller can use fallback.
        return "", "", {
            "side_by_side_detected": True,
            "side_by_side_split": "not_found",
            "side_by_side_items": len(items),
        }

    functional_items = items[:split_idx]
    technical_items = items[split_idx:]
    return "\n".join(f"● {item}" for item in functional_items), "\n".join(f"● {item}" for item in technical_items), {
        "side_by_side_detected": True,
        "side_by_side_split": "technical_start_pattern",
        "side_by_side_total_items": len(items),
        "side_by_side_functional_items": len(functional_items),
        "side_by_side_technical_items": len(technical_items),
        "technical_boundary": technical_items[0] if technical_items else None,
    }


def infer_severity(text: str, section: str) -> str:
    t = text.lower()
    if section in {"Functional acceptance criteria", "Technical acceptance criteria"}:
        return "blocker"
    if any(k in t for k in ["must", "required", "at least", "coverage", "readme", "tests", "test", "security", "ci", "schema", "openapi"]):
        return "blocker"
    if any(k in t for k in ["should", "explain", "document", "report"]):
        return "major"
    return "minor"


def infer_dimension(section: str, criterion: str) -> str:
    """Classify a criterion into the two required review dimensions."""
    section_l = section.lower()
    text = criterion.lower()
    if "technical" in section_l:
        return "technical"
    if "functional" in section_l:
        return "functional"
    technical_keywords = [
        "test", "coverage", "ci", "github actions", "architecture", "layer",
        "clean", "validation", "error handling", "schema", "openapi", "pydantic",
        "database", "index", "query plan", "explain", "idempotent", "logging",
        "environment variables", "security", "playwright", "page object", "pom",
        "parallel", "browser", "api keys", "tool schemas", "retry", "backoff",
        "commit history", "red-green-refactor", "refactor", "line coverage",
    ]
    functional_keywords = [
        "form", "admin", "user", "feature", "create", "edit", "delete",
        "mark", "captures", "shows", "opens", "accepted", "rejected", "in review",
        "charters", "session", "test plan", "defects", "regression matrix",
        "pipeline runs", "dataset", "star schema", "queries", "structured answer",
    ]
    if any(k in text for k in technical_keywords):
        return "technical"
    if any(k in text for k in functional_keywords):
        return "functional"
    # Deliverables and generic items are functional by default; engineering quality terms route technical.
    if section_l in {"deliverables", "acceptance criteria", "fallback_policy"}:
        return "functional"
    return "functional"


def evidence_requirements_for(kind: str, criterion: str) -> list[str]:
    t = criterion.lower()
    requirements = ["file_path", "content_reference"]
    if any(k in t for k in ["test", "coverage", "run", "execute", "ci", "pipeline", "command", "query", "explain analyze"]):
        requirements.append("command_output_or_execution_log")
    if any(k in t for k in ["line", "code", "api", "openapi", "schema", "model", "implementation", "playwright", "postman", "bruno", "etl", "sql"]):
        requirements.append("file_content_or_line_range")
    if kind == "software_engineering" and any(k in t for k in ["commit", "history", "red-green-refactor"]):
        requirements.append("git_history_evidence")
    return list(dict.fromkeys(requirements))


def fallback_criteria(kind: str) -> list[dict[str, object]]:
    common = ["Prompts-used Markdown file is included when required by the challenge."]
    if kind == "software_engineering":
        raw = [
            "Vision/specification documents exist and align with the challenge scope.",
            "Functional requirements or user stories include verifiable acceptance criteria.",
            "The implementation matches the documented specification without unrelated extra features.",
            "Tests or validation commands are included and can be executed.",
            "README explains how to run, test, and validate the solution.",
            *common,
        ]
    elif kind == "qa_engineering":
        raw = [
            "Test strategy or test plan is documented with scope, risks, environments, and criteria.",
            "Test artifacts satisfy the challenge-specific minimum quantity and coverage requirements.",
            "Execution evidence is included with pass/fail/blocked or equivalent results.",
            "Defects or findings are reported with reproducible evidence when applicable.",
            "README or equivalent instructions explain how to inspect or run the QA artifacts.",
            *common,
        ]
    else:
        raw = [
            "Data pipeline, SQL, or modeling artifacts required by the challenge are included.",
            "Source data, schemas, transformations, or query logic are documented.",
            "The work can be reproduced with documented commands or scripts.",
            "Validation, data quality checks, tests, or query results are included.",
            "README explains how to reproduce the data engineering work.",
            *common,
        ]
    return [
        {
            "criterion": c,
            "source_section": "fallback_policy",
            "source_text": c,
            "severity": infer_severity(c, "fallback_policy"),
            "dimension": infer_dimension("fallback_policy", c),
            "evidence_required": evidence_requirements_for(kind, c),
        }
        for c in raw
    ]


def extract_dynamic_criteria(text: str, kind: str) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Generate session acceptance criteria dynamically from FILE_BASE.

    FILE_BASE is the source of truth. Functional and technical acceptance
    criteria must remain in their original dimensions when the document provides
    those dimensions. Deliverables are used only as fallback when the document
    has no explicit acceptance-criteria sections.
    """
    sections: list[tuple[str, str]] = []
    extraction_notes: dict[str, object] = {}

    side_fac, side_tac, side_meta = extract_side_by_side_acceptance_sections(text)
    extraction_notes.update(side_meta)

    if side_fac or side_tac:
        if side_fac:
            sections.append(("Functional acceptance criteria", side_fac))
        if side_tac:
            sections.append(("Technical acceptance criteria", side_tac))
    else:
        fac = extract_section(text, ["functional acceptance criteria"], ["technical acceptance criteria", "sw challenge", "qa challenge", "de challenge", "document identifier"])
        tac = extract_section(text, ["technical acceptance criteria"], ["sw challenge", "qa challenge", "de challenge", "document identifier"])
        if fac:
            sections.append(("Functional acceptance criteria", fac))
        if tac:
            sections.append(("Technical acceptance criteria", tac))

    explicit = ""
    if not sections:
        explicit = extract_section(text, ["acceptance criteria"], ["deliverables", "technical acceptance criteria", "sw challenge", "qa challenge", "de challenge", "document identifier"])
        if explicit:
            sections.append(("Acceptance criteria", explicit))

    # Deliverables are not acceptance criteria when explicit functional/technical
    # criteria exist. Keeping deliverables in that case duplicates criteria and
    # can invert the dimensions, as seen in v0.7.2 reports.
    deliverables_used_as_fallback = False
    if not sections:
        deliverables = extract_section(text, ["deliverables"], ["functional acceptance criteria", "technical acceptance criteria", "sw challenge", "qa challenge", "de challenge", "document identifier"])
        if deliverables:
            sections.append(("Deliverables", deliverables))
            deliverables_used_as_fallback = True

    criteria: list[dict[str, object]] = []
    seen: set[str] = set()
    for section_name, block in sections:
        for item in split_candidate_items(block):
            key = re.sub(r"\W+", " ", item.lower()).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            dimension = infer_dimension(section_name, item)
            criteria.append({
                "criterion": item,
                "source_section": section_name,
                "source_text": item,
                "severity": infer_severity(item, section_name),
                "dimension": dimension,
                "evidence_required": evidence_requirements_for(kind, item),
            })

    source = "dynamic_file_base"
    if not criteria:
        criteria = fallback_criteria(kind)
        source = "fallback_review_policy"

    extraction = {
        "source": source,
        "criteria_count": len(criteria),
        "dimension_counts": {
            "functional": sum(1 for item in criteria if item.get("dimension") == "functional"),
            "technical": sum(1 for item in criteria if item.get("dimension") == "technical"),
        },
        "sections_detected": [name for name, _ in sections],
        "fallback_used": source == "fallback_review_policy",
        "deliverables_used_as_fallback": deliverables_used_as_fallback,
        "role_classification": kind,
        "review_dimensions": ["functional", "technical"],
        **extraction_notes,
    }
    return criteria, extraction



def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_simple_pdf(text: str, output: Path) -> None:
    """Create a minimal dependency-free PDF placeholder for final evaluation."""
    lines = []
    for raw in text.splitlines() or ["Final Challenge Review Report"]:
        raw = raw[:120]
        while len(raw) > 95:
            lines.append(raw[:95])
            raw = raw[95:]
        lines.append(raw)
    chunks = [lines[i:i + 52] for i in range(0, len(lines), 52)] or [["Final Challenge Review Report"]]
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    kids = []
    page_objects = []
    for idx, chunk in enumerate(chunks):
        content_obj = 3 + idx * 2
        page_obj = 4 + idx * 2
        kids.append(f"{page_obj} 0 R")
        cmds = ["BT", "/F1 10 Tf", "50 792 Td", "14 TL"]
        first = True
        for line in chunk:
            if not first:
                cmds.append("T*")
            first = False
            cmds.append(f"({pdf_escape(line)}) Tj")
        cmds.append("ET")
        stream = "\n".join(cmds).encode("latin-1", errors="replace")
        page_objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
        page_objects.append((f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {content_obj} 0 R >>").encode())
    objects.append(f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(chunks)} >>".encode())
    objects.extend(page_objects)
    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{i} 0 obj\n".encode())
        data.extend(obj)
        data.extend(b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects)+1}\n".encode())
    data.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        data.extend(f"{off:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    output.write_bytes(bytes(data))

def create_review_session(base_file: Path, kind: str, workspaces_root: Path, sessions_root: Path, attempt_number: str = "0", employee_id: str = "ABC-123") -> Path:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", base_file.stem).strip("-").lower()[:25]
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = sessions_root / f"{kind.replace('_','-')}-{slug}-{ts}"

    for directory in ["input", "intake", "review", "reports", "logs"]:
        (root / directory).mkdir(parents=True, exist_ok=True)

    base_copy_name = f"base-challenge{base_file.suffix.lower() or '.txt'}"
    base_copy_path = root / "input" / base_copy_name
    shutil.copy2(base_file, base_copy_path)

    policy_path = Path.cwd() / "config" / "review-policy.yaml"
    base_text = read_text(base_file)
    criteria, extraction = extract_dynamic_criteria(base_text, kind)
    inventory = file_inventory(workspaces_root)
    strict_review = True

    dimension_counters = {"functional": 0, "technical": 0}
    matrix_rows = []
    for item in criteria:
        dimension = str(item.get("dimension") or infer_dimension(str(item.get("source_section", "FILE_BASE")), str(item["criterion"])))
        if dimension not in dimension_counters:
            dimension = "functional"
        dimension_counters[dimension] += 1
        prefix = "FAC" if dimension == "functional" else "TAC"
        matrix_rows.append({
            "criterion_id": f"{prefix}-{dimension_counters[dimension]:03d}",
            "dimension": dimension,
            "dimension_label": "Functional acceptance criteria" if dimension == "functional" else "Technical acceptance criteria",
            "criterion": str(item["criterion"]),
            "status": "failed",
            "severity": str(item.get("severity", "blocker")),
            "evidence": "PENDING: reviewer must provide concrete evidence before marking passed or partial.",
            "comment": "Pending reviewer assessment.",
            "source_section": item.get("source_section", "FILE_BASE"),
            "source_text": item.get("source_text", item["criterion"]),
            "evidence_required": item.get("evidence_required", ["file_path", "content_reference"]),
        })

    dimensions_payload = {
        "functional": {
            "label": "Functional acceptance criteria",
            "score": None,
            "grade": "N/A",
            "criteria_count": sum(1 for row in matrix_rows if row["dimension"] == "functional"),
            "passed": 0,
            "partial": 0,
            "failed": sum(1 for row in matrix_rows if row["dimension"] == "functional"),
        },
        "technical": {
            "label": "Technical acceptance criteria",
            "score": None,
            "grade": "N/A",
            "criteria_count": sum(1 for row in matrix_rows if row["dimension"] == "technical"),
            "passed": 0,
            "partial": 0,
            "failed": sum(1 for row in matrix_rows if row["dimension"] == "technical"),
        },
    }
    matrix_payload = {
        "schema_version": "2.0",
        "review_dimensions": ["functional", "technical"],
        "dimension_scoring": {
            "functional_weight": 0.5,
            "technical_weight": 0.5,
            "final_score_formula": "round(functional_score * 0.5 + technical_score * 0.5)",
            "grade_thresholds": {"JUNIOR": "0-59", "INTERMEDIATE": "60-84", "SENIOR": "85-100"},
            "senior_requires": ["functional_score >= 85", "technical_score >= 85", "complete_acceptance", "strict_review_pass"],
        },
        "dimensions": dimensions_payload,
        "criteria": matrix_rows,
    }

    matrix_md = ["# Acceptance Matrix", "", "## Functional Acceptance Criteria", "", "| ID | Criterion | Status | Severity | Evidence | Comment |", "|---|---|---|---|---|---|"]
    for row in [r for r in matrix_rows if r["dimension"] == "functional"]:
        matrix_md.append(f"| {row['criterion_id']} | {row['criterion']} | {row['status']} | {row['severity']} | {row['evidence']} | {row['comment']} |")
    matrix_md.extend(["", "## Technical Acceptance Criteria", "", "| ID | Criterion | Status | Severity | Evidence | Comment |", "|---|---|---|---|---|---|"])
    for row in [r for r in matrix_rows if r["dimension"] == "technical"]:
        matrix_md.append(f"| {row['criterion_id']} | {row['criterion']} | {row['status']} | {row['severity']} | {row['evidence']} | {row['comment']} |")
    (root / "review" / "acceptance-matrix.md").write_text("\n".join(matrix_md) + "\n", encoding="utf-8")
    (root / "review" / "acceptance-matrix.json").write_text(json.dumps(matrix_payload, indent=2), encoding="utf-8")
    (root / "intake" / "file-base-extracted-criteria.json").write_text(json.dumps({"extraction": extraction, "criteria": criteria}, indent=2), encoding="utf-8")

    manifest = {
        "orchestrator_version": VERSION,
        "workflow": "review_challenge",
        "phases": ["intake", "review", "report"],
        "base_file": str(base_file),
        "base_file_sha256": sha256_file(base_file),
        "base_file_copy": str(base_copy_path),
        "classification": kind,
        "criteria_source": extraction["source"],
        "dynamic_criteria_count": extraction["criteria_count"],
        "dimension_counts": extraction.get("dimension_counts", {"functional": 0, "technical": 0}),
        "review_dimensions": ["functional", "technical"],
        "criteria_extraction": str(root / "intake" / "file-base-extracted-criteria.json"),
        "created_at": now(),
        "review_session": str(root),
        "workspaces_root": str(workspaces_root),
        "policy_file": str(policy_path),
        "policy_role": kind,
        "file_base_is_source_of_truth": True,
        "strict_review": strict_review,
        "require_evidence_per_criterion": True,
        "anti_false_positive_validation": "Criteria without concrete evidence must remain failed or partial; they cannot be marked passed.",
        "reviewer_agent": "universal-specialist",
        "legacy_reviewer_agent": "challenge-reviewer",
        "reporter_agent": "challenge-reporter",
        "grading_levels": ["JUNIOR", "INTERMEDIATE", "SENIOR"],
        "attempt_number": attempt_number,
        "employee_id": employee_id,
        "numeric_score": None,
        "functional_score": None,
        "technical_score": None,
        "dimension_scores": {"functional": None, "technical": None},
        "score_range": {"min": 0, "max": 100},
        "acceptance_statuses": ["complete_acceptance", "partial_acceptance", "no_acceptance"],
        "status": "initialized",
        "acceptance_status": "pending",
        "grade": "N/A",
        "acceptance_matrix": str(root / "review" / "acceptance-matrix.json"),
        "final_report_markdown": str(root / "reports" / "final-evaluation.md"),
        "final_report_json": str(root / "reports" / "final-evaluation.json"),
        "final_report_html": str(root / "reports" / "final-evaluation.html"),
        "final_report_pdf": str(root / "reports" / "final-evaluation.pdf"),
    }
    (root / "review-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lock = {
        "lock_version": 1,
        "created_at": now(),
        "orchestrator_version": VERSION,
        "workflow": "review_challenge",
        "base_file": {"path": str(base_file), "sha256": sha256_file(base_file)},
        "attempt_number": attempt_number,
        "employee_id": employee_id,
        "workspace_inventory_count": len(inventory),
        "workspace_inventory": inventory,
        "policy_file": str(policy_path),
        "criteria_source": extraction["source"],
        "criteria_extraction_sha256": sha256_file(root / "intake" / "file-base-extracted-criteria.json"),
        "commands": {"review": "universal-specialist", "legacy_review": "challenge-reviewer", "report": "challenge-reporter"},
    }
    (root / "MANIFEST.lock.json").write_text(json.dumps(lock, indent=2), encoding="utf-8")
    (root / "intake" / "workspace-inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    (root / "logs" / "execution.log").write_text(f"{now()} | intake | initialized review session\n", encoding="utf-8")
    (root / "review" / "reviewer-assessment.md").write_text("# Reviewer Assessment\n\nStatus: pending OpenCode agent execution.\n", encoding="utf-8")
    final_md = f"# Final Challenge Review Report\n\nStatus: pending OpenCode agent execution.\n\nAttempt number: {attempt_number}\n\nEmployee ID: {employee_id}\n"
    final_json = {
        "status": "pending",
        "attempt_number": attempt_number,
        "employee_id": employee_id,
        "review_dimensions": ["functional", "technical"],
        "dimension_scores": {"functional": None, "technical": None},
        "functional_score": None,
        "technical_score": None,
        "html_report": str(root / "reports" / "final-evaluation.html"),
        "pdf_report": str(root / "reports" / "final-evaluation.pdf")
    }
    final_md_path = root / "reports" / "final-evaluation.md"
    final_json_path = root / "reports" / "final-evaluation.json"
    final_html_path = root / "reports" / "final-evaluation.html"
    final_pdf_path = root / "reports" / "final-evaluation.pdf"
    final_md_path.write_text(final_md, encoding="utf-8")
    final_json_path.write_text(json.dumps(final_json, indent=2), encoding="utf-8")

    generator = Path.cwd() / "scripts" / "generate_final_pdf.py"
    browsers_env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    browsers_path = Path(browsers_env) if browsers_env else None
    pdf_runtime_available = (Path.cwd() / "node_modules" / "playwright").exists() or bool(browsers_path and browsers_path.exists()) or os.environ.get("FORCE_FINAL_PDF") == "1"
    if generator.exists() and pdf_runtime_available:
        try:
            pdf_result = subprocess.run(
                [
                    sys.executable,
                    str(generator),
                    str(final_md_path),
                    "--json-report",
                    str(final_json_path),
                    "--html-output",
                    str(final_html_path),
                    "--output",
                    str(final_pdf_path),
                    "--attempt-number",
                    attempt_number,
                    "--employee-id",
                    employee_id,
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=45,
            )
        except subprocess.TimeoutExpired as exc:
            pdf_result = subprocess.CompletedProcess(args=exc.cmd, returncode=124, stdout="PDF generation timed out while waiting for Playwright/Chromium runtime. Run /setup_opencode_environment before generating PDF reports.")
        with (root / "logs" / "execution.log").open("a", encoding="utf-8") as log:
            log.write(f"{now()} | report | initial pdf generation exit={pdf_result.returncode}\n")
            if pdf_result.stdout:
                log.write(pdf_result.stdout.rstrip() + "\n")
        pdf_status = {
            "status": "pdf_generated" if pdf_result.returncode == 0 and final_pdf_path.exists() else "pdf_generation_pending_or_failed",
            "exit_code": pdf_result.returncode,
            "markdown_report": str(final_md_path),
            "html_report": str(final_html_path),
            "pdf_report": str(final_pdf_path),
            "renderer_policy": "HTML_TO_PDF_WITH_PLAYWRIGHT_MCP_OR_CHROMIUM_ONLY",
            "note": "The HTML artifact is preserved even when PDF generation fails. No plain-text fallback PDF is created."
        }
        (root / "reports" / "pdf-generation-status.json").write_text(json.dumps(pdf_status, indent=2), encoding="utf-8")
    else:
        reason = "PDF generator script not found" if not generator.exists() else "Playwright/Chromium runtime is not installed. Run /setup_opencode_environment or use the Docker setup."
        (root / "logs" / "execution.log").open("a", encoding="utf-8").write(f"{now()} | report | {reason}\n")
        (root / "reports" / "pdf-generation-status.json").write_text(json.dumps({
            "status": "pdf_generation_pending_runtime" if generator.exists() else "pdf_generation_failed",
            "error": reason,
            "markdown_report": str(final_md_path),
            "html_report": str(final_html_path),
            "pdf_report": str(final_pdf_path),
            "renderer_policy": "HTML_TO_PDF_WITH_PLAYWRIGHT_MCP_OR_CHROMIUM_ONLY"
        }, indent=2), encoding="utf-8")

    skill_extractor = Path.cwd() / "scripts" / "extract_agent_skill_profile.py"
    if skill_extractor.exists():
        try:
            skill_result = subprocess.run(
                [sys.executable, str(skill_extractor), str(base_file), "--session", str(root), "--role", kind],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            skill_result = subprocess.CompletedProcess(args=exc.cmd, returncode=124, stdout="Skill extraction timed out.")
        with (root / "logs" / "execution.log").open("a", encoding="utf-8") as log:
            log.write(f"{now()} | skill-extraction | exit={skill_result.returncode}\n")
            if skill_result.stdout:
                log.write(skill_result.stdout.rstrip() + "\n")
        try:
            manifest_update = json.loads((root / "review-manifest.json").read_text(encoding="utf-8"))
            manifest_update["agent_skill_profile"] = str(root / "intake" / "agent-skill-profile.json")
            manifest_update["skill_extraction_report_markdown"] = str(root / "skills" / "skill-extraction.md")
            manifest_update["skill_extraction_report_html"] = str(root / "skills" / "skill-extraction.html")
            manifest_update["skill_extraction_report_pdf"] = str(root / "skills" / "skill-extraction.pdf")
            manifest_update["reviewer_agent"] = "universal-specialist"
            manifest_update["legacy_reviewer_agent"] = "challenge-reviewer"
            (root / "review-manifest.json").write_text(json.dumps(manifest_update, indent=2), encoding="utf-8")
        except Exception as exc:
            with (root / "logs" / "execution.log").open("a", encoding="utf-8") as log:
                log.write(f"{now()} | skill-extraction | manifest update failed: {exc}\n")
    else:
        with (root / "logs" / "execution.log").open("a", encoding="utf-8") as log:
            log.write(f"{now()} | skill-extraction | extractor script not found\n")
    return root


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print(ERRORS["missing_path"])
        return 2
    base_file = Path(sys.argv[1]).expanduser().resolve()
    attempt_number = sys.argv[2].strip() if len(sys.argv) >= 3 and sys.argv[2].strip() else "0"
    employee_id = sys.argv[3].strip() if len(sys.argv) >= 4 and sys.argv[3].strip() else "ABC-123"
    if not base_file.exists() or not base_file.is_file():
        print(ERRORS["unreadable_file"].format(path=base_file))
        return 2
    workspaces_root = Path.cwd() / "workspaces"
    if not workspace_has_data(workspaces_root):
        print(ERRORS["empty_workspaces"])
        return 6
    text = read_text(base_file)
    kind = classify(f"{text}\n{base_file.name}")
    if not kind:
        print(ERRORS["unclassified"])
        return 3
    try:
        session = create_review_session(base_file, kind, workspaces_root, Path.cwd() / "review-sessions", attempt_number, employee_id)
    except Exception as exc:
        print(f"{ERRORS['review_session_failed']} {exc}")
        return 5
    print(json.dumps({
        "status": "initialized",
        "workflow": "review_challenge",
        "orchestrator_version": VERSION,
        "phases": ["intake", "review", "report"],
        "classification": kind,
        "criteria_source": "dynamic_file_base",
        "criteria_extraction": str(session / "intake" / "file-base-extracted-criteria.json"),
        "review_dimensions": ["functional", "technical"],
        "reviewer_agent": "universal-specialist",
        "legacy_reviewer_agent": "challenge-reviewer",
        "reporter_agent": "challenge-reporter",
        "review_session": str(session),
        "workspaces_root": str(workspaces_root),
        "acceptance_matrix": str(session / "review" / "acceptance-matrix.json"),
        "manifest_lock": str(session / "MANIFEST.lock.json"),
        "execution_log": str(session / "logs" / "execution.log"),
        "final_report_html": str(session / "reports" / "final-evaluation.html"),
        "final_report_pdf": str(session / "reports" / "final-evaluation.pdf"),
        "agent_skill_profile": str(session / "intake" / "agent-skill-profile.json"),
        "skill_extraction_report_markdown": str(session / "skills" / "skill-extraction.md"),
        "skill_extraction_report_html": str(session / "skills" / "skill-extraction.html"),
        "skill_extraction_report_pdf": str(session / "skills" / "skill-extraction.pdf"),
        "attempt_number": attempt_number,
        "employee_id": employee_id,
        "strict_review": True,
        "report_required_for": ["complete_acceptance", "partial_acceptance", "no_acceptance"],
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
