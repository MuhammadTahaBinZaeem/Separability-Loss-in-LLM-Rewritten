"""Validate the Methods/Results writing blueprint and checklist.

This checker does not validate the final manuscript. It validates that the repo
contains a complete enough drafting blueprint to prevent the paper from becoming
an essay-style narrative without equations, figures, tables, or validity checks.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/methods_results_writing_blueprint.md"
CHECKLIST = ROOT / "metadata/methods_results_blueprint_checklist.csv"
OUT = ROOT / "metadata/methods_results_blueprint_check_summary.csv"
REPORT = ROOT / "logs/methods_results_blueprint_check_report.md"

# Human-facing phrases are checked case-insensitively so wording such as
# "Twelve works" does not fail only because the checklist says "twelve works".
# Exact mathematical equation markers are still checked separately below.
REQUIRED_PHRASES = [
    "LLM rewriting changes the evidentiary status of literary texts",
    "six authors",
    "twelve works",
    "360 unique passages",
    "1,440 modeling rows",
    "non-US copyright status is jurisdiction-dependent",
    "feature vector",
    "train-on-original, test-on-rewrite",
    "MacroF1",
    "\\Delta \\mathrm{F1}_{c}",
    "paired passage-level bootstrap",
    "5,000 bootstrap replicates",
    "semantic-fidelity audit",
    "structured single-review audit",
    "semantic-risk sensitivity",
    "strict semantic-risk filter",
    "Llama-modernize reversal",
    "Table 1",
    "Figure 1",
    "Do not overclaim",
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
    if not DOC.exists(): errors.append(f"missing {DOC.relative_to(ROOT)}")
    if not CHECKLIST.exists(): errors.append(f"missing {CHECKLIST.relative_to(ROOT)}")
    if errors:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("# Methods/Results Blueprint Check Report\n\nFAIL\n\n" + "\n".join(f"- {e}" for e in errors) + "\n", encoding="utf-8")
        return 1

    text = DOC.read_text(encoding="utf-8")
    text_lower = text.lower()
    checklist = read_csv(CHECKLIST)
    missing_phrases = [p for p in REQUIRED_PHRASES if p.lower() not in text_lower]
    if missing_phrases:
        errors.extend([f"blueprint missing phrase: {p}" for p in missing_phrases])

    if len(checklist) < 20:
        errors.append(f"expected at least 20 checklist items, found {len(checklist)}")
    required_items = [r for r in checklist if r.get("status") == "required"]
    if len(required_items) != len(checklist):
        errors.append("all checklist items should be marked required")

    sections = {r.get("section") for r in checklist}
    for section in ["Methods", "Results", "Figures", "Writing"]:
        if section not in sections:
            errors.append(f"checklist missing section category: {section}")

    equation_markers = ["\\mathbf{x}_{i,c}", "\\mathcal{D}_{train}", "\\mathrm{MacroF1}", "\\Delta \\mathrm{F1}_{c}", "\\Delta \\mathrm{F1}_{c,strict}"]
    missing_equations = [e for e in equation_markers if e not in text]
    if missing_equations:
        errors.extend([f"missing equation marker: {e}" for e in missing_equations])

    summary = [{
        "required_phrases": len(REQUIRED_PHRASES),
        "missing_required_phrases": len(missing_phrases),
        "checklist_items": len(checklist),
        "equation_markers_checked": len(equation_markers),
        "missing_equation_markers": len(missing_equations),
        "status": "PASS" if not errors else "FAIL",
    }]
    write_csv(OUT, summary, list(summary[0].keys()))

    lines = [
        "# Methods/Results Blueprint Check Report",
        "",
        f"- required phrases checked: {len(REQUIRED_PHRASES)}",
        f"- missing required phrases: {len(missing_phrases)}",
        f"- checklist items: {len(checklist)}",
        f"- equation markers checked: {len(equation_markers)}",
        f"- missing equation markers: {len(missing_equations)}",
        "",
    ]
    if errors:
        lines += ["## Errors", ""] + [f"- {e}" for e in errors]
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("FAIL: Methods/Results blueprint checker found errors")
        for e in errors[:20]: print("- " + e)
        return 1
    lines += ["## Final verdict", "", "PASS: Methods/Results writing blueprint is complete enough for manuscript drafting discipline."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS: Methods/Results blueprint checker passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
