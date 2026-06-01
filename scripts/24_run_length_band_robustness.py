"""
E7: length-band robustness analysis.

Run from repository root:

    python scripts/24_run_length_band_robustness.py

This script trains transfer classifiers on all original-condition training rows,
then stratifies validation/test predictions by length bands under two strategies:
actual text length and source-original passage length.
"""

from __future__ import annotations

import csv
import hashlib
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META_DIR = ROOT / "metadata"
RESULTS_DIR = ROOT / "data" / "results"
LOGS_DIR = ROOT / "logs"

MODELING_METADATA = ROOT / "data" / "modeling" / "modeling_metadata.csv"
X_RAW = ROOT / "data" / "modeling" / "X_stylometric_raw.csv"
Y_LABELS = ROOT / "data" / "modeling" / "y_author_labels.csv"
FEATURE_COLUMNS = ROOT / "metadata" / "modeling_feature_columns.csv"

PREDICTIONS = RESULTS_DIR / "length_band_transfer_predictions.csv"
SUMMARY = META_DIR / "length_band_transfer_summary.csv"
DIST = META_DIR / "length_band_distribution_summary.csv"
MANIFEST = META_DIR / "length_band_manifest.csv"
REPORT = LOGS_DIR / "length_band_robustness_report.md"

AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
EVAL_SPLITS = ["validation", "test"]
MODELS = ["nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"]
GROUPING_STRATEGIES = ["actual_text_length", "source_original_length"]
BANDS = [
    ("450_500", 450, 500),
    ("501_575", 501, 575),
    ("576_650", 576, 650),
]


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


def band_for_word_count(word_count: float) -> str:
    wc = int(round(word_count))
    for band_id, low, high in BANDS:
        if low <= wc <= high:
            return band_id
    return "outside_bands"


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


def evaluate(rows: list[dict[str, object]]) -> dict[str, float]:
    y_true = [str(r["true_author"]) for r in rows]
    y_pred = [str(r["predicted_author"]) for r in rows]
    if not y_true:
        return {"accuracy": 0.0, "macro_f1": 0.0, "weighted_f1": 0.0}
    accuracy = sum(1 for a, b in zip(y_true, y_pred) if a == b) / len(y_true)
    per = [precision_recall_f1(y_true, y_pred, label) for label in AUTHORS]
    macro_f1 = sum(x[2] for x in per) / len(per)
    total = sum(x[3] for x in per)
    weighted_f1 = sum(x[2] * x[3] for x in per) / total if total else 0.0
    return {"accuracy": round(accuracy, 6), "macro_f1": round(macro_f1, 6), "weighted_f1": round(weighted_f1, 6)}


def build_dataset(meta_rows: list[dict[str, str]], x_rows: list[dict[str, str]], y_rows: list[dict[str, str]], feature_cols: list[str]) -> list[dict[str, object]]:
    by_text_x = {row["text_id"]: row for row in x_rows}
    by_text_y = {row["text_id"]: row for row in y_rows}
    original_word_count_by_passage = {}
    for row in meta_rows:
        if row["condition"] == "original":
            original_word_count_by_passage[row["passage_id"]] = float(by_text_x[row["text_id"]]["word_count_feature"])

    dataset = []
    for row in meta_rows:
        text_id = row["text_id"]
        x_vector = [float(by_text_x[text_id][col]) for col in feature_cols]
        actual_word_count = float(by_text_x[text_id]["word_count_feature"])
        source_word_count = original_word_count_by_passage[row["passage_id"]]
        dataset.append({
            "meta": row,
            "x": x_vector,
            "y": by_text_y[text_id]["author_id"],
            "actual_word_count": actual_word_count,
            "source_original_word_count": source_word_count,
            "actual_text_length_band": band_for_word_count(actual_word_count),
            "source_original_length_band": band_for_word_count(source_word_count),
        })
    return dataset


