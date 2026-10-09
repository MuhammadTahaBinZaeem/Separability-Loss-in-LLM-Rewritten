"""
E8: leave-one-feature-family-out ablation.

Run from repository root:

    python scripts/25_run_leave_one_feature_family_out.py

This script trains nearest-centroid transfer classifiers on original-condition
training rows under full features and full-minus-one-family feature sets.
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

PREDICTIONS = RESULTS_DIR / "leave_one_feature_family_out_predictions.csv"
SUMMARY = META_DIR / "leave_one_feature_family_out_summary.csv"
DELTA = META_DIR / "leave_one_feature_family_out_delta_vs_full.csv"
FEATURE_REGISTRY = META_DIR / "leave_one_feature_family_out_feature_registry.csv"
MANIFEST = META_DIR / "leave_one_feature_family_out_manifest.csv"
REPORT = LOGS_DIR / "leave_one_feature_family_out_report.md"

AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
EVAL_SPLITS = ["validation", "test"]
MODEL_NAME = "nearest_centroid"


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
    return {
        label: [sum(row[j] for row in rows) / len(rows) for j in range(len(rows[0]))]
        for label, rows in by_class.items()
    }


def predict_nearest_centroid(model: dict[str, list[float]], x: list[list[float]]) -> list[str]:
    return [min(model, key=lambda label: euclidean2(row, model[label])) for row in x]


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


def build_dataset(meta_rows: list[dict[str, str]], x_rows: list[dict[str, str]], y_rows: list[dict[str, str]], feature_cols: list[str]) -> list[dict[str, object]]:
    by_text_x = {row["text_id"]: row for row in x_rows}
    by_text_y = {row["text_id"]: row for row in y_rows}
    dataset = []
    for row in meta_rows:
        text_id = row["text_id"]
        dataset.append({
            "meta": row,
            "x_all": [float(by_text_x[text_id][col]) for col in feature_cols],
            "y": by_text_y[text_id]["author_id"],
        })
    return dataset


def make_ablation_modes(feature_manifest: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    families = []
    for row in feature_manifest:
        fam = row["feature_family"]
        if fam not in families:
            families.append(fam)
    all_indices = list(range(len(feature_manifest)))
    modes = [{
        "ablation_mode": "full_features",
        "removed_family": "none",
        "included_indices": all_indices,
    }]
    for family in families:
        indices = [i for i, row in enumerate(feature_manifest) if row["feature_family"] != family]
        modes.append({
            "ablation_mode": f"minus_{family}",
            "removed_family": family,
            "included_indices": indices,
        })

    registry = []
    for mode in modes:
        included = set(mode["included_indices"])
        removed = [i for i in all_indices if i not in included]
        registry.append({
            "ablation_mode": mode["ablation_mode"],
            "removed_family": mode["removed_family"],
            "included_feature_count": len(included),
            "removed_feature_count": len(removed),
            "included_families": ";".join(sorted({feature_manifest[i]["feature_family"] for i in included})),
            "removed_features": ";".join(feature_manifest[i]["feature"] for i in removed),
        })
    return modes, registry


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
    feature_manifest = read_csv(FEATURE_COLUMNS)
    feature_cols = [row["feature"] for row in feature_manifest]
    dataset = build_dataset(meta_rows, x_rows, y_rows, feature_cols)
    modes, registry = make_ablation_modes(feature_manifest)

    prediction_rows = []
    metric_rows = []
    for mode in modes:
        indices = mode["included_indices"]
        ablation_mode = mode["ablation_mode"]
        removed_family = mode["removed_family"]
        train_rows = [row for row in dataset if row["meta"]["split"] == "train" and row["meta"]["condition"] == "original"]
        x_train_raw = [[row["x_all"][i] for i in indices] for row in train_rows]
        y_train = [row["y"] for row in train_rows]
        means, stds = zscore_fit(x_train_raw)
        x_train = zscore_apply(x_train_raw, means, stds)
        model = fit_nearest_centroid(x_train, y_train)

        for split in EVAL_SPLITS:
            for condition in CONDITIONS:
                eval_rows = [row for row in dataset if row["meta"]["split"] == split and row["meta"]["condition"] == condition]
                x_eval_raw = [[row["x_all"][i] for i in indices] for row in eval_rows]
                x_eval = zscore_apply(x_eval_raw, means, stds)
                y_eval = [row["y"] for row in eval_rows]
                preds = predict_nearest_centroid(model, x_eval)
                metrics = evaluate(y_eval, preds)
                metric_rows.append({
                    "ablation_mode": ablation_mode,
                    "removed_family": removed_family,
                    "model": MODEL_NAME,
                    "split": split,
                    "condition": condition,
                    "included_feature_count": len(indices),
                    **metrics,
                    "rows": len(y_eval),
                })
                for item, pred in zip(eval_rows, preds):
                    prediction_rows.append({
                        "ablation_mode": ablation_mode,
                        "removed_family": removed_family,
                        "model": MODEL_NAME,
                        "split": split,
                        "condition": condition,
                        "text_id": item["meta"]["text_id"],
                        "passage_id": item["meta"]["passage_id"],
                        "true_author": item["y"],
                        "predicted_author": pred,
                        "correct": int(item["y"] == pred),
                    })

    by_key = {(row["ablation_mode"], row["split"], row["condition"]): row for row in metric_rows}
    summary_rows = []
    for row in metric_rows:
        base = by_key[(row["ablation_mode"], row["split"], "original")]
        summary_rows.append({
            "ablation_mode": row["ablation_mode"],
            "removed_family": row["removed_family"],
            "model": row["model"],
            "split": row["split"],
            "condition": row["condition"],
            "baseline_condition": "original",
            "included_feature_count": row["included_feature_count"],
            "accuracy": row["accuracy"],
            "macro_f1": row["macro_f1"],
            "weighted_f1": row["weighted_f1"],
            "accuracy_loss_vs_original": round(float(base["accuracy"]) - float(row["accuracy"]), 6),
            "macro_f1_loss_vs_original": round(float(base["macro_f1"]) - float(row["macro_f1"]), 6),
            "weighted_f1_loss_vs_original": round(float(base["weighted_f1"]) - float(row["weighted_f1"]), 6),
            "rows": row["rows"],
        })

    full_by_key = {(row["split"], row["condition"]): row for row in summary_rows if row["ablation_mode"] == "full_features"}
    delta_rows = []
    for row in summary_rows:
        full = full_by_key[(row["split"], row["condition"])]
        delta_rows.append({
            "ablation_mode": row["ablation_mode"],
            "removed_family": row["removed_family"],
            "model": row["model"],
            "split": row["split"],
            "condition": row["condition"],
            "macro_f1": row["macro_f1"],
            "full_macro_f1": full["macro_f1"],
            "macro_f1_delta_vs_full": round(float(row["macro_f1"]) - float(full["macro_f1"]), 6),
            "macro_f1_loss_vs_original": row["macro_f1_loss_vs_original"],
            "full_macro_f1_loss_vs_original": full["macro_f1_loss_vs_original"],
            "loss_delta_vs_full": round(float(row["macro_f1_loss_vs_original"]) - float(full["macro_f1_loss_vs_original"]), 6),
            "included_feature_count": row["included_feature_count"],
        })

    write_csv(PREDICTIONS, prediction_rows, [
        "ablation_mode", "removed_family", "model", "split", "condition", "text_id",
        "passage_id", "true_author", "predicted_author", "correct",
    ])
    write_csv(SUMMARY, summary_rows, [
        "ablation_mode", "removed_family", "model", "split", "condition", "baseline_condition",
        "included_feature_count", "accuracy", "macro_f1", "weighted_f1", "accuracy_loss_vs_original",
        "macro_f1_loss_vs_original", "weighted_f1_loss_vs_original", "rows",
    ])
    write_csv(DELTA, delta_rows, [
        "ablation_mode", "removed_family", "model", "split", "condition", "macro_f1",
        "full_macro_f1", "macro_f1_delta_vs_full", "macro_f1_loss_vs_original",
        "full_macro_f1_loss_vs_original", "loss_delta_vs_full", "included_feature_count",
    ])
    write_csv(FEATURE_REGISTRY, registry, [
        "ablation_mode", "removed_family", "included_feature_count", "removed_feature_count",
        "included_families", "removed_features",
    ])

    artifacts = [PREDICTIONS, SUMMARY, DELTA, FEATURE_REGISTRY]
    manifest_rows = [{
        "artifact": path.stem,
        "path": path.relative_to(ROOT).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha_file(path),
    } for path in artifacts]
    write_csv(MANIFEST, manifest_rows, ["artifact", "path", "size_bytes", "sha256"])

    focus = [
        row for row in delta_rows
        if row["split"] == "test"
        and row["condition"] in {"paraphrase", "modernize", "simplify"}
        and row["ablation_mode"] != "full_features"
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# E8 Leave-One-Feature-Family-Out Ablation Report\n\n"
        "## Status\n\nComplete when generated locally and checker passes.\n\n"
        "## Design\n\n"
        "- model: nearest-centroid transfer classifier.\n"
        "- baseline: full 205-feature representation.\n"
        "- ablations: full features minus one feature family at a time.\n\n"
        "## Output rows\n\n"
        f"- prediction rows: {len(prediction_rows)}\n"
        f"- summary rows: {len(summary_rows)}\n"
        f"- delta rows: {len(delta_rows)}\n"
        f"- feature registry rows: {len(registry)}\n\n"
        "## Test split loss deltas versus full baseline\n\n"
        + "".join(
            f"- {row['ablation_mode']} / {row['condition']}: macro_f1={row['macro_f1']}, loss={row['macro_f1_loss_vs_original']}, loss_delta_vs_full={row['loss_delta_vs_full']}\n"
            for row in focus
        ),
        encoding="utf-8",
    )

    print("Ran E8 leave-one-feature-family-out ablation.")
    print(f"Ablation modes: {len(modes)}")
    print(f"Prediction rows: {len(prediction_rows)}")
    print(f"Summary rows: {len(summary_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
