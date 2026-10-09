"""
Consistency checker for Step 14 original-condition author baseline.

Run from repository root after Step 14:

    python scripts/check_step_14_original_baseline.py

Exit code:
    0 = Step 14 baseline outputs are internally consistent
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS = ROOT / "data" / "results" / "original_author_baseline_predictions.csv"
METRICS = ROOT / "metadata" / "original_author_baseline_metrics.csv"
CONFUSION = ROOT / "metadata" / "original_author_baseline_confusion_matrices.csv"
CLASS_REPORT = ROOT / "metadata" / "original_author_baseline_classification_report.csv"
MANIFEST = ROOT / "metadata" / "original_author_baseline_manifest.csv"
REPORT = ROOT / "logs" / "step_14_original_author_baseline_report.md"
SCRIPT = ROOT / "scripts" / "15_run_original_author_baseline.py"
PROTOCOL = ROOT / "docs" / "original_author_classification_protocol.md"

MODELS = {"nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"}
SPLITS = {"validation", "test"}
AUTHORS = {"austen", "dickens", "poe", "shelley", "twain", "wilde"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    required = [PREDICTIONS, METRICS, CONFUSION, CLASS_REPORT, MANIFEST, REPORT, SCRIPT, PROTOCOL]
    for path in required:
        check(path.exists(), f"missing required Step 14 file: {path.relative_to(ROOT)}", failures)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    pred_rows = read_csv(PREDICTIONS)
    metric_rows = read_csv(METRICS)
    confusion_rows = read_csv(CONFUSION)
    report_rows = read_csv(CLASS_REPORT)

    check(len(metric_rows) == 6, f"expected 6 metric rows, found {len(metric_rows)}", failures)
    check(len(pred_rows) == 324, f"expected 324 prediction rows, found {len(pred_rows)}", failures)
    check(len(confusion_rows) == 216, f"expected 216 confusion rows, found {len(confusion_rows)}", failures)
    check(len(report_rows) == 36, f"expected 36 classification report rows, found {len(report_rows)}", failures)

    model_set = {row["model"] for row in metric_rows}
    split_set = {row["split"] for row in metric_rows}
    check(model_set == MODELS, f"metric model set mismatch: {model_set}", failures)
    check(split_set == SPLITS, f"metric split set mismatch: {split_set}", failures)

    pred_conditions = {row["condition"] for row in pred_rows}
    check(pred_conditions == {"original"}, f"predictions include non-original conditions: {pred_conditions}", failures)
    pred_split_counts = Counter((row["model"], row["split"]) for row in pred_rows)
    for model in MODELS:
        check(pred_split_counts[(model, "validation")] == 54, f"{model} validation predictions not 54", failures)
        check(pred_split_counts[(model, "test")] == 54, f"{model} test predictions not 54", failures)

    for row in metric_rows:
        for metric in ["accuracy", "macro_f1", "weighted_f1"]:
            value = float(row[metric])
            check(0.0 <= value <= 1.0, f"{metric} outside [0,1]: {row}", failures)
        check(row["rows"] == "54", f"metric row count not 54: {row}", failures)

    confusion_counts = Counter((row["model"], row["split"]) for row in confusion_rows)
    for model in MODELS:
        for split in SPLITS:
            rows = [row for row in confusion_rows if row["model"] == model and row["split"] == split]
            check(confusion_counts[(model, split)] == 36, f"confusion size mismatch for {model}/{split}", failures)
            check(sum(int(row["count"]) for row in rows) == 54, f"confusion count sum not 54 for {model}/{split}", failures)

    class_authors = {row["author_id"] for row in report_rows}
    check(class_authors == AUTHORS, f"classification report author set mismatch: {class_authors}", failures)
    report_counts = Counter((row["model"], row["split"]) for row in report_rows)
    for model in MODELS:
        for split in SPLITS:
            check(report_counts[(model, split)] == 6, f"classification report rows not 6 for {model}/{split}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: Step 14 original-condition author baseline is complete and internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
