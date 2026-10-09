"""
Step 17: Burrows' Delta and inter-author distance analysis.

Run from repository root after Step 16:

    python scripts/18_run_burrows_delta_distance.py

Inputs:
- data/modeling/modeling_metadata.csv
- data/modeling/X_stylometric_raw.csv
- metadata/modeling_feature_columns.csv

Outputs:
- data/results/burrows_delta_text_to_author.csv
- metadata/inter_author_distance_matrices.csv
- metadata/inter_author_distance_summary.csv
- metadata/author_centroid_shift_summary.csv
- metadata/burrows_delta_distance_manifest.csv
- logs/step_17_burrows_delta_distance_report.md
"""

from __future__ import annotations

import csv
import hashlib
import math
import statistics
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELING_METADATA = ROOT / "data" / "modeling" / "modeling_metadata.csv"
X_RAW = ROOT / "data" / "modeling" / "X_stylometric_raw.csv"
FEATURE_COLUMNS = ROOT / "metadata" / "modeling_feature_columns.csv"
RESULTS = ROOT / "data" / "results"
META = ROOT / "metadata"
LOGS = ROOT / "logs"

TEXT_TO_AUTHOR = RESULTS / "burrows_delta_text_to_author.csv"
DIST_MATRICES = META / "inter_author_distance_matrices.csv"
DIST_SUMMARY = META / "inter_author_distance_summary.csv"
CENTROID_SHIFT = META / "author_centroid_shift_summary.csv"
MANIFEST = META / "burrows_delta_distance_manifest.csv"
REPORT = LOGS / "step_17_burrows_delta_distance_report.md"

AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
FEATURE_SETS = ["function_word", "all_features"]


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


def mean_vector(rows: list[dict[str, float]], features: list[str]) -> list[float]:
    return [sum(row[f] for row in rows) / len(rows) for f in features]


def mean_abs_distance(a: list[float], b: list[float]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a) if a else 0.0


def euclidean_distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def zscore_condition(rows: list[dict[str, object]], features: list[str]) -> list[dict[str, object]]:
    means = {}
    stds = {}
    for feature in features:
        vals = [float(row[feature]) for row in rows]
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(var)
        means[feature] = mean
        stds[feature] = std if std > 0 else 1.0
    zrows = []
    for row in rows:
        z = {k: row[k] for k in ["text_id", "passage_id", "condition", "author_id"]}
        for feature in features:
            z[feature] = (float(row[feature]) - means[feature]) / stds[feature]
        zrows.append(z)
    return zrows


