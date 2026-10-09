"""
Consistency checker for Step 8 final selected original passages.

Run from repository root after `scripts/07_select_final_passages.py`:

    python scripts/check_step_08_selection.py

This checker validates the full local Step 8 text-bearing outputs when they are
present. It also validates the committed Step 8 summary/count files.

Exit code:
    0 = Step 8 is internally consistent and complete locally
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import hashlib
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SELECTED_CSV = ROOT / "data" / "processed" / "selected_original_passages.csv"
SELECTED_METADATA = ROOT / "metadata" / "selected_original_passage_metadata.csv"
COUNTS_AUTHOR = ROOT / "metadata" / "selected_counts_by_author.csv"
COUNTS_WORK = ROOT / "metadata" / "selected_counts_by_work.csv"
SUMMARY = ROOT / "metadata" / "selection_summary.csv"
FILTER_REPORT = ROOT / "metadata" / "selection_filter_report.csv"
MANIFEST = ROOT / "metadata" / "step8_output_manifest.csv"
MD_MANIFEST = ROOT / "metadata" / "selected_passage_md_manifest.csv"
STATUS = ROOT / "logs" / "step_08_status.md"
SCRIPT = ROOT / "scripts" / "07_select_final_passages.py"

EXPECTED_AUTHORS = 6
EXPECTED_WORKS = 12
EXPECTED_SELECTED = 360
EXPECTED_PER_AUTHOR = 60
EXPECTED_PER_WORK = 30
MIN_WORDS = 450
MAX_WORDS = 650


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_summary(path: Path) -> dict[str, str]:
    return {row["metric"]: row["value"] for row in read_csv(path)}


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    required_committed = [
        COUNTS_AUTHOR,
        COUNTS_WORK,
        SUMMARY,
        FILTER_REPORT,
        MANIFEST,
        STATUS,
        SCRIPT,
    ]
    for path in required_committed:
        check(path.exists(), f"missing required Step 8 file: {path.relative_to(ROOT)}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    summary = read_summary(SUMMARY)
    check(summary.get("selected_passages") == str(EXPECTED_SELECTED), "summary selected_passages mismatch", failures)
    check(summary.get("authors") == str(EXPECTED_AUTHORS), "summary authors mismatch", failures)
    check(summary.get("works") == str(EXPECTED_WORKS), "summary works mismatch", failures)
    check(summary.get("selected_per_author") == str(EXPECTED_PER_AUTHOR), "summary selected_per_author mismatch", failures)
    check(summary.get("selected_per_work") == str(EXPECTED_PER_WORK), "summary selected_per_work mismatch", failures)
    check(summary.get("selection_status") == "complete", "selection_status is not complete", failures)

    counts_author = read_csv(COUNTS_AUTHOR)
    counts_work = read_csv(COUNTS_WORK)
    check(len(counts_author) == EXPECTED_AUTHORS, "author count table row mismatch", failures)
    check(len(counts_work) == EXPECTED_WORKS, "work count table row mismatch", failures)
    for row in counts_author:
        check(int(row["selected_passages"]) == EXPECTED_PER_AUTHOR, f"{row['author_id']} != 60 selected passages", failures)
        check(int(row["min_words"]) >= MIN_WORDS, f"{row['author_id']} min_words below bound", failures)
        check(int(row["max_words"]) <= MAX_WORDS, f"{row['author_id']} max_words above bound", failures)
    for row in counts_work:
        check(int(row["selected_passages"]) == EXPECTED_PER_WORK, f"{row['author_id']}/{row['work_id']} != 30 selected passages", failures)
        check(int(row["min_words"]) >= MIN_WORDS, f"{row['work_id']} min_words below bound", failures)
        check(int(row["max_words"]) <= MAX_WORDS, f"{row['work_id']} max_words above bound", failures)

    # Full local artifact checks are required for final local completeness.
    local_text_files = [SELECTED_CSV, SELECTED_METADATA, MD_MANIFEST]
    for path in local_text_files:
        check(path.exists(), f"missing local text-bearing Step 8 artifact: {path.relative_to(ROOT)}", failures)

    if SELECTED_CSV.exists():
        rows = read_csv(SELECTED_CSV)
        check(len(rows) == EXPECTED_SELECTED, "selected_original_passages.csv row count mismatch", failures)
        check(len({row["passage_id"] for row in rows}) == EXPECTED_SELECTED, "passage_id values are not unique", failures)
        check(len({row["candidate_id"] for row in rows}) == EXPECTED_SELECTED, "candidate_id values are not unique", failures)
        author_counts = Counter(row["author_id"] for row in rows)
        work_counts = Counter((row["author_id"], row["work_id"]) for row in rows)
        check(len(author_counts) == EXPECTED_AUTHORS, "selected CSV author count mismatch", failures)
        check(len(work_counts) == EXPECTED_WORKS, "selected CSV work count mismatch", failures)
        for author_id, count in author_counts.items():
            check(count == EXPECTED_PER_AUTHOR, f"selected CSV {author_id} count mismatch", failures)
        for (author_id, work_id), count in work_counts.items():
            check(count == EXPECTED_PER_WORK, f"selected CSV {author_id}/{work_id} count mismatch", failures)
        word_counts = [int(row["word_count"]) for row in rows]
        sentence_counts = [int(row["sentence_count"]) for row in rows]
        check(min(word_counts) >= MIN_WORDS, "selected CSV min word count below bound", failures)
        check(max(word_counts) <= MAX_WORDS, "selected CSV max word count above bound", failures)
        check(min(sentence_counts) >= 5, "selected CSV sentence count below 5", failures)
        check({row["condition"] for row in rows} == {"original"}, "selected CSV condition is not exactly original", failures)

    if SELECTED_METADATA.exists() and SELECTED_CSV.exists():
        meta = read_csv(SELECTED_METADATA)
        check(len(meta) == EXPECTED_SELECTED, "selected metadata row count mismatch", failures)
        check("text" not in meta[0], "selected metadata should not include full text column", failures)

    if MD_MANIFEST.exists():
        md_rows = read_csv(MD_MANIFEST)
        check(len(md_rows) == EXPECTED_AUTHORS, "selected markdown manifest should have 6 rows", failures)
        for row in md_rows:
            path = ROOT / row["path"]
            check(path.exists(), f"missing selected markdown file: {row['path']}", failures)
            if path.exists():
                check(path.stat().st_size == int(row["size_bytes"]), f"markdown size mismatch: {row['path']}", failures)
                check(sha_file(path) == row["sha256"], f"markdown SHA mismatch: {row['path']}", failures)
                text = path.read_text(encoding="utf-8", errors="replace")
                check(text.count("\n## ") == EXPECTED_PER_AUTHOR, f"markdown passage count mismatch: {row['path']}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: Step 8 selected original-passage layer is complete and internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
