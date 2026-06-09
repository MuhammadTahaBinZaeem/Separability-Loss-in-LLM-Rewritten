"""Validate the DSH manuscript skeleton.

This checker ensures that the skeleton contains the required DSH-style paper
structure, equation slots, table/figure callouts, and caution language before
full prose drafting begins.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKELETON = ROOT / "paper/manuscript_dsh_skeleton.md"
META = ROOT / "metadata"
LOGS = ROOT / "logs"
CHECK_SUMMARY = META / "manuscript_skeleton_check_summary.csv"
CHECK_REPORT = LOGS / "manuscript_skeleton_check_report.md"

REQUIRED_PHRASES = [
    "Digital Scholarship in the Humanities-style",
    "six authors",
    "twelve works",
    "360 source passages",
    "1440 text-condition rows",
    "Macro-F1",
    "passage-level paired bootstrap",
    "semantic-fidelity audit",
    "semantic-risk sensitivity analysis",
    "Groq free-model replication",
    "single-review audit",
    "not independent double annotation",
    "non-US copyright status is jurisdiction-dependent",
    "Llama-modernize reversal",
    "model/condition heterogeneity",
    "AI Disclosure Statement",
    "Data availability",
    "Code availability",
]

REQUIRED_SECTIONS = [
    "## Abstract",
    "## 1. Introduction",
    "## 2. Related work",
    "## 3. Materials and methods",
    "## 4. Results",
    "## 5. Discussion",
    "## 6. Limitations",
    "## 7. Conclusion",
    "## Declarations and end matter",
    "## Tables and figures",
]

REQUIRED_EQUATION_MARKERS = [
    "\\mathbf{x}_i =",
    "\\mathcal{D}_{train}=",
    "\\mathcal{D}_{eval}(c,s)=",
    "\\mathrm{MacroF1}=",
    "\\Delta \\mathrm{F1}_{m,c,s}=",
    "CI_{95\\%}(\\Delta \\mathrm{F1})",
    "\\Delta \\mathrm{F1}_{m,c,s}^{strict}=",
]

REQUIRED_TABLES_FIGURES = [
    "Table 1",
    "Table 2",
    "Table 3",
    "Table 4",
    "Figure 1",
    "Figure 2",
    "Table S1",
    "Table S2",
    "Table S3",
    "Table S4",
    "Table S5",
]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    errors: list[str] = []
    if not SKELETON.exists():
        errors.append(f"missing {SKELETON.relative_to(ROOT)}")
        text = ""
    else:
        text = SKELETON.read_text(encoding="utf-8")
    text_lower = text.lower()

    missing_phrases = [p for p in REQUIRED_PHRASES if p.lower() not in text_lower]
    missing_sections = [s for s in REQUIRED_SECTIONS if s.lower() not in text_lower]
    missing_equations = [e for e in REQUIRED_EQUATION_MARKERS if e not in text]
    missing_tf = [x for x in REQUIRED_TABLES_FIGURES if x.lower() not in text_lower]

    for p in missing_phrases:
        errors.append(f"missing phrase: {p}")
    for s in missing_sections:
        errors.append(f"missing section: {s}")
    for e in missing_equations:
        errors.append(f"missing equation marker: {e}")
    for x in missing_tf:
        errors.append(f"missing table/figure callout: {x}")

    unsafe_phrases = [
        "destroys authorial style",
        "proves LLMs erase authorship",
        "human annotation study",
        "semantic fidelity was guaranteed",
        "all models show the same effect",
        "universal effect of LLM rewriting",
    ]
    found_unsafe = [p for p in unsafe_phrases if p.lower() in text_lower and f"avoid:\n\n- \u201c{p}".lower() not in text_lower]
    for p in found_unsafe:
        errors.append(f"unsafe phrase appears outside avoidance context: {p}")

    rows = [{
        "required_phrases_checked": len(REQUIRED_PHRASES),
        "missing_required_phrases": len(missing_phrases),
        "required_sections_checked": len(REQUIRED_SECTIONS),
        "missing_required_sections": len(missing_sections),
        "equation_markers_checked": len(REQUIRED_EQUATION_MARKERS),
        "missing_equation_markers": len(missing_equations),
        "table_figure_callouts_checked": len(REQUIRED_TABLES_FIGURES),
        "missing_table_figure_callouts": len(missing_tf),
        "unsafe_phrases_found": len(found_unsafe),
        "status": "PASS" if not errors else "FAIL",
    }]
    write_csv(CHECK_SUMMARY, rows, list(rows[0].keys()))

    lines = [
        "# Manuscript Skeleton Check Report",
        "",
        f"- required phrases checked: {len(REQUIRED_PHRASES)}",
        f"- missing required phrases: {len(missing_phrases)}",
        f"- required sections checked: {len(REQUIRED_SECTIONS)}",
        f"- missing required sections: {len(missing_sections)}",
        f"- equation markers checked: {len(REQUIRED_EQUATION_MARKERS)}",
        f"- missing equation markers: {len(missing_equations)}",
        f"- table/figure callouts checked: {len(REQUIRED_TABLES_FIGURES)}",
        f"- missing table/figure callouts: {len(missing_tf)}",
        f"- unsafe phrases found: {len(found_unsafe)}",
        "",
    ]
    if errors:
        lines += ["## Errors", ""] + [f"- {e}" for e in errors]
        CHECK_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("FAIL: manuscript skeleton checker found errors")
        for e in errors[:30]: print("- " + e)
        return 1

    lines += [
        "## Final verdict",
        "",
        "PASS: manuscript skeleton contains the required DSH-style structure, equations, table/figure callouts, and caution language for full drafting.",
    ]
    CHECK_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS: manuscript skeleton checker passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
