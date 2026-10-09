"""
Step 16: same-condition author classification for original and rewritten conditions.

Run from repository root after Step 15:

    python scripts/17_run_rewritten_condition_classification.py

Inputs:
- data/modeling/modeling_metadata.csv
- data/modeling/X_stylometric_raw.csv
- data/modeling/y_author_labels.csv
- metadata/modeling_feature_columns.csv

Outputs:
- data/results/rewritten_condition_author_predictions.csv
- metadata/rewritten_condition_author_metrics.csv
- metadata/rewritten_condition_author_survival_summary.csv
- metadata/rewritten_condition_author_confusion_matrices.csv
- metadata/rewritten_condition_author_classification_report.csv
- metadata/rewritten_condition_author_manifest.csv
- logs/step_16_rewritten_condition_classification_report.md
"""

from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELING_METADATA = ROOT / "data" / "modeling" / "modeling_metadata.csv"
X_RAW = ROOT / "data" / "modeling" / "X_stylometric_raw.csv"
Y_LABELS = ROOT / "data" / "modeling" / "y_author_labels.csv"
FEATURE_COLUMNS = ROOT / "metadata" / "modeling_feature_columns.csv"
RESULTS = ROOT / "data" / "results"
META = ROOT / "metadata"
LOGS = ROOT / "logs"

PREDICTIONS = RESULTS / "rewritten_condition_author_predictions.csv"
METRICS = META / "rewritten_condition_author_metrics.csv"
SURVIVAL = META / "rewritten_condition_author_survival_summary.csv"
CONFUSION = META / "rewritten_condition_author_confusion_matrices.csv"
CLASS_REPORT = META / "rewritten_condition_author_classification_report.csv"
MANIFEST = META / "rewritten_condition_author_manifest.csv"
REPORT = LOGS / "step_16_rewritten_condition_classification_report.md"

AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
EVAL_SPLITS = ["validation", "test"]
MODELS = ["nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def zscore_fit(matrix: list[list[float]]) -> tuple[list[float], list[float]]:
    n = len(matrix)
    p = len(matrix[0])
    means, stds = [], []
    for j in range(p):
        vals = [row[j] for row in matrix]
        mean = sum(vals) / n
        var = sum((v - mean) ** 2 for v in vals) / n
        std = math.sqrt(var)
        means.append(mean)
        stds.append(std if std > 0 else 1.0)
    return means, stds


def zscore_apply(matrix: list[list[float]], means: list[float], stds: list[float]) -> list[list[float]]:
    return [[(row[j] - means[j]) / stds[j] for j in range(len(row))] for row in matrix]


def euclidean2(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def fit_nearest_centroid(x: list[list[float]], y: list[str]) -> dict[str, list[float]]:
    by_class: dict[str, list[list[float]]] = defaultdict(list)
    for row, label in zip(x, y):
        by_class[label].append(row)
    return {label: [sum(row[j] for row in rows) / len(rows) for j in range(len(rows[0]))] for label, rows in by_class.items()}


def predict_nearest_centroid(model: dict[str, list[float]], x: list[list[float]]) -> list[str]:
    return [min(model, key=lambda label: euclidean2(row, model[label])) for row in x]


def fit_gaussian_nb(x: list[list[float]], y: list[str]) -> dict[str, object]:
    by_class: dict[str, list[list[float]]] = defaultdict(list)
    for row, label in zip(x, y):
        by_class[label].append(row)
    priors = {label: len(rows) / len(x) for label, rows in by_class.items()}
    means, variances = {}, {}
    for label, rows in by_class.items():
        p = len(rows[0])
        means[label] = [sum(row[j] for row in rows) / len(rows) for j in range(p)]
        variances[label] = []
        for j in range(p):
            m = means[label][j]
            v = sum((row[j] - m) ** 2 for row in rows) / len(rows)
            variances[label].append(max(v, 1e-6))
    return {"priors": priors, "means": means, "variances": variances}


def predict_gaussian_nb(model: dict[str, object], x: list[list[float]]) -> list[str]:
    preds = []
    priors = model["priors"]
    means = model["means"]
    variances = model["variances"]
    for row in x:
        scores = {}
        for label in priors:
            score = math.log(priors[label])
            for j, value in enumerate(row):
                var = variances[label][j]
                mean = means[label][j]
                score += -0.5 * math.log(2 * math.pi * var) - ((value - mean) ** 2) / (2 * var)
            scores[label] = score
        preds.append(max(scores, key=scores.get))
    return preds


def fit_lda_shrinkage(x: list[list[float]], y: list[str]) -> dict[str, object]:
    counts = Counter(y)
    by_class: dict[str, list[list[float]]] = defaultdict(list)
    for row, label in zip(x, y):
        by_class[label].append(row)
    p = len(x[0])
    means = {label: [sum(row[j] for row in rows) / len(rows) for j in range(p)] for label, rows in by_class.items()}
    pooled = []
    for j in range(p):
        ss, denom = 0.0, 0
        for label, rows in by_class.items():
            m = means[label][j]
            ss += sum((row[j] - m) ** 2 for row in rows)
            denom += max(len(rows) - 1, 0)
        pooled.append(max(ss / max(denom, 1), 1e-6))
    priors = {label: counts[label] / len(y) for label in counts}
    return {"means": means, "pooled_variances": pooled, "priors": priors}


def predict_lda_shrinkage(model: dict[str, object], x: list[list[float]]) -> list[str]:
    preds = []
    means = model["means"]
    pooled = model["pooled_variances"]
    priors = model["priors"]
    for row in x:
        scores = {}
        for label, mean in means.items():
            score = math.log(priors[label])
            for j, value in enumerate(row):
                score += (value * mean[j] / pooled[j]) - (mean[j] ** 2 / (2 * pooled[j]))
            scores[label] = score
        preds.append(max(scores, key=scores.get))
    return preds


def precision_recall_f1(y_true: list[str], y_pred: list[str], label: str) -> tuple[float, float, float, int]:
    tp = sum(1 for a, b in zip(y_true, y_pred) if a == label and b == label)
    fp = sum(1 for a, b in zip(y_true, y_pred) if a != label and b == label)
    fn = sum(1 for a, b in zip(y_true, y_pred) if a == label and b != label)
    support = sum(1 for a in y_true if a == label)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1, support


def evaluate(y_true: list[str], y_pred: list[str]) -> dict[str, float]:
    accuracy = sum(1 for a, b in zip(y_true, y_pred) if a == b) / len(y_true) if y_true else 0.0
    per = [precision_recall_f1(y_true, y_pred, label) for label in AUTHORS]
    macro_f1 = sum(x[2] for x in per) / len(per)
    total = sum(x[3] for x in per)
    weighted_f1 = sum(x[2] * x[3] for x in per) / total if total else 0.0
    return {"accuracy": round(accuracy, 6), "macro_f1": round(macro_f1, 6), "weighted_f1": round(weighted_f1, 6)}


def confusion_rows(model_name: str, split: str, condition: str, y_true: list[str], y_pred: list[str]) -> list[dict[str, object]]:
    return [{"model": model_name, "split": split, "condition": condition, "actual_author": actual, "predicted_author": predicted, "count": sum(1 for a, b in zip(y_true, y_pred) if a == actual and b == predicted)} for actual in AUTHORS for predicted in AUTHORS]


def report_rows(model_name: str, split: str, condition: str, y_true: list[str], y_pred: list[str]) -> list[dict[str, object]]:
    rows = []
    for label in AUTHORS:
        p, r, f, s = precision_recall_f1(y_true, y_pred, label)
        rows.append({"model": model_name, "split": split, "condition": condition, "author_id": label, "precision": round(p, 6), "recall": round(r, 6), "f1": round(f, 6), "support": s})
    return rows


def main() -> int:
    for path in [MODELING_METADATA, X_RAW, Y_LABELS, FEATURE_COLUMNS]:
        if not path.exists():
            print(f"Missing input: {path.relative_to(ROOT)}")
            return 1
    meta_rows = read_csv(MODELING_METADATA)
    x_rows = read_csv(X_RAW)
    y_rows = read_csv(Y_LABELS)
    feature_cols = [row["feature"] for row in read_csv(FEATURE_COLUMNS)]
    by_text_x = {row["text_id"]: row for row in x_rows}
    by_text_y = {row["text_id"]: row for row in y_rows}

    dataset = []
    for row in meta_rows:
        text_id = row["text_id"]
        dataset.append({"meta": row, "x": [float(by_text_x[text_id][col]) for col in feature_cols], "y": by_text_y[text_id]["author_id"]})

    prediction_rows, metric_rows, survival_rows, confusion_all, class_report_all = [], [], [], [], []
    for condition in CONDITIONS:
        train = [r for r in dataset if r["meta"]["split"] == "train" and r["meta"]["condition"] == condition]
        if len(train) != 252:
            print(f"Expected 252 train rows for {condition}, found {len(train)}")
            return 1
        x_train_raw = [r["x"] for r in train]
        y_train = [r["y"] for r in train]
        means, stds = zscore_fit(x_train_raw)
        x_train = zscore_apply(x_train_raw, means, stds)
        fitted = {
            "nearest_centroid": fit_nearest_centroid(x_train, y_train),
            "diagonal_gaussian_nb": fit_gaussian_nb(x_train, y_train),
            "linear_discriminant_shrinkage": fit_lda_shrinkage(x_train, y_train),
        }
        predictors = {
            "nearest_centroid": predict_nearest_centroid,
            "diagonal_gaussian_nb": predict_gaussian_nb,
            "linear_discriminant_shrinkage": predict_lda_shrinkage,
        }
        for model_name in MODELS:
            for split in EVAL_SPLITS:
                subset = [r for r in dataset if r["meta"]["split"] == split and r["meta"]["condition"] == condition]
                if len(subset) != 54:
                    print(f"Expected 54 rows for {split}/{condition}, found {len(subset)}")
                    return 1
                x_eval = zscore_apply([r["x"] for r in subset], means, stds)
                y_eval = [r["y"] for r in subset]
                preds = predictors[model_name](fitted[model_name], x_eval)
                metrics = evaluate(y_eval, preds)
                metric_rows.append({"model": model_name, "split": split, "condition": condition, **metrics, "rows": len(y_eval), "train_condition": condition, "scaler_fit_scope": f"train_{condition}_only"})
                confusion_all.extend(confusion_rows(model_name, split, condition, y_eval, preds))
                class_report_all.extend(report_rows(model_name, split, condition, y_eval, preds))
                for item, pred in zip(subset, preds):
                    prediction_rows.append({
                        "model": model_name,
                        "split": split,
                        "condition": condition,
                        "text_id": item["meta"]["text_id"],
                        "passage_id": item["meta"]["passage_id"],
                        "true_author": item["y"],
                        "predicted_author": pred,
                        "correct": int(item["y"] == pred),
                    })

    by_key = {(row["model"], row["split"], row["condition"]): row for row in metric_rows}
    for model_name in MODELS:
        for split in EVAL_SPLITS:
            base = by_key[(model_name, split, "original")]
            for condition in CONDITIONS:
                row = by_key[(model_name, split, condition)]
                base_f1 = float(base["macro_f1"])
                survival_rows.append({
                    "model": model_name,
                    "split": split,
                    "condition": condition,
                    "baseline_condition": "original",
                    "accuracy": row["accuracy"],
                    "macro_f1": row["macro_f1"],
                    "weighted_f1": row["weighted_f1"],
                    "accuracy_difference_vs_original": round(float(row["accuracy"]) - float(base["accuracy"]), 6),
                    "macro_f1_difference_vs_original": round(float(row["macro_f1"]) - base_f1, 6),
                    "weighted_f1_difference_vs_original": round(float(row["weighted_f1"]) - float(base["weighted_f1"]), 6),
                    "macro_f1_survival_ratio": round(float(row["macro_f1"]) / base_f1, 6) if base_f1 else 0.0,
                    "rows": row["rows"],
                })

    write_csv(PREDICTIONS, prediction_rows, ["model", "split", "condition", "text_id", "passage_id", "true_author", "predicted_author", "correct"])
    write_csv(METRICS, metric_rows, ["model", "split", "condition", "accuracy", "macro_f1", "weighted_f1", "rows", "train_condition", "scaler_fit_scope"])
    write_csv(SURVIVAL, survival_rows, ["model", "split", "condition", "baseline_condition", "accuracy", "macro_f1", "weighted_f1", "accuracy_difference_vs_original", "macro_f1_difference_vs_original", "weighted_f1_difference_vs_original", "macro_f1_survival_ratio", "rows"])
    write_csv(CONFUSION, confusion_all, ["model", "split", "condition", "actual_author", "predicted_author", "count"])
    write_csv(CLASS_REPORT, class_report_all, ["model", "split", "condition", "author_id", "precision", "recall", "f1", "support"])

    artifacts = [PREDICTIONS, METRICS, SURVIVAL, CONFUSION, CLASS_REPORT]
    manifest_rows = [{"artifact": p.stem, "path": p.relative_to(ROOT).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha_file(p)} for p in artifacts]
    write_csv(MANIFEST, manifest_rows, ["artifact", "path", "size_bytes", "sha256"])

    best_original_test = max((row for row in metric_rows if row["split"] == "test" and row["condition"] == "original"), key=lambda r: float(r["macro_f1"]))
    model = best_original_test["model"]
    test_survival = [row for row in survival_rows if row["split"] == "test" and row["model"] == model]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Step 16 Rewritten-Condition Author Classification Report\n\n"
        "## Status\n\nComplete when generated locally and checker passes.\n\n"
        "## Design\n\n"
        "- one same-condition classifier per condition\n"
        "- train rows per condition: 252\n"
        "- validation rows per condition: 54\n"
        "- test rows per condition: 54\n"
        "- scaler fit scope: train rows of each condition only\n"
        f"- feature columns: {len(feature_cols)}\n\n"
        "## Best original-condition test model\n\n"
        f"- model: {model}\n"
        f"- original test macro F1: {best_original_test['macro_f1']}\n"
        f"- original test accuracy: {best_original_test['accuracy']}\n\n"
        "## Test same-condition separability for that model\n\n" + "".join(
            f"- {row['condition']}: macro_f1={row['macro_f1']}, survival_ratio={row['macro_f1_survival_ratio']}\n"
            for row in test_survival
        ),
        encoding="utf-8",
    )
    print("Ran rewritten-condition author classification for 3 models across 4 conditions.")
    print(f"Best original-condition test model: {model}; original test macro F1={best_original_test['macro_f1']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
