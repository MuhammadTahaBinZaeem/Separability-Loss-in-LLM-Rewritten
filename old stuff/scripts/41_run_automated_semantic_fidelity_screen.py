"""Automated preliminary semantic-fidelity screen.

This is NOT a human annotation substitute. It creates a transparent automated
screen for the E4 audit sample when human annotators are unavailable.

Inputs:
- data/audit/semantic_fidelity_sample.csv

Outputs:
- data/audit/automated_semantic_fidelity_screen.csv
- metadata/automated_semantic_fidelity_screen_summary.csv
- logs/automated_semantic_fidelity_screen_report.md
"""
from __future__ import annotations

import csv, hashlib, math, re, string
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data/audit/semantic_fidelity_sample.csv"
OUT = ROOT / "data/audit/automated_semantic_fidelity_screen.csv"
SUMMARY = ROOT / "metadata/automated_semantic_fidelity_screen_summary.csv"
REPORT = ROOT / "logs/automated_semantic_fidelity_screen_report.md"
MANIFEST = ROOT / "metadata/automated_semantic_fidelity_screen_manifest.csv"

STOP = set("""
a an the and or but if then than that this these those to of in on for from with without by as at is are was were be been being it its into over under through after before not no nor so such very can could would should will shall may might must do did done does have has had he she they them his her their him who whom whose what which when where why how i you we our us my me your
""".split())
NEGATIONS = {"not", "no", "never", "none", "nothing", "neither", "nor", "without", "cannot", "can't", "won't", "don't", "didn't", "isn't", "wasn't", "weren't"}

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""

def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+(?:\.\d+)?", text.lower())

def content_tokens(text: str) -> list[str]:
    return [t.strip(string.punctuation) for t in tokens(text) if t not in STOP and len(t) > 2]

def caps(text: str) -> set[str]:
    return set(re.findall(r"\b[A-Z][a-z]{2,}\b", text))

def numbers(text: str) -> set[str]:
    return set(re.findall(r"\b\d+(?:\.\d+)?\b", text))

def quote_count(text: str) -> int:
    return text.count('"') + text.count("'") + text.count("“") + text.count("”") + text.count("‘") + text.count("’")

def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)

def ratio(a: int, b: int) -> float:
    return round(b / a, 6) if a else 0.0

def main() -> int:
    rows = read_csv(SAMPLE)
    out = []
    for r in rows:
        original = r["original_text"]
        rewritten = r["rewritten_text"]
        ot = tokens(original); rt = tokens(rewritten)
        oc = set(content_tokens(original)); rc = set(content_tokens(rewritten))
        ocaps = caps(original); rcaps = caps(rewritten)
        onums = numbers(original); rnums = numbers(rewritten)
        oneg = set(t for t in tokens(original) if t in NEGATIONS)
        rneg = set(t for t in tokens(rewritten) if t in NEGATIONS)
        overlap = jaccard(oc, rc)
        wc_ratio = ratio(len(ot), len(rt))
        missing_caps = sorted(ocaps - rcaps)
        added_caps = sorted(rcaps - ocaps)
        missing_nums = sorted(onums - rnums)
        added_nums = sorted(rnums - onums)
        quote_delta = abs(quote_count(original) - quote_count(rewritten))
        negation_changed = int(oneg != rneg)
        flags = []
        if overlap < 0.34: flags.append("low_content_overlap")
        if wc_ratio < 0.70: flags.append("large_compression")
        if wc_ratio > 1.35: flags.append("large_expansion")
        if missing_nums or added_nums: flags.append("number_change")
        if len(missing_caps) >= 3: flags.append("many_original_capitalized_terms_missing")
        if len(added_caps) >= 3: flags.append("many_new_capitalized_terms_added")
        if quote_delta >= 4: flags.append("large_quote_punctuation_change")
        if negation_changed: flags.append("negation_set_changed")
        risk_score = len(flags)
        if risk_score == 0:
            risk = "low"
        elif risk_score <= 2:
            risk = "medium"
        else:
            risk = "high"
        out.append({
            "audit_id": r["audit_id"],
            "condition": r["condition"],
            "original_word_count": len(ot),
            "rewritten_word_count": len(rt),
            "word_count_ratio": wc_ratio,
            "content_token_jaccard": round(overlap, 6),
            "missing_original_capitalized_terms": ";".join(missing_caps[:20]),
            "added_new_capitalized_terms": ";".join(added_caps[:20]),
            "missing_numbers": ";".join(missing_nums),
            "added_numbers": ";".join(added_nums),
            "quote_punctuation_delta": quote_delta,
            "negation_set_changed": negation_changed,
            "automated_flags": ";".join(flags),
            "automated_risk_level": risk,
            "important_note": "automated screen only; not human annotation",
        })
    fields = ["audit_id","condition","original_word_count","rewritten_word_count","word_count_ratio","content_token_jaccard","missing_original_capitalized_terms","added_new_capitalized_terms","missing_numbers","added_numbers","quote_punctuation_delta","negation_set_changed","automated_flags","automated_risk_level","important_note"]
    write_csv(OUT, out, fields)
    by_condition = Counter((r["condition"], r["automated_risk_level"]) for r in out)
    summary_rows = []
    for condition in sorted({r["condition"] for r in out}):
        subset = [r for r in out if r["condition"] == condition]
        summary_rows.append({
            "condition": condition,
            "rows": len(subset),
            "low_risk": by_condition[(condition,"low")],
            "medium_risk": by_condition[(condition,"medium")],
            "high_risk": by_condition[(condition,"high")],
            "mean_content_token_jaccard": round(sum(float(r["content_token_jaccard"]) for r in subset)/len(subset), 6),
            "mean_word_count_ratio": round(sum(float(r["word_count_ratio"]) for r in subset)/len(subset), 6),
        })
    write_csv(SUMMARY, summary_rows, ["condition","rows","low_risk","medium_risk","high_risk","mean_content_token_jaccard","mean_word_count_ratio"])
    artifacts = [OUT, SUMMARY]
    write_csv(MANIFEST, [{"artifact": p.stem, "path": p.relative_to(ROOT).as_posix(), "rows": len(read_csv(p)), "size_bytes": p.stat().st_size, "sha256": sha_file(p)} for p in artifacts], ["artifact","path","rows","size_bytes","sha256"])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Automated Semantic Fidelity Screen Report\n\n"
        "This is an automated preliminary screen, not a human semantic-fidelity audit. It must not be described as human annotation.\n\n"
        + "\n".join(f"- {r['condition']}: rows={r['rows']}, low={r['low_risk']}, medium={r['medium_risk']}, high={r['high_risk']}, mean_jaccard={r['mean_content_token_jaccard']}, mean_wc_ratio={r['mean_word_count_ratio']}" for r in summary_rows)
        + "\n\nUse this only to prioritize manual review or to report a transparent automated limitation when human annotators are unavailable.\n",
        encoding="utf-8",
    )
    print(f"Automated semantic screen complete: rows={len(out)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
