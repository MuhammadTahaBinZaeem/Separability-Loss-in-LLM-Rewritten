"""
Step 11: build the master 1440-row text dataset.

Run from repository root after Step 10 rewrite outputs and QC are present:

    python scripts/12_build_master_text_dataset.py

Inputs:
- data/processed/selected_original_passages.csv
- data/interim/rewrite_responses_parsed.csv
- metadata/rewrite_qc_report.csv

Outputs:
- data/final/master_text_dataset.csv
- metadata/master_text_dataset_summary.csv
- metadata/master_text_counts_by_condition.csv
- metadata/master_text_counts_by_author_condition.csv
- metadata/master_text_dataset_manifest.csv
- logs/step_11_master_dataset_report.md
"""

from __future__ import annotations

import csv
import hashlib
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SELECTED = ROOT / "data" / "processed" / "selected_original_passages.csv"
REWRITES = ROOT / "data" / "interim" / "rewrite_responses_parsed.csv"
REWRITE_QC = ROOT / "metadata" / "rewrite_qc_report.csv"

MASTER = ROOT / "data" / "final" / "master_text_dataset.csv"
SUMMARY = ROOT / "metadata" / "master_text_dataset_summary.csv"
COUNTS_CONDITION = ROOT / "metadata" / "master_text_counts_by_condition.csv"
COUNTS_AUTHOR_CONDITION = ROOT / "metadata" / "master_text_counts_by_author_condition.csv"
MANIFEST = ROOT / "metadata" / "master_text_dataset_manifest.csv"
REPORT = ROOT / "logs" / "step_11_master_dataset_report.md"

EXPECTED_ORIGINALS = 360
EXPECTED_REWRITES = 1080
EXPECTED_MASTER_ROWS = 1440
EXPECTED_AUTHORS = 6
EXPECTED_WORKS = 12
EXPECTED_PER_CONDITION = 360
EXPECTED_PER_AUTHOR_CONDITION = 60
EXPECTED_PER_WORK_CONDITION = 30
CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
REWRITE_CONDITIONS = CONDITIONS[1:]

