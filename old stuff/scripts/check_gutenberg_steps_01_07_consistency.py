"""
Consistency checker for the canonical Gutenberg source layer through Step 7.

Run from repository root:

    python scripts/check_gutenberg_steps_01_07_consistency.py

Exit code:
    0 = canonical Gutenberg layer is internally consistent and balance-ready
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SOURCES = 12
EXPECTED_AUTHORS = 6
EXPECTED_CANDIDATES = 1879
EXPECTED_PASSING = 1879
EXPECTED_MIN_PER_AUTHOR = 120
EXPECTED_CLEANED_WORDS = 1373324
EXPECTED_RAW_WORDS = 1373324

REQUIRED_FILES = [
    "metadata/gutenberg_canonical_registry.csv",
    "metadata/gutenberg_alias_map.csv",
    "metadata/gutenberg_raw_text_checksums.csv",
    "metadata/gutenberg_cleaned_text_checksums.csv",
    "metadata/gutenberg_cleaning_summary.csv",
    "metadata/gutenberg_cleaning_validation_metrics.csv",
    "metadata/gutenberg_author_summary.csv",
    "metadata/gutenberg_candidate_generation_summary.csv",
    "metadata/gutenberg_candidate_counts_by_author.csv",
    "metadata/gutenberg_candidate_counts_by_source.csv",
    "logs/gutenberg_fetch_report.md",
    "logs/gutenberg_cleaning_report.csv",
    "logs/gutenberg_candidate_generation_report.md",
    "logs/step_07_gutenberg_status.md",
    "scripts/04_fetch_gutenberg_sources.py",
    "scripts/05_run_canonical_migration.py",
]


def read_csv(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_summary(path: str) -> dict[str, str]:
    return {row["metric"]: row["value"] for row in read_csv(path)}


def fail_if(condition: bool, message: str, failures: list[str]) -> None:
    if condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    for rel in REQUIRED_FILES:
        fail_if(not (ROOT / rel).exists(), f"missing required file: {rel}", failures)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    registry = read_csv("metadata/gutenberg_canonical_registry.csv")
    alias_map = read_csv("metadata/gutenberg_alias_map.csv")
    raw = read_csv("metadata/gutenberg_raw_text_checksums.csv")
    cleaned = read_csv("metadata/gutenberg_cleaned_text_checksums.csv")
    validation = read_csv("metadata/gutenberg_cleaning_validation_metrics.csv")
    author_summary = read_csv("metadata/gutenberg_author_summary.csv")
    candidate_summary = read_summary("metadata/gutenberg_candidate_generation_summary.csv")
    by_author = read_csv("metadata/gutenberg_candidate_counts_by_author.csv")
    by_source = read_csv("metadata/gutenberg_candidate_counts_by_source.csv")
    cleaning_summary = read_summary("metadata/gutenberg_cleaning_summary.csv")

    for name, rows in [
        ("registry", registry),
        ("alias_map", alias_map),
        ("raw checksums", raw),
        ("cleaned checksums", cleaned),
        ("validation metrics", validation),
        ("source candidate counts", by_source),
    ]:
        fail_if(len(rows) != EXPECTED_SOURCES, f"{name} row count expected {EXPECTED_SOURCES}, got {len(rows)}", failures)

    fail_if(len(author_summary) != EXPECTED_AUTHORS, "author summary row count mismatch", failures)
    fail_if(len(by_author) != EXPECTED_AUTHORS, "candidate author count row count mismatch", failures)

    canonical_ids = {row["canonical_id"] for row in registry}
    alias_ids = {row["alias_id"] for row in alias_map}
    fail_if(len(canonical_ids) != EXPECTED_SOURCES, "canonical IDs are not unique", failures)
    fail_if(len(alias_ids) != EXPECTED_SOURCES, "alias IDs are not unique", failures)
    for name, rows in [
        ("alias map", alias_map),
        ("raw checksums", raw),
        ("cleaned checksums", cleaned),
        ("validation metrics", validation),
        ("source candidate counts", by_source),
    ]:
        fail_if({row["canonical_id"] for row in rows} != canonical_ids, f"{name} canonical ID set mismatch", failures)

    fail_if(cleaning_summary.get("cleaned_file_count") != str(EXPECTED_SOURCES), "cleaned file count mismatch", failures)
    fail_if(cleaning_summary.get("total_raw_words") != str(EXPECTED_RAW_WORDS), "total raw word count mismatch", failures)
    fail_if(cleaning_summary.get("total_cleaned_words") != str(EXPECTED_CLEANED_WORDS), "total cleaned word count mismatch", failures)
    fail_if(cleaning_summary.get("files_with_warning_flags") != "0", "cleaning warnings present", failures)

    fail_if(candidate_summary.get("candidate_rows") != str(EXPECTED_CANDIDATES), "candidate row count mismatch", failures)
    fail_if(candidate_summary.get("candidate_pass_length") != str(EXPECTED_PASSING), "passing candidate count mismatch", failures)
    fail_if(candidate_summary.get("candidate_fail_length") != "0", "failed length candidates present", failures)
    fail_if(candidate_summary.get("candidate_fail_low_sentence_count") != "0", "failed low-sentence candidates present", failures)
    fail_if(candidate_summary.get("authors_meeting_120_candidate_target") != "6", "not all authors meet candidate target", failures)
    fail_if(candidate_summary.get("authors_below_120_candidate_target") != "0", "some authors below candidate target", failures)

    for row in by_author:
        fail_if(int(row["candidate_pass_length"]) < EXPECTED_MIN_PER_AUTHOR, f"{row['author_id']} below 120 candidates", failures)
        fail_if(str(row["meets_120_target"]).lower() != "true", f"{row['author_id']} target flag false", failures)

    fail_if(any(row["validation_flags"].strip() for row in validation), "validation flags present", failures)
    fail_if(any(row["result"] != "pass" for row in author_summary), "author summary not all pass", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: Gutenberg canonical Steps 1-7 are internally consistent and balance-ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
