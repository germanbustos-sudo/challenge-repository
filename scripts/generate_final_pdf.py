#!/usr/bin/env python3
"""Render final-evaluation.md to HTML and export it to PDF.

Required workflow:
1. Generate final-evaluation.md.
2. Validate Markdown structure.
3. Render Markdown to final-evaluation.html with print-safe CSS.
4. Export HTML to final-evaluation.pdf with Playwright MCP/Chromium.

This renderer is designed for professional report output and intentionally does not create plain-text fallback PDFs: rendered tables,
clean page breaks, UTF-8/Unicode, consistent headings, formatted code blocks,
headers/footers, and print compatibility.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

VERSION = "0.8.7"


def _safe(text: object) -> str:
    value = "" if text is None else str(text)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)


def _inline_markdown_to_html(text: str) -> str:
    escaped = html.escape(_safe(text), quote=True)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def _split_table_row(line: str) -> list[str]:
    raw = line.strip().strip("|")
    return [cell.strip() for cell in raw.split("|")]


def _is_table_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*", line))


def _is_hr(line: str) -> bool:
    return bool(re.fullmatch(r"\s*(-{3,}|_{3,}|\*{3,})\s*", line))


def _validate_markdown(markdown_path: Path, strict: bool = False) -> list[str]:
    errors: list[str] = []
    text = markdown_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not text.strip():
        errors.append("Markdown report is empty.")
    if text.count("```") % 2 != 0:
        errors.append("Unclosed fenced code block detected.")
    for idx, line in enumerate(lines[:-1]):
        if line.strip().startswith("|") and _is_table_separator(lines[idx + 1]):
            header_cols = len(_split_table_row(line))
            separator_cols = len(_split_table_row(lines[idx + 1]))
            if header_cols != separator_cols:
                errors.append(f"Table column mismatch near line {idx + 1}.")
    if strict:
        required = ["Final Challenge Review Report", "Acceptance Matrix", "Evidence Log", "Final Recommendation"]
        lowered = text.lower()
        for section in required:
            if section.lower() not in lowered:
                errors.append(f"Missing required report section: {section}")
    return errors


def _normalize_row(row: list[str], count: int) -> list[str]:
    if len(row) < count:
        return row + [""] * (count - len(row))
    if len(row) > count:
        return row[: count - 1] + [" | ".join(row[count - 1 :])]
    return row


def _render_markdown_body(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    html_parts: list[str] = []
    paragraph: list[str] = []
    first_h1_skipped = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(p.strip() for p in paragraph if p.strip())
            if text:
                html_parts.append(f"<p>{_inline_markdown_to_html(text)}</p>")
            paragraph = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            language = stripped.strip("`").strip() or "text"
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            code = html.escape("\n".join(code_lines))
            html_parts.append(f'<figure class="code-block"><figcaption>{html.escape(language)}</figcaption><pre><code>{code}</code></pre></figure>')
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and _is_table_separator(lines[i + 1]):
            flush_paragraph()
            header = _split_table_row(stripped)
            col_count = len(header)
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_normalize_row(_split_table_row(lines[i]), col_count))
                i += 1
            thead = "".join(f"<th>{_inline_markdown_to_html(cell)}</th>" for cell in header)
            tbody_rows = []
            for row in rows:
                tbody_rows.append("<tr>" + "".join(f"<td>{_inline_markdown_to_html(cell)}</td>" for cell in row) + "</tr>")
            html_parts.append('<div class="table-wrap"><table><thead><tr>' + thead + "</tr></thead><tbody>" + "".join(tbody_rows) + "</tbody></table></div>")
            continue

        if re.match(r"^#{1,6}\s+", stripped):
            flush_paragraph()
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            if level == 1 and not first_h1_skipped and text.lower() == "final challenge review report":
                first_h1_skipped = True
                i += 1
                continue
            html_parts.append(f"<h{min(level, 6)}>{_inline_markdown_to_html(text)}</h{min(level, 6)}>")
            i += 1
            continue

        if _is_hr(stripped):
            flush_paragraph()
            html_parts.append('<hr class="section-break"/>')
            i += 1
            continue

        if stripped.startswith(('- ', '* ')):
            flush_paragraph()
            items = []
            while i < len(lines) and lines[i].strip().startswith(('- ', '* ')):
                items.append(lines[i].strip()[2:].strip())
                i += 1
            html_parts.append("<ul>" + "".join(f"<li>{_inline_markdown_to_html(item)}</li>" for item in items) + "</ul>")
            continue

        if re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            html_parts.append("<ol>" + "".join(f"<li>{_inline_markdown_to_html(item)}</li>" for item in items) + "</ol>")
            continue

        if not stripped:
            flush_paragraph()
            i += 1
            continue

        paragraph.append(line)
        i += 1

    flush_paragraph()
    return "\n".join(html_parts)


def _load_metadata(json_path: Path | None) -> dict[str, object]:
    if json_path and json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _metadata_table(metadata: dict[str, object], attempt_number: str, employee_id: str) -> str:
    rows: list[tuple[str, str]] = [
        ("Generated at", datetime.now().isoformat(timespec="seconds")),
        ("Orchestrator version", VERSION),
        ("Attempt number", attempt_number),
        ("Employee ID", employee_id),
    ]
    for key, label in [
        ("workflow_status", "Workflow status"),
        ("acceptance_status", "Acceptance status"),
        ("numeric_score", "Numeric score"),
        ("grade", "Grade"),
        ("challenge_type", "Challenge type"),
    ]:
        if key in metadata:
            rows.append((label, _safe(metadata.get(key))))
    body = "".join(f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>" for k, v in rows)
    return f'<table class="metadata"><tbody>{body}</tbody></table>'


def _build_html(markdown_path: Path, json_path: Path | None, attempt_number: str, employee_id: str) -> str:
    metadata = _load_metadata(json_path)
    body = _render_markdown_body(markdown_path.read_text(encoding="utf-8", errors="replace"))
    generated_at = datetime.now().isoformat(timespec="seconds")
    css = r"""
