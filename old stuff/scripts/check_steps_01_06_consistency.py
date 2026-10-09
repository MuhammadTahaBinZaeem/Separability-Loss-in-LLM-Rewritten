"""
Automated consistency checker for Steps 1-6.

Run from repository root:

    python scripts/check_steps_01_06_consistency.py

Exit code:
    0 = all checks passed
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TRACKED_SOURCES = 29
EXPECTED_EXTRACTED = 29
EXPECTED_CLEANED = 29
EXPECTED_VALIDATED_SOURCES = 29
EXPECTED_ELIGIBLE_VALIDATED_SOURCES = 22
EXPECTED_EXCLUDED_TRACKED_SOURCES = 7
EXPECTED_VALIDATION_FLAGGED_SOURCES = 0
EXPECTED_TARGET_FINAL_PASSAGES_PER_AUTHOR = 60
EXPECTED_MINIMUM_CANDIDATE_PASSAGES_PER_AUTHOR = 120

FORBIDDEN_STRINGS = [
    "not_extracted_yet",
    "44,782,448",
    "44782448",
    "Actual cleaned text output is not generated",
    "Step 3 incomplete",
    "Step 4 deferred",
    "Step 5 incomplete",
    "Wilde source gap: completely missing",
]

REQUIRED_FILES = [
    "logs/step_01_status.md",
    "logs/step_02_status.md",
    "logs/step_03_status.md",
    "logs/step_03_final_verification.md",
    "logs/step_04_status.md",
    "logs/step_04_reproduction_verification.md",
    "logs/step_05_status.md",
    "logs/step_06_status.md",
    "logs/cleaning_validation_report.md",
    "metadata/source_inventory.csv",
    "metadata/source_id_map.csv",
    "metadata/raw_file_checksums.csv",
    "metadata/extracted_text_checksums_by_id.csv",
    "metadata/cleaned_text_checksums_by_id.csv",
    "metadata/cleaning_validation_metrics.csv",
    "metadata/author_style_validation_summary.csv",
    "metadata/candidate_passage_schema.csv",
    "metadata/passage_extraction_config.json",
    "docs/passage_extraction_protocol.md",
    "docs/data_dictionary.md",
    "scripts/00_preserve_sources.py",
    "scripts/01_clean_texts.py",
    "scripts/02_validate_cleaning.py",
    "scripts/03_extract_candidate_passages.py",
]


def read_csv(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def normalized_source_ids(rows: list[dict[str, str]]) -> set[str]:
    return {row["source_id"].split("_")[0] + "_" + row["source_id"].split("_")[1] for row in rows}


def main() -> int:
    failures: list[str] = []

    for rel in REQUIRED_FILES:
        check((ROOT / rel).exists(), f"missing required file: {rel}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    source_inventory = read_csv("metadata/source_inventory.csv")
    source_id_map = read_csv("metadata/source_id_map.csv")
    extracted = read_csv("metadata/extracted_text_checksums_by_id.csv")
    cleaned = read_csv("metadata/cleaned_text_checksums_by_id.csv")
    validation_metrics = read_csv("metadata/cleaning_validation_metrics.csv")
    author_validation = read_csv("metadata/author_style_validation_summary.csv")
    candidate_schema = read_csv("metadata/candidate_passage_schema.csv")
    config = json.loads((ROOT / "metadata/passage_extraction_config.json").read_text(encoding="utf-8"))

    check(len(source_inventory) == EXPECTED_TRACKED_SOURCES, "source_inventory row count mismatch", failures)
    check(len(source_id_map) == EXPECTED_TRACKED_SOURCES, "source_id_map row count mismatch", failures)
    check(len(extracted) == EXPECTED_EXTRACTED, "extracted checksum row count mismatch", failures)
    check(len(cleaned) == EXPECTED_CLEANED, "cleaned checksum row count mismatch", failures)
    check(len(validation_metrics) == EXPECTED_VALIDATED_SOURCES, "validation metrics row count mismatch", failures)
    check(len(author_validation) == 6, "author validation count mismatch", failures)

    expected_ids = {f"src_{i:03d}" for i in range(1, EXPECTED_TRACKED_SOURCES + 1)}
    for table_name, rows in [
        ("source_id_map", source_id_map),
        ("extracted_text_checksums_by_id", extracted),
        ("cleaned_text_checksums_by_id", cleaned),
        ("cleaning_validation_metrics", validation_metrics),
    ]:
        check(normalized_source_ids(rows) == expected_ids, f"{table_name} source_id set mismatch", failures)

    eligible = [row for row in validation_metrics if row["main_corpus_status"] != "excluded"]
    excluded = [row for row in validation_metrics if row["main_corpus_status"] == "excluded"]
    flagged = [row for row in validation_metrics if row["validation_flags"].strip()]
    check(len(eligible) == EXPECTED_ELIGIBLE_VALIDATED_SOURCES, "eligible validation count mismatch", failures)
    check(len(excluded) == EXPECTED_EXCLUDED_TRACKED_SOURCES, "excluded validation count mismatch", failures)
    check(len(flagged) == EXPECTED_VALIDATION_FLAGGED_SOURCES, "validation flags present", failures)
    check(all(row["style_validation_result"] == "pass" for row in author_validation), "author validation not all pass", failures)

    schema_cols = {row["column"] for row in candidate_schema}
    required_candidate_cols = {
        "candidate_id", "source_id", "author_id", "author_name", "work_id", "work_title", "source_path",
        "candidate_index_within_source", "start_word_index", "end_word_index", "word_count", "sentence_count",
        "paragraph_count", "start_char", "end_char", "dialogue_marker_count", "dialogue_marker_per_1000w",
        "punctuation_per_1000w", "semicolon_per_1000w", "dash_per_1000w", "apostrophe_per_1000w",
        "mean_sentence_words", "long_sentence_ratio", "extraction_rule_version", "candidate_status", "exclusion_reason", "text",
    }
    check(required_candidate_cols.issubset(schema_cols), "candidate passage schema missing required columns", failures)

    check(config.get("target_final_passages_per_author") == EXPECTED_TARGET_FINAL_PASSAGES_PER_AUTHOR, "target_final_passages_per_author mismatch", failures)
    check(config.get("minimum_candidate_passages_per_author") == EXPECTED_MINIMUM_CANDIDATE_PASSAGES_PER_AUTHOR, "minimum_candidate_passages_per_author mismatch", failures)
    check(config.get("minimum_words_per_passage") == 400, "minimum_words_per_passage mismatch", failures)
    check(config.get("maximum_words_per_passage") == 700, "maximum_words_per_passage mismatch", failures)
    check(config.get("minimum_gap_words_same_source") == 150, "minimum_gap_words_same_source mismatch", failures)

    source_text = "\n".join(
        (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for rel in REQUIRED_FILES
        if (ROOT / rel).suffix in {".md", ".csv", ".json", ".py"}
    )
    for forbidden in FORBIDDEN_STRINGS:
        check(forbidden not in source_text, f"forbidden stale string found: {forbidden}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: Steps 1-6 consistency checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
