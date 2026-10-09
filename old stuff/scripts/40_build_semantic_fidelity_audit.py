"""Build E4 semantic fidelity audit package.

Creates a deterministic 10% audit sample from the frozen core rewrite dataset:
6 authors × 2 works × 3 rewrite conditions × 3 passages = 108 rewrites.

Outputs:
- data/audit/semantic_fidelity_sample.csv
- data/audit/semantic_fidelity_annotation_sheet.csv
- data/audit/semantic_fidelity_key.csv
- metadata/semantic_fidelity_audit_manifest.csv
- logs/semantic_fidelity_audit_build_report.md
"""
from __future__ import annotations

import csv, hashlib
from collections import defaultdict, Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data/final/master_text_dataset.csv"
AUDIT = ROOT / "data/audit"
META = ROOT / "metadata"
LOGS = ROOT / "logs"
SAMPLE = AUDIT / "semantic_fidelity_sample.csv"
SHEET = AUDIT / "semantic_fidelity_annotation_sheet.csv"
KEY = AUDIT / "semantic_fidelity_key.csv"
MANIFEST = META / "semantic_fidelity_audit_manifest.csv"
REPORT = LOGS / "semantic_fidelity_audit_build_report.md"
SEED = "semantic-fidelity-audit-v1"
CONDITIONS = ["paraphrase", "modernize", "simplify"]
ANNOTATORS = ["A1", "A2"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def score(row: dict[str, str]) -> str:
    key = "|".join([SEED, row["author_id"], row["work_id"], row["condition"], row["passage_id"]])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def main() -> int:
    rows = read_csv(MASTER)
    originals = {r["passage_id"]: r for r in rows if r["condition"] == "original"}
    rewrites = [r for r in rows if r["condition"] in CONDITIONS]
    if len(originals) != 360 or len(rewrites) != 1080:
        raise RuntimeError(f"Unexpected master counts: originals={len(originals)}, rewrites={len(rewrites)}")

    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for r in rewrites:
        if r.get("qc_status") == "fail":
            continue
        groups[(r["author_id"], r["work_id"], r["condition"])].append(r)

    selected: list[dict[str, str]] = []
    for key in sorted(groups):
        candidates = sorted(groups[key], key=score)
        if len(candidates) < 3:
            raise RuntimeError(f"Group {key} has only {len(candidates)} candidates")
        selected.extend(candidates[:3])
    selected = sorted(selected, key=lambda r: score(r))
    if len(selected) != 108:
        raise RuntimeError(f"Expected 108 selected rows, got {len(selected)}")

    sample_rows=[]; key_rows=[]; sheet_rows=[]
    for i, r in enumerate(selected, start=1):
        audit_id = f"E4_{i:03d}"
        orig = originals[r["passage_id"]]
        sample_rows.append({
            "audit_id": audit_id,
            "condition": r["condition"],
            "original_text": orig["text"],
            "rewritten_text": r["text"],
        })
        key_rows.append({
            "audit_id": audit_id,
            "text_id": r["text_id"],
            "passage_id": r["passage_id"],
            "condition": r["condition"],
            "author_id": r["author_id"],
            "author_name": r["author_name"],
            "work_id": r["work_id"],
            "work_title": r["work_title"],
            "qc_status": r["qc_status"],
            "qc_flags": r["qc_flags"],
            "original_text_sha256": orig["text_sha256"],
            "rewritten_text_sha256": r["text_sha256"],
        })
        for annotator in ANNOTATORS:
            sheet_rows.append({
                "audit_id": audit_id,
                "annotator_id": annotator,
                "condition": r["condition"],
                "original_text": orig["text"],
                "rewritten_text": r["text"],
                "added_facts_0_1": "",
                "omitted_facts_0_1": "",
                "narrative_order_change_0_1": "",
                "speaker_or_character_relation_change_0_1": "",
                "tone_drift_0_2": "",
                "meaning_preservation_1_5": "",
                "overall_usable_yes_no": "",
                "notes": "",
            })

    write_csv(SAMPLE, sample_rows, ["audit_id","condition","original_text","rewritten_text"])
    write_csv(KEY, key_rows, ["audit_id","text_id","passage_id","condition","author_id","author_name","work_id","work_title","qc_status","qc_flags","original_text_sha256","rewritten_text_sha256"])
    write_csv(SHEET, sheet_rows, ["audit_id","annotator_id","condition","original_text","rewritten_text","added_facts_0_1","omitted_facts_0_1","narrative_order_change_0_1","speaker_or_character_relation_change_0_1","tone_drift_0_2","meaning_preservation_1_5","overall_usable_yes_no","notes"])

    artifacts = [SAMPLE, SHEET, KEY]
    write_csv(MANIFEST, [{"artifact": p.stem, "path": p.relative_to(ROOT).as_posix(), "rows": len(read_csv(p)), "size_bytes": p.stat().st_size, "sha256": sha_file(p)} for p in artifacts], ["artifact","path","rows","size_bytes","sha256"])

    cond_counts = Counter(r["condition"] for r in key_rows)
    author_counts = Counter(r["author_id"] for r in key_rows)
    work_condition_counts = Counter((r["work_id"], r["condition"]) for r in key_rows)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# E4 Semantic Fidelity Audit Build Report\n\n"
        f"- selected rewrite rows: {len(sample_rows)}\n"
        f"- annotation rows: {len(sheet_rows)}\n"
        f"- condition counts: {dict(sorted(cond_counts.items()))}\n"
        f"- author counts: {dict(sorted(author_counts.items()))}\n"
        f"- work-condition groups: {len(work_condition_counts)} groups, each expected 3 rows\n"
        f"- sample: `{SAMPLE.relative_to(ROOT)}`\n"
        f"- annotation sheet: `{SHEET.relative_to(ROOT)}`\n"
        f"- key: `{KEY.relative_to(ROOT)}`\n",
        encoding="utf-8",
    )
    print(f"Built semantic fidelity audit package: sample={len(sample_rows)}, annotation_rows={len(sheet_rows)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