@page {
  size: Letter;
  margin: 18mm 14mm 18mm 14mm;
  @bottom-left { content: "Employee ID: " attr(data-employee) " | Attempt: " attr(data-attempt); }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); }
}
* { box-sizing: border-box; }
html { font-family: "Segoe UI", "DejaVu Sans", Arial, sans-serif; color: #111827; line-height: 1.45; font-size: 10.5pt; }
body { margin: 0; background: #fff; }
.report-page { max-width: 100%; }
.cover { border-bottom: 2px solid #111827; padding-bottom: 12px; margin-bottom: 18px; break-after: avoid; }
h1.title { font-size: 24pt; margin: 0 0 6px 0; letter-spacing: -0.02em; color: #111827; }
.subtitle { color: #4b5563; margin: 0; font-size: 9.5pt; }
h1, h2, h3, h4, h5, h6 { color: #111827; margin: 18px 0 8px 0; line-height: 1.2; break-after: avoid; page-break-after: avoid; }
h1 { font-size: 20pt; border-bottom: 1px solid #d1d5db; padding-bottom: 6px; }
h2 { font-size: 15pt; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }
h3 { font-size: 12pt; color: #374151; }
p { margin: 0 0 8px 0; orphans: 3; widows: 3; }
ul, ol { margin: 0 0 10px 22px; padding: 0; }
li { margin: 2px 0; }
a { color: #1d4ed8; text-decoration: none; }
code { font-family: "Cascadia Mono", "Consolas", "DejaVu Sans Mono", monospace; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 3px; padding: 0 3px; font-size: 9pt; }
.code-block { margin: 10px 0 14px 0; break-inside: avoid; page-break-inside: avoid; }
.code-block figcaption { background: #111827; color: #fff; padding: 5px 8px; border-radius: 6px 6px 0 0; font-size: 8.5pt; font-weight: 600; }
pre { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; background: #f9fafb; border: 1px solid #d1d5db; border-top: 0; padding: 9px; border-radius: 0 0 6px 6px; font-size: 8.5pt; line-height: 1.35; }
.table-wrap { width: 100%; margin: 10px 0 14px 0; break-inside: auto; page-break-inside: auto; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 8.5pt; }
thead { display: table-header-group; }
tfoot { display: table-footer-group; }
tr { break-inside: avoid; page-break-inside: avoid; }
th, td { border: 1px solid #d1d5db; padding: 6px 7px; vertical-align: top; overflow-wrap: anywhere; word-break: normal; }
th { background: #111827; color: #fff; font-weight: 700; }
tbody tr:nth-child(even) td { background: #f9fafb; }
.metadata { table-layout: auto; margin-top: 12px; font-size: 9.5pt; }
.metadata th { width: 34%; background: #f3f4f6; color: #111827; }
.metadata td { background: #fff; }
.section-break { border: 0; border-top: 1px solid #d1d5db; margin: 18px 0; }
@media print {
  body { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
  .avoid-break { break-inside: avoid; page-break-inside: avoid; }
}
"""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Final Challenge Review Report</title>
  <style>{css}</style>
</head>
<body data-employee="{html.escape(employee_id)}" data-attempt="{html.escape(attempt_number)}">
  <main class="report-page">
    <section class="cover avoid-break">
      <h1 class="title">Final Challenge Review Report</h1>
      <p class="subtitle">Generated at {html.escape(generated_at)} by OpenCode Challenge Orchestrator v{VERSION}</p>
      {_metadata_table(metadata, attempt_number, employee_id)}
    </section>
    {body}
  </main>
</body>
</html>
"""


def _run_playwright(html_path: Path, pdf_path: Path) -> None:
    script = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const page = await browser.newPage();
  await page.goto('file:///{html_path.as_posix().replace(':', '%3A')}', {{ waitUntil: 'networkidle' }});
  await page.pdf({{
    path: {json.dumps(str(pdf_path))},
    format: 'Letter',
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: false,
    margin: {{ top: '18mm', right: '14mm', bottom: '18mm', left: '14mm' }}
  }});
  await browser.close();
}})().catch(err => {{ console.error(err); process.exit(1); }});
"""
    subprocess.run(["node", "-e", script], check=True, cwd=str(html_path.parent), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)


def _run_python_playwright(html_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright  # type: ignore

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.pdf(path=str(pdf_path), format="Letter", print_background=True, prefer_css_page_size=True)
        browser.close()


def _run_chromium_cli(html_path: Path, pdf_path: Path) -> None:
    candidates = [
        os.environ.get("CHROMIUM_PATH"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("msedge"),
        shutil.which("chrome"),
    ]
    browser = next((c for c in candidates if c), None)
    if not browser:
        raise RuntimeError("No Chromium-compatible browser found. Configure Playwright MCP and install Chromium, or set CHROMIUM_PATH.")
    subprocess.run([
        browser,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-software-rasterizer",
        "--no-first-run",
        "--no-default-browser-check",
        f"--print-to-pdf={pdf_path}",
        "--print-to-pdf-no-header",
        html_path.as_uri(),
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)


def _export_pdf(html_path: Path, pdf_path: Path) -> str:
    errors: list[str] = []
    try:
        _run_python_playwright(html_path, pdf_path)
        return "python-playwright"
    except Exception as exc:
        errors.append(f"python-playwright: {exc}")
    try:
        _run_playwright(html_path, pdf_path)
        return "node-playwright"
    except Exception as exc:
        errors.append(f"node-playwright: {exc}")
    try:
        _run_chromium_cli(html_path, pdf_path)
        return "chromium-cli"
    except Exception as exc:
        errors.append(f"chromium-cli: {exc}")
    raise RuntimeError("PDF export failed. Playwright MCP/Chromium is required; no plain-text fallback PDF will be generated. " + " | ".join(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Markdown, render HTML, and export final-evaluation.pdf with Playwright MCP/Chromium.")
    parser.add_argument("markdown_report", help="Path to final-evaluation.md")
    parser.add_argument("--json-report", default=None, help="Optional path to final-evaluation.json")
    parser.add_argument("--html-output", default=None, help="Output HTML path. Defaults to final-evaluation.html")
    parser.add_argument("--output", default=None, help="Output PDF path. Defaults to final-evaluation.pdf")
    parser.add_argument("--attempt-number", default="0")
    parser.add_argument("--employee-id", default="ABC-123")
    parser.add_argument("--strict", action="store_true", help="Require standard report sections before HTML/PDF export")
    parser.add_argument("--html-only", action="store_true", help="Only render final-evaluation.html and skip PDF export")
    args = parser.parse_args(argv)

    md = Path(args.markdown_report).expanduser().resolve()
    if not md.exists() or not md.is_file():
        print(json.dumps({"status": "error", "error": f"Markdown report not found: {md}"}, indent=2))
        return 2
    js = Path(args.json_report).expanduser().resolve() if args.json_report else md.with_suffix(".json")
    html_out = Path(args.html_output).expanduser().resolve() if args.html_output else md.with_suffix(".html")
    pdf_out = Path(args.output).expanduser().resolve() if args.output else md.with_suffix(".pdf")
    html_out.parent.mkdir(parents=True, exist_ok=True)
    pdf_out.parent.mkdir(parents=True, exist_ok=True)

    errors = _validate_markdown(md, strict=args.strict)
    if errors:
        print(json.dumps({"status": "markdown_invalid", "markdown_report": str(md), "errors": errors}, indent=2))
        return 3

    html_doc = _build_html(md, js if js.exists() else None, args.attempt_number or "0", args.employee_id or "ABC-123")
    html_out.write_text(html_doc, encoding="utf-8")

    if args.html_only:
        print(json.dumps({
            "status": "html_generated",
            "markdown_report": str(md),
            "html_report": str(html_out),
            "pdf_generator_version": VERSION,
        }, indent=2))
        return 0

    try:
        renderer = _export_pdf(html_out, pdf_out)
    except Exception as exc:
        print(json.dumps({
            "status": "pdf_generation_failed",
            "markdown_report": str(md),
            "html_report": str(html_out),
            "pdf_report": str(pdf_out),
            "error": str(exc),
            "required_install": "Configure Playwright MCP in opencode.json and install runtime dependencies: `npm install`, `npx playwright install chromium`, then verify with `python scripts/check_playwright_mcp.py --runtime`.",
        }, indent=2))
        return 4

    print(json.dumps({
        "status": "pdf_generated",
        "renderer": renderer,
        "markdown_report": str(md),
        "html_report": str(html_out),
        "pdf_report": str(pdf_out),
        "attempt_number": args.attempt_number or "0",
        "employee_id": args.employee_id or "ABC-123",
        "pdf_generator_version": VERSION,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
