"""
Consistency checker for Step 11 master text dataset.

Run from repository root after `scripts/12_build_master_text_dataset.py`:

    python scripts/check_step_11_master_dataset.py
"""

from __future__ import annotations

import csv
import hashlib
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MASTER = ROOT / "data" / "final" / "master_text_dataset.csv"
SUMMARY = ROOT / "metadata" / "master_text_dataset_summary.csv"
COUNTS_CONDITION = ROOT / "metadata" / "master_text_counts_by_condition.csv"
COUNTS_AUTHOR_CONDITION = ROOT / "metadata" / "master_text_counts_by_author_condition.csv"
MANIFEST = ROOT / "metadata" / "master_text_dataset_manifest.csv"
REPORT = ROOT / "logs" / "step_11_master_dataset_report.md"

EXPECTED_ROWS = 1440
EXPECTED_PASSAGES = 360
EXPECTED_AUTHORS = 6
EXPECTED_WORKS = 12
EXPECTED_CONDITIONS = {"original", "paraphrase", "modernize", "simplify"}
EXPECTED_PER_CONDITION = 360
EXPECTED_PER_AUTHOR_CONDITION = 60
EXPECTED_PER_WORK_CONDITION = 30

REQUIRED_MASTER_FIELDS = {
    "text_id",
    "passage_id",
    "condition",
    "text_group",
    "author_id",
    "author_name",
    "work_id",
    "work_title",
    "original_word_count",
    "text_word_count",
    "text_sha256",
    "source_text_sha256",
    "qc_status",
    "qc_flags",
    "parse_status",
    "text",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def read_summary(path: Path) -> dict[str, str]:
    return {row["metric"]: row["value"] for row in read_csv(path)}


def main() -> int:
    failures: list[str] = []
    required = [MASTER, SUMMARY, COUNTS_CONDITION, COUNTS_AUTHOR_CONDITION, MANIFEST, REPORT]
    for path in required:
        check(path.exists(), f"missing Step 11 file: {path.relative_to(ROOT)}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    master = read_csv(MASTER)
    summary = read_summary(SUMMARY)
    counts_condition = read_csv(COUNTS_CONDITION)
    counts_author_condition = read_csv(COUNTS_AUTHOR_CONDITION)
    manifest = read_csv(MANIFEST)

    check(len(master) == EXPECTED_ROWS, "master row count mismatch", failures)
    if master:
        check(REQUIRED_MASTER_FIELDS.issubset(master[0].keys()), "master dataset missing required columns", failures)

    text_ids = [row["text_id"] for row in master]
    passage_ids = [row["passage_id"] for row in master]
    condition_counts = Counter(row["condition"] for row in master)
    author_condition_counts = Counter((row["author_id"], row["condition"]) for row in master)
    work_condition_counts = Counter((row["author_id"], row["work_id"], row["condition"]) for row in master)
    statuses = Counter(row["qc_status"] for row in master)
    parse_statuses = Counter(row["parse_status"] for row in master if row["condition"] != "original")

    check(len(set(text_ids)) == EXPECTED_ROWS, "text_id values are not unique", failures)
    check(len(set(passage_ids)) == EXPECTED_PASSAGES, "unique passage_id count mismatch", failures)
    check(set(condition_counts) == EXPECTED_CONDITIONS, "condition set mismatch", failures)
    for condition in EXPECTED_CONDITIONS:
        check(condition_counts[condition] == EXPECTED_PER_CONDITION, f"{condition} row count mismatch", failures)

    check(len({row["author_id"] for row in master}) == EXPECTED_AUTHORS, "author count mismatch", failures)
    check(len({(row["author_id"], row["work_id"]) for row in master}) == EXPECTED_WORKS, "work count mismatch", failures)
    for key, count in author_condition_counts.items():
        check(count == EXPECTED_PER_AUTHOR_CONDITION, f"author-condition count mismatch: {key}", failures)
    for key, count in work_condition_counts.items():
        check(count == EXPECTED_PER_WORK_CONDITION, f"work-condition count mismatch: {key}", failures)

    by_passage: dict[str, set[str]] = {}
    for row in master:
        by_passage.setdefault(row["passage_id"], set()).add(row["condition"])
        check(bool(row["text"].strip()), f"empty text: {row['text_id']}", failures)
        check(row["text_sha256"] == sha_text(row["text"]), f"text SHA mismatch: {row['text_id']}", failures)
        check(row["qc_status"] in {"pass", "warning"}, f"unexpected QC status: {row['text_id']}", failures)
        if row["condition"] == "original":
            check(row["text_group"] == "original", f"original text_group mismatch: {row['text_id']}", failures)
            check(row["parse_status"] == "not_applicable", f"original parse_status mismatch: {row['text_id']}", failures)
        else:
            check(row["text_group"] == "rewrite", f"rewrite text_group mismatch: {row['text_id']}", failures)
            check(row["rewrite_request_id"] == row["text_id"], f"rewrite_request_id mismatch: {row['text_id']}", failures)
            check(row["parse_status"] in {"json_ok", "json_parse_failed_used_raw_content"}, f"unexpected parse_status: {row['text_id']}", failures)

    for passage_id, conditions in by_passage.items():
        check(conditions == EXPECTED_CONDITIONS, f"condition coverage mismatch: {passage_id}", failures)

    check(statuses.get("fail", 0) == 0, "master dataset contains QC fail rows", failures)
    check(parse_statuses.get("json_parse_failed_used_raw_content", 0) == 1, "JSON parse fallback count mismatch", failures)

    check(summary.get("master_rows") == str(EXPECTED_ROWS), "summary master_rows mismatch", failures)
    check(summary.get("rewrite_qc_fail") == "0", "summary rewrite_qc_fail mismatch", failures)
    check(summary.get("empty_text_rows") == "0", "summary empty_text_rows mismatch", failures)

    count_condition_map = {row["condition"]: row for row in counts_condition}
    check(set(count_condition_map) == EXPECTED_CONDITIONS, "condition counts table condition set mismatch", failures)
    for condition in EXPECTED_CONDITIONS:
        row = count_condition_map.get(condition, {})
        check(row.get("row_count") == str(EXPECTED_PER_CONDITION), f"condition count mismatch: {condition}", failures)
        check(row.get("unique_passages") == str(EXPECTED_PASSAGES), f"condition unique passage mismatch: {condition}", failures)
        check(row.get("qc_fail") == "0", f"condition QC fail mismatch: {condition}", failures)

    check(len(counts_author_condition) == EXPECTED_AUTHORS * len(EXPECTED_CONDITIONS), "author-condition table row count mismatch", failures)
    for row in counts_author_condition:
        key = (row["author_id"], row["condition"])
        check(author_condition_counts[key] == int(row["row_count"]), f"author-condition table mismatch: {key}", failures)
        check(row["row_count"] == str(EXPECTED_PER_AUTHOR_CONDITION), f"author-condition row count mismatch: {key}", failures)
        check(row["qc_fail"] == "0", f"author-condition QC fail mismatch: {key}", failures)

    for row in manifest:
        path = ROOT / row["path"]
        check(path.exists(), f"manifest path missing: {row['path']}", failures)
        if path.exists():
            check(path.stat().st_size == int(row["size_bytes"]), f"manifest size mismatch: {row['path']}", failures)
            check(sha_file(path) == row["sha256"], f"manifest SHA mismatch: {row['path']}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: Step 11 master text dataset is complete and internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
