"""
Consistency checker for Step 15 original-to-rewritten degradation experiment.

Run from repository root after Step 15:

    python scripts/check_step_15_rewrite_degradation.py

Exit code:
    0 = Step 15 degradation outputs are internally consistent
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS = ROOT / "data" / "results" / "original_to_rewritten_predictions.csv"
METRICS = ROOT / "metadata" / "original_to_rewritten_metrics.csv"
DEGRADATION = ROOT / "metadata" / "original_to_rewritten_degradation_summary.csv"
CONFUSION = ROOT / "metadata" / "original_to_rewritten_confusion_matrices.csv"
CLASS_REPORT = ROOT / "metadata" / "original_to_rewritten_classification_report.csv"
MANIFEST = ROOT / "metadata" / "original_to_rewritten_manifest.csv"
REPORT = ROOT / "logs" / "step_15_original_to_rewritten_degradation_report.md"
SCRIPT = ROOT / "scripts" / "16_run_original_to_rewritten_degradation.py"
PROTOCOL = ROOT / "docs" / "original_to_rewritten_degradation_protocol.md"

MODELS = {"nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"}
SPLITS = {"validation", "test"}
CONDITIONS = {"original", "paraphrase", "modernize", "simplify"}
AUTHORS = {"austen", "dickens", "poe", "shelley", "twain", "wilde"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    required = [PREDICTIONS, METRICS, DEGRADATION, CONFUSION, CLASS_REPORT, MANIFEST, REPORT, SCRIPT, PROTOCOL]
    for path in required:
        check(path.exists(), f"missing required Step 15 file: {path.relative_to(ROOT)}", failures)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    pred_rows = read_csv(PREDICTIONS)
    metric_rows = read_csv(METRICS)
    deg_rows = read_csv(DEGRADATION)
    confusion_rows = read_csv(CONFUSION)
    report_rows = read_csv(CLASS_REPORT)

    check(len(metric_rows) == 24, f"expected 24 metric rows, found {len(metric_rows)}", failures)
    check(len(deg_rows) == 24, f"expected 24 degradation rows, found {len(deg_rows)}", failures)
    check(len(pred_rows) == 1296, f"expected 1296 prediction rows, found {len(pred_rows)}", failures)
    check(len(confusion_rows) == 864, f"expected 864 confusion rows, found {len(confusion_rows)}", failures)
    check(len(report_rows) == 144, f"expected 144 classification report rows, found {len(report_rows)}", failures)

    metric_keys = {(row["model"], row["split"], row["condition"]) for row in metric_rows}
    expected_keys = {(m, s, c) for m in MODELS for s in SPLITS for c in CONDITIONS}
    check(metric_keys == expected_keys, "metric model/split/condition grid mismatch", failures)
    deg_keys = {(row["model"], row["split"], row["condition"]) for row in deg_rows}
    check(deg_keys == expected_keys, "degradation model/split/condition grid mismatch", failures)

    pred_conditions = {row["condition"] for row in pred_rows}
    pred_splits = {row["split"] for row in pred_rows}
    pred_models = {row["model"] for row in pred_rows}
    check(pred_conditions == CONDITIONS, f"prediction condition set mismatch: {pred_conditions}", failures)
    check(pred_splits == SPLITS, f"prediction split set mismatch: {pred_splits}", failures)
    check(pred_models == MODELS, f"prediction model set mismatch: {pred_models}", failures)
    pred_counts = Counter((row["model"], row["split"], row["condition"]) for row in pred_rows)
    for key in expected_keys:
        check(pred_counts[key] == 54, f"prediction count not 54 for {key}", failures)

    for row in metric_rows:
        check(row["rows"] == "54", f"metric row count not 54: {row}", failures)
        for metric in ["accuracy", "macro_f1", "weighted_f1"]:
            value = float(row[metric])
            check(0.0 <= value <= 1.0, f"{metric} outside [0,1]: {row}", failures)

    for row in deg_rows:
        check(row["baseline_condition"] == "original", f"baseline is not original: {row}", failures)
        check(row["rows"] == "54", f"degradation row count not 54: {row}", failures)
        for metric in ["accuracy", "macro_f1", "weighted_f1"]:
            value = float(row[metric])
            check(0.0 <= value <= 1.0, f"degradation metric outside [0,1]: {row}", failures)
        for loss_col in ["accuracy_loss_vs_original", "macro_f1_loss_vs_original", "weighted_f1_loss_vs_original"]:
            float(row[loss_col])

    confusion_counts = Counter((row["model"], row["split"], row["condition"]) for row in confusion_rows)
    for key in expected_keys:
        rows = [row for row in confusion_rows if (row["model"], row["split"], row["condition"]) == key]
        check(confusion_counts[key] == 36, f"confusion size mismatch for {key}", failures)
        check(sum(int(row["count"]) for row in rows) == 54, f"confusion count sum not 54 for {key}", failures)

    report_counts = Counter((row["model"], row["split"], row["condition"]) for row in report_rows)
    class_authors = {row["author_id"] for row in report_rows}
    check(class_authors == AUTHORS, f"classification report author set mismatch: {class_authors}", failures)
    for key in expected_keys:
        check(report_counts[key] == 6, f"classification report rows not 6 for {key}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: Step 15 original-to-rewritten degradation experiment is complete and internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
