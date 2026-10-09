"""
Checker for E2 held-out-work validation outputs.

Run from repository root after:

    python scripts/23_run_heldout_work_validation.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "metadata"
RESULTS = ROOT / "data" / "results"
LOGS = ROOT / "logs"

REQUIRED_FILES = [
    META / "heldout_work_fold_registry.csv",
    RESULTS / "heldout_work_transfer_predictions.csv",
    META / "heldout_work_transfer_summary.csv",
    META / "heldout_work_same_condition_summary.csv",
    META / "heldout_work_distance_summary.csv",
    META / "heldout_work_manifest.csv",
    LOGS / "heldout_work_validation_report.md",
]

AUTHORS = {"austen", "dickens", "poe", "shelley", "twain", "wilde"}
FOLDS = {"work_fold_1", "work_fold_2"}
MEAN_FOLD = "mean_across_folds"
CONDITIONS = {"original", "paraphrase", "modernize", "simplify"}
MODELS = {"nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"}
FEATURE_SETS = {"function_word", "all_features"}


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
        return fail(f"missing E2 output files: {missing}")

    column_checks = {
        META / "heldout_work_fold_registry.csv": {
            "fold_id", "author_id", "train_work_id", "train_work_title", "test_work_id",
            "test_work_title", "train_selected_passages", "test_selected_passages",
        },
        RESULTS / "heldout_work_transfer_predictions.csv": {
            "fold_id", "model", "condition", "text_id", "passage_id",
            "train_work_for_author", "test_work_id", "true_author", "predicted_author", "correct",
        },
        META / "heldout_work_transfer_summary.csv": {
            "fold_id", "model", "condition", "baseline_condition", "accuracy", "macro_f1",
            "weighted_f1", "accuracy_loss_vs_original", "macro_f1_loss_vs_original",
            "weighted_f1_loss_vs_original", "rows",
        },
        META / "heldout_work_same_condition_summary.csv": {
            "fold_id", "model", "condition", "accuracy", "macro_f1", "weighted_f1", "rows",
            "baseline_condition", "macro_f1_difference_vs_original", "macro_f1_survival_ratio",
        },
        META / "heldout_work_distance_summary.csv": {
            "fold_id", "feature_set", "condition", "pair_count", "mean_burrows_delta",
            "median_burrows_delta", "min_burrows_delta", "max_burrows_delta",
            "std_burrows_delta", "distance_ratio_vs_original",
        },
        META / "heldout_work_manifest.csv": {"artifact", "path", "size_bytes", "sha256"},
    }
    for path, expected in column_checks.items():
        error = assert_columns(path, expected)
        if error:
            return fail(error)

    registry = read_csv(META / "heldout_work_fold_registry.csv")
    if len(registry) != 12:
        return fail(f"expected 12 fold registry rows, found {len(registry)}")
    registry_keys = {(row["fold_id"], row["author_id"]) for row in registry}
    expected_registry_keys = {(fold, author) for fold in FOLDS for author in AUTHORS}
    if registry_keys != expected_registry_keys:
        return fail("fold registry does not cover both folds for all six authors")
    for row in registry:
        if row["train_work_id"] == row["test_work_id"]:
            return fail(f"train and test work match for {row['fold_id']} / {row['author_id']}")
        if int(row["train_selected_passages"]) != 30 or int(row["test_selected_passages"]) != 30:
            return fail(f"unexpected selected passage count in fold registry row: {row}")

    transfer = read_csv(META / "heldout_work_transfer_summary.csv")
    transfer_keys = {(row["fold_id"], row["model"], row["condition"]) for row in transfer}
    expected_transfer_keys = {
        (fold, model, condition)
        for fold in (FOLDS | {MEAN_FOLD})
        for model in MODELS
        for condition in CONDITIONS
    }
    missing_transfer = sorted(expected_transfer_keys - transfer_keys)
    if missing_transfer:
        return fail(f"missing transfer summary combinations: {missing_transfer[:10]}")

    same = read_csv(META / "heldout_work_same_condition_summary.csv")
    same_keys = {(row["fold_id"], row["model"], row["condition"]) for row in same}
    expected_same_keys = expected_transfer_keys
    missing_same = sorted(expected_same_keys - same_keys)
    if missing_same:
        return fail(f"missing same-condition combinations: {missing_same[:10]}")

    distance = read_csv(META / "heldout_work_distance_summary.csv")
    distance_keys = {(row["fold_id"], row["feature_set"], row["condition"]) for row in distance}
    expected_distance_keys = {
        (fold, feature_set, condition)
        for fold in (FOLDS | {MEAN_FOLD})
        for feature_set in FEATURE_SETS
        for condition in CONDITIONS
    }
    missing_distance = sorted(expected_distance_keys - distance_keys)
    if missing_distance:
        return fail(f"missing distance summary combinations: {missing_distance[:10]}")

    predictions = read_csv(RESULTS / "heldout_work_transfer_predictions.csv")
    expected_prediction_rows = 2 * len(MODELS) * len(CONDITIONS) * 180
    if len(predictions) != expected_prediction_rows:
        return fail(f"expected {expected_prediction_rows} prediction rows, found {len(predictions)}")
    for row in predictions:
        if row["train_work_for_author"] == row["test_work_id"]:
            return fail(f"prediction leaks same work into train/test: {row['text_id']}")

    manifest = read_csv(META / "heldout_work_manifest.csv")
    for row in manifest:
        path = ROOT / row["path"]
        if not path.exists():
            return fail(f"manifest path missing: {row['path']}")
        if int(row["size_bytes"]) <= 0:
            return fail(f"manifest reports non-positive size: {row['path']}")
        if not row["sha256"]:
            return fail(f"manifest missing sha256: {row['path']}")

    print("PASS: E2 held-out-work validation outputs are complete and structurally valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
