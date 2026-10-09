"""Check that DSH submission end-matter package exists and contains required statements."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/dsh_submission_endmatter_package.md"
CHECKLIST = ROOT / "metadata/dsh_submission_compliance_checklist.csv"
OUT = ROOT / "metadata/dsh_submission_endmatter_check_summary.csv"
REPORT = ROOT / "logs/dsh_submission_endmatter_check_report.md"

REQUIRED_PHRASES = [
    "Data availability",
    "AI Disclosure Statement",
    "Funding",
    "Conflict of interest",
    "Ethics statement",
    "Figure accessibility and alt text",
    "semantic-fidelity review",
    "single-review",
    "GitHub/Codex-style code assistance",
    "All AI-assisted text, code, tables, figures, and references were reviewed and approved",
]

CHECKLIST_REQUIRED = [
    "Data availability statement",
    "AI Disclosure Statement",
    "Funding statement",
    "Conflict of interest statement",
    "Figure alt text",
    "Bootstrap confidence intervals",
    "Semantic-fidelity limitation",
    "Groq heterogeneity limitation",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    errors: list[str] = []
    for path in [DOC, CHECKLIST]:
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT)}")
        elif path.stat().st_size == 0:
            errors.append(f"empty {path.relative_to(ROOT)}")
    if errors:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("# DSH Submission End-Matter Check Report\n\nFAIL\n\n" + "\n".join(f"- {e}" for e in errors) + "\n", encoding="utf-8")
        print("FAIL: missing required files")
        return 1

    text = DOC.read_text(encoding="utf-8")
    checklist = read_csv(CHECKLIST)
    checklist_items = {r["item"] for r in checklist}

    missing_phrases = [p for p in REQUIRED_PHRASES if p not in text]
    missing_items = [p for p in CHECKLIST_REQUIRED if p not in checklist_items]
    if missing_phrases:
        errors.extend([f"end-matter package missing phrase: {p}" for p in missing_phrases])
    if missing_items:
        errors.extend([f"checklist missing item: {p}" for p in missing_items])

    drafted = sum(1 for r in checklist if r.get("current_status") in {"drafted", "available"})
    not_done = sum(1 for r in checklist if r.get("current_status") == "not_done")
    planned = sum(1 for r in checklist if r.get("current_status") == "planned")

    rows = [{
        "required_phrases_checked": len(REQUIRED_PHRASES),
        "missing_required_phrases": len(missing_phrases),
        "checklist_items": len(checklist),
        "drafted_or_available_items": drafted,
        "planned_items": planned,
        "not_done_items": not_done,
        "status": "PASS" if not errors else "FAIL",
    }]
    write_csv(OUT, rows, list(rows[0].keys()))

    lines = [
        "# DSH Submission End-Matter Check Report",
        "",
        f"- required phrases checked: {len(REQUIRED_PHRASES)}",
        f"- missing required phrases: {len(missing_phrases)}",
        f"- checklist items: {len(checklist)}",
        f"- drafted or available items: {drafted}",
        f"- planned items: {planned}",
        f"- not-done items: {not_done}",
        "",
    ]
    if errors:
        lines += ["## Errors", ""] + [f"- {e}" for e in errors]
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("FAIL: DSH submission end-matter checker found errors")
        return 1
    lines += [
        "## Final verdict",
        "",
        "PASS: DSH submission end-matter package contains the required data availability, AI disclosure, ethics, funding, conflict, accessibility, and limitation language. Remaining not-done items are expected pre-submission tasks such as DOI archival and final copyright verification.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS: DSH submission end-matter checker passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
