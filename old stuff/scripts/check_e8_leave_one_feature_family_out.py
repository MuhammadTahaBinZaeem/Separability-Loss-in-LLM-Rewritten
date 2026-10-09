"""
Checker for E8 leave-one-feature-family-out ablation outputs.

Run from repository root after:

    python scripts/25_run_leave_one_feature_family_out.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "metadata"
RESULTS = ROOT / "data" / "results"
LOGS = ROOT / "logs"

REQUIRED_FILES = [
    RESULTS / "leave_one_feature_family_out_predictions.csv",
    META / "leave_one_feature_family_out_summary.csv",
    META / "leave_one_feature_family_out_delta_vs_full.csv",
    META / "leave_one_feature_family_out_feature_registry.csv",
    META / "leave_one_feature_family_out_manifest.csv",
    LOGS / "leave_one_feature_family_out_report.md",
]

FAMILIES = {"length_rhythm", "punctuation", "lexical_richness", "register_marker", "function_word", "char3"}
ABLATION_MODES = {"full_features"} | {f"minus_{family}" for family in FAMILIES}
SPLITS = {"validation", "test"}
CONDITIONS = {"original", "paraphrase", "modernize", "simplify"}
MODEL = "nearest_centroid"


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
    missing = expected - set(rows[0].keys())
    if missing:
        return f"{path.relative_to(ROOT)} missing columns: {sorted(missing)}"
    return None


def main() -> int:
    missing = [path.relative_to(ROOT).as_posix() for path in REQUIRED_FILES if not path.exists()]
    if missing:
        return fail(f"missing E8 output files: {missing}")

    column_checks = {
        RESULTS / "leave_one_feature_family_out_predictions.csv": {
            "ablation_mode", "removed_family", "model", "split", "condition", "text_id",
            "passage_id", "true_author", "predicted_author", "correct",
        },
        META / "leave_one_feature_family_out_summary.csv": {
            "ablation_mode", "removed_family", "model", "split", "condition", "baseline_condition",
            "included_feature_count", "accuracy", "macro_f1", "weighted_f1", "accuracy_loss_vs_original",
            "macro_f1_loss_vs_original", "weighted_f1_loss_vs_original", "rows",
        },
        META / "leave_one_feature_family_out_delta_vs_full.csv": {
            "ablation_mode", "removed_family", "model", "split", "condition", "macro_f1",
            "full_macro_f1", "macro_f1_delta_vs_full", "macro_f1_loss_vs_original",
            "full_macro_f1_loss_vs_original", "loss_delta_vs_full", "included_feature_count",
        },
        META / "leave_one_feature_family_out_feature_registry.csv": {
            "ablation_mode", "removed_family", "included_feature_count", "removed_feature_count",
            "included_families", "removed_features",
        },
        META / "leave_one_feature_family_out_manifest.csv": {"artifact", "path", "size_bytes", "sha256"},
    }
    for path, expected in column_checks.items():
        error = assert_columns(path, expected)
        if error:
            return fail(error)

    predictions = read_csv(RESULTS / "leave_one_feature_family_out_predictions.csv")
    expected_prediction_rows = len(ABLATION_MODES) * len(SPLITS) * len(CONDITIONS) * 54
    if len(predictions) != expected_prediction_rows:
        return fail(f"expected {expected_prediction_rows} prediction rows, found {len(predictions)}")

    summary = read_csv(META / "leave_one_feature_family_out_summary.csv")
    summary_keys = {(r["ablation_mode"], r["model"], r["split"], r["condition"]) for r in summary}
    expected_summary_keys = {
        (mode, MODEL, split, condition)
        for mode in ABLATION_MODES
        for split in SPLITS
        for condition in CONDITIONS
    }
    missing_summary = sorted(expected_summary_keys - summary_keys)
    if missing_summary:
        return fail(f"missing summary combinations: {missing_summary[:10]}")

    delta = read_csv(META / "leave_one_feature_family_out_delta_vs_full.csv")
    delta_keys = {(r["ablation_mode"], r["model"], r["split"], r["condition"]) for r in delta}
    if delta_keys != expected_summary_keys:
        return fail("delta table does not match expected ablation/model/split/condition coverage")

    registry = read_csv(META / "leave_one_feature_family_out_feature_registry.csv")
    registry_modes = {r["ablation_mode"] for r in registry}
    if registry_modes != ABLATION_MODES:
        return fail(f"feature registry modes mismatch: {sorted(registry_modes)}")
    for row in registry:
        mode = row["ablation_mode"]
        if mode == "full_features":
            if row["removed_family"] != "none" or int(row["removed_feature_count"]) != 0:
                return fail("full_features registry row has unexpected removed family/count")
        else:
            expected_family = mode.removeprefix("minus_")
            if row["removed_family"] != expected_family:
                return fail(f"{mode} registry removed family mismatch")
            if int(row["removed_feature_count"]) <= 0:
                return fail(f"{mode} removed no features")

    manifest = read_csv(META / "leave_one_feature_family_out_manifest.csv")
    for row in manifest:
        path = ROOT / row["path"]
        if not path.exists():
            return fail(f"manifest path missing: {row['path']}")
        if int(row["size_bytes"]) <= 0:
            return fail(f"manifest reports non-positive size: {row['path']}")
        if not row["sha256"]:
            return fail(f"manifest missing sha256: {row['path']}")

    print("PASS: E8 leave-one-feature-family-out outputs are complete and structurally valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
