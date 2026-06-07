"""Validate semantic-risk sensitivity outputs.

Checks that semantic-fidelity filtering did not break the Step 15 transfer
sensitivity analysis and that all test rewrite losses remain positive under the
strictest semantic-risk exclusion.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "metadata"
LOGS = ROOT / "logs"
SUMMARY = META / "semantic_risk_sensitivity_transfer_summary.csv"
EXCLUDED = META / "semantic_risk_sensitivity_excluded_rows.csv"
MANIFEST = META / "semantic_risk_sensitivity_manifest.csv"
REPORT = LOGS / "semantic_risk_sensitivity_report.md"
CHECK_SUMMARY = META / "semantic_risk_sensitivity_check_summary.csv"
CHECK_REPORT = LOGS / "semantic_risk_sensitivity_check_report.md"

FILTERS = ["all_rows", "exclude_unusable", "exclude_any_semantic_issue"]
MODELS = ["nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"]
SPLITS = ["validation", "test"]
CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
REWRITE_CONDITIONS = ["paraphrase", "modernize", "simplify"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def ffloat(value: str) -> float:
    return float(value)


def main() -> int:
    errors: list[str] = []
    for path in [SUMMARY, EXCLUDED, MANIFEST, REPORT]:
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT)}")
        elif path.stat().st_size == 0:
            errors.append(f"empty {path.relative_to(ROOT)}")

    if errors:
        CHECK_REPORT.parent.mkdir(parents=True, exist_ok=True)
        CHECK_REPORT.write_text("# Semantic-Risk Sensitivity Check Report\n\nFAIL\n\n" + "\n".join(f"- {e}" for e in errors) + "\n", encoding="utf-8")
        print("FAIL: required semantic-risk files missing")
        return 1

    rows = read_csv(SUMMARY)
    excluded = read_csv(EXCLUDED)
    report_text = REPORT.read_text(encoding="utf-8")

    expected_rows = len(FILTERS) * len(MODELS) * len(SPLITS) * len(CONDITIONS)
    if len(rows) != expected_rows:
        errors.append(f"expected {expected_rows} transfer-summary rows, found {len(rows)}")

    keys = {(r["sensitivity_filter"], r["model"], r["split"], r["condition"]) for r in rows}
    for filt in FILTERS:
        for model in MODELS:
            for split in SPLITS:
                for condition in CONDITIONS:
                    if (filt, model, split, condition) not in keys:
                        errors.append(f"missing combo {filt}/{model}/{split}/{condition}")

    if len(excluded) != 17:
        errors.append(f"expected 17 excluded detail rows, found {len(excluded)}")
    unusable = [r for r in excluded if r.get("overall_usable_yes_no") == "no"]
    issue = [r for r in excluded if r.get("any_semantic_issue_flag") == "1"]
    high = [r for r in excluded if r.get("semantic_issue_level") == "high"]
    if len(unusable) != 1:
        errors.append(f"expected 1 unusable detail row, found {len(unusable)}")
    if len(issue) != 17:
        errors.append(f"expected 17 semantic-issue detail rows, found {len(issue)}")
    if len(high) != 1:
        errors.append(f"expected 1 high-risk detail row, found {len(high)}")

    strict_test_rewrites = [
        r for r in rows
        if r["sensitivity_filter"] == "exclude_any_semantic_issue"
        and r["split"] == "test"
        and r["condition"] in REWRITE_CONDITIONS
    ]
    if len(strict_test_rewrites) != len(MODELS) * len(REWRITE_CONDITIONS):
        errors.append(f"expected 9 strict test rewrite rows, found {len(strict_test_rewrites)}")
    nonpositive = [r for r in strict_test_rewrites if ffloat(r["macro_f1_loss_vs_original"]) <= 0]
    if nonpositive:
        for r in nonpositive:
            errors.append(f"non-positive strict test loss: {r['model']}/{r['condition']}={r['macro_f1_loss_vs_original']}")

    for required_phrase in ["exclude_unusable", "exclude_any_semantic_issue", "Nearest-centroid test focus"]:
        if required_phrase not in report_text:
            errors.append(f"report missing phrase: {required_phrase}")

    min_strict_loss = min(ffloat(r["macro_f1_loss_vs_original"]) for r in strict_test_rewrites) if strict_test_rewrites else 0.0
    max_excluded = max(int(r["excluded_rows"]) for r in rows if r["condition"] != "original")

    out = [{
        "transfer_summary_rows": len(rows),
        "excluded_detail_rows": len(excluded),
        "unusable_detail_rows": len(unusable),
        "semantic_issue_detail_rows": len(issue),
        "high_risk_detail_rows": len(high),
        "strict_test_rewrite_rows": len(strict_test_rewrites),
        "strict_test_nonpositive_losses": len(nonpositive),
        "minimum_strict_test_macro_f1_loss": round(min_strict_loss, 6),
        "maximum_rewrite_rows_excluded_in_any_cell": max_excluded,
        "status": "PASS" if not errors else "FAIL",
    }]
    write_csv(CHECK_SUMMARY, out, list(out[0].keys()))

    lines = [
        "# Semantic-Risk Sensitivity Check Report",
        "",
        f"- transfer summary rows: {len(rows)}",
        f"- excluded detail rows: {len(excluded)}",
        f"- unusable detail rows: {len(unusable)}",
        f"- semantic-issue detail rows: {len(issue)}",
        f"- high-risk detail rows: {len(high)}",
        f"- strict test rewrite rows: {len(strict_test_rewrites)}",
        f"- strict test non-positive losses: {len(nonpositive)}",
        f"- minimum strict test macro-F1 loss: {min_strict_loss:.6f}",
        f"- maximum rewrite rows excluded in any cell: {max_excluded}",
        "",
    ]
    if errors:
        lines += ["## Errors", ""] + [f"- {e}" for e in errors]
        CHECK_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("FAIL: semantic-risk sensitivity checker found errors")
        for e in errors[:20]: print("- " + e)
        return 1

    lines += [
        "## Final verdict",
        "",
        "PASS: semantic-risk sensitivity outputs are complete. All strict-filter test rewrite macro-F1 losses remain positive after excluding rows with semantic-fidelity issue flags.",
    ]
    CHECK_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS: semantic-risk sensitivity checker passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
