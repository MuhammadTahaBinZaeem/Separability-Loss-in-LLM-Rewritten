"""
Step 13: prepare modeling matrices from stylometric features.

Run from repository root after Step 12:

    python scripts/14_prepare_modeling_matrices.py

Inputs:
- data/features/stylometric_features.csv

Outputs:
- data/modeling/modeling_metadata.csv
- data/modeling/X_stylometric_raw.csv
- data/modeling/X_stylometric_scaled_descriptive.csv
- data/modeling/y_author_labels.csv
- data/modeling/passage_level_split.csv
- metadata/modeling_feature_columns.csv
- metadata/modeling_split_summary.csv
- metadata/modeling_matrix_manifest.csv
- metadata/descriptive_scaling_parameters.csv
- logs/step_13_modeling_matrix_report.md
"""

from __future__ import annotations

import csv
import hashlib
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "data" / "features" / "stylometric_features.csv"
OUT_DIR = ROOT / "data" / "modeling"
META = ROOT / "metadata"
LOGS = ROOT / "logs"

MODELING_METADATA = OUT_DIR / "modeling_metadata.csv"
X_RAW = OUT_DIR / "X_stylometric_raw.csv"
X_SCALED = OUT_DIR / "X_stylometric_scaled_descriptive.csv"
Y_LABELS = OUT_DIR / "y_author_labels.csv"
SPLIT = OUT_DIR / "passage_level_split.csv"
FEATURE_COLUMNS = META / "modeling_feature_columns.csv"
SPLIT_SUMMARY = META / "modeling_split_summary.csv"
SCALING_PARAMS = META / "descriptive_scaling_parameters.csv"
MANIFEST = META / "modeling_matrix_manifest.csv"
REPORT = LOGS / "step_13_modeling_matrix_report.md"

ID_COLS = ["text_id", "passage_id", "condition", "author_id", "author_name", "work_id", "work_title", "qc_status", "qc_flags"]
EXPECTED_CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
EXPECTED_AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
SPLIT_COUNTS_PER_AUTHOR = {"train": 42, "validation": 9, "test": 9}


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


def feature_family(feature_name: str) -> str:
    if feature_name.startswith("fw_"):
        return "function_word"
    if feature_name.startswith("char3_"):
        return "char3"
    if feature_name in {"word_count_feature", "sentence_count_feature", "paragraph_count_feature", "mean_sentence_words", "median_sentence_words", "std_sentence_words", "short_sentence_ratio", "long_sentence_ratio"}:
        return "length_rhythm"
    if "punctuation" in feature_name or feature_name.endswith("_per_1000w") and any(x in feature_name for x in ["comma", "semicolon", "colon", "dash", "question", "exclamation", "quote", "apostrophe", "ellipsis"]):
        return "punctuation"
    if feature_name in {"type_token_ratio", "root_type_token_ratio", "hapax_ratio", "avg_word_length", "long_word_ratio", "short_word_ratio"}:
        return "lexical_richness"
    return "register_marker"


