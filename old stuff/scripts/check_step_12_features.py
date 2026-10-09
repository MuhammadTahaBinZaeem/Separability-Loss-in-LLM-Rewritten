"""
Consistency checker for Step 12 stylometric features.

Run from repository root after Step 12 extraction:

    python scripts/check_step_12_features.py

Exit code:
    0 = Step 12 feature table is internally consistent
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "final" / "master_text_dataset.csv"
FEATURES = ROOT / "data" / "features" / "stylometric_features.csv"
SUMMARY = ROOT / "metadata" / "stylometric_feature_summary.csv"
FAMILY_COUNTS = ROOT / "metadata" / "stylometric_feature_family_counts.csv"
MANIFEST = ROOT / "metadata" / "stylometric_feature_manifest.csv"
REPORT = ROOT / "logs" / "step_12_feature_extraction_report.md"
SCRIPT = ROOT / "scripts" / "13_extract_stylometric_features.py"

EXPECTED_CONDITIONS = {"original", "paraphrase", "modernize", "simplify"}
EXPECTED_AUTHORS = {"austen", "dickens", "poe", "shelley", "twain", "wilde"}
ID_COLS = {"text_id", "passage_id", "condition", "author_id", "author_name", "work_id", "work_title", "qc_status", "qc_flags"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def summary_dict(path: Path) -> dict[str, str]:
    return {row["metric"]: row["value"] for row in read_csv(path)}


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    for path in [MASTER, FEATURES, SUMMARY, FAMILY_COUNTS, MANIFEST, REPORT, SCRIPT]:
        check(path.exists(), f"missing required Step 12 file: {path.relative_to(ROOT)}", failures)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    master_rows = read_csv(MASTER)
    feature_rows = read_csv(FEATURES)
    check(len(master_rows) == 1440, f"master rows expected 1440, found {len(master_rows)}", failures)
    check(len(feature_rows) == 1440, f"feature rows expected 1440, found {len(feature_rows)}", failures)
    check({row["text_id"] for row in master_rows} == {row["text_id"] for row in feature_rows}, "feature text_id set does not match master", failures)
    check(len({row["text_id"] for row in feature_rows}) == 1440, "feature text_id values not unique", failures)

    fieldnames = list(feature_rows[0].keys()) if feature_rows else []
    check(ID_COLS.issubset(set(fieldnames)), "missing identifier columns", failures)
    numeric_cols = [col for col in fieldnames if col not in ID_COLS]
    check(len(numeric_cols) >= 150, f"expected at least 150 numeric feature columns, found {len(numeric_cols)}", failures)

    condition_counts = Counter(row["condition"] for row in feature_rows)
    author_counts = Counter(row["author_id"] for row in feature_rows)
    check(set(condition_counts) == EXPECTED_CONDITIONS, f"conditions mismatch: {set(condition_counts)}", failures)
    for condition in EXPECTED_CONDITIONS:
        check(condition_counts[condition] == 360, f"condition {condition} not 360", failures)
    check(set(author_counts) == EXPECTED_AUTHORS, f"authors mismatch: {set(author_counts)}", failures)
    for author in EXPECTED_AUTHORS:
        check(author_counts[author] == 240, f"author {author} not 240", failures)

    for col in numeric_cols:
        values = [row[col] for row in feature_rows]
        check(any(v not in ("", "nan", "NaN", "None") for v in values), f"feature column entirely empty: {col}", failures)
        try:
            [float(v) for v in values]
        except ValueError:
            failures.append(f"feature column is not numeric: {col}")

    summary = summary_dict(SUMMARY)
    check(summary.get("feature_rows") == "1440", "summary feature_rows mismatch", failures)
    check(summary.get("unique_text_ids") == "1440", "summary unique_text_ids mismatch", failures)
    check(int(summary.get("feature_columns", "0")) == len(numeric_cols), "summary feature_columns mismatch", failures)
    check(summary.get("original_rows") == "360", "summary original_rows mismatch", failures)
    check(summary.get("paraphrase_rows") == "360", "summary paraphrase_rows mismatch", failures)
    check(summary.get("modernize_rows") == "360", "summary modernize_rows mismatch", failures)
    check(summary.get("simplify_rows") == "360", "summary simplify_rows mismatch", failures)

    family_rows = read_csv(FAMILY_COUNTS)
    families = {row["feature_family"] for row in family_rows}
    expected_families = {"char3", "function_word", "length_rhythm", "lexical_richness", "punctuation", "register_marker"}
    check(expected_families.issubset(families), f"missing feature families: {expected_families - families}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: Step 12 stylometric feature table is complete and internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
