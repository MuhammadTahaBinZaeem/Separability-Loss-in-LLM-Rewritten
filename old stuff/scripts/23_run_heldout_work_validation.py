"""
E2: held-out-work validation.

Run from repository root:

    python scripts/23_run_heldout_work_validation.py

This script creates two leave-one-work-out folds. Each author contributes two
works, so fold 1 trains on the first listed work for every author and tests on
the second; fold 2 reverses the direction.

The script does not modify frozen Step 1-20 outputs. It writes extension outputs.
"""

from __future__ import annotations

import csv
import hashlib
import math
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META_DIR = ROOT / "metadata"
RESULTS_DIR = ROOT / "data" / "results"
LOGS_DIR = ROOT / "logs"

MODELING_METADATA = ROOT / "data" / "modeling" / "modeling_metadata.csv"
X_RAW = ROOT / "data" / "modeling" / "X_stylometric_raw.csv"
Y_LABELS = ROOT / "data" / "modeling" / "y_author_labels.csv"
FEATURE_COLUMNS = ROOT / "metadata" / "modeling_feature_columns.csv"
SELECTED_COUNTS_BY_WORK = ROOT / "metadata" / "selected_counts_by_work.csv"

FOLD_REGISTRY = META_DIR / "heldout_work_fold_registry.csv"
TRANSFER_PREDICTIONS = RESULTS_DIR / "heldout_work_transfer_predictions.csv"
TRANSFER_SUMMARY = META_DIR / "heldout_work_transfer_summary.csv"
SAME_CONDITION_SUMMARY = META_DIR / "heldout_work_same_condition_summary.csv"
DISTANCE_SUMMARY = META_DIR / "heldout_work_distance_summary.csv"
MANIFEST = META_DIR / "heldout_work_manifest.csv"
REPORT = LOGS_DIR / "heldout_work_validation_report.md"

AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
REWRITE_CONDITIONS = ["paraphrase", "modernize", "simplify"]
MODELS = ["nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"]
FEATURE_SETS_FOR_DISTANCE = ["function_word", "all_features"]


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


FITTERS = {
    "nearest_centroid": fit_nearest_centroid,
    "diagonal_gaussian_nb": fit_gaussian_nb,
    "linear_discriminant_shrinkage": fit_lda_shrinkage,
}
PREDICTORS = {
    "nearest_centroid": predict_nearest_centroid,
    "diagonal_gaussian_nb": predict_gaussian_nb,
    "linear_discriminant_shrinkage": predict_lda_shrinkage,
}


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


def build_dataset(meta_rows: list[dict[str, str]], x_rows: list[dict[str, str]], y_rows: list[dict[str, str]], feature_cols: list[str]) -> list[dict[str, object]]:
    by_text_x = {row["text_id"]: row for row in x_rows}
    by_text_y = {row["text_id"]: row for row in y_rows}
    dataset = []
    for row in meta_rows:
        text_id = row["text_id"]
        dataset.append({
            "meta": row,
            "x_all": [float(by_text_x[text_id][col]) for col in feature_cols],
            "features": {col: float(by_text_x[text_id][col]) for col in feature_cols},
            "y": by_text_y[text_id]["author_id"],
        })
    return dataset


