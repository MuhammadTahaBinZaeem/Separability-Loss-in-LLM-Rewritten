"""
E3: warning-row sensitivity analysis.

Run from repository root after the frozen Step 20 package exists:

    python scripts/22_run_warning_row_sensitivity.py

Purpose:
- recompute the main Step 15-19 empirical metrics under three QC subsets:
  1. all_rows;
  2. qc_pass_only;
  3. pass_plus_non_hard_length_warning.

This script does not modify the frozen core outputs. It writes extension outputs only.
"""

from __future__ import annotations

import csv
import hashlib
import math
import random
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
REWRITE_QC = ROOT / "metadata" / "rewrite_qc_report.csv"

TRANSFER_PREDICTIONS = RESULTS_DIR / "warning_row_sensitivity_transfer_predictions.csv"
TRANSFER_SUMMARY = META_DIR / "warning_row_sensitivity_transfer_summary.csv"
SAME_CONDITION_SUMMARY = META_DIR / "warning_row_sensitivity_same_condition_summary.csv"
DISTANCE_SUMMARY = META_DIR / "warning_row_sensitivity_distance_summary.csv"
FEATURE_FAMILY_SUMMARY = META_DIR / "warning_row_sensitivity_feature_family_summary.csv"
BOOTSTRAP_SUMMARY = META_DIR / "warning_row_sensitivity_bootstrap_macro_f1_loss.csv"
SUBSET_COUNTS = META_DIR / "warning_row_sensitivity_subset_counts.csv"
MANIFEST = META_DIR / "warning_row_sensitivity_manifest.csv"
REPORT = LOGS_DIR / "warning_row_sensitivity_report.md"

AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
REWRITE_CONDITIONS = ["paraphrase", "modernize", "simplify"]
EVAL_SPLITS = ["validation", "test"]
MODELS = ["nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"]
SUBSETS = [
    ("all_rows", "All original and rewrite rows, including QC warning rows."),
    ("qc_pass_only", "Original rows plus rewrite rows with qc_status == pass."),
    ("pass_plus_non_hard_length_warning", "Original rows plus pass rows and warning rows that do not contain length_hard_warning."),
]
BOOTSTRAP_ITERATIONS = 2000
BOOTSTRAP_SEED = 20260601


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
    if not matrix:
        return [], []
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
    if not matrix:
        return []
    return [[(row[j] - means[j]) / stds[j] for j in range(len(row))] for row in matrix]


