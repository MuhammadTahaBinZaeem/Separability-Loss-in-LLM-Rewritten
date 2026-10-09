"""
Consistency checker for Step 16 rewritten-condition author classification.

Run from repository root after Step 16:

    python scripts/check_step_16_rewritten_condition_classification.py

Exit code:
    0 = Step 16 outputs are internally consistent
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS = ROOT / "data" / "results" / "rewritten_condition_author_predictions.csv"
METRICS = ROOT / "metadata" / "rewritten_condition_author_metrics.csv"
SURVIVAL = ROOT / "metadata" / "rewritten_condition_author_survival_summary.csv"
CONFUSION = ROOT / "metadata" / "rewritten_condition_author_confusion_matrices.csv"
CLASS_REPORT = ROOT / "metadata" / "rewritten_condition_author_classification_report.csv"
MANIFEST = ROOT / "metadata" / "rewritten_condition_author_manifest.csv"
REPORT = ROOT / "logs" / "step_16_rewritten_condition_classification_report.md"
SCRIPT = ROOT / "scripts" / "17_run_rewritten_condition_classification.py"
PROTOCOL = ROOT / "docs" / "rewritten_condition_classification_protocol.md"

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
    required = [PREDICTIONS, METRICS, SURVIVAL, CONFUSION, CLASS_REPORT, MANIFEST, REPORT, SCRIPT, PROTOCOL]
    for path in required:
        check(path.exists(), f"missing required Step 16 file: {path.relative_to(ROOT)}", failures)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    pred_rows = read_csv(PREDICTIONS)
    metric_rows = read_csv(METRICS)
    survival_rows = read_csv(SURVIVAL)
    confusion_rows = read_csv(CONFUSION)
    report_rows = read_csv(CLASS_REPORT)

    check(len(metric_rows) == 24, f"expected 24 metric rows, found {len(metric_rows)}", failures)
    check(len(survival_rows) == 24, f"expected 24 survival rows, found {len(survival_rows)}", failures)
    check(len(pred_rows) == 1296, f"expected 1296 prediction rows, found {len(pred_rows)}", failures)
    check(len(confusion_rows) == 864, f"expected 864 confusion rows, found {len(confusion_rows)}", failures)
    check(len(report_rows) == 144, f"expected 144 classification report rows, found {len(report_rows)}", failures)

    expected_keys = {(m, s, c) for m in MODELS for s in SPLITS for c in CONDITIONS}
    metric_keys = {(row["model"], row["split"], row["condition"]) for row in metric_rows}
    survival_keys = {(row["model"], row["split"], row["condition"]) for row in survival_rows}
    check(metric_keys == expected_keys, "metric model/split/condition grid mismatch", failures)
    check(survival_keys == expected_keys, "survival model/split/condition grid mismatch", failures)

    pred_counts = Counter((row["model"], row["split"], row["condition"]) for row in pred_rows)
    for key in expected_keys:
        check(pred_counts[key] == 54, f"prediction count not 54 for {key}", failures)

    for row in metric_rows:
        check(row["rows"] == "54", f"metric row count not 54: {row}", failures)
        check(row["train_condition"] == row["condition"], f"train condition mismatch: {row}", failures)
        check(row["scaler_fit_scope"] == f"train_{row['condition']}_only", f"scaler fit scope mismatch: {row}", failures)
        for metric in ["accuracy", "macro_f1", "weighted_f1"]:
            value = float(row[metric])
            check(0.0 <= value <= 1.0, f"{metric} outside [0,1]: {row}", failures)

    for row in survival_rows:
        check(row["baseline_condition"] == "original", f"baseline is not original: {row}", failures)
        check(row["rows"] == "54", f"survival row count not 54: {row}", failures)
        for metric in ["accuracy", "macro_f1", "weighted_f1", "macro_f1_survival_ratio"]:
            float(row[metric])
        if row["condition"] == "original":
            check(abs(float(row["macro_f1_difference_vs_original"])) < 1e-9, f"original difference not zero: {row}", failures)
            check(abs(float(row["macro_f1_survival_ratio"]) - 1.0) < 1e-6, f"original survival ratio not one: {row}", failures)

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
    print("PASS: Step 16 rewritten-condition author classification is complete and internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
