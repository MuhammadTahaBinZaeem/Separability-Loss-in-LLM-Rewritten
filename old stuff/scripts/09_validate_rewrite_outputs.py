"""
Step 9/10 helper: validate parsed rewrite outputs.

Run after Step 10 has produced parsed rewrite responses:

    python scripts/09_validate_rewrite_outputs.py

Input:
- data/processed/selected_original_passages.csv
- data/interim/rewrite_responses_parsed.csv
- metadata/rewrite_generation_config.json

Outputs:
- metadata/rewrite_qc_report.csv
- logs/rewrite_qc_summary.md

This script validates structure and basic quality-control constraints. It does
not judge literary quality.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELECTED = ROOT / "data" / "processed" / "selected_original_passages.csv"
PARSED = ROOT / "data" / "interim" / "rewrite_responses_parsed.csv"
QC_OUT = ROOT / "metadata" / "rewrite_qc_report.csv"
SUMMARY = ROOT / "logs" / "rewrite_qc_summary.md"

WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)
SENT_RE = re.compile(r"[^.!?]+[.!?]+(?:[\"”’]+)?|[^.!?]+$", re.UNICODE)
FORBIDDEN_RE = re.compile(
    r"Project\s+Gutenberg|\bdataset\b|\bauthor\s*:|\btitle\s*:|\bas\s+an\s+ai\b|\blanguage\s+model\b",
    re.I,
)
MARKDOWN_RE = re.compile(r"^\s*(#|[-*]\s+|\d+\.\s+)", re.M)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def sentence_count(text: str) -> int:
    return len([m for m in SENT_RE.finditer(text) if word_count(m.group(0)) > 0])


def main() -> int:
    if not SELECTED.exists():
        print(f"Missing selected originals: {SELECTED}", file=sys.stderr)
        return 1
    if not PARSED.exists():
        print(f"Missing parsed rewrite responses: {PARSED}", file=sys.stderr)
        return 1

    originals = {row["passage_id"]: row for row in read_csv(SELECTED)}
    rows = read_csv(PARSED)
    qc_rows = []
    status_counts = {"pass": 0, "warning": 0, "fail": 0}

    for row in rows:
        flags: list[str] = []
        passage_id = row.get("passage_id", "")
        condition = row.get("condition", "")
        rewritten = row.get("rewritten_text", "")
        if passage_id not in originals:
            flags.append("unknown_passage_id")
            original_wc = 0
        else:
            original_wc = int(originals[passage_id]["word_count"])
        if condition not in {"paraphrase", "modernize", "simplify"}:
            flags.append("invalid_condition")
        if not rewritten.strip():
            flags.append("empty_rewritten_text")
        if FORBIDDEN_RE.search(rewritten):
            flags.append("prompt_or_source_leakage")
        if MARKDOWN_RE.search(rewritten):
            flags.append("markdown_or_list_format")

        rewritten_wc = word_count(rewritten)
        rewritten_sentences = sentence_count(rewritten)
        ratio = round(rewritten_wc / original_wc, 6) if original_wc else 0.0
        if original_wc and (ratio < 0.80 or ratio > 1.20):
            flags.append("length_hard_warning")
        elif original_wc and (ratio < 0.85 or ratio > 1.15):
            flags.append("length_soft_warning")
        if rewritten_sentences < 3:
            flags.append("low_sentence_count")

        fail_flags = {"unknown_passage_id", "invalid_condition", "empty_rewritten_text", "prompt_or_source_leakage", "markdown_or_list_format"}
        if any(flag in fail_flags for flag in flags):
            status = "fail"
        elif flags:
            status = "warning"
        else:
            status = "pass"
        status_counts[status] += 1

        qc_rows.append({
            "passage_id": passage_id,
            "condition": condition,
            "original_word_count": original_wc,
            "rewritten_word_count": rewritten_wc,
            "length_ratio": ratio,
            "rewritten_sentence_count": rewritten_sentences,
            "rewritten_text_sha256": sha_text(rewritten),
            "qc_status": status,
            "qc_flags": ";".join(flags),
        })

    QC_OUT.parent.mkdir(parents=True, exist_ok=True)
    with QC_OUT.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "passage_id", "condition", "original_word_count", "rewritten_word_count", "length_ratio",
            "rewritten_sentence_count", "rewritten_text_sha256", "qc_status", "qc_flags",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(qc_rows)

    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(
        "# Rewrite QC Summary\n\n"
        f"- rows checked: {len(qc_rows)}\n"
        f"- pass: {status_counts['pass']}\n"
        f"- warning: {status_counts['warning']}\n"
        f"- fail: {status_counts['fail']}\n",
        encoding="utf-8",
    )
    print(f"Checked {len(qc_rows)} rewrite rows: {status_counts}")
    return 1 if status_counts["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