def deterministic_passage_split(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    passages_by_author: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        passage_id = row["passage_id"]
        author_id = row["author_id"]
        if passage_id not in passages_by_author[author_id]:
            passages_by_author[author_id].append(passage_id)

    split_rows: list[dict[str, object]] = []
    for author in EXPECTED_AUTHORS:
        passages = sorted(passages_by_author[author])
        if len(passages) != 60:
            raise ValueError(f"Expected 60 passages for {author}, found {len(passages)}")
        idx = 0
        for split_name, n in SPLIT_COUNTS_PER_AUTHOR.items():
            for passage_id in passages[idx:idx+n]:
                split_rows.append({"passage_id": passage_id, "author_id": author, "split": split_name})
            idx += n
    return split_rows


def main() -> int:
    if not FEATURES.exists():
        print(f"Missing Step 12 features: {FEATURES.relative_to(ROOT)}")
        return 1
    rows = read_csv(FEATURES)
    if len(rows) != 1440:
        print(f"Expected 1440 feature rows, found {len(rows)}")
        return 1
    fieldnames = list(rows[0].keys())
    feature_cols = [col for col in fieldnames if col not in ID_COLS]
    if len(feature_cols) < 150:
        print(f"Too few feature columns: {len(feature_cols)}")
        return 1

    split_rows = deterministic_passage_split(rows)
    split_by_passage = {row["passage_id"]: row["split"] for row in split_rows}

    metadata_rows = []
    x_raw_rows = []
    y_rows = []
    for row in rows:
        split = split_by_passage[row["passage_id"]]
        metadata_rows.append({
            "text_id": row["text_id"],
            "passage_id": row["passage_id"],
            "condition": row["condition"],
            "author_id": row["author_id"],
            "author_name": row["author_name"],
            "work_id": row["work_id"],
            "work_title": row["work_title"],
            "qc_status": row["qc_status"],
            "qc_flags": row["qc_flags"],
            "split": split,
        })
        x_raw_rows.append({"text_id": row["text_id"], **{col: row[col] for col in feature_cols}})
        y_rows.append({"text_id": row["text_id"], "author_id": row["author_id"], "condition": row["condition"], "split": split})

    scaling_rows = []
    scaled_rows = []
    numeric_matrix: dict[str, list[float]] = {col: [float(row[col]) for row in rows] for col in feature_cols}
    means = {col: statistics.mean(vals) for col, vals in numeric_matrix.items()}
    stds = {col: statistics.pstdev(vals) for col, vals in numeric_matrix.items()}
    for col in feature_cols:
        scaling_rows.append({
            "feature": col,
            "mean_full_dataset": round(means[col], 12),
            "std_full_dataset": round(stds[col], 12),
            "scaling_scope": "full_dataset_descriptive_not_for_classifier_training",
        })
    for row in rows:
        out = {"text_id": row["text_id"]}
        for col in feature_cols:
            std = stds[col]
            value = float(row[col])
            out[col] = round((value - means[col]) / std, 12) if std else 0.0
        scaled_rows.append(out)

    feature_column_rows = [
        {"feature": col, "feature_index": i + 1, "feature_family": feature_family(col)}
        for i, col in enumerate(feature_cols)
    ]

    split_summary_rows = []
    for split_name in ["train", "validation", "test"]:
        subset = [row for row in metadata_rows if row["split"] == split_name]
        split_summary_rows.append({
            "split": split_name,
            "text_rows": len(subset),
            "unique_passages": len({row["passage_id"] for row in subset}),
            "authors": len({row["author_id"] for row in subset}),
            "original_rows": sum(1 for row in subset if row["condition"] == "original"),
            "paraphrase_rows": sum(1 for row in subset if row["condition"] == "paraphrase"),
            "modernize_rows": sum(1 for row in subset if row["condition"] == "modernize"),
            "simplify_rows": sum(1 for row in subset if row["condition"] == "simplify"),
        })

    write_csv(MODELING_METADATA, metadata_rows, ["text_id", "passage_id", "condition", "author_id", "author_name", "work_id", "work_title", "qc_status", "qc_flags", "split"])
    write_csv(X_RAW, x_raw_rows, ["text_id"] + feature_cols)
    write_csv(X_SCALED, scaled_rows, ["text_id"] + feature_cols)
    write_csv(Y_LABELS, y_rows, ["text_id", "author_id", "condition", "split"])
    write_csv(SPLIT, split_rows, ["passage_id", "author_id", "split"])
    write_csv(FEATURE_COLUMNS, feature_column_rows, ["feature", "feature_index", "feature_family"])
    write_csv(SPLIT_SUMMARY, split_summary_rows, ["split", "text_rows", "unique_passages", "authors", "original_rows", "paraphrase_rows", "modernize_rows", "simplify_rows"])
    write_csv(SCALING_PARAMS, scaling_rows, ["feature", "mean_full_dataset", "std_full_dataset", "scaling_scope"])

    artifacts = [MODELING_METADATA, X_RAW, X_SCALED, Y_LABELS, SPLIT, FEATURE_COLUMNS, SPLIT_SUMMARY, SCALING_PARAMS]
    manifest_rows = [
        {"artifact": path.stem, "path": path.relative_to(ROOT).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha_file(path)}
        for path in artifacts
    ]
    write_csv(MANIFEST, manifest_rows, ["artifact", "path", "size_bytes", "sha256"])

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Step 13 Modeling Matrix Report\n\n"
        "## Status\n\nComplete when generated locally and checker passes.\n\n"
        "## Matrix sizes\n\n"
        f"- rows: {len(rows)}\n"
        f"- feature columns: {len(feature_cols)}\n"
        f"- train rows: {next(row['text_rows'] for row in split_summary_rows if row['split'] == 'train')}\n"
        f"- validation rows: {next(row['text_rows'] for row in split_summary_rows if row['split'] == 'validation')}\n"
        f"- test rows: {next(row['text_rows'] for row in split_summary_rows if row['split'] == 'test')}\n\n"
        "## Scaling note\n\n"
        "`X_stylometric_scaled_descriptive.csv` is full-dataset descriptive scaling only. Classifier experiments must fit scalers on training rows only inside later modeling scripts.\n",
        encoding="utf-8",
    )
    print(f"Prepared modeling matrices with {len(rows)} rows and {len(feature_cols)} feature columns.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
