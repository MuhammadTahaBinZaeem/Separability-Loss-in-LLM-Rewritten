"""
Checker for completed E1 Groq free-model generation.

This script validates the committed 360-scope Groq generation outputs for:
- Llama 3.3 70B on Groq
- Qwen 32B on Groq
- GPT-OSS 120B on Groq

It does not call Groq, does not use secrets, and does not modify raw outputs.

Important resume note:
raw_responses.jsonl may contain historical duplicate successful rows from
interrupted/resumed runs. That is not automatically fatal. The checker validates
against the unique successful raw IDs that belong to the current requests_used
scope, and reports duplicate/out-of-scope raw rows separately.

Run from repository root:

    python scripts/37_check_e1_groq_free_generation.py
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "interim" / "e1_free_model_replication" / "groq_generation"
MASTER = ROOT / "data" / "final" / "master_text_dataset.csv"
META = ROOT / "metadata"
LOGS = ROOT / "logs"

SUMMARY_CSV = META / "e1_groq_free_generation_completion_summary.csv"
FLAG_COUNTS_CSV = META / "e1_groq_free_generation_qc_flag_counts.csv"
CONDITION_COUNTS_CSV = META / "e1_groq_free_generation_condition_counts.csv"
AUTHOR_COUNTS_CSV = META / "e1_groq_free_generation_author_counts.csv"
CONTAMINATION_CSV = META / "e1_groq_free_generation_contamination_scan.csv"
REPORT = LOGS / "e1_groq_free_generation_completion_report.md"

EXPECTED_REQUESTS = 360
CONDITIONS = {"paraphrase", "modernize", "simplify"}
QC_STATUSES = {"pass", "warning", "fail"}

MODELS = {
    "groq_llama_3_3_70b_free": {
        "label": "Groq Llama 3.3 70B",
        "folder": BASE / "groq_llama_3_3_70b_free",
        "report": LOGS / "e1_groq_llama_generation_report.md",
    },
    "groq_qwen_32b_free": {
        "label": "Groq Qwen 32B",
        "folder": BASE / "groq_qwen_32b_free",
        "report": LOGS / "e1_groq_qwen_generation_report.md",
    },
    "groq_gpt_oss_120b_free": {
        "label": "Groq GPT-OSS 120B",
        "folder": BASE / "groq_gpt_oss_120b_free",
        "report": LOGS / "e1_groq_gptoss_generation_report.md",
    },
}

CONTAMINATION_PATTERNS = {
    "think_open": re.compile(r"<think>", re.IGNORECASE),
    "think_close": re.compile(r"</think>", re.IGNORECASE),
    "as_an_ai": re.compile(r"\bas an ai\b", re.IGNORECASE),
    "i_cannot": re.compile(r"\bi cannot\b", re.IGNORECASE),
    "here_is": re.compile(r"\bhere is\b", re.IGNORECASE),
    "below_is": re.compile(r"\bbelow is\b", re.IGNORECASE),
    "the_rewritten": re.compile(r"\bthe rewritten\b", re.IGNORECASE),
    "json_literal": re.compile(r"\bjson\b", re.IGNORECASE),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                rows.append({"_json_error": str(exc), "_line_number": line_number})
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def author_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in read_csv(MASTER):
        if row.get("condition") == "original":
            lookup[row["passage_id"]] = row.get("author_id", "unknown")
    return lookup


def split_flags(value: str) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(";") if x.strip()]


def detect_contamination(text: str) -> list[str]:
    hits = []
    for name, pattern in CONTAMINATION_PATTERNS.items():
        if pattern.search(text or ""):
            hits.append(name)
    return hits


def main() -> int:
    report_lines = [
        "# E1 Groq Free-Model Generation Completion Report",
        "",
        "This report validates the committed 360-scope Groq free-model generation outputs.",
        "",
        "Historical duplicate successful raw rows from resumed runs are reported as diagnostics, not treated as fatal, as long as the de-duplicated scoped successful raw IDs match `requests_used.jsonl` and `parsed_outputs.csv`.",
        "",
    ]
    errors: list[str] = []
    author_by_passage = author_lookup()

    summary_rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    condition_rows: list[dict[str, Any]] = []
    author_rows: list[dict[str, Any]] = []
    contamination_rows: list[dict[str, Any]] = []

    for model_id, info in MODELS.items():
        model_errors: list[str] = []
        folder: Path = info["folder"]
        requests_path = folder / "requests_used.jsonl"
        raw_path = folder / "raw_responses.jsonl"
        parsed_path = folder / "parsed_outputs.csv"
        report_path = info["report"]

        for required in [folder, requests_path, raw_path, parsed_path, report_path]:
            if not required.exists():
                model_errors.append(f"{model_id}: missing {required.relative_to(ROOT)}")

        if model_errors:
            errors.extend(model_errors)
            summary_rows.append({
                "model_id": model_id,
                "label": info["label"],
                "requests": 0,
                "raw_ok_rows_total": 0,
                "unique_successful_scoped_raw_rows": 0,
                "duplicate_successful_scoped_raw_rows": 0,
                "successful_raw_rows_outside_scope": 0,
                "parsed_rows": 0,
                "remaining": EXPECTED_REQUESTS,
                "qc_pass_rows": 0,
                "qc_warning_rows": 0,
                "qc_fail_rows": 0,
                "contaminated_rows_flagged_by_scan": 0,
                "status": "FAIL",
            })
            continue

        requests = read_jsonl(requests_path)
        raw_rows = read_jsonl(raw_path)
        parsed_rows = read_csv(parsed_path)

        request_ids = [row.get("request_id", "") for row in requests]
        request_id_set = set(request_ids)
        parsed_ids = [row.get("request_id", "") for row in parsed_rows]
        parsed_id_set = set(parsed_ids)

        successful_raw_ids_all = [row.get("request_id", "") for row in raw_rows if row.get("status") == "ok"]
        successful_scoped_raw_ids = [rid for rid in successful_raw_ids_all if rid in request_id_set]
        successful_scoped_raw_id_set = set(successful_scoped_raw_ids)
        raw_ok_outside_scope = [rid for rid in successful_raw_ids_all if rid not in request_id_set]
        duplicate_successful_scoped_count = len(successful_scoped_raw_ids) - len(successful_scoped_raw_id_set)

        if len(requests) != EXPECTED_REQUESTS:
            model_errors.append(f"{model_id}: expected {EXPECTED_REQUESTS} requests, found {len(requests)}")
        if len(parsed_rows) != EXPECTED_REQUESTS:
            model_errors.append(f"{model_id}: expected {EXPECTED_REQUESTS} parsed rows, found {len(parsed_rows)}")
        if len(request_ids) != len(request_id_set):
            model_errors.append(f"{model_id}: duplicate request_id in requests_used.jsonl")
        if len(parsed_ids) != len(parsed_id_set):
            model_errors.append(f"{model_id}: duplicate request_id in parsed_outputs.csv")
        if parsed_id_set != successful_scoped_raw_id_set:
            missing_in_parsed = sorted(successful_scoped_raw_id_set - parsed_id_set)[:5]
            missing_in_raw = sorted(parsed_id_set - successful_scoped_raw_id_set)[:5]
            model_errors.append(
                f"{model_id}: parsed IDs do not match unique scoped successful raw IDs; "
                f"missing_in_parsed_sample={missing_in_parsed}; missing_in_raw_sample={missing_in_raw}"
            )
        if request_id_set != parsed_id_set:
            missing_parsed = sorted(request_id_set - parsed_id_set)[:5]
            extra_parsed = sorted(parsed_id_set - request_id_set)[:5]
            model_errors.append(
                f"{model_id}: parsed request IDs do not match scoped requests; "
                f"missing_parsed_sample={missing_parsed}; extra_parsed_sample={extra_parsed}"
            )

        qc_counts = Counter(row.get("qc_status", "") for row in parsed_rows)
        condition_counts = Counter(row.get("condition", "") for row in parsed_rows)
        flag_counts: Counter[str] = Counter()
        author_counts: Counter[str] = Counter()
        contamination_counts: Counter[str] = Counter()
        contaminated_rows = 0
        contaminated_examples: list[str] = []

        for row in parsed_rows:
            request_id = row.get("request_id", "")
            passage_id = row.get("passage_id", "")
            condition = row.get("condition", "")
            qc_status = row.get("qc_status", "")
            rewritten = row.get("rewritten_text", "")

            if not rewritten.strip():
                model_errors.append(f"{model_id}: empty rewritten_text for {request_id}")
            if condition not in CONDITIONS:
                model_errors.append(f"{model_id}: invalid condition {condition!r} for {request_id}")
            if qc_status not in QC_STATUSES:
                model_errors.append(f"{model_id}: invalid qc_status {qc_status!r} for {request_id}")

            for flag in split_flags(row.get("qc_flags", "")):
                flag_counts[flag] += 1
            author_counts[author_by_passage.get(passage_id, "unknown")] += 1
            hits = detect_contamination(rewritten)
            if hits:
                contaminated_rows += 1
            for hit in hits:
                contamination_counts[hit] += 1
            if hits and len(contaminated_examples) < 10:
                contaminated_examples.append(f"{request_id}: {','.join(hits)}")

        if qc_counts.get("fail", 0) != 0:
            model_errors.append(f"{model_id}: qc_fail rows found: {qc_counts.get('fail', 0)}")

        summary_rows.append({
            "model_id": model_id,
            "label": info["label"],
            "requests": len(requests),
            "raw_ok_rows_total": len(successful_raw_ids_all),
            "unique_successful_scoped_raw_rows": len(successful_scoped_raw_id_set),
            "duplicate_successful_scoped_raw_rows": duplicate_successful_scoped_count,
            "successful_raw_rows_outside_scope": len(raw_ok_outside_scope),
            "parsed_rows": len(parsed_rows),
            "remaining": EXPECTED_REQUESTS - len(parsed_rows),
            "qc_pass_rows": qc_counts.get("pass", 0),
            "qc_warning_rows": qc_counts.get("warning", 0),
            "qc_fail_rows": qc_counts.get("fail", 0),
            "contaminated_rows_flagged_by_scan": contaminated_rows,
            "status": "PASS" if not model_errors else "FAIL",
        })

        for condition in sorted(CONDITIONS):
            condition_rows.append({"model_id": model_id, "condition": condition, "rows": condition_counts.get(condition, 0)})
        for flag, count in sorted(flag_counts.items()):
            flag_rows.append({"model_id": model_id, "qc_flag": flag, "rows": count})
        for author, count in sorted(author_counts.items()):
            author_rows.append({"model_id": model_id, "author_id": author, "rows": count})
        for pattern_name in sorted(CONTAMINATION_PATTERNS):
            contamination_rows.append({"model_id": model_id, "pattern": pattern_name, "rows": contamination_counts.get(pattern_name, 0)})

        report_lines.extend([
            f"## {info['label']}",
            "",
            f"- requests: {len(requests)}",
            f"- raw OK rows total: {len(successful_raw_ids_all)}",
            f"- unique successful scoped raw rows: {len(successful_scoped_raw_id_set)}",
            f"- duplicate successful scoped raw rows: {duplicate_successful_scoped_count}",
            f"- successful raw rows outside current scope: {len(raw_ok_outside_scope)}",
            f"- parsed rows: {len(parsed_rows)}",
            f"- QC pass/warning/fail: {qc_counts.get('pass', 0)} / {qc_counts.get('warning', 0)} / {qc_counts.get('fail', 0)}",
            f"- condition counts: {dict(sorted(condition_counts.items()))}",
            f"- author counts: {dict(sorted(author_counts.items()))}",
            f"- contamination scan counts: {dict(sorted(contamination_counts.items()))}",
            "",
        ])
        if duplicate_successful_scoped_count or raw_ok_outside_scope:
            report_lines.extend([
                "Resume diagnostics:",
                f"- duplicate successful raw rows are historical resume artifacts: {duplicate_successful_scoped_count}",
                f"- successful raw rows outside current 360-scope are ignored for validation: {len(raw_ok_outside_scope)}",
                "",
            ])
        if contaminated_examples:
            report_lines.append("Contamination examples needing manual review:")
            report_lines.extend(f"- {item}" for item in contaminated_examples)
            report_lines.append("")

        errors.extend(model_errors)

    write_csv(SUMMARY_CSV, summary_rows, [
        "model_id", "label", "requests", "raw_ok_rows_total", "unique_successful_scoped_raw_rows",
        "duplicate_successful_scoped_raw_rows", "successful_raw_rows_outside_scope", "parsed_rows", "remaining",
        "qc_pass_rows", "qc_warning_rows", "qc_fail_rows", "contaminated_rows_flagged_by_scan", "status",
    ])
    write_csv(FLAG_COUNTS_CSV, flag_rows, ["model_id", "qc_flag", "rows"])
    write_csv(CONDITION_COUNTS_CSV, condition_rows, ["model_id", "condition", "rows"])
    write_csv(AUTHOR_COUNTS_CSV, author_rows, ["model_id", "author_id", "rows"])
    write_csv(CONTAMINATION_CSV, contamination_rows, ["model_id", "pattern", "rows"])

    if errors:
        report_lines.append("## Errors")
        report_lines.append("")
        report_lines.extend(f"- {error}" for error in errors)
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("\n".join(report_lines), encoding="utf-8")
        print("FAIL: E1 Groq completion validation found errors.")
        for error in errors[:20]:
            print(f"- {error}")
        return 1

    report_lines.extend([
        "## Final verdict",
        "",
        "PASS: all three 360-scope Groq free-model generation outputs are structurally complete and safe for downstream E1 feature extraction/modeling, subject to manual review of warning-heavy rows.",
        "",
        f"Machine-readable summaries written to `{SUMMARY_CSV.relative_to(ROOT)}` and related `metadata/e1_groq_free_generation_*` files.",
    ])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print("PASS: E1 Groq free-model generation completion checker passed.")
    print(f"Report: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
