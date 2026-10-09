"""
Step 14: original-condition author classification baseline.

Run from repository root after Step 13:

    python scripts/15_run_original_author_baseline.py

Inputs:
- data/modeling/modeling_metadata.csv
- data/modeling/X_stylometric_raw.csv
- data/modeling/y_author_labels.csv
- metadata/modeling_feature_columns.csv

Outputs:
- data/results/original_author_baseline_predictions.csv
- metadata/original_author_baseline_metrics.csv
- metadata/original_author_baseline_confusion_matrices.csv
- metadata/original_author_baseline_classification_report.csv
- metadata/original_author_baseline_manifest.csv
- logs/step_14_original_author_baseline_report.md
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

PREDICTIONS = RESULTS / "original_author_baseline_predictions.csv"
METRICS = META / "original_author_baseline_metrics.csv"
CONFUSION = META / "original_author_baseline_confusion_matrices.csv"
CLASS_REPORT = META / "original_author_baseline_classification_report.csv"
MANIFEST = META / "original_author_baseline_manifest.csv"
REPORT = LOGS / "step_14_original_author_baseline_report.md"

AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
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
    means = []
    stds = []
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


def dot(a: list[float], b: list[float]) -> float:
    return sum(x*y for x, y in zip(a, b))


def euclidean2(a: list[float], b: list[float]) -> float:
    return sum((x-y)**2 for x, y in zip(a, b))


def class_counts(labels: list[str]) -> Counter[str]:
    return Counter(labels)


def fit_nearest_centroid(x: list[list[float]], y: list[str]) -> dict[str, list[float]]:
    by_class: dict[str, list[list[float]]] = defaultdict(list)
    for row, label in zip(x, y):
        by_class[label].append(row)
    centroids = {}
    for label, rows in by_class.items():
        centroids[label] = [sum(row[j] for row in rows) / len(rows) for j in range(len(rows[0]))]
    return centroids


def predict_nearest_centroid(model: dict[str, list[float]], x: list[list[float]]) -> list[str]:
    preds = []
    for row in x:
        preds.append(min(model, key=lambda label: euclidean2(row, model[label])))
    return preds


def fit_gaussian_nb(x: list[list[float]], y: list[str]) -> dict[str, object]:
    by_class: dict[str, list[list[float]]] = defaultdict(list)
    for row, label in zip(x, y):
        by_class[label].append(row)
    priors = {label: len(rows) / len(x) for label, rows in by_class.items()}
    means = {}
    variances = {}
    for label, rows in by_class.items():
        p = len(rows[0])
        means[label] = [sum(row[j] for row in rows) / len(rows) for j in range(p)]
        var = []
        for j in range(p):
            m = means[label][j]
            v = sum((row[j] - m) ** 2 for row in rows) / len(rows)
            var.append(max(v, 1e-6))
        variances[label] = var
    return {"priors": priors, "means": means, "variances": variances}


def predict_gaussian_nb(model: dict[str, object], x: list[list[float]]) -> list[str]:
    priors = model["priors"]
    means = model["means"]
    variances = model["variances"]
    preds = []
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
    # Diagonal pooled-variance linear discriminant. This is a stable standard-library
    # approximation to linear discriminant classification for small n / many features.
    counts = Counter(y)
    by_class: dict[str, list[list[float]]] = defaultdict(list)
    for row, label in zip(x, y):
        by_class[label].append(row)
    p = len(x[0])
    means = {}
    for label, rows in by_class.items():
        means[label] = [sum(row[j] for row in rows) / len(rows) for j in range(p)]
    pooled = []
    for j in range(p):
        ss = 0.0
        denom = 0
        for label, rows in by_class.items():
            m = means[label][j]
            ss += sum((row[j] - m) ** 2 for row in rows)
            denom += max(len(rows) - 1, 0)
        pooled.append(max(ss / max(denom, 1), 1e-6))
    priors = {label: counts[label] / len(y) for label in counts}
    return {"means": means, "pooled_variances": pooled, "priors": priors}


def predict_lda_shrinkage(model: dict[str, object], x: list[list[float]]) -> list[str]:
    means = model["means"]
    pooled = model["pooled_variances"]
    priors = model["priors"]
    preds = []
    for row in x:
        scores = {}
        for label, mean in means.items():
            # Linear discriminant under diagonal shared covariance.
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


def confusion_rows(model_name: str, split: str, y_true: list[str], y_pred: list[str]) -> list[dict[str, object]]:
    rows = []
    for actual in AUTHORS:
        for predicted in AUTHORS:
            rows.append({
                "model": model_name,
                "split": split,
                "actual_author": actual,
                "predicted_author": predicted,
                "count": sum(1 for a, b in zip(y_true, y_pred) if a == actual and b == predicted),
            })
    return rows


def report_rows(model_name: str, split: str, y_true: list[str], y_pred: list[str]) -> list[dict[str, object]]:
    rows = []
    for label in AUTHORS:
        p, r, f, s = precision_recall_f1(y_true, y_pred, label)
        rows.append({
            "model": model_name,
            "split": split,
            "author_id": label,
            "precision": round(p, 6),
            "recall": round(r, 6),
            "f1": round(f, 6),
            "support": s,
        })
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

    original_meta = [row for row in meta_rows if row["condition"] == "original"]
    if len(original_meta) != 360:
        print(f"Expected 360 original rows, found {len(original_meta)}")
        return 1

    dataset = []
    for row in original_meta:
        text_id = row["text_id"]
        x = [float(by_text_x[text_id][col]) for col in feature_cols]
        y = by_text_y[text_id]["author_id"]
        dataset.append({"meta": row, "x": x, "y": y})

    train = [r for r in dataset if r["meta"]["split"] == "train"]
    validation = [r for r in dataset if r["meta"]["split"] == "validation"]
    test = [r for r in dataset if r["meta"]["split"] == "test"]
    if (len(train), len(validation), len(test)) != (252, 54, 54):
        print(f"Unexpected split sizes: {len(train)}, {len(validation)}, {len(test)}")
        return 1

    x_train_raw = [r["x"] for r in train]
    y_train = [r["y"] for r in train]
    means, stds = zscore_fit(x_train_raw)
    x_train = zscore_apply(x_train_raw, means, stds)
    splits = {
        "validation": (validation, zscore_apply([r["x"] for r in validation], means, stds), [r["y"] for r in validation]),
        "test": (test, zscore_apply([r["x"] for r in test], means, stds), [r["y"] for r in test]),
    }

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

    prediction_rows = []
    metric_rows = []
    confusion_all = []
    class_report_all = []
    for model_name in MODELS:
        for split_name, (split_data, x_eval, y_eval) in splits.items():
            preds = predictors[model_name](fitted[model_name], x_eval)
            metrics = evaluate(y_eval, preds)
            metric_rows.append({"model": model_name, "split": split_name, **metrics, "rows": len(y_eval)})
            confusion_all.extend(confusion_rows(model_name, split_name, y_eval, preds))
            class_report_all.extend(report_rows(model_name, split_name, y_eval, preds))
            for item, pred in zip(split_data, preds):
                prediction_rows.append({
                    "model": model_name,
                    "split": split_name,
                    "text_id": item["meta"]["text_id"],
                    "passage_id": item["meta"]["passage_id"],
                    "condition": item["meta"]["condition"],
                    "true_author": item["y"],
                    "predicted_author": pred,
                    "correct": int(item["y"] == pred),
                })

    write_csv(PREDICTIONS, prediction_rows, ["model", "split", "text_id", "passage_id", "condition", "true_author", "predicted_author", "correct"])
    write_csv(METRICS, metric_rows, ["model", "split", "accuracy", "macro_f1", "weighted_f1", "rows"])
    write_csv(CONFUSION, confusion_all, ["model", "split", "actual_author", "predicted_author", "count"])
    write_csv(CLASS_REPORT, class_report_all, ["model", "split", "author_id", "precision", "recall", "f1", "support"])

    artifacts = [PREDICTIONS, METRICS, CONFUSION, CLASS_REPORT]
    manifest_rows = [{"artifact": p.stem, "path": p.relative_to(ROOT).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha_file(p)} for p in artifacts]
    write_csv(MANIFEST, manifest_rows, ["artifact", "path", "size_bytes", "sha256"])

    best_validation = max((row for row in metric_rows if row["split"] == "validation"), key=lambda r: float(r["macro_f1"]))
    best_model = best_validation["model"]
    test_for_best = [row for row in metric_rows if row["split"] == "test" and row["model"] == best_model][0]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Step 14 Original Author Classification Baseline Report\n\n"
        "## Status\n\nComplete when generated locally and checker passes.\n\n"
        "## Dataset\n\n"
        "- condition used: original only\n"
        f"- train rows: {len(train)}\n"
        f"- validation rows: {len(validation)}\n"
        f"- test rows: {len(test)}\n"
        f"- feature columns: {len(feature_cols)}\n\n"
        "## Best validation model\n\n"
        f"- model: {best_model}\n"
        f"- validation macro F1: {best_validation['macro_f1']}\n"
        f"- test macro F1: {test_for_best['macro_f1']}\n"
        f"- test accuracy: {test_for_best['accuracy']}\n",
        encoding="utf-8",
    )
    print(f"Ran original-condition author baseline for {len(MODELS)} models.")
    print(f"Best validation model: {best_model}; test macro F1={test_for_best['macro_f1']}; test accuracy={test_for_best['accuracy']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
