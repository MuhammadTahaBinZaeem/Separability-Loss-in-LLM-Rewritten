"""
Checker for E7 length-band robustness outputs.

Run from repository root after:

    python scripts/24_run_length_band_robustness.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "metadata"
RESULTS = ROOT / "data" / "results"
LOGS = ROOT / "logs"

REQUIRED_FILES = [
    RESULTS / "length_band_transfer_predictions.csv",
    META / "length_band_transfer_summary.csv",
    META / "length_band_distribution_summary.csv",
    META / "length_band_manifest.csv",
    LOGS / "length_band_robustness_report.md",
]

GROUPING_STRATEGIES = {"actual_text_length", "source_original_length"}
MODELS = {"nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"}
SPLITS = {"validation", "test"}
CONDITIONS = {"original", "paraphrase", "modernize", "simplify"}
BANDS = {"450_500", "501_575", "576_650", "outside_bands"}


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
        return fail(f"missing E7 output files: {missing}")

    column_checks = {
        RESULTS / "length_band_transfer_predictions.csv": {
            "model", "split", "condition", "text_id", "passage_id", "true_author", "predicted_author",
            "correct", "actual_word_count", "source_original_word_count", "actual_text_length_band",
            "source_original_length_band",
        },
        META / "length_band_transfer_summary.csv": {
            "grouping_strategy", "model", "split", "length_band", "condition", "baseline_condition",
            "rows", "authors", "accuracy", "macro_f1", "weighted_f1", "accuracy_loss_vs_original",
            "macro_f1_loss_vs_original", "weighted_f1_loss_vs_original", "baseline_rows", "baseline_available",
        },
        META / "length_band_distribution_summary.csv": {
            "grouping_strategy", "split", "condition", "length_band", "rows", "authors",
            "min_word_count", "max_word_count",
        },
        META / "length_band_manifest.csv": {"artifact", "path", "size_bytes", "sha256"},
    }
    for path, expected in column_checks.items():
        error = assert_columns(path, expected)
        if error:
            return fail(error)

    predictions = read_csv(RESULTS / "length_band_transfer_predictions.csv")
    expected_prediction_rows = len(MODELS) * len(SPLITS) * len(CONDITIONS) * 54
    if len(predictions) != expected_prediction_rows:
        return fail(f"expected {expected_prediction_rows} prediction rows, found {len(predictions)}")

    summary = read_csv(META / "length_band_transfer_summary.csv")
    expected_summary_keys = {
        (strategy, model, split, band, condition)
        for strategy in GROUPING_STRATEGIES
        for model in MODELS
        for split in SPLITS
        for band in BANDS
        for condition in CONDITIONS
    }
    summary_keys = {(r["grouping_strategy"], r["model"], r["split"], r["length_band"], r["condition"]) for r in summary}
    missing_summary = sorted(expected_summary_keys - summary_keys)
    if missing_summary:
        return fail(f"missing summary combinations: {missing_summary[:10]}")

    dist = read_csv(META / "length_band_distribution_summary.csv")
    expected_dist_keys = {
        (strategy, split, condition, band)
        for strategy in GROUPING_STRATEGIES
        for split in SPLITS
        for condition in CONDITIONS
        for band in BANDS
    }
    dist_keys = {(r["grouping_strategy"], r["split"], r["condition"], r["length_band"]) for r in dist}
    missing_dist = sorted(expected_dist_keys - dist_keys)
    if missing_dist:
        return fail(f"missing distribution combinations: {missing_dist[:10]}")

    # Main comparable bands should have source-original rows in validation/test.
    focus_rows = [
        r for r in summary
        if r["grouping_strategy"] == "source_original_length"
        and r["model"] == "nearest_centroid"
        and r["split"] == "test"
        and r["length_band"] in {"501_575", "576_650"}
        and r["condition"] in CONDITIONS
    ]
    if not focus_rows:
        return fail("no source-original length focus rows found")
    populated_focus = [r for r in focus_rows if int(r["rows"]) > 0]
    if len(populated_focus) < 4:
        return fail("too few populated source-original focus rows")

    manifest = read_csv(META / "length_band_manifest.csv")
    for row in manifest:
        path = ROOT / row["path"]
        if not path.exists():
            return fail(f"manifest path missing: {row['path']}")
        if int(row["size_bytes"]) <= 0:
            return fail(f"manifest reports non-positive size: {row['path']}")
        if not row["sha256"]:
            return fail(f"manifest missing sha256: {row['path']}")

    print("PASS: E7 length-band robustness outputs are complete and structurally valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
