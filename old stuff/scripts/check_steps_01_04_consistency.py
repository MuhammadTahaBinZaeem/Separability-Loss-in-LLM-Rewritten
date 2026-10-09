"""
Automated consistency checker for Steps 1-4.

This script is a guardrail against stale metadata. It checks that the early
pipeline files agree on source counts, extraction counts, cleaning counts, and
known excluded/accepted source decisions.

Run from repository root:

    python scripts/check_steps_01_04_consistency.py

Exit code:
    0 = all checks passed
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TRACKED_SOURCES = 29
EXPECTED_ORIGINAL_ZIP_SOURCES = 27
EXPECTED_LATER_WILDE_SOURCES = 2
EXPECTED_EXTRACTED = 29
EXPECTED_CLEANED = 29
EXPECTED_EXTRACTION_WORDS = 8245542
EXPECTED_EXTRACTION_BYTES = 47056686
EXPECTED_CLEANED_WORDS = 8235425
EXPECTED_CLEANED_CHARS = 46089342

FORBIDDEN_STRINGS = [
    "not_extracted_yet",
    "44,782,448",
    "44782448",
    "Actual cleaned text output is not generated",
    "Step 3 incomplete",
    "Step 4 deferred",
    "Wilde source gap: completely missing",
]

REQUIRED_FILES = [
    "logs/step_01_status.md",
    "logs/step_02_status.md",
    "logs/step_03_status.md",
    "logs/step_03_final_verification.md",
    "logs/step_04_status.md",
    "logs/step_04_reproduction_verification.md",
    "metadata/source_inventory.csv",
    "metadata/source_item_review.csv",
    "metadata/source_id_map.csv",
    "metadata/author_work_map.csv",
    "metadata/raw_file_checksums.csv",
    "metadata/extracted_text_checksums_by_id.csv",
    "metadata/text_extraction_status_summary.csv",
    "metadata/cleaning_summary.csv",
    "metadata/cleaned_text_checksums_by_id.csv",
    "logs/cleaning_report.csv",
    "scripts/00_preserve_sources.py",
    "scripts/01_clean_texts.py",
    "docs/cleaning_rules.md",
    "docs/raw_source_handling.md",
    "docs/corpus_selection_rationale.md",
    "docs/data_dictionary.md",
]


def read_csv(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_summary(path: str) -> dict[str, str]:
    rows = read_csv(path)
    return {row["metric"]: row["value"] for row in rows}


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []

    for rel in REQUIRED_FILES:
        check((ROOT / rel).exists(), f"missing required file: {rel}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    source_inventory = read_csv("metadata/source_inventory.csv")
    raw_checksums = read_csv("metadata/raw_file_checksums.csv")
    source_id_map = read_csv("metadata/source_id_map.csv")
    extracted = read_csv("metadata/extracted_text_checksums_by_id.csv")
    cleaned = read_csv("metadata/cleaned_text_checksums_by_id.csv")
    cleaning_report = read_csv("logs/cleaning_report.csv")
    extraction_summary = read_summary("metadata/text_extraction_status_summary.csv")
    cleaning_summary = read_summary("metadata/cleaning_summary.csv")

    check(len(source_inventory) == EXPECTED_TRACKED_SOURCES, "source_inventory row count mismatch", failures)
    check(len(raw_checksums) == EXPECTED_TRACKED_SOURCES, "raw_file_checksums row count mismatch", failures)
    check(len(source_id_map) == EXPECTED_TRACKED_SOURCES, "source_id_map row count mismatch", failures)
    check(len(extracted) == EXPECTED_EXTRACTED, "extracted_text_checksums_by_id row count mismatch", failures)
    check(len(cleaned) == EXPECTED_CLEANED, "cleaned_text_checksums_by_id row count mismatch", failures)
    check(len(cleaning_report) == EXPECTED_CLEANED, "cleaning_report row count mismatch", failures)

    expected_ids = {f"src_{i:03d}" for i in range(1, EXPECTED_TRACKED_SOURCES + 1)}
    for table_name, rows in [
        ("source_id_map", source_id_map),
        ("extracted_text_checksums_by_id", extracted),
        ("cleaned_text_checksums_by_id", cleaned),
    ]:
        ids = {row["source_id"].split("_")[0] + "_" + row["source_id"].split("_")[1] for row in rows}
        check(ids == expected_ids, f"{table_name} source_id set mismatch", failures)

    check(extraction_summary.get("tracked_pdf_count") == str(EXPECTED_TRACKED_SOURCES), "tracked_pdf_count mismatch", failures)
    check(extraction_summary.get("original_zip_pdf_count") == str(EXPECTED_ORIGINAL_ZIP_SOURCES), "original_zip_pdf_count mismatch", failures)
    check(extraction_summary.get("later_uploaded_wilde_pdf_count") == str(EXPECTED_LATER_WILDE_SOURCES), "later_uploaded_wilde_pdf_count mismatch", failures)
    check(extraction_summary.get("extracted_pdf_count") == str(EXPECTED_EXTRACTED), "extracted_pdf_count mismatch", failures)
    check(extraction_summary.get("failed_or_empty_pdf_count") == "0", "failed_or_empty_pdf_count is not zero", failures)
    check(extraction_summary.get("total_extracted_words") == str(EXPECTED_EXTRACTION_WORDS), "total_extracted_words mismatch", failures)
    check(extraction_summary.get("total_extracted_text_bytes_utf8") == str(EXPECTED_EXTRACTION_BYTES), "total_extracted_text_bytes_utf8 mismatch", failures)

    check(cleaning_summary.get("cleaned_file_count") == str(EXPECTED_CLEANED), "cleaned_file_count mismatch", failures)
    check(cleaning_summary.get("total_cleaned_words") == str(EXPECTED_CLEANED_WORDS), "total_cleaned_words mismatch", failures)
    check(cleaning_summary.get("total_cleaned_chars") == str(EXPECTED_CLEANED_CHARS), "total_cleaned_chars mismatch", failures)
    check(cleaning_summary.get("files_with_warning_flags") == "0", "files_with_warning_flags is not zero", failures)

    source_text = "\n".join((ROOT / rel).read_text(encoding="utf-8", errors="replace") for rel in REQUIRED_FILES if (ROOT / rel).suffix in {".md", ".csv", ".json", ".py"})
    for forbidden in FORBIDDEN_STRINGS:
        check(forbidden not in source_text, f"forbidden stale string found: {forbidden}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: Steps 1-4 consistency checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
