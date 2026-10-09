"""Verify actual agent artifacts without pretending they are provider API responses."""
from __future__ import annotations

from .corpus import clean_text, paragraph_issue, words
from .io import OUT, digest_text, file_hash, read_csv, read_json, write_csv, write_json


def run() -> dict:
    folder=OUT/"agent_rewrite"
    joins={r["request_id"]:r for r in read_csv(folder/"private_join_key.csv")}
    current_hashes={r["text_sha256"]:r for r in read_csv(OUT/"corpus/originals.csv")}
    rows=[]; errors=[]; model="gpt-5.5"
    for condition in ("paraphrase","modernize","simplify"):
        packet=read_json(folder/f"packets/{condition}.json")
        output_path=folder/f"outputs/{condition}.json"
        if not output_path.exists():
            errors.append(f"missing {condition}"); continue
        outputs=read_json(output_path)
        expected={r["request_id"]:r for r in packet["requests"]}
        if len(outputs)!=18 or len({r.get("request_id") for r in outputs})!=18 or {r.get("request_id") for r in outputs}!=set(expected):
            errors.append(f"incomplete/duplicate IDs: {condition}"); continue
        for row in outputs:
            if set(row)!={"request_id","rewritten_text"} or not isinstance(row["rewritten_text"],str) or not row["rewritten_text"].strip():
                errors.append(f"invalid row {row.get('request_id')}"); continue
            source=expected[row["request_id"]]; key=joins[row["request_id"]]
            if digest_text(source["text"])!=key["source_sha256"]:
                errors.append(f"source hash mismatch {row['request_id']}")
            ratio=words(row["rewritten_text"])/source["original_word_count"]
            status="warning" if abs(ratio-1)>.15 else "pass"
            if digest_text(row["rewritten_text"])==key["source_sha256"]:
                status="fail"; errors.append(f"unchanged output {row['request_id']}")
            rows.append({**key,"requested_agent_model":model,"generation_method":"codex_subagent_persistent_context",
                         "task_name":f"/root/rewrite_{condition}","experiment_role":"supplemental_feasibility_only",
                         "source_in_final_corpus":int(key["source_sha256"] in current_hashes),
                         "current_passage_id":current_hashes.get(key["source_sha256"],{}).get("passage_id",""),
                         "original_word_count":source["original_word_count"],"rewrite_word_count":words(row["rewritten_text"]),
                         "length_ratio":ratio,"qc_status":status,"rewritten_text":row["rewritten_text"],
                         "rewrite_sha256":digest_text(row["rewritten_text"]),"output_file_sha256":file_hash(output_path),
                         "provider_response_id":"not_available_for_agent_generation"})
    write_csv(folder/"validated_rewrites.csv",rows)
    status={"expected":54,"received":len(rows),"errors":errors,"structurally_complete":len(rows)==54 and not errors,
            "primary_experiment":False,"requested_agent_model":model,"separate_human_review":False,
            "source_matches_final_corpus":sum(r["source_in_final_corpus"] for r in rows),
            "within_15pct":sum(r["qc_status"]=="pass" for r in rows),
            "limitations":["Multiple passages shared a persistent agent context.","No API sampling parameters, provider response IDs or token counts are available.",
                           "Samples were requested from an earlier source-review draft; only exact final-source hash matches can enter a supplemental comparison.",
                           "These outputs are model-generated text, not independent human annotations."]}
    write_json(folder/"provenance.json",status)
    return status


if __name__=="__main__":
    print(run())