def euclidean2(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def fit_nearest_centroid(x: list[list[float]], y: list[str]) -> dict[str, list[float]]:
    by_class: dict[str, list[list[float]]] = defaultdict(list)
    for row, label in zip(x, y):
        by_class[label].append(row)
    return {
        label: [sum(row[j] for row in rows) / len(rows) for j in range(len(rows[0]))]
        for label, rows in by_class.items()
    }


def predict_nearest_centroid(model: dict[str, list[float]], x: list[list[float]]) -> list[str]:
    if not model:
        return []
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
    means = {
        label: [sum(row[j] for row in rows) / len(rows) for j in range(p)]
        for label, rows in by_class.items()
    }
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
    if not y_true:
        return {"accuracy": 0.0, "macro_f1": 0.0, "weighted_f1": 0.0}
    accuracy = sum(1 for a, b in zip(y_true, y_pred) if a == b) / len(y_true)
    per = [precision_recall_f1(y_true, y_pred, label) for label in AUTHORS]
    macro_f1 = sum(x[2] for x in per) / len(per)
    total = sum(x[3] for x in per)
    weighted_f1 = sum(x[2] * x[3] for x in per) / total if total else 0.0
    return {"accuracy": round(accuracy, 6), "macro_f1": round(macro_f1, 6), "weighted_f1": round(weighted_f1, 6)}


def build_dataset(
    meta_rows: list[dict[str, str]],
    x_rows: list[dict[str, str]],
    y_rows: list[dict[str, str]],
    feature_cols: list[str],
    qc_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    by_text_x = {row["text_id"]: row for row in x_rows}
    by_text_y = {row["text_id"]: row for row in y_rows}
    qc_by_key = {(row["passage_id"], row["condition"]): row for row in qc_rows}

    dataset = []
    for row in meta_rows:
        text_id = row["text_id"]
        condition = row["condition"]
        qc = {"qc_status": row.get("qc_status", "pass"), "qc_flags": row.get("qc_flags", "")}
        if condition != "original":
            qc = qc_by_key.get((row["passage_id"], condition), qc)
        dataset.append({
            "meta": row,
            "x_all": [float(by_text_x[text_id][col]) for col in feature_cols],
            "features": {col: float(by_text_x[text_id][col]) for col in feature_cols},
            "y": by_text_y[text_id]["author_id"],
            "qc_status": qc.get("qc_status", ""),
            "qc_flags": qc.get("qc_flags", ""),
        })
    return dataset


def include_in_subset(row: dict[str, object], subset_id: str) -> bool:
    meta = row["meta"]
    if meta["condition"] == "original":
        return True
    status = str(row.get("qc_status", ""))
    flags = str(row.get("qc_flags", ""))
    if subset_id == "all_rows":
        return True
    if subset_id == "qc_pass_only":
        return status == "pass"
    if subset_id == "pass_plus_non_hard_length_warning":
        return status in {"pass", "warning"} and "length_hard_warning" not in flags.split(";")
    raise ValueError(f"Unknown subset: {subset_id}")


def subset_dataset(dataset: list[dict[str, object]], subset_id: str) -> list[dict[str, object]]:
    return [row for row in dataset if include_in_subset(row, subset_id)]


def fit_models(train_rows: list[dict[str, object]], feature_indices: list[int]) -> tuple[dict[str, object], list[float], list[float]]:
    x_train_raw = [[row["x_all"][i] for i in feature_indices] for row in train_rows]
    y_train = [row["y"] for row in train_rows]
    means, stds = zscore_fit(x_train_raw)
    x_train = zscore_apply(x_train_raw, means, stds)
    fitted = {model_name: FITTERS[model_name](x_train, y_train) for model_name in MODELS}
    return fitted, means, stds


def run_transfer(
    subset_id: str,
    rows: list[dict[str, object]],
    feature_indices: list[int],
    model_names: list[str] | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    model_names = model_names or MODELS
    train = [r for r in rows if r["meta"]["split"] == "train" and r["meta"]["condition"] == "original"]
    if not train:
        raise RuntimeError(f"No train/original rows available for subset {subset_id}.")
    fitted, means, stds = fit_models(train, feature_indices)

    prediction_rows = []
    metric_rows = []
    for model_name in model_names:
        for split in EVAL_SPLITS:
            for condition in CONDITIONS:
                eval_rows = [r for r in rows if r["meta"]["split"] == split and r["meta"]["condition"] == condition]
                x_eval_raw = [[r["x_all"][i] for i in feature_indices] for r in eval_rows]
                x_eval = zscore_apply(x_eval_raw, means, stds)
                y_eval = [r["y"] for r in eval_rows]
                preds = PREDICTORS[model_name](fitted[model_name], x_eval) if eval_rows else []
                metrics = evaluate(y_eval, preds)
                metric_rows.append({
                    "subset_id": subset_id,
                    "model": model_name,
                    "split": split,
                    "condition": condition,
                    **metrics,
                    "rows": len(y_eval),
                })
                for item, pred in zip(eval_rows, preds):
                    prediction_rows.append({
                        "subset_id": subset_id,
                        "model": model_name,
                        "split": split,
                        "condition": condition,
                        "text_id": item["meta"]["text_id"],
                        "passage_id": item["meta"]["passage_id"],
                        "true_author": item["y"],
                        "predicted_author": pred,
                        "correct": int(item["y"] == pred),
                        "qc_status": item["qc_status"],
                        "qc_flags": item["qc_flags"],
                    })

    by_key = {(row["model"], row["split"], row["condition"]): row for row in metric_rows}
    degradation_rows = []
    for model_name in model_names:
        for split in EVAL_SPLITS:
            base = by_key[(model_name, split, "original")]
            for condition in CONDITIONS:
                row = by_key[(model_name, split, condition)]
                degradation_rows.append({
                    "subset_id": subset_id,
                    "model": model_name,
                    "split": split,
                    "condition": condition,
                    "baseline_condition": "original",
                    "accuracy": row["accuracy"],
                    "macro_f1": row["macro_f1"],
                    "weighted_f1": row["weighted_f1"],
                    "accuracy_loss_vs_original": round(float(base["accuracy"]) - float(row["accuracy"]), 6),
                    "macro_f1_loss_vs_original": round(float(base["macro_f1"]) - float(row["macro_f1"]), 6),
                    "weighted_f1_loss_vs_original": round(float(base["weighted_f1"]) - float(row["weighted_f1"]), 6),
                    "rows": row["rows"],
                })
    return prediction_rows, degradation_rows


def run_same_condition(
    subset_id: str,
    rows: list[dict[str, object]],
    feature_indices: list[int],
) -> list[dict[str, object]]:
    metric_rows = []
    for condition in CONDITIONS:
        train = [r for r in rows if r["meta"]["split"] == "train" and r["meta"]["condition"] == condition]
        if not train:
            continue
        fitted, means, stds = fit_models(train, feature_indices)
        for model_name in MODELS:
            for split in EVAL_SPLITS:
                eval_rows = [r for r in rows if r["meta"]["split"] == split and r["meta"]["condition"] == condition]
                x_eval_raw = [[r["x_all"][i] for i in feature_indices] for r in eval_rows]
                x_eval = zscore_apply(x_eval_raw, means, stds)
                y_eval = [r["y"] for r in eval_rows]
                preds = PREDICTORS[model_name](fitted[model_name], x_eval) if eval_rows else []
                metrics = evaluate(y_eval, preds)
                metric_rows.append({
                    "subset_id": subset_id,
                    "model": model_name,
                    "split": split,
                    "condition": condition,
                    **metrics,
                    "rows": len(y_eval),
                })

    by_key = {(row["model"], row["split"], row["condition"]): row for row in metric_rows}
    summary_rows = []
    for row in metric_rows:
        base = by_key.get((row["model"], row["split"], "original"))
        base_macro = float(base["macro_f1"]) if base else 0.0
        macro = float(row["macro_f1"])
        summary_rows.append({
            **row,
            "baseline_condition": "original",
            "macro_f1_difference_vs_original": round(macro - base_macro, 6),
            "macro_f1_survival_ratio": round(macro / base_macro, 6) if base_macro else 0.0,
        })
    return summary_rows


def mean_vector(rows: list[dict[str, object]], features: list[str]) -> list[float]:
    return [sum(float(row["features"][f]) for row in rows) / len(rows) for f in features]


def mean_abs_distance(a: list[float], b: list[float]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a) if a else 0.0


def zscore_rows_by_condition(rows: list[dict[str, object]], features: list[str]) -> list[dict[str, object]]:
    if not rows:
        return []
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
        zrow = {
            "text_id": row["meta"]["text_id"],
            "passage_id": row["meta"]["passage_id"],
            "condition": row["meta"]["condition"],
            "author_id": row["y"],
            "features": {},
        }
        for feature in features:
            zrow["features"][feature] = (float(row["features"][feature]) - means[feature]) / stds[feature]
        zrows.append(zrow)
    return zrows


def run_distance_summary(
    subset_id: str,
    rows: list[dict[str, object]],
    feature_cols: list[str],
) -> list[dict[str, object]]:
    function_features = [f for f in feature_cols if f.startswith("fw_")]
    feature_sets = {
        "function_word": function_features,
        "all_features": feature_cols,
    }
    summary_rows = []
    for feature_set, features in feature_sets.items():
        baseline_mean = None
        for condition in CONDITIONS:
            condition_rows = [row for row in rows if row["meta"]["condition"] == condition]
            zrows = zscore_rows_by_condition(condition_rows, features)
            by_author = {author: [row for row in zrows if row["author_id"] == author] for author in AUTHORS}
            if any(not by_author[author] for author in AUTHORS):
                vals = []
            else:
                centroids = {author: mean_vector(by_author[author], features) for author in AUTHORS}
                vals = [
                    mean_abs_distance(centroids[a], centroids[b])
                    for a, b in combinations(AUTHORS, 2)
                ]
            mean_delta = statistics.mean(vals) if vals else 0.0
            if condition == "original":
                baseline_mean = mean_delta
            summary_rows.append({
                "subset_id": subset_id,
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
    return summary_rows


def run_feature_family_summary(
    subset_id: str,
    rows: list[dict[str, object]],
    feature_manifest: list[dict[str, str]],
) -> list[dict[str, object]]:
    by_family: dict[str, list[int]] = defaultdict(list)
    for idx, frow in enumerate(feature_manifest):
        by_family[frow["feature_family"]].append(idx)

    summary_rows = []
    for family, indices in sorted(by_family.items()):
        _, degradation_rows = run_transfer(subset_id, rows, indices)
        for row in degradation_rows:
            summary_rows.append({
                "subset_id": subset_id,
                "feature_family": family,
                "feature_count": len(indices),
                **row,
            })
    return summary_rows


def macro_f1_for_prediction_rows(rows: list[dict[str, object]]) -> float:
    y_true = [str(r["true_author"]) for r in rows]
    y_pred = [str(r["predicted_author"]) for r in rows]
    return float(evaluate(y_true, y_pred)["macro_f1"])


def bootstrap_transfer_losses(prediction_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_key: dict[tuple[str, str, str, str, str], dict[str, object]] = {}
    for row in prediction_rows:
        by_key[(row["subset_id"], row["model"], row["split"], row["condition"], row["passage_id"])] = row

    rng = random.Random(BOOTSTRAP_SEED)
    out_rows = []
    for subset_id, _desc in SUBSETS:
        for model in MODELS:
            for split in EVAL_SPLITS:
                original_ids = {
                    pid for (s, m, sp, c, pid) in by_key
                    if s == subset_id and m == model and sp == split and c == "original"
                }
                for condition in REWRITE_CONDITIONS:
                    condition_ids = {
                        pid for (s, m, sp, c, pid) in by_key
                        if s == subset_id and m == model and sp == split and c == condition
                    }
                    paired_ids = sorted(original_ids & condition_ids)
                    if not paired_ids:
                        continue

                    original_rows = [
                        by_key[(subset_id, model, split, "original", pid)]
                        for pid in paired_ids
                    ]
                    condition_rows = [
                        by_key[(subset_id, model, split, condition, pid)]
                        for pid in paired_ids
                    ]
                    observed_loss = macro_f1_for_prediction_rows(original_rows) - macro_f1_for_prediction_rows(condition_rows)

                    losses = []
                    for _ in range(BOOTSTRAP_ITERATIONS):
                        sample_ids = [rng.choice(paired_ids) for _ in paired_ids]
                        boot_original = [
                            by_key[(subset_id, model, split, "original", pid)]
                            for pid in sample_ids
                        ]
                        boot_condition = [
                            by_key[(subset_id, model, split, condition, pid)]
                            for pid in sample_ids
                        ]
                        losses.append(macro_f1_for_prediction_rows(boot_original) - macro_f1_for_prediction_rows(boot_condition))

                    losses_sorted = sorted(losses)
                    low_idx = int(0.025 * BOOTSTRAP_ITERATIONS)
                    high_idx = int(0.975 * BOOTSTRAP_ITERATIONS) - 1
                    p_loss_le_zero = sum(1 for x in losses if x <= 0) / len(losses)
                    out_rows.append({
                        "subset_id": subset_id,
                        "model": model,
                        "split": split,
                        "condition": condition,
                        "paired_passages": len(paired_ids),
                        "observed_macro_f1_loss": round(observed_loss, 9),
                        "ci_low_95": round(losses_sorted[low_idx], 9),
                        "ci_high_95": round(losses_sorted[high_idx], 9),
                        "p_loss_le_zero_bootstrap": round(p_loss_le_zero, 6),
                        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
                        "rng_seed": BOOTSTRAP_SEED,
                    })
    return out_rows


def make_subset_counts(subset_id: str, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    for condition in CONDITIONS:
        condition_rows = [r for r in rows if r["meta"]["condition"] == condition]
        status_counts = Counter(str(r["qc_status"]) for r in condition_rows)
        hard_warnings = sum(1 for r in condition_rows if "length_hard_warning" in str(r["qc_flags"]).split(";"))
        soft_warnings = sum(1 for r in condition_rows if "length_soft_warning" in str(r["qc_flags"]).split(";"))
        out.append({
            "subset_id": subset_id,
            "condition": condition,
            "rows": len(condition_rows),
            "authors": len({r["y"] for r in condition_rows}),
            "pass_rows": status_counts.get("pass", 0),
            "warning_rows": status_counts.get("warning", 0),
            "fail_rows": status_counts.get("fail", 0),
            "length_hard_warning_rows": hard_warnings,
            "length_soft_warning_rows": soft_warnings,
        })
    return out


def main() -> int:
    required = [MODELING_METADATA, X_RAW, Y_LABELS, FEATURE_COLUMNS, REWRITE_QC]
    missing = [p for p in required if not p.exists()]
    if missing:
        for path in missing:
            print(f"Missing input: {path.relative_to(ROOT)}")
        return 1

    meta_rows = read_csv(MODELING_METADATA)
    x_rows = read_csv(X_RAW)
    y_rows = read_csv(Y_LABELS)
    feature_manifest = read_csv(FEATURE_COLUMNS)
    qc_rows = read_csv(REWRITE_QC)
    feature_cols = [row["feature"] for row in feature_manifest]
    full_indices = list(range(len(feature_cols)))

    dataset = build_dataset(meta_rows, x_rows, y_rows, feature_cols, qc_rows)

    all_predictions = []
    all_transfer = []
    all_same_condition = []
    all_distance = []
    all_feature_family = []
    all_counts = []

    for subset_id, _description in SUBSETS:
        rows = subset_dataset(dataset, subset_id)
        all_counts.extend(make_subset_counts(subset_id, rows))

        preds, transfer = run_transfer(subset_id, rows, full_indices)
        all_predictions.extend(preds)
        all_transfer.extend(transfer)

        all_same_condition.extend(run_same_condition(subset_id, rows, full_indices))
        all_distance.extend(run_distance_summary(subset_id, rows, feature_cols))
        all_feature_family.extend(run_feature_family_summary(subset_id, rows, feature_manifest))

    bootstrap_rows = bootstrap_transfer_losses(all_predictions)

    write_csv(TRANSFER_PREDICTIONS, all_predictions, [
        "subset_id", "model", "split", "condition", "text_id", "passage_id",
        "true_author", "predicted_author", "correct", "qc_status", "qc_flags",
    ])
    write_csv(TRANSFER_SUMMARY, all_transfer, [
        "subset_id", "model", "split", "condition", "baseline_condition", "accuracy",
        "macro_f1", "weighted_f1", "accuracy_loss_vs_original",
        "macro_f1_loss_vs_original", "weighted_f1_loss_vs_original", "rows",
    ])
    write_csv(SAME_CONDITION_SUMMARY, all_same_condition, [
        "subset_id", "model", "split", "condition", "accuracy", "macro_f1",
        "weighted_f1", "rows", "baseline_condition",
        "macro_f1_difference_vs_original", "macro_f1_survival_ratio",
    ])
    write_csv(DISTANCE_SUMMARY, all_distance, [
        "subset_id", "feature_set", "condition", "pair_count", "mean_burrows_delta",
        "median_burrows_delta", "min_burrows_delta", "max_burrows_delta",
        "std_burrows_delta", "distance_ratio_vs_original",
    ])
    write_csv(FEATURE_FAMILY_SUMMARY, all_feature_family, [
        "subset_id", "feature_family", "feature_count", "model", "split",
        "condition", "baseline_condition", "accuracy", "macro_f1", "weighted_f1",
        "accuracy_loss_vs_original", "macro_f1_loss_vs_original",
        "weighted_f1_loss_vs_original", "rows",
    ])
    write_csv(BOOTSTRAP_SUMMARY, bootstrap_rows, [
        "subset_id", "model", "split", "condition", "paired_passages",
        "observed_macro_f1_loss", "ci_low_95", "ci_high_95",
        "p_loss_le_zero_bootstrap", "bootstrap_iterations", "rng_seed",
    ])
    write_csv(SUBSET_COUNTS, all_counts, [
        "subset_id", "condition", "rows", "authors", "pass_rows", "warning_rows",
        "fail_rows", "length_hard_warning_rows", "length_soft_warning_rows",
    ])

    artifacts = [
        TRANSFER_PREDICTIONS,
        TRANSFER_SUMMARY,
        SAME_CONDITION_SUMMARY,
        DISTANCE_SUMMARY,
        FEATURE_FAMILY_SUMMARY,
        BOOTSTRAP_SUMMARY,
        SUBSET_COUNTS,
    ]
    manifest_rows = [{
        "artifact": path.stem,
        "path": path.relative_to(ROOT).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha_file(path),
    } for path in artifacts]
    write_csv(MANIFEST, manifest_rows, ["artifact", "path", "size_bytes", "sha256"])

    best_rows = [
        row for row in all_transfer
        if row["model"] == "nearest_centroid" and row["split"] == "test"
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# E3 Warning-Row Sensitivity Analysis Report\n\n"
        "## Status\n\nComplete when generated locally and checker passes.\n\n"
        "## Subsets\n\n"
        + "".join(f"- `{subset_id}`: {desc}\n" for subset_id, desc in SUBSETS)
        + "\n## Output row counts\n\n"
        f"- transfer predictions: {len(all_predictions)}\n"
        f"- transfer summary rows: {len(all_transfer)}\n"
        f"- same-condition summary rows: {len(all_same_condition)}\n"
        f"- distance summary rows: {len(all_distance)}\n"
        f"- feature-family summary rows: {len(all_feature_family)}\n"
        f"- bootstrap rows: {len(bootstrap_rows)}\n\n"
        "## Nearest-centroid test transfer summary\n\n"
        + "".join(
            f"- {row['subset_id']} / {row['condition']}: macro_f1={row['macro_f1']}, loss={row['macro_f1_loss_vs_original']}, rows={row['rows']}\n"
            for row in best_rows
        ),
        encoding="utf-8",
    )

    print("Ran E3 warning-row sensitivity analysis.")
    print(f"Subsets: {', '.join(s for s, _ in SUBSETS)}")
    print(f"Wrote {len(artifacts)} output artifacts plus manifest and report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