MASTER_FIELDS = [
    "text_id",
    "passage_id",
    "condition",
    "text_group",
    "is_generated_rewrite",
    "candidate_id",
    "canonical_id",
    "alias_id",
    "author_id",
    "author_name",
    "work_id",
    "work_title",
    "gutenberg_ebook_no",
    "selection_rank_within_work",
    "final_index_within_author",
    "candidate_index_within_source",
    "start_word_index",
    "end_word_index",
    "original_word_count",
    "text_word_count",
    "original_sentence_count",
    "text_sentence_count",
    "paragraph_count",
    "text_sha256",
    "source_text_sha256",
    "rewrite_request_id",
    "rewrite_batch_label",
    "rewrite_global_request_index",
    "rewrite_batch_request_index",
    "model_provider",
    "model_name",
    "model_version_or_snapshot",
    "temperature",
    "top_p",
    "seed_if_available",
    "prompt_template_id",
    "prompt_template_sha256",
    "qc_status",
    "qc_flags",
    "parse_status",
    "created_utc",
    "text",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def round_mean(values: list[int]) -> str:
    if not values:
        return "0"
    return f"{sum(values) / len(values):.6f}"


def original_master_row(row: dict[str, str], created_utc: str) -> dict[str, object]:
    text = row["text"]
    text_sha = sha_text(text)
    return {
        "text_id": f"{row['passage_id']}__original",
        "passage_id": row["passage_id"],
        "condition": "original",
        "text_group": "original",
        "is_generated_rewrite": "false",
        "candidate_id": row["candidate_id"],
        "canonical_id": row["canonical_id"],
        "alias_id": row["alias_id"],
        "author_id": row["author_id"],
        "author_name": row["author_name"],
        "work_id": row["work_id"],
        "work_title": row["work_title"],
        "gutenberg_ebook_no": row["gutenberg_ebook_no"],
        "selection_rank_within_work": row["selection_rank_within_work"],
        "final_index_within_author": row["final_index_within_author"],
        "candidate_index_within_source": row["candidate_index_within_source"],
        "start_word_index": row["start_word_index"],
        "end_word_index": row["end_word_index"],
        "original_word_count": row["word_count"],
        "text_word_count": row["word_count"],
        "original_sentence_count": row["sentence_count"],
        "text_sentence_count": row["sentence_count"],
        "paragraph_count": row["paragraph_count"],
        "text_sha256": text_sha,
        "source_text_sha256": text_sha,
        "rewrite_request_id": "",
        "rewrite_batch_label": "",
        "rewrite_global_request_index": "",
        "rewrite_batch_request_index": "",
        "model_provider": "",
        "model_name": "",
        "model_version_or_snapshot": "",
        "temperature": "",
        "top_p": "",
        "seed_if_available": "",
        "prompt_template_id": "",
        "prompt_template_sha256": "",
        "qc_status": "pass",
        "qc_flags": "",
        "parse_status": "not_applicable",
        "created_utc": created_utc,
        "text": text,
    }


def rewrite_master_row(
    original: dict[str, str],
    rewrite: dict[str, str],
    qc: dict[str, str],
    created_utc: str,
) -> dict[str, object]:
    text = rewrite["rewritten_text"]
    return {
        "text_id": rewrite["request_id"],
        "passage_id": original["passage_id"],
        "condition": rewrite["condition"],
        "text_group": "rewrite",
        "is_generated_rewrite": "true",
        "candidate_id": original["candidate_id"],
        "canonical_id": original["canonical_id"],
        "alias_id": original["alias_id"],
        "author_id": original["author_id"],
        "author_name": original["author_name"],
        "work_id": original["work_id"],
        "work_title": original["work_title"],
        "gutenberg_ebook_no": original["gutenberg_ebook_no"],
        "selection_rank_within_work": original["selection_rank_within_work"],
        "final_index_within_author": original["final_index_within_author"],
        "candidate_index_within_source": original["candidate_index_within_source"],
        "start_word_index": original["start_word_index"],
        "end_word_index": original["end_word_index"],
        "original_word_count": original["word_count"],
        "text_word_count": qc["rewritten_word_count"],
        "original_sentence_count": original["sentence_count"],
        "text_sentence_count": qc["rewritten_sentence_count"],
        "paragraph_count": original["paragraph_count"],
        "text_sha256": qc["rewritten_text_sha256"],
        "source_text_sha256": rewrite["source_text_sha256"],
        "rewrite_request_id": rewrite["request_id"],
        "rewrite_batch_label": rewrite["batch_label"],
        "rewrite_global_request_index": rewrite["global_request_index"],
        "rewrite_batch_request_index": rewrite["batch_request_index"],
        "model_provider": rewrite["model_provider"],
        "model_name": rewrite["model_name"],
        "model_version_or_snapshot": rewrite["model_version_or_snapshot"],
        "temperature": rewrite["temperature"],
        "top_p": rewrite["top_p"],
        "seed_if_available": rewrite["seed_if_available"],
        "prompt_template_id": rewrite["prompt_template_id"],
        "prompt_template_sha256": rewrite["prompt_template_sha256"],
        "qc_status": qc["qc_status"],
        "qc_flags": qc["qc_flags"],
        "parse_status": rewrite["parse_status"],
        "created_utc": created_utc,
        "text": text,
    }


def counts_by_condition(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    output = []
    for condition in CONDITIONS:
        subset = [row for row in rows if row["condition"] == condition]
        word_counts = [int(row["text_word_count"]) for row in subset]
        statuses = Counter(str(row["qc_status"]) for row in subset)
        output.append({
            "condition": condition,
            "row_count": len(subset),
            "unique_passages": len({row["passage_id"] for row in subset}),
            "total_word_count": sum(word_counts),
            "min_word_count": min(word_counts) if word_counts else 0,
            "max_word_count": max(word_counts) if word_counts else 0,
            "mean_word_count": round_mean(word_counts),
            "qc_pass": statuses.get("pass", 0),
            "qc_warning": statuses.get("warning", 0),
            "qc_fail": statuses.get("fail", 0),
            "empty_text_count": sum(1 for row in subset if not str(row["text"]).strip()),
        })
    return output


def counts_by_author_condition(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    author_names: dict[str, str] = {}
    for row in rows:
        author_id = str(row["author_id"])
        groups[(author_id, str(row["condition"]))].append(row)
        author_names[author_id] = str(row["author_name"])

    output = []
    for author_id in sorted(author_names):
        for condition in CONDITIONS:
            subset = groups[(author_id, condition)]
            word_counts = [int(row["text_word_count"]) for row in subset]
            statuses = Counter(str(row["qc_status"]) for row in subset)
            output.append({
                "author_id": author_id,
                "author_name": author_names[author_id],
                "condition": condition,
                "row_count": len(subset),
                "unique_works": len({row["work_id"] for row in subset}),
                "unique_passages": len({row["passage_id"] for row in subset}),
                "total_word_count": sum(word_counts),
                "min_word_count": min(word_counts) if word_counts else 0,
                "max_word_count": max(word_counts) if word_counts else 0,
                "mean_word_count": round_mean(word_counts),
                "qc_pass": statuses.get("pass", 0),
                "qc_warning": statuses.get("warning", 0),
                "qc_fail": statuses.get("fail", 0),
            })
    return output


def write_summary(rows: list[dict[str, object]], created_utc: str) -> None:
    statuses = Counter(str(row["qc_status"]) for row in rows)
    rewrite_rows = [row for row in rows if row["condition"] != "original"]
    rewrite_statuses = Counter(str(row["qc_status"]) for row in rewrite_rows)
    parse_statuses = Counter(str(row["parse_status"]) for row in rewrite_rows)
    condition_counts = Counter(str(row["condition"]) for row in rows)
    summary_rows = [
        {"metric": "master_rows", "value": len(rows)},
        {"metric": "expected_master_rows", "value": EXPECTED_MASTER_ROWS},
        {"metric": "original_rows", "value": condition_counts.get("original", 0)},
        {"metric": "rewrite_rows", "value": len(rewrite_rows)},
        {"metric": "paraphrase_rows", "value": condition_counts.get("paraphrase", 0)},
        {"metric": "modernize_rows", "value": condition_counts.get("modernize", 0)},
        {"metric": "simplify_rows", "value": condition_counts.get("simplify", 0)},
        {"metric": "authors", "value": len({row["author_id"] for row in rows})},
        {"metric": "works", "value": len({row["work_id"] for row in rows})},
        {"metric": "unique_passages", "value": len({row["passage_id"] for row in rows})},
        {"metric": "master_qc_pass", "value": statuses.get("pass", 0)},
        {"metric": "master_qc_warning", "value": statuses.get("warning", 0)},
        {"metric": "master_qc_fail", "value": statuses.get("fail", 0)},
        {"metric": "rewrite_qc_pass", "value": rewrite_statuses.get("pass", 0)},
        {"metric": "rewrite_qc_warning", "value": rewrite_statuses.get("warning", 0)},
        {"metric": "rewrite_qc_fail", "value": rewrite_statuses.get("fail", 0)},
        {"metric": "empty_text_rows", "value": sum(1 for row in rows if not str(row["text"]).strip())},
        {
            "metric": "json_parse_failed_used_raw_content",
            "value": parse_statuses.get("json_parse_failed_used_raw_content", 0),
        },
        {"metric": "master_text_dataset_csv_bytes", "value": MASTER.stat().st_size},
        {"metric": "master_text_dataset_csv_sha256", "value": sha_file(MASTER)},
        {"metric": "selected_original_passages_csv_sha256", "value": sha_file(SELECTED)},
        {"metric": "rewrite_responses_parsed_csv_sha256", "value": sha_file(REWRITES)},
        {"metric": "rewrite_qc_report_csv_sha256", "value": sha_file(REWRITE_QC)},
        {"metric": "created_utc", "value": created_utc},
    ]
    write_csv(SUMMARY, summary_rows, ["metric", "value"])


def write_manifest() -> None:
    rows = []
    for artifact, path, description in [
        ("master_text_dataset_csv", MASTER, "Final 1440-row original/rewrite text dataset."),
        ("master_text_dataset_summary_csv", SUMMARY, "Step 11 summary metrics."),
        ("master_text_counts_by_condition_csv", COUNTS_CONDITION, "Counts and QC totals by text condition."),
        (
            "master_text_counts_by_author_condition_csv",
            COUNTS_AUTHOR_CONDITION,
            "Counts and QC totals by author and text condition.",
        ),
        ("step_11_master_dataset_report_md", REPORT, "Human-readable Step 11 report."),
    ]:
        rows.append({
            "artifact": artifact,
            "path": path.relative_to(ROOT).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha_file(path),
            "description": description,
        })
    write_csv(MANIFEST, rows, ["artifact", "path", "size_bytes", "sha256", "description"])


def write_report(rows: list[dict[str, object]]) -> None:
    condition_counts = Counter(str(row["condition"]) for row in rows)
    statuses = Counter(str(row["qc_status"]) for row in rows)
    rewrite_rows = [row for row in rows if row["condition"] != "original"]
    rewrite_statuses = Counter(str(row["qc_status"]) for row in rewrite_rows)
    parse_statuses = Counter(str(row["parse_status"]) for row in rewrite_rows)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Step 11 Master Text Dataset Report\n\n"
        f"- total rows: {len(rows)}\n"
        f"- original rows: {condition_counts.get('original', 0)}\n"
        f"- paraphrase rows: {condition_counts.get('paraphrase', 0)}\n"
        f"- modernize rows: {condition_counts.get('modernize', 0)}\n"
        f"- simplify rows: {condition_counts.get('simplify', 0)}\n"
        f"- authors: {len({row['author_id'] for row in rows})}\n"
        f"- works: {len({row['work_id'] for row in rows})}\n"
        f"- unique passages: {len({row['passage_id'] for row in rows})}\n"
        f"- master QC pass: {statuses.get('pass', 0)}\n"
        f"- master QC warning: {statuses.get('warning', 0)}\n"
        f"- master QC fail: {statuses.get('fail', 0)}\n"
        f"- rewrite QC pass: {rewrite_statuses.get('pass', 0)}\n"
        f"- rewrite QC warning: {rewrite_statuses.get('warning', 0)}\n"
        f"- rewrite QC fail: {rewrite_statuses.get('fail', 0)}\n"
        f"- empty text rows: {sum(1 for row in rows if not str(row['text']).strip())}\n"
        f"- JSON parse failed but raw content used: {parse_statuses.get('json_parse_failed_used_raw_content', 0)}\n\n"
        "## Outputs\n\n"
        "- master dataset: `data/final/master_text_dataset.csv`\n"
        "- summary: `metadata/master_text_dataset_summary.csv`\n"
        "- condition counts: `metadata/master_text_counts_by_condition.csv`\n"
        "- author-condition counts: `metadata/master_text_counts_by_author_condition.csv`\n"
        "- manifest: `metadata/master_text_dataset_manifest.csv`\n",
        encoding="utf-8",
    )


def main() -> int:
    for path in [SELECTED, REWRITES, REWRITE_QC]:
        if not path.exists():
            return fail(f"missing required input: {path.relative_to(ROOT)}")

    originals = read_csv(SELECTED)
    rewrites = read_csv(REWRITES)
    qc_rows = read_csv(REWRITE_QC)

    if len(originals) != EXPECTED_ORIGINALS:
        return fail(f"expected {EXPECTED_ORIGINALS} originals, found {len(originals)}")
    if len(rewrites) != EXPECTED_REWRITES:
        return fail(f"expected {EXPECTED_REWRITES} rewrites, found {len(rewrites)}")
    if len(qc_rows) != EXPECTED_REWRITES:
        return fail(f"expected {EXPECTED_REWRITES} rewrite QC rows, found {len(qc_rows)}")

    original_by_id = {row["passage_id"]: row for row in originals}
    if len(original_by_id) != EXPECTED_ORIGINALS:
        return fail("original passage_id values are not unique")

    rewrite_by_request = {row["request_id"]: row for row in rewrites}
    if len(rewrite_by_request) != EXPECTED_REWRITES:
        return fail("rewrite request_id values are not unique")

    qc_by_request = {f"{row['passage_id']}__{row['condition']}": row for row in qc_rows}
    if len(qc_by_request) != EXPECTED_REWRITES:
        return fail("rewrite QC request keys are not unique")

    if any(row["qc_status"] == "fail" for row in qc_rows):
        return fail("rewrite QC report still contains fail rows")

    created_utc = datetime.now(timezone.utc).isoformat()
    master_rows: list[dict[str, object]] = []
    for original in originals:
        passage_id = original["passage_id"]
        source_sha = sha_text(original["text"])
        master_rows.append(original_master_row(original, created_utc))
        for condition in REWRITE_CONDITIONS:
            request_id = f"{passage_id}__{condition}"
            rewrite = rewrite_by_request.get(request_id)
            qc = qc_by_request.get(request_id)
            if rewrite is None:
                return fail(f"missing rewrite row: {request_id}")
            if qc is None:
                return fail(f"missing rewrite QC row: {request_id}")
            if rewrite["passage_id"] != passage_id or rewrite["condition"] != condition:
                return fail(f"rewrite key mismatch: {request_id}")
            if rewrite["source_text_sha256"] != source_sha:
                return fail(f"source text SHA mismatch: {request_id}")
            if qc["rewritten_text_sha256"] != sha_text(rewrite["rewritten_text"]):
                return fail(f"rewrite text SHA mismatch: {request_id}")
            master_rows.append(rewrite_master_row(original, rewrite, qc, created_utc))

    if len(master_rows) != EXPECTED_MASTER_ROWS:
        return fail(f"expected {EXPECTED_MASTER_ROWS} master rows, found {len(master_rows)}")

    MASTER.parent.mkdir(parents=True, exist_ok=True)
    write_csv(MASTER, master_rows, MASTER_FIELDS)

    condition_rows = counts_by_condition(master_rows)
    author_condition_rows = counts_by_author_condition(master_rows)
    write_csv(
        COUNTS_CONDITION,
        condition_rows,
        [
            "condition",
            "row_count",
            "unique_passages",
            "total_word_count",
            "min_word_count",
            "max_word_count",
            "mean_word_count",
            "qc_pass",
            "qc_warning",
            "qc_fail",
            "empty_text_count",
        ],
    )
    write_csv(
        COUNTS_AUTHOR_CONDITION,
        author_condition_rows,
        [
            "author_id",
            "author_name",
            "condition",
            "row_count",
            "unique_works",
            "unique_passages",
            "total_word_count",
            "min_word_count",
            "max_word_count",
            "mean_word_count",
            "qc_pass",
            "qc_warning",
            "qc_fail",
        ],
    )
    write_summary(master_rows, created_utc)
    write_report(master_rows)
    write_manifest()

    print(f"Built master text dataset with {len(master_rows)} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
