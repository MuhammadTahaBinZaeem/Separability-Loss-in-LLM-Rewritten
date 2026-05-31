"""
Checker for E3 warning-row sensitivity outputs.

Run from repository root after:

    python scripts/22_run_warning_row_sensitivity.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "metadata"
RESULTS = ROOT / "data" / "results"
LOGS = ROOT / "logs"

REQUIRED_FILES = [
    RESULTS / "warning_row_sensitivity_transfer_predictions.csv",
    META / "warning_row_sensitivity_transfer_summary.csv",
    META / "warning_row_sensitivity_same_condition_summary.csv",
    META / "warning_row_sensitivity_distance_summary.csv",
    META / "warning_row_sensitivity_feature_family_summary.csv",
    META / "warning_row_sensitivity_bootstrap_macro_f1_loss.csv",
    META / "warning_row_sensitivity_subset_counts.csv",
    META / "warning_row_sensitivity_manifest.csv",
    LOGS / "warning_row_sensitivity_report.md",
]

SUBSETS = {"all_rows", "qc_pass_only", "pass_plus_non_hard_length_warning"}
CONDITIONS = {"original", "paraphrase", "modernize", "simplify"}
REWRITE_CONDITIONS = {"paraphrase", "modernize", "simplify"}
MODELS = {"nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"}
SPLITS = {"validation", "test"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def assert_columns(path: Path, expected: set[str]) -> str | None:
    rows = read_csv(path)
    if not rows:
        return f"{path.relative_to(ROOT)} is empty"
    cols = set(rows[0].keys())
    missing = expected - cols
    if missing:
        return f"{path.relative_to(ROOT)} missing columns: {sorted(missing)}"
    return None


def main() -> int:
    missing = [p.relative_to(ROOT).as_posix() for p in REQUIRED_FILES if not p.exists()]
    if missing:
        return fail(f"missing E3 output files: {missing}")

    column_checks = {
        RESULTS / "warning_row_sensitivity_transfer_predictions.csv": {
            "subset_id", "model", "split", "condition", "text_id", "passage_id",
            "true_author", "predicted_author", "correct", "qc_status", "qc_flags",
        },
        META / "warning_row_sensitivity_transfer_summary.csv": {
            "subset_id", "model", "split", "condition", "baseline_condition", "accuracy",
            "macro_f1", "weighted_f1", "accuracy_loss_vs_original", "macro_f1_loss_vs_original",
            "weighted_f1_loss_vs_original", "rows",
        },
        META / "warning_row_sensitivity_same_condition_summary.csv": {
            "subset_id", "model", "split", "condition", "accuracy", "macro_f1", "weighted_f1",
            "rows", "baseline_condition", "macro_f1_difference_vs_original",
            "macro_f1_survival_ratio",
        },
        META / "warning_row_sensitivity_distance_summary.csv": {
            "subset_id", "feature_set", "condition", "pair_count", "mean_burrows_delta",
            "median_burrows_delta", "min_burrows_delta", "max_burrows_delta",
            "std_burrows_delta", "distance_ratio_vs_original",
        },
        META / "warning_row_sensitivity_feature_family_summary.csv": {
            "subset_id", "feature_family", "feature_count", "model", "split", "condition",
            "baseline_condition", "accuracy", "macro_f1", "weighted_f1",
            "accuracy_loss_vs_original", "macro_f1_loss_vs_original",
            "weighted_f1_loss_vs_original", "rows",
        },
        META / "warning_row_sensitivity_bootstrap_macro_f1_loss.csv": {
            "subset_id", "model", "split", "condition", "paired_passages",
            "observed_macro_f1_loss", "ci_low_95", "ci_high_95",
            "p_loss_le_zero_bootstrap", "bootstrap_iterations", "rng_seed",
        },
        META / "warning_row_sensitivity_subset_counts.csv": {
            "subset_id", "condition", "rows", "authors", "pass_rows", "warning_rows",
            "fail_rows", "length_hard_warning_rows", "length_soft_warning_rows",
        },
        META / "warning_row_sensitivity_manifest.csv": {
            "artifact", "path", "size_bytes", "sha256",
        },
    }
    for path, expected in column_checks.items():
        error = assert_columns(path, expected)
        if error:
            return fail(error)

    transfer = read_csv(META / "warning_row_sensitivity_transfer_summary.csv")
    transfer_keys = {(r["subset_id"], r["model"], r["split"], r["condition"]) for r in transfer}
    expected_transfer = {
        (subset, model, split, condition)
        for subset in SUBSETS
        for model in MODELS
        for split in SPLITS
        for condition in CONDITIONS
    }
    missing_transfer = sorted(expected_transfer - transfer_keys)
    if missing_transfer:
        return fail(f"missing transfer summary combinations: {missing_transfer[:10]}")

    subset_counts = read_csv(META / "warning_row_sensitivity_subset_counts.csv")
    count_keys = {(r["subset_id"], r["condition"]) for r in subset_counts}
    expected_count_keys = {(subset, condition) for subset in SUBSETS for condition in CONDITIONS}
    if count_keys != expected_count_keys:
        return fail("subset count table does not cover every subset/condition pair")

    bootstrap = read_csv(META / "warning_row_sensitivity_bootstrap_macro_f1_loss.csv")
    bootstrap_keys = {(r["subset_id"], r["model"], r["split"], r["condition"]) for r in bootstrap}
    expected_bootstrap = {
        (subset, model, split, condition)
        for subset in SUBSETS
        for model in MODELS
        for split in SPLITS
        for condition in REWRITE_CONDITIONS
    }
    missing_bootstrap = sorted(expected_bootstrap - bootstrap_keys)
    if missing_bootstrap:
        return fail(f"missing bootstrap combinations: {missing_bootstrap[:10]}")

    problematic = []
    for row in transfer:
        if row["model"] == "nearest_centroid" and row["split"] == "test" and row["condition"] in REWRITE_CONDITIONS:
            if float(row["macro_f1_loss_vs_original"]) <= 0:
                problematic.append((row["subset_id"], row["condition"], row["macro_f1_loss_vs_original"]))
    if problematic:
        return fail(f"nearest-centroid test loss is not positive for: {problematic}")

    manifest = read_csv(META / "warning_row_sensitivity_manifest.csv")
    for row in manifest:
        path = ROOT / row["path"]
        if not path.exists():
            return fail(f"manifest path missing: {row['path']}")
        if int(row["size_bytes"]) <= 0:
            return fail(f"manifest reports non-positive size: {row['path']}")
        if not row["sha256"]:
            return fail(f"manifest missing sha256: {row['path']}")

    print("PASS: E3 warning-row sensitivity outputs are complete and directionally stable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
