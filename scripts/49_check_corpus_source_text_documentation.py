"""Validate corpus source-text and copyright documentation.

Checks that the source-text register matches the locked selected-work metadata and
that the manuscript-facing source-text documentation includes the required reuse
and non-US copyright cautions.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "metadata/source_text_copyright_register.csv"
SELECTED = ROOT / "metadata/selected_counts_by_work.csv"
ALIAS = ROOT / "metadata/gutenberg_alias_map.csv"
MASTER_SUMMARY = ROOT / "metadata/master_text_dataset_summary.csv"
DOC = ROOT / "docs/corpus_source_text_documentation.md"
OUT = ROOT / "metadata/corpus_source_text_documentation_check_summary.csv"
REPORT = ROOT / "logs/corpus_source_text_documentation_check_report.md"

REQUIRED_DOC_PHRASES = [
    "Project Gutenberg",
    "source-text register",
    "non-US copyright status is jurisdiction-dependent",
    "verify local copyright law",
    "no claim that all texts are globally public domain",
    "1440-row master dataset",
    "360 original passages",
    "thirty passages",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def clean_row(row: dict[str, str]) -> dict[str, str]:
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def main() -> int:
    errors: list[str] = []
    for p in [REGISTER, SELECTED, ALIAS, MASTER_SUMMARY, DOC]:
        if not p.exists(): errors.append(f"missing {p.relative_to(ROOT)}")
        elif p.stat().st_size == 0: errors.append(f"empty {p.relative_to(ROOT)}")
    if errors:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("# Corpus Source-Text Documentation Check Report\n\nFAIL\n\n" + "\n".join(f"- {e}" for e in errors) + "\n", encoding="utf-8")
        print("FAIL: required source-text files missing")
        return 1

    register = [clean_row(r) for r in read_csv(REGISTER)]
    selected = [clean_row(r) for r in read_csv(SELECTED)]
    alias = [clean_row(r) for r in read_csv(ALIAS)]
    master = {r["metric"]: r["value"] for r in read_csv(MASTER_SUMMARY)}
    doc = DOC.read_text(encoding="utf-8")

    if len(register) != 12: errors.append(f"expected 12 register rows, found {len(register)}")
    if len(selected) != 12: errors.append(f"expected 12 selected-count rows, found {len(selected)}")
    if len(alias) != 12: errors.append(f"expected 12 alias-map rows, found {len(alias)}")

    reg_by_work = {r["work_id"]: r for r in register}
    alias_by_work = {r["work_id"]: r for r in alias}
    for s in selected:
        work_id = s["work_id"]
        if work_id not in reg_by_work:
            errors.append(f"selected work missing from register: {work_id}")
            continue
        r = reg_by_work[work_id]
        if r["author_id"] != s["author_id"]: errors.append(f"author mismatch for {work_id}")
        if r["work_title"] != s["work_title"]: errors.append(f"title mismatch for {work_id}")
        if r["selected_passages"] != s["selected_passages"]: errors.append(f"selected passage mismatch for {work_id}: {r['selected_passages']} vs {s['selected_passages']}")
        if r["selected_passages"] != "30": errors.append(f"expected 30 selected passages for {work_id}, found {r['selected_passages']}")
        if work_id not in alias_by_work:
            errors.append(f"work missing from alias map: {work_id}")
        else:
            a = alias_by_work[work_id]
            for col in ["gutenberg_ebook_no", "gutenberg_url", "plain_text_url"]:
                if r[col] != a[col]: errors.append(f"{col} mismatch for {work_id}")
        if not r["gutenberg_url"].startswith("https://www.gutenberg.org/ebooks/"):
            errors.append(f"bad gutenberg_url for {work_id}")
        if not r["plain_text_url"].startswith("https://www.gutenberg.org/cache/epub/"):
            errors.append(f"bad plain_text_url for {work_id}")
        if "non-US" not in r["non_us_caution"]:
            errors.append(f"missing non-US caution for {work_id}")
        if r["manuscript_status"] != "ready":
            errors.append(f"register status not ready for {work_id}")

    expected_master = {"master_rows": "1440", "authors": "6", "works": "12", "unique_passages": "360"}
    for k, v in expected_master.items():
        if master.get(k) != v:
            errors.append(f"master summary {k} expected {v}, found {master.get(k)}")

    missing_phrases = [p for p in REQUIRED_DOC_PHRASES if p not in doc]
    for p in missing_phrases:
        errors.append(f"documentation missing phrase: {p}")

    authors = sorted(set(r["author_id"] for r in register))
    total_selected = sum(int(r["selected_passages"]) for r in register)
    out = [{
        "register_rows": len(register),
        "selected_rows": len(selected),
        "alias_rows": len(alias),
        "authors": len(authors),
        "works": len(register),
        "total_selected_passages": total_selected,
        "master_rows": master.get("master_rows", ""),
        "unique_passages": master.get("unique_passages", ""),
        "missing_required_doc_phrases": len(missing_phrases),
        "status": "PASS" if not errors else "FAIL",
    }]
    write_csv(OUT, out, list(out[0].keys()))

    lines = [
        "# Corpus Source-Text Documentation Check Report",
        "",
        f"- register rows: {len(register)}",
        f"- selected-work rows: {len(selected)}",
        f"- alias-map rows: {len(alias)}",
        f"- authors: {len(authors)}",
        f"- works: {len(register)}",
        f"- total selected passages: {total_selected}",
        f"- master rows: {master.get('master_rows', '')}",
        f"- unique passages: {master.get('unique_passages', '')}",
        f"- missing required doc phrases: {len(missing_phrases)}",
        "",
    ]
    if errors:
        lines += ["## Errors", ""] + [f"- {e}" for e in errors]
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("FAIL: corpus source-text documentation checker found errors")
        for e in errors[:20]: print("- " + e)
        return 1

    lines += [
        "## Final verdict",
        "",
        "PASS: corpus source-text documentation is synchronized with selected-work metadata and includes the required Project Gutenberg reuse and non-US copyright cautions.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS: corpus source-text documentation checker passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