def main() -> int:
    for path in [MODELING_METADATA, X_RAW, FEATURE_COLUMNS]:
        if not path.exists():
            print(f"Missing input: {path.relative_to(ROOT)}")
            return 1

    meta_rows = read_csv(MODELING_METADATA)
    x_rows = read_csv(X_RAW)
    feature_manifest = read_csv(FEATURE_COLUMNS)
    feature_cols = [row["feature"] for row in feature_manifest]
    function_features = [f for f in feature_cols if f.startswith("fw_")]
    if not function_features:
        print("No function-word features found.")
        return 1
    if len(feature_cols) != 205:
        print(f"Expected 205 all-feature columns, found {len(feature_cols)}")
        return 1

    by_text_x = {row["text_id"]: row for row in x_rows}
    rows = []
    for meta in meta_rows:
        text_id = meta["text_id"]
        row = {k: meta[k] for k in ["text_id", "passage_id", "condition", "author_id"]}
        for feature in feature_cols:
            row[feature] = float(by_text_x[text_id][feature])
        rows.append(row)

    feature_sets = {
        "function_word": function_features,
        "all_features": feature_cols,
    }

    distance_rows = []
    distance_values_by_group: dict[tuple[str, str], list[float]] = defaultdict(list)
    centroids_by_set_condition: dict[tuple[str, str, str], list[float]] = {}
    zrows_by_set_condition: dict[tuple[str, str], list[dict[str, object]]] = {}

    for feature_set, features in feature_sets.items():
        for condition in CONDITIONS:
            condition_rows = [row for row in rows if row["condition"] == condition]
            zrows = zscore_condition(condition_rows, features)
            zrows_by_set_condition[(feature_set, condition)] = zrows
            by_author = {author: [row for row in zrows if row["author_id"] == author] for author in AUTHORS}
            centroids = {author: mean_vector(by_author[author], features) for author in AUTHORS}
            for author, vec in centroids.items():
                centroids_by_set_condition[(feature_set, condition, author)] = vec
            for author_a, author_b in combinations(AUTHORS, 2):
                a = centroids[author_a]
                b = centroids[author_b]
                burrows_delta = mean_abs_distance(a, b)
                euclid = euclidean_distance(a, b)
                distance_rows.append({
                    "feature_set": feature_set,
                    "condition": condition,
                    "author_a": author_a,
                    "author_b": author_b,
                    "burrows_delta": round(burrows_delta, 9),
                    "mean_absolute_z_distance": round(burrows_delta, 9),
                    "euclidean_z_distance": round(euclid, 9),
                    "feature_count": len(features),
                })
                distance_values_by_group[(feature_set, condition)].append(burrows_delta)

    summary_rows = []
    for feature_set in FEATURE_SETS:
        for condition in CONDITIONS:
            vals = distance_values_by_group[(feature_set, condition)]
            summary_rows.append({
                "feature_set": feature_set,
                "condition": condition,
                "pair_count": len(vals),
                "mean_burrows_delta": round(statistics.mean(vals), 9),
                "median_burrows_delta": round(statistics.median(vals), 9),
                "min_burrows_delta": round(min(vals), 9),
                "max_burrows_delta": round(max(vals), 9),
                "std_burrows_delta": round(statistics.pstdev(vals), 9),
            })

    shift_rows = []
    for feature_set, features in feature_sets.items():
        for author in AUTHORS:
            original_centroid = centroids_by_set_condition[(feature_set, "original", author)]
            for condition in ["paraphrase", "modernize", "simplify"]:
                rewritten_centroid = centroids_by_set_condition[(feature_set, condition, author)]
                shift_rows.append({
                    "feature_set": feature_set,
                    "author_id": author,
                    "from_condition": "original",
                    "to_condition": condition,
                    "burrows_delta_shift": round(mean_abs_distance(original_centroid, rewritten_centroid), 9),
                    "euclidean_z_shift": round(euclidean_distance(original_centroid, rewritten_centroid), 9),
                    "feature_count": len(features),
                })

    text_delta_rows = []
    # Classical text-to-author Delta only for function-word set.
    fw_features = feature_sets["function_word"]
    for condition in CONDITIONS:
        zrows = zrows_by_set_condition[("function_word", condition)]
        by_author = {author: [row for row in zrows if row["author_id"] == author] for author in AUTHORS}
        centroids = {author: mean_vector(by_author[author], fw_features) for author in AUTHORS}
        for row in zrows:
            vec = [float(row[f]) for f in fw_features]
            true_author = row["author_id"]
            distances = {author: mean_abs_distance(vec, centroids[author]) for author in AUTHORS}
            nearest_author = min(distances, key=distances.get)
            for author in AUTHORS:
                text_delta_rows.append({
                    "text_id": row["text_id"],
                    "passage_id": row["passage_id"],
                    "condition": condition,
                    "true_author": true_author,
                    "centroid_author": author,
                    "burrows_delta": round(distances[author], 9),
                    "is_true_author_centroid": int(author == true_author),
                    "is_nearest_centroid": int(author == nearest_author),
                    "nearest_centroid_author": nearest_author,
                    "nearest_centroid_correct": int(nearest_author == true_author),
                })

    write_csv(TEXT_TO_AUTHOR, text_delta_rows, ["text_id", "passage_id", "condition", "true_author", "centroid_author", "burrows_delta", "is_true_author_centroid", "is_nearest_centroid", "nearest_centroid_author", "nearest_centroid_correct"])
    write_csv(DIST_MATRICES, distance_rows, ["feature_set", "condition", "author_a", "author_b", "burrows_delta", "mean_absolute_z_distance", "euclidean_z_distance", "feature_count"])
    write_csv(DIST_SUMMARY, summary_rows, ["feature_set", "condition", "pair_count", "mean_burrows_delta", "median_burrows_delta", "min_burrows_delta", "max_burrows_delta", "std_burrows_delta"])
    write_csv(CENTROID_SHIFT, shift_rows, ["feature_set", "author_id", "from_condition", "to_condition", "burrows_delta_shift", "euclidean_z_shift", "feature_count"])

    artifacts = [TEXT_TO_AUTHOR, DIST_MATRICES, DIST_SUMMARY, CENTROID_SHIFT]
    manifest_rows = [{"artifact": p.stem, "path": p.relative_to(ROOT).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha_file(p)} for p in artifacts]
    write_csv(MANIFEST, manifest_rows, ["artifact", "path", "size_bytes", "sha256"])

    function_summary = [row for row in summary_rows if row["feature_set"] == "function_word"]
    all_summary = [row for row in summary_rows if row["feature_set"] == "all_features"]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Step 17 Burrows' Delta and Inter-Author Distance Report\n\n"
        "## Status\n\nComplete when generated locally and checker passes.\n\n"
        "## Feature sets\n\n"
        f"- function_word features: {len(function_features)}\n"
        f"- all_features: {len(feature_cols)}\n\n"
        "## Output rows\n\n"
        f"- text-to-author Delta rows: {len(text_delta_rows)}\n"
        f"- inter-author distance rows: {len(distance_rows)}\n"
        f"- distance summary rows: {len(summary_rows)}\n"
        f"- centroid shift rows: {len(shift_rows)}\n\n"
        "## Function-word mean inter-author Burrows' Delta by condition\n\n" + "".join(
            f"- {row['condition']}: {row['mean_burrows_delta']}\n" for row in function_summary
        ) + "\n## All-feature mean inter-author distance by condition\n\n" + "".join(
            f"- {row['condition']}: {row['mean_burrows_delta']}\n" for row in all_summary
        ),
        encoding="utf-8",
    )
    print("Ran Burrows' Delta and inter-author distance analysis.")
    print(f"Text-to-author Delta rows: {len(text_delta_rows)}")
    print(f"Inter-author distance rows: {len(distance_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
