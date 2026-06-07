"""Validate E4 semantic-fidelity annotation outputs.

This checker validates the single-review semantic-fidelity annotation flags and
summary. It intentionally verifies that the audit is described as a single filled
review, not as two independent annotators.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ROOT / "data/audit/semantic_fidelity_annotation_flags.csv"
SUMMARY = ROOT / "metadata/semantic_fidelity_annotation_summary.csv"
REPORT = ROOT / "logs/semantic_fidelity_annotation_report.md"
CHECK_REPORT = ROOT / "logs/semantic_fidelity_annotation_check_report.md"
CHECK_SUMMARY = ROOT / "metadata/semantic_fidelity_annotation_check_summary.csv"

CONDITIONS = {"paraphrase", "modernize", "simplify"}
ISSUE_LEVELS = {"low", "medium", "high"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def as_int(row: dict[str, str], col: str) -> int:
    return int(row[col])


def main() -> int:
    errors: list[str] = []
    for path in [FLAGS, SUMMARY, REPORT]:
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT)}")
        elif path.stat().st_size == 0:
            errors.append(f"empty {path.relative_to(ROOT)}")
    if errors:
        CHECK_REPORT.parent.mkdir(parents=True, exist_ok=True)
        CHECK_REPORT.write_text("# Semantic Fidelity Annotation Check Report\n\nFAIL\n\n" + "\n".join(f"- {e}" for e in errors) + "\n", encoding="utf-8")
        print("FAIL: missing required files")
        return 1

    rows = read_csv(FLAGS)
    summary = read_csv(SUMMARY)
    report_text = REPORT.read_text(encoding="utf-8")

    if len(rows) != 108:
        errors.append(f"expected 108 annotation flag rows, found {len(rows)}")
    if len({r["audit_id"] for r in rows}) != 108:
        errors.append("audit_id values are not unique")
    if Counter(r["condition"] for r in rows) != Counter({"paraphrase": 36, "modernize": 36, "simplify": 36}):
        errors.append(f"condition counts wrong: {dict(Counter(r['condition'] for r in rows))}")

    for r in rows:
        audit_id = r.get("audit_id", "")
        if r.get("condition") not in CONDITIONS:
            errors.append(f"{audit_id}: invalid condition {r.get('condition')}")
        for col in ["added_facts_0_1", "omitted_facts_0_1", "narrative_order_change_0_1", "speaker_or_character_relation_change_0_1", "any_semantic_issue_flag"]:
            if r.get(col) not in {"0", "1"}:
                errors.append(f"{audit_id}: invalid {col}={r.get(col)}")
        if r.get("tone_drift_0_2") not in {"0", "1", "2"}:
            errors.append(f"{audit_id}: invalid tone_drift_0_2={r.get('tone_drift_0_2')}")
        if r.get("meaning_preservation_1_5") not in {"1", "2", "3", "4", "5"}:
            errors.append(f"{audit_id}: invalid meaning_preservation_1_5={r.get('meaning_preservation_1_5')}")
        if r.get("overall_usable_yes_no") not in {"yes", "no"}:
            errors.append(f"{audit_id}: invalid overall_usable_yes_no={r.get('overall_usable_yes_no')}")
        if r.get("semantic_issue_level") not in ISSUE_LEVELS:
            errors.append(f"{audit_id}: invalid semantic_issue_level={r.get('semantic_issue_level')}")

    added = sum(as_int(r, "added_facts_0_1") for r in rows)
    omitted = sum(as_int(r, "omitted_facts_0_1") for r in rows)
    order = sum(as_int(r, "narrative_order_change_0_1") for r in rows)
    speaker = sum(as_int(r, "speaker_or_character_relation_change_0_1") for r in rows)
    tone_mean = sum(as_int(r, "tone_drift_0_2") for r in rows) / len(rows)
    meaning_mean = sum(as_int(r, "meaning_preservation_1_5") for r in rows) / len(rows)
    usable_yes = sum(1 for r in rows if r["overall_usable_yes_no"] == "yes")
    issue_flags = sum(as_int(r, "any_semantic_issue_flag") for r in rows)
    high = sum(1 for r in rows if r["semantic_issue_level"] == "high")

    expected = {
        "added": 6,
        "omitted": 5,
        "order": 0,
        "speaker": 0,
        "usable_yes": 107,
        "issue_flags": 17,
        "high": 1,
    }
    if added != expected["added"]: errors.append(f"added count expected 6, found {added}")
    if omitted != expected["omitted"]: errors.append(f"omitted count expected 5, found {omitted}")
    if order != expected["order"]: errors.append(f"order count expected 0, found {order}")
    if speaker != expected["speaker"]: errors.append(f"speaker count expected 0, found {speaker}")
    if usable_yes != expected["usable_yes"]: errors.append(f"usable yes expected 107, found {usable_yes}")
    if issue_flags != expected["issue_flags"]: errors.append(f"issue flags expected 17, found {issue_flags}")
    if high != expected["high"]: errors.append(f"high issue rows expected 1, found {high}")
    if round(meaning_mean, 6) != 4.527778:
        errors.append(f"meaning mean expected 4.527778, found {meaning_mean:.6f}")
    if round(tone_mean, 6) != 0.981481:
        errors.append(f"tone mean expected 0.981481, found {tone_mean:.6f}")

    if "single-review audit" not in report_text and "single filled semantic-fidelity review" not in report_text:
        errors.append("report does not clearly state single-review audit status")
    if "Do not claim two independent human annotators" not in report_text:
        errors.append("report does not warn against claiming two independent annotators")

    check_rows = [{
        "rows": len(rows),
        "added_facts_count": added,
        "omitted_facts_count": omitted,
        "narrative_order_change_count": order,
        "speaker_relation_change_count": speaker,
        "tone_drift_mean": round(tone_mean, 6),
        "meaning_preservation_mean": round(meaning_mean, 6),
        "usable_yes_count": usable_yes,
        "usable_no_count": len(rows) - usable_yes,
        "any_semantic_issue_count": issue_flags,
        "high_issue_level_count": high,
        "status": "PASS" if not errors else "FAIL",
    }]
    write_csv(CHECK_SUMMARY, check_rows, list(check_rows[0].keys()))

    lines = [
        "# Semantic Fidelity Annotation Check Report",
        "",
        f"- rows: {len(rows)}",
        f"- added facts: {added}",
        f"- omitted facts: {omitted}",
        f"- narrative-order changes: {order}",
        f"- speaker/character-relation changes: {speaker}",
        f"- tone drift mean: {tone_mean:.6f}",
        f"- meaning preservation mean: {meaning_mean:.6f}",
        f"- usable rows: {usable_yes}/{len(rows)}",
        f"- semantic issue flags: {issue_flags}",
        f"- high issue rows: {high}",
        "",
    ]
    if errors:
        lines += ["## Errors", ""] + [f"- {e}" for e in errors]
        CHECK_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("FAIL: semantic fidelity annotation checker found errors")
        for e in errors[:20]: print("- " + e)
        return 1
    lines += [
        "## Final verdict",
        "",
        "PASS: semantic-fidelity annotation outputs are complete and internally consistent. Treat as a single-review audit, not independent double annotation.",
    ]
    CHECK_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS: semantic fidelity annotation checker passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
