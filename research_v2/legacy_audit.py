"""Reconcile historical QC stages without rewriting original experimental records."""
from __future__ import annotations

import importlib.util
from collections import Counter

from .io import OUT, ROOT, digest_text, read_csv, write_csv, write_json, write_text


def run() -> dict:
    originals={r["passage_id"]:r for r in read_csv(ROOT/"data/processed/selected_original_passages.csv")}
    parsed=read_csv(ROOT/"data/interim/rewrite_responses_parsed.csv")
    historical_qc={(r["passage_id"],r["condition"]):r for r in read_csv(ROOT/"metadata/rewrite_qc_report.csv")}
    spec=importlib.util.spec_from_file_location("legacy_qc_rules",ROOT/"scripts/09_validate_rewrite_outputs.py")
    legacy=importlib.util.module_from_spec(spec); spec.loader.exec_module(legacy)
    rows=[]; errors=[]
    for row in parsed:
        key=(row["passage_id"],row["condition"])
        text=row["rewritten_text"]
        original=originals[row["passage_id"]]
        source_hash=digest_text(original["text"]); rewrite_hash=digest_text(text)
        if source_hash!=row["source_text_sha256"] or rewrite_hash!=row["rewritten_text_sha256"]:
            errors.append(f"text hash mismatch {key}")
        flags=[]
        if not text.strip(): flags.append("empty_rewritten_text")
        if legacy.FORBIDDEN_RE.search(text): flags.append("prompt_or_source_leakage")
        if legacy.MARKDOWN_RE.search(text): flags.append("markdown_or_list_format")
        ratio=round(legacy.word_count(text)/int(original["word_count"]),6)
        if ratio<.8 or ratio>1.2: flags.append("length_hard_warning")
        elif ratio<.85 or ratio>1.15: flags.append("length_soft_warning")
        if legacy.sentence_count(text)<3: flags.append("low_sentence_count")
        failure=any(f in flags for f in ("empty_rewritten_text","prompt_or_source_leakage","markdown_or_list_format"))
        status="fail" if failure else "warning" if flags else "pass"
        current=historical_qc[key]
        if status!=current["qc_status"] or ";".join(flags)!=current["qc_flags"]:
            errors.append(f"stored final QC differs from current-rule recomputation {key}")
        rows.append({"passage_id":key[0],"condition":key[1],"batch_label":row["batch_label"],
                     "generation_time_qc":row["qc_status"],"generation_time_flags":row["qc_flags"],
                     "stored_revalidation_qc":current["qc_status"],"recomputed_revalidation_qc":status,
                     "recomputed_flags":";".join(flags),"source_sha256":source_hash,"rewrite_sha256":rewrite_hash,
                     "status_changed":int(row["qc_status"]!=status)})
    if len({(r["passage_id"],r["condition"]) for r in rows})!=1080 or len(rows)!=1080:
        errors.append("Missing/duplicate historical original-condition pair")
    summary={"historical_rows":len(rows),"generation_time_counts":dict(Counter(r["generation_time_qc"] for r in rows)),
             "revalidation_counts":dict(Counter(r["recomputed_revalidation_qc"] for r in rows)),
             "changed_status_rows":sum(r["status_changed"] for r in rows),"errors":errors,
             "consistent":not errors,"historical_data_are_primary":False}
    write_csv(OUT/"legacy/qc_reconciliation.csv",rows)
    write_json(OUT/"legacy/qc_reconciliation.json",summary)
    write_text(OUT/"legacy/README.md", "# Historical QC reconciliation\n\n"
               "The June generation-time manifest and parsed response table retain their original QC classifications. "
               "The later QC report uses the narrower current validator regex. The reconciliation CSV labels both stages "
               "and recomputes the later stage from the preserved prose with normalized LF text hashing. "
               "Changed classifications are not additional generations and do not establish that the prose was fabricated.\n\n"
               f"Rows: {len(rows)}. Changed classifications: {summary['changed_status_rows']}. "
               f"Recomputation errors: {len(errors)}.\n\n"
               "Historical bootstrap tables used different replicate counts and a bootstrap tail proportion mislabeled as a p-value. "
               "Both are superseded for publication by revision/results/primary_comparisons.csv when the revised experiment completes. "
               "Do not combine old confidence limits or semantic flags with revised predictions.\n")
    return summary


if __name__=="__main__":
    print(run())