def build_folds(work_rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    by_author: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in work_rows:
        by_author[row["author_id"]].append(row)
    missing = [author for author in AUTHORS if len(by_author[author]) != 2]
    if missing:
        raise RuntimeError(f"Each author must have exactly two works. Problem authors: {missing}")

    folds = []
    registry = []
    for fold_index, fold_id in enumerate(["work_fold_1", "work_fold_2"]):
        train_by_author = {}
        test_by_author = {}
        for author in AUTHORS:
            works = by_author[author]
            train_work = works[fold_index % 2]
            test_work = works[(fold_index + 1) % 2]
            train_by_author[author] = train_work["work_id"]
            test_by_author[author] = test_work["work_id"]
            registry.append({
                "fold_id": fold_id,
                "author_id": author,
                "train_work_id": train_work["work_id"],
                "train_work_title": train_work["work_title"],
                "test_work_id": test_work["work_id"],
                "test_work_title": test_work["work_title"],
                "train_selected_passages": train_work["selected_passages"],
                "test_selected_passages": test_work["selected_passages"],
            })
        folds.append({"fold_id": fold_id, "train_by_author": train_by_author, "test_by_author": test_by_author})
    return folds, registry


def is_train_work(row: dict[str, object], fold: dict[str, object]) -> bool:
    meta = row["meta"]
    return meta["work_id"] == fold["train_by_author"][meta["author_id"]]


def is_test_work(row: dict[str, object], fold: dict[str, object]) -> bool:
    meta = row["meta"]
    return meta["work_id"] == fold["test_by_author"][meta["author_id"]]


def fit_models(train_rows: list[dict[str, object]], feature_indices: list[int]) -> tuple[dict[str, object], list[float], list[float]]:
    x_train_raw = [[row["x_all"][i] for i in feature_indices] for row in train_rows]
    y_train = [row["y"] for row in train_rows]
    means, stds = zscore_fit(x_train_raw)
    x_train = zscore_apply(x_train_raw, means, stds)
    fitted = {model_name: FITTERS[model_name](x_train, y_train) for model_name in MODELS}
    return fitted, means, stds


def run_transfer(folds: list[dict[str, object]], dataset: list[dict[str, object]], feature_indices: list[int]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    prediction_rows = []
    metric_rows = []
    for fold in folds:
        fold_id = fold["fold_id"]
        train_rows = [r for r in dataset if is_train_work(r, fold) and r["meta"]["condition"] == "original"]
        fitted, means, stds = fit_models(train_rows, feature_indices)
        for model_name in MODELS:
            for condition in CONDITIONS:
                eval_rows = [r for r in dataset if is_test_work(r, fold) and r["meta"]["condition"] == condition]
                x_eval_raw = [[r["x_all"][i] for i in feature_indices] for r in eval_rows]
                x_eval = zscore_apply(x_eval_raw, means, stds)
                y_eval = [r["y"] for r in eval_rows]
                preds = PREDICTORS[model_name](fitted[model_name], x_eval)
                metrics = evaluate(y_eval, preds)
                metric_rows.append({"fold_id": fold_id, "model": model_name, "condition": condition, **metrics, "rows": len(y_eval)})
                for item, pred in zip(eval_rows, preds):
                    prediction_rows.append({
                        "fold_id": fold_id,
                        "model": model_name,
                        "condition": condition,
                        "text_id": item["meta"]["text_id"],
                        "passage_id": item["meta"]["passage_id"],
                        "train_work_for_author": fold["train_by_author"][item["meta"]["author_id"]],
                        "test_work_id": item["meta"]["work_id"],
                        "true_author": item["y"],
                        "predicted_author": pred,
                        "correct": int(item["y"] == pred),
                    })

    by_key = {(row["fold_id"], row["model"], row["condition"]): row for row in metric_rows}
    summary_rows = []
    for row in metric_rows:
        base = by_key[(row["fold_id"], row["model"], "original")]
        summary_rows.append({
            "fold_id": row["fold_id"],
            "model": row["model"],
            "condition": row["condition"],
            "baseline_condition": "original",
            "accuracy": row["accuracy"],
            "macro_f1": row["macro_f1"],
            "weighted_f1": row["weighted_f1"],
            "accuracy_loss_vs_original": round(float(base["accuracy"]) - float(row["accuracy"]), 6),
            "macro_f1_loss_vs_original": round(float(base["macro_f1"]) - float(row["macro_f1"]), 6),
            "weighted_f1_loss_vs_original": round(float(base["weighted_f1"]) - float(row["weighted_f1"]), 6),
            "rows": row["rows"],
        })

    # Add fold-averaged summary rows.
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in summary_rows:
        grouped[(row["model"], row["condition"])].append(row)
    for (model, condition), rows in grouped.items():
        if len(rows) == 2:
            base_rows = [r for r in rows]
            summary_rows.append({
                "fold_id": "mean_across_folds",
                "model": model,
                "condition": condition,
                "baseline_condition": "original",
                "accuracy": round(statistics.mean(float(r["accuracy"]) for r in base_rows), 6),
                "macro_f1": round(statistics.mean(float(r["macro_f1"]) for r in base_rows), 6),
                "weighted_f1": round(statistics.mean(float(r["weighted_f1"]) for r in base_rows), 6),
                "accuracy_loss_vs_original": round(statistics.mean(float(r["accuracy_loss_vs_original"]) for r in base_rows), 6),
                "macro_f1_loss_vs_original": round(statistics.mean(float(r["macro_f1_loss_vs_original"]) for r in base_rows), 6),
                "weighted_f1_loss_vs_original": round(statistics.mean(float(r["weighted_f1_loss_vs_original"]) for r in base_rows), 6),
                "rows": sum(int(r["rows"]) for r in base_rows),
            })
    return prediction_rows, summary_rows


def run_same_condition(folds: list[dict[str, object]], dataset: list[dict[str, object]], feature_indices: list[int]) -> list[dict[str, object]]:
    metric_rows = []
    for fold in folds:
        fold_id = fold["fold_id"]
        for condition in CONDITIONS:
            train_rows = [r for r in dataset if is_train_work(r, fold) and r["meta"]["condition"] == condition]
            eval_rows = [r for r in dataset if is_test_work(r, fold) and r["meta"]["condition"] == condition]
            fitted, means, stds = fit_models(train_rows, feature_indices)
            for model_name in MODELS:
                x_eval_raw = [[r["x_all"][i] for i in feature_indices] for r in eval_rows]
                x_eval = zscore_apply(x_eval_raw, means, stds)
                y_eval = [r["y"] for r in eval_rows]
                preds = PREDICTORS[model_name](fitted[model_name], x_eval)
                metrics = evaluate(y_eval, preds)
                metric_rows.append({"fold_id": fold_id, "model": model_name, "condition": condition, **metrics, "rows": len(y_eval)})

    by_key = {(row["fold_id"], row["model"], row["condition"]): row for row in metric_rows}
    summary_rows = []
    for row in metric_rows:
        base = by_key[(row["fold_id"], row["model"], "original")]
        base_macro = float(base["macro_f1"])
        macro = float(row["macro_f1"])
        summary_rows.append({
            **row,
            "baseline_condition": "original",
            "macro_f1_difference_vs_original": round(macro - base_macro, 6),
            "macro_f1_survival_ratio": round(macro / base_macro, 6) if base_macro else 0.0,
        })

    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in summary_rows:
        grouped[(row["model"], row["condition"])].append(row)
    for (model, condition), rows in grouped.items():
        if len(rows) == 2:
            summary_rows.append({
                "fold_id": "mean_across_folds",
                "model": model,
                "condition": condition,
                "accuracy": round(statistics.mean(float(r["accuracy"]) for r in rows), 6),
                "macro_f1": round(statistics.mean(float(r["macro_f1"]) for r in rows), 6),
                "weighted_f1": round(statistics.mean(float(r["weighted_f1"]) for r in rows), 6),
                "rows": sum(int(r["rows"]) for r in rows),
                "baseline_condition": "original",
                "macro_f1_difference_vs_original": round(statistics.mean(float(r["macro_f1_difference_vs_original"]) for r in rows), 6),
                "macro_f1_survival_ratio": round(statistics.mean(float(r["macro_f1_survival_ratio"]) for r in rows), 6),
            })
    return summary_rows


def mean_vector(rows: list[dict[str, object]], features: list[str]) -> list[float]:
    return [sum(float(row["features"][feature]) for row in rows) / len(rows) for feature in features]


def mean_abs_distance(a: list[float], b: list[float]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a) if a else 0.0


def zscore_rows(rows: list[dict[str, object]], features: list[str]) -> list[dict[str, object]]:
    means, stds = {}, {}
    for feature in features:
        vals = [float(row["features"][feature]) for row in rows]
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(var)
        means[feature] = mean
        stds[feature] = std if std > 0 else 1.0
    zrows = []
    for row in rows:
        zrow = {"author_id": row["y"], "features": {}}
        for feature in features:
            zrow["features"][feature] = (float(row["features"][feature]) - means[feature]) / stds[feature]
        zrows.append(zrow)
    return zrows


def run_distance(folds: list[dict[str, object]], dataset: list[dict[str, object]], feature_cols: list[str]) -> list[dict[str, object]]:
    function_features = [feature for feature in feature_cols if feature.startswith("fw_")]
    feature_sets = {"function_word": function_features, "all_features": feature_cols}
    rows_out = []
    for fold in folds:
        fold_id = fold["fold_id"]
        for feature_set, features in feature_sets.items():
            baseline_mean = None
            for condition in CONDITIONS:
                test_rows = [row for row in dataset if is_test_work(row, fold) and row["meta"]["condition"] == condition]
                zrows = zscore_rows(test_rows, features)
                by_author = {author: [row for row in zrows if row["author_id"] == author] for author in AUTHORS}
                vals = []
                if all(by_author[author] for author in AUTHORS):
                    centroids = {author: mean_vector(by_author[author], features) for author in AUTHORS}
                    vals = [mean_abs_distance(centroids[a], centroids[b]) for a, b in combinations(AUTHORS, 2)]
                mean_delta = statistics.mean(vals) if vals else 0.0
                if condition == "original":
                    baseline_mean = mean_delta
                rows_out.append({
                    "fold_id": fold_id,
                    "feature_set": feature_set,
                    "condition": condition,
                    "pair_count": len(vals),
                    "mean_burrows_delta": round(mean_delta, 9),
                    "median_burrows_delta": round(statistics.median(vals), 9) if vals else 0.0,
                    "min_burrows_delta": round(min(vals), 9) if vals else 0.0,
                    "max_burrows_delta": round(max(vals), 9) if vals else 0.0,
                    "std_burrows_delta": round(statistics.pstdev(vals), 9) if vals else 0.0,
                    "distance_ratio_vs_original": round(mean_delta / baseline_mean, 9) if baseline_mean else 1.0,
                })

    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows_out:
        grouped[(row["feature_set"], row["condition"])].append(row)
    for (feature_set, condition), rows in grouped.items():
        if len(rows) == 2:
            rows_out.append({
                "fold_id": "mean_across_folds",
                "feature_set": feature_set,
                "condition": condition,
                "pair_count": sum(int(r["pair_count"]) for r in rows),
                "mean_burrows_delta": round(statistics.mean(float(r["mean_burrows_delta"]) for r in rows), 9),
                "median_burrows_delta": round(statistics.mean(float(r["median_burrows_delta"]) for r in rows), 9),
                "min_burrows_delta": round(statistics.mean(float(r["min_burrows_delta"]) for r in rows), 9),
                "max_burrows_delta": round(statistics.mean(float(r["max_burrows_delta"]) for r in rows), 9),
                "std_burrows_delta": round(statistics.mean(float(r["std_burrows_delta"]) for r in rows), 9),
                "distance_ratio_vs_original": round(statistics.mean(float(r["distance_ratio_vs_original"]) for r in rows), 9),
            })
    return rows_out


def main() -> int:
    required = [MODELING_METADATA, X_RAW, Y_LABELS, FEATURE_COLUMNS, SELECTED_COUNTS_BY_WORK]
    missing = [path for path in required if not path.exists()]
    if missing:
        for path in missing:
            print(f"Missing input: {path.relative_to(ROOT)}")
        return 1

    meta_rows = read_csv(MODELING_METADATA)
    x_rows = read_csv(X_RAW)
    y_rows = read_csv(Y_LABELS)
    feature_manifest = read_csv(FEATURE_COLUMNS)
    feature_cols = [row["feature"] for row in feature_manifest]
    work_rows = read_csv(SELECTED_COUNTS_BY_WORK)
    folds, fold_registry = build_folds(work_rows)
    dataset = build_dataset(meta_rows, x_rows, y_rows, feature_cols)
    full_indices = list(range(len(feature_cols)))

    predictions, transfer_summary = run_transfer(folds, dataset, full_indices)
    same_condition_summary = run_same_condition(folds, dataset, full_indices)
    distance_summary = run_distance(folds, dataset, feature_cols)

    write_csv(FOLD_REGISTRY, fold_registry, [
        "fold_id", "author_id", "train_work_id", "train_work_title", "test_work_id",
        "test_work_title", "train_selected_passages", "test_selected_passages",
    ])
    write_csv(TRANSFER_PREDICTIONS, predictions, [
        "fold_id", "model", "condition", "text_id", "passage_id", "train_work_for_author",
        "test_work_id", "true_author", "predicted_author", "correct",
    ])
    write_csv(TRANSFER_SUMMARY, transfer_summary, [
        "fold_id", "model", "condition", "baseline_condition", "accuracy", "macro_f1",
        "weighted_f1", "accuracy_loss_vs_original", "macro_f1_loss_vs_original",
        "weighted_f1_loss_vs_original", "rows",
    ])
    write_csv(SAME_CONDITION_SUMMARY, same_condition_summary, [
        "fold_id", "model", "condition", "accuracy", "macro_f1", "weighted_f1",
        "rows", "baseline_condition", "macro_f1_difference_vs_original",
        "macro_f1_survival_ratio",
    ])
    write_csv(DISTANCE_SUMMARY, distance_summary, [
        "fold_id", "feature_set", "condition", "pair_count", "mean_burrows_delta",
        "median_burrows_delta", "min_burrows_delta", "max_burrows_delta",
        "std_burrows_delta", "distance_ratio_vs_original",
    ])

    artifacts = [FOLD_REGISTRY, TRANSFER_PREDICTIONS, TRANSFER_SUMMARY, SAME_CONDITION_SUMMARY, DISTANCE_SUMMARY]
    manifest_rows = [{
        "artifact": path.stem,
        "path": path.relative_to(ROOT).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha_file(path),
    } for path in artifacts]
    write_csv(MANIFEST, manifest_rows, ["artifact", "path", "size_bytes", "sha256"])

    mean_transfer = [row for row in transfer_summary if row["fold_id"] == "mean_across_folds" and row["model"] == "nearest_centroid"]
    mean_distance = [row for row in distance_summary if row["fold_id"] == "mean_across_folds"]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# E2 Held-Out-Work Validation Report\n\n"
        "## Status\n\nComplete when generated locally and checker passes.\n\n"
        "## Design\n\n"
        "- two folds: first-work-to-second-work and second-work-to-first-work.\n"
        "- training condition for transfer: original only.\n"
        "- evaluation conditions: original, paraphrase, modernize, simplify on held-out works.\n\n"
        "## Output rows\n\n"
        f"- fold registry rows: {len(fold_registry)}\n"
        f"- transfer prediction rows: {len(predictions)}\n"
        f"- transfer summary rows: {len(transfer_summary)}\n"
        f"- same-condition summary rows: {len(same_condition_summary)}\n"
        f"- distance summary rows: {len(distance_summary)}\n\n"
        "## Mean-across-fold nearest-centroid transfer summary\n\n"
        + "".join(
            f"- {row['condition']}: macro_f1={row['macro_f1']}, loss={row['macro_f1_loss_vs_original']}, rows={row['rows']}\n"
            for row in mean_transfer
        )
        + "\n## Mean-across-fold distance ratios\n\n"
        + "".join(
            f"- {row['feature_set']} / {row['condition']}: ratio={row['distance_ratio_vs_original']}\n"
            for row in mean_distance
        ),
        encoding="utf-8",
    )

    print("Ran E2 held-out-work validation.")
    print(f"Fold registry rows: {len(fold_registry)}")
    print(f"Transfer prediction rows: {len(predictions)}")
    print(f"Wrote {len(artifacts)} output artifacts plus manifest and report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