def main() -> int:
    required = [MODELING_METADATA, X_RAW, Y_LABELS, FEATURE_COLUMNS]
    missing = [p for p in required if not p.exists()]
    if missing:
        for path in missing:
            print(f"Missing input: {path.relative_to(ROOT)}")
        return 1

    meta_rows = read_csv(MODELING_METADATA)
    x_rows = read_csv(X_RAW)
    y_rows = read_csv(Y_LABELS)
    feature_cols = [row["feature"] for row in read_csv(FEATURE_COLUMNS)]
    dataset = build_dataset(meta_rows, x_rows, y_rows, feature_cols)

    train = [row for row in dataset if row["meta"]["split"] == "train" and row["meta"]["condition"] == "original"]
    x_train_raw = [row["x"] for row in train]
    y_train = [row["y"] for row in train]
    means, stds = zscore_fit(x_train_raw)
    x_train = zscore_apply(x_train_raw, means, stds)
    fitted = {model_name: FITTERS[model_name](x_train, y_train) for model_name in MODELS}

    prediction_rows = []
    for model_name in MODELS:
        for split in EVAL_SPLITS:
            for condition in CONDITIONS:
                subset = [row for row in dataset if row["meta"]["split"] == split and row["meta"]["condition"] == condition]
                x_eval = zscore_apply([row["x"] for row in subset], means, stds)
                preds = PREDICTORS[model_name](fitted[model_name], x_eval)
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
                        "actual_word_count": int(round(item["actual_word_count"])),
                        "source_original_word_count": int(round(item["source_original_word_count"])),
                        "actual_text_length_band": item["actual_text_length_band"],
                        "source_original_length_band": item["source_original_length_band"],
                    })

    distribution_rows = []
    for strategy in GROUPING_STRATEGIES:
        band_column = strategy + "_band" if strategy == "actual_text_length" else "source_original_length_band"
        for split in EVAL_SPLITS:
            for condition in CONDITIONS:
                rows = [row for row in prediction_rows if row["split"] == split and row["condition"] == condition and row["model"] == "nearest_centroid"]
                by_band = Counter(row[band_column] for row in rows)
                for band_id in [b[0] for b in BANDS] + ["outside_bands"]:
                    band_rows = [row for row in rows if row[band_column] == band_id]
                    distribution_rows.append({
                        "grouping_strategy": strategy,
                        "split": split,
                        "condition": condition,
                        "length_band": band_id,
                        "rows": len(band_rows),
                        "authors": len({row["true_author"] for row in band_rows}),
                        "min_word_count": min((int(row["actual_word_count"]) for row in band_rows), default=0),
                        "max_word_count": max((int(row["actual_word_count"]) for row in band_rows), default=0),
                    })

    summary_rows = []
    for strategy in GROUPING_STRATEGIES:
        band_column = "actual_text_length_band" if strategy == "actual_text_length" else "source_original_length_band"
        for model_name in MODELS:
            for split in EVAL_SPLITS:
                for band_id in [b[0] for b in BANDS] + ["outside_bands"]:
                    by_condition = {}
                    for condition in CONDITIONS:
                        rows = [
                            row for row in prediction_rows
                            if row["model"] == model_name
                            and row["split"] == split
                            and row["condition"] == condition
                            and row[band_column] == band_id
                        ]
                        by_condition[condition] = rows
                    base_metrics = evaluate(by_condition["original"])
                    base_macro = float(base_metrics["macro_f1"])
                    base_acc = float(base_metrics["accuracy"])
                    base_weighted = float(base_metrics["weighted_f1"])
                    for condition in CONDITIONS:
                        metrics = evaluate(by_condition[condition])
                        macro = float(metrics["macro_f1"])
                        acc = float(metrics["accuracy"])
                        weighted = float(metrics["weighted_f1"])
                        summary_rows.append({
                            "grouping_strategy": strategy,
                            "model": model_name,
                            "split": split,
                            "length_band": band_id,
                            "condition": condition,
                            "baseline_condition": "original",
                            "rows": len(by_condition[condition]),
                            "authors": len({row["true_author"] for row in by_condition[condition]}),
                            "accuracy": metrics["accuracy"],
                            "macro_f1": metrics["macro_f1"],
                            "weighted_f1": metrics["weighted_f1"],
                            "accuracy_loss_vs_original": round(base_acc - acc, 6) if by_condition["original"] else "NA",
                            "macro_f1_loss_vs_original": round(base_macro - macro, 6) if by_condition["original"] else "NA",
                            "weighted_f1_loss_vs_original": round(base_weighted - weighted, 6) if by_condition["original"] else "NA",
                            "baseline_rows": len(by_condition["original"]),
                            "baseline_available": int(bool(by_condition["original"])),
                        })

    write_csv(PREDICTIONS, prediction_rows, [
        "model", "split", "condition", "text_id", "passage_id", "true_author", "predicted_author",
        "correct", "actual_word_count", "source_original_word_count", "actual_text_length_band",
        "source_original_length_band",
    ])
    write_csv(SUMMARY, summary_rows, [
        "grouping_strategy", "model", "split", "length_band", "condition", "baseline_condition",
        "rows", "authors", "accuracy", "macro_f1", "weighted_f1", "accuracy_loss_vs_original",
        "macro_f1_loss_vs_original", "weighted_f1_loss_vs_original", "baseline_rows", "baseline_available",
    ])
    write_csv(DIST, distribution_rows, [
        "grouping_strategy", "split", "condition", "length_band", "rows", "authors",
        "min_word_count", "max_word_count",
    ])

    artifacts = [PREDICTIONS, SUMMARY, DIST]
    manifest_rows = [{
        "artifact": path.stem,
        "path": path.relative_to(ROOT).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha_file(path),
    } for path in artifacts]
    write_csv(MANIFEST, manifest_rows, ["artifact", "path", "size_bytes", "sha256"])

    report_focus = [
        row for row in summary_rows
        if row["grouping_strategy"] == "source_original_length"
        and row["model"] == "nearest_centroid"
        and row["split"] == "test"
        and row["length_band"] in {"501_575", "576_650"}
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# E7 Length-Band Robustness Report\n\n"
        "## Status\n\nComplete when generated locally and checker passes.\n\n"
        "## Design\n\n"
        "- transfer classifiers trained on all original-condition training rows.\n"
        "- predictions stratified by actual text length and source-original passage length.\n"
        "- bands: 450-500, 501-575, 576-650, outside bands.\n\n"
        "## Output rows\n\n"
        f"- prediction rows: {len(prediction_rows)}\n"
        f"- transfer summary rows: {len(summary_rows)}\n"
        f"- distribution rows: {len(distribution_rows)}\n\n"
        "## Source-original length, nearest-centroid test focus\n\n"
        + "".join(
            f"- band={row['length_band']} / {row['condition']}: rows={row['rows']}, macro_f1={row['macro_f1']}, loss={row['macro_f1_loss_vs_original']}\n"
            for row in report_focus
        ),
        encoding="utf-8",
    )

    print("Ran E7 length-band robustness analysis.")
    print(f"Prediction rows: {len(prediction_rows)}")
    print(f"Summary rows: {len(summary_rows)}")
    print(f"Distribution rows: {len(distribution_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
