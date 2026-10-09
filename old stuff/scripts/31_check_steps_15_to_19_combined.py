"""
Step 20 checker for the combined Steps 15-19 run.

Run from repository root after:

    python scripts/30_run_steps_15_to_19_combined.py
    python scripts/31_check_steps_15_to_19_combined.py

This checker verifies that the combined runner produced the expected manifest,
reports, core result files, tables, bootstrap results, and figures.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "metadata"
RESULTS = ROOT / "data" / "results"
FIGURES = ROOT / "figures"
LOGS = ROOT / "logs"

COMBINED_REPORT = LOGS / "steps_15_to_19_combined_run_report.md"
COMBINED_MANIFEST = META / "steps_15_to_19_combined_manifest.csv"
CHECK_REPORT = LOGS / "step_20_combined_steps_15_to_19_check_report.md"

REQUIRED_FILES = [
    COMBINED_REPORT,
    COMBINED_MANIFEST,
    META / "original_author_baseline_metrics.csv",
    RESULTS / "original_author_baseline_predictions.csv",
    META / "original_to_rewritten_metrics.csv",
    META / "original_to_rewritten_degradation_summary.csv",
    RESULTS / "original_to_rewritten_predictions.csv",
    META / "rewritten_condition_author_metrics.csv",
    META / "rewritten_condition_author_survival_summary.csv",
    RESULTS / "rewritten_condition_author_predictions.csv",
    META / "inter_author_distance_summary.csv",
    META / "feature_family_vulnerability_summary.csv",
    META / "feature_family_distance_contraction.csv",
    META / "paper_table_original_baseline.csv",
    META / "paper_table_transfer_degradation.csv",
    META / "paper_table_same_condition_survival.csv",
    META / "paper_table_distance_contraction.csv",
    META / "paper_table_feature_family_vulnerability.csv",
    META / "statistical_tests_bootstrap_macro_f1_loss.csv",
    META / "step19_tables_figures_manifest.csv",
    FIGURES / "fig_step19_macro_f1_degradation.svg",
    FIGURES / "fig_step19_distance_contraction.svg",
    FIGURES / "fig_step19_feature_family_losses.svg",
]

CONDITIONS = {"original", "paraphrase", "modernize", "simplify"}
REWRITE_CONDITIONS = {"paraphrase", "modernize", "simplify"}
MODELS = {"nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"}
SPLITS = {"validation", "test"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fail(lines: list[str], message: str) -> int:
    lines.append(f"FAIL: {message}")
    CHECK_REPORT.parent.mkdir(parents=True, exist_ok=True)
    CHECK_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"FAIL: {message}")
    return 1


def main() -> int:
    lines = ["# Step 20 Combined Steps 15-19 Check Report", ""]

    missing = [p.relative_to(ROOT).as_posix() for p in REQUIRED_FILES if not p.exists()]
    if missing:
        return fail(lines, f"missing required files: {missing}")

    empty = [p.relative_to(ROOT).as_posix() for p in REQUIRED_FILES if p.stat().st_size <= 0]
    if empty:
        return fail(lines, f"empty required files: {empty}")

    manifest = read_csv(COMBINED_MANIFEST)
    if not manifest:
        return fail(lines, "combined manifest is empty")
    bad_manifest = [row for row in manifest if row.get("exists") != "1" or int(row.get("size_bytes", "0")) <= 0 or not row.get("sha256")]
    if bad_manifest:
        return fail(lines, f"combined manifest contains bad rows: {bad_manifest[:3]}")

    transfer = read_csv(META / "original_to_rewritten_degradation_summary.csv")
    transfer_keys = {(r["model"], r["split"], r["condition"]) for r in transfer}
    expected_transfer = {(model, split, condition) for model in MODELS for split in SPLITS for condition in CONDITIONS}
    if not expected_transfer.issubset(transfer_keys):
        return fail(lines, "transfer degradation summary missing model/split/condition combinations")

    bootstrap = read_csv(META / "statistical_tests_bootstrap_macro_f1_loss.csv")
    bootstrap_keys = {(r["model"], r["split"], r["condition"]) for r in bootstrap}
    expected_boot = {(model, split, condition) for model in MODELS for split in SPLITS for condition in REWRITE_CONDITIONS}
    if not expected_boot.issubset(bootstrap_keys):
        return fail(lines, "bootstrap table missing model/split/condition combinations")

    # Directional sanity check for the main model on test split.
    main_rows = [r for r in transfer if r["model"] == "nearest_centroid" and r["split"] == "test" and r["condition"] in REWRITE_CONDITIONS]
    non_positive = [r for r in main_rows if float(r["macro_f1_loss_vs_original"]) <= 0]
    if non_positive:
        return fail(lines, f"nearest-centroid test losses not positive: {non_positive}")

    distance = read_csv(META / "paper_table_distance_contraction.csv")
    if not distance:
        return fail(lines, "paper distance table is empty")
    bad_distance = [r for r in distance if r["condition"] in REWRITE_CONDITIONS and float(r["distance_ratio"]) <= 0]
    if bad_distance:
        return fail(lines, "distance table contains invalid non-positive distance ratios")

    lines.extend([
        "PASS: combined Steps 15-19 outputs are present and internally coherent.",
        "",
        f"Manifest rows checked: {len(manifest)}",
        f"Transfer rows checked: {len(transfer)}",
        f"Bootstrap rows checked: {len(bootstrap)}",
        f"Distance rows checked: {len(distance)}",
        "",
        "Main nearest-centroid test transfer losses remain positive for paraphrase, modernize, and simplify.",
    ])
    CHECK_REPORT.parent.mkdir(parents=True, exist_ok=True)
    CHECK_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS: Step 20 combined Steps 15-19 checker passed.")
    print(f"Report: {CHECK_REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
