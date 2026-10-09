"""
Consistency checker for Step 13 modeling matrices.

Run from repository root after Step 13:

    python scripts/check_step_13_modeling_matrices.py

Exit code:
    0 = Step 13 modeling matrices are internally consistent
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "data" / "features" / "stylometric_features.csv"
MODELING_METADATA = ROOT / "data" / "modeling" / "modeling_metadata.csv"
X_RAW = ROOT / "data" / "modeling" / "X_stylometric_raw.csv"
X_SCALED = ROOT / "data" / "modeling" / "X_stylometric_scaled_descriptive.csv"
Y_LABELS = ROOT / "data" / "modeling" / "y_author_labels.csv"
SPLIT = ROOT / "data" / "modeling" / "passage_level_split.csv"
FEATURE_COLUMNS = ROOT / "metadata" / "modeling_feature_columns.csv"
SPLIT_SUMMARY = ROOT / "metadata" / "modeling_split_summary.csv"
SCALING_PARAMS = ROOT / "metadata" / "descriptive_scaling_parameters.csv"
MANIFEST = ROOT / "metadata" / "modeling_matrix_manifest.csv"
REPORT = ROOT / "logs" / "step_13_modeling_matrix_report.md"
SCRIPT = ROOT / "scripts" / "14_prepare_modeling_matrices.py"

EXPECTED_CONDITIONS = {"original", "paraphrase", "modernize", "simplify"}
EXPECTED_AUTHORS = {"austen", "dickens", "poe", "shelley", "twain", "wilde"}
EXPECTED_SPLITS = {"train", "validation", "test"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def ids(path: Path) -> list[str]:
    return [row["text_id"] for row in read_csv(path)]


def main() -> int:
    failures: list[str] = []
    required = [FEATURES, MODELING_METADATA, X_RAW, X_SCALED, Y_LABELS, SPLIT, FEATURE_COLUMNS, SPLIT_SUMMARY, SCALING_PARAMS, MANIFEST, REPORT, SCRIPT]
    for path in required:
        check(path.exists(), f"missing required Step 13 file: {path.relative_to(ROOT)}", failures)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    feature_rows = read_csv(FEATURES)
    meta_rows = read_csv(MODELING_METADATA)
    x_raw_rows = read_csv(X_RAW)
    x_scaled_rows = read_csv(X_SCALED)
    y_rows = read_csv(Y_LABELS)
    split_rows = read_csv(SPLIT)
    feature_cols = read_csv(FEATURE_COLUMNS)
    split_summary = read_csv(SPLIT_SUMMARY)
    scaling_rows = read_csv(SCALING_PARAMS)

    for name, rows in [("features", feature_rows), ("metadata", meta_rows), ("X_raw", x_raw_rows), ("X_scaled", x_scaled_rows), ("y", y_rows)]:
        check(len(rows) == 1440, f"{name} row count expected 1440, found {len(rows)}", failures)
        check(len({row["text_id"] for row in rows}) == 1440, f"{name} text_id values not unique", failures)

    reference_ids = [row["text_id"] for row in feature_rows]
    check([row["text_id"] for row in meta_rows] == reference_ids, "metadata text_id order mismatch", failures)
    check([row["text_id"] for row in x_raw_rows] == reference_ids, "X_raw text_id order mismatch", failures)
    check([row["text_id"] for row in x_scaled_rows] == reference_ids, "X_scaled text_id order mismatch", failures)
    check([row["text_id"] for row in y_rows] == reference_ids, "y label text_id order mismatch", failures)

    check(len(feature_cols) >= 150, f"feature column manifest too small: {len(feature_cols)}", failures)
    check(len(scaling_rows) == len(feature_cols), "scaling parameter row count does not match feature count", failures)
    check(len(split_rows) == 360, f"split passage rows expected 360, found {len(split_rows)}", failures)

    split_by_passage = {row["passage_id"]: row["split"] for row in split_rows}
    check(len(split_by_passage) == 360, "split passage IDs not unique", failures)
    check(set(row["split"] for row in split_rows) == EXPECTED_SPLITS, "split names mismatch", failures)

    by_passage_splits = defaultdict(set)
    for row in meta_rows:
        by_passage_splits[row["passage_id"]].add(row["split"])
        check(split_by_passage.get(row["passage_id"]) == row["split"], f"split mismatch for {row['passage_id']}", failures)
    bad_passages = [pid for pid, splits in by_passage_splits.items() if len(splits) != 1]
    check(not bad_passages, f"passages assigned to multiple splits: {bad_passages[:10]}", failures)

    split_counts = Counter(row["split"] for row in meta_rows)
    check(split_counts["train"] == 1008, f"train rows expected 1008, found {split_counts['train']}", failures)
    check(split_counts["validation"] == 216, f"validation rows expected 216, found {split_counts['validation']}", failures)
    check(split_counts["test"] == 216, f"test rows expected 216, found {split_counts['test']}", failures)

    condition_counts = Counter(row["condition"] for row in meta_rows)
    author_counts = Counter(row["author_id"] for row in meta_rows)
    check(set(condition_counts) == EXPECTED_CONDITIONS, f"condition set mismatch: {set(condition_counts)}", failures)
    check(set(author_counts) == EXPECTED_AUTHORS, f"author set mismatch: {set(author_counts)}", failures)

    for split_name in EXPECTED_SPLITS:
        subset = [row for row in meta_rows if row["split"] == split_name]
        check({row["author_id"] for row in subset} == EXPECTED_AUTHORS, f"{split_name} missing authors", failures)
        check({row["condition"] for row in subset} == EXPECTED_CONDITIONS, f"{split_name} missing conditions", failures)

    summary_by_split = {row["split"]: row for row in split_summary}
    check(set(summary_by_split) == EXPECTED_SPLITS, "split summary split set mismatch", failures)
    check(summary_by_split.get("train", {}).get("text_rows") == "1008", "split summary train text_rows mismatch", failures)
    check(summary_by_split.get("validation", {}).get("text_rows") == "216", "split summary validation text_rows mismatch", failures)
    check(summary_by_split.get("test", {}).get("text_rows") == "216", "split summary test text_rows mismatch", failures)

    numeric_cols = [row["feature"] for row in feature_cols]
    raw_header = list(x_raw_rows[0].keys())
    scaled_header = list(x_scaled_rows[0].keys())
    check(raw_header == ["text_id"] + numeric_cols, "X_raw header does not match feature manifest", failures)
    check(scaled_header == ["text_id"] + numeric_cols, "X_scaled header does not match feature manifest", failures)
    for col in numeric_cols:
        try:
            [float(row[col]) for row in x_raw_rows]
            [float(row[col]) for row in x_scaled_rows]
        except ValueError:
            failures.append(f"non-numeric matrix column: {col}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: Step 13 modeling matrices are complete and internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
