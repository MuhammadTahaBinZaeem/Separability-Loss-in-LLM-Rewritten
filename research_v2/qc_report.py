"""One auditable table of generation failures, length warnings and model provenance."""
from __future__ import annotations
from collections import Counter,defaultdict
from statistics import mean,median
from .generation import consolidate
from .io import OUT,read_csv,read_json,read_jsonl,write_csv,write_json


def run():
    originals={r["passage_id"]:r for r in read_csv(OUT / "corpus/originals.csv")}
    plan=read_json(OUT / "generation_plan.json")
    summary,cells,failures=[],[],[]
    for model in plan["models"]:
        folder=OUT / f"generation/{model}"
        if not (folder / "requests.jsonl").exists():
            continue
        status=consolidate(model)
        rows=read_csv(folder / "rewrites.csv")
        raw={r["request_id"]:r["response"] for r in read_jsonl(folder / "raw_responses.jsonl")}
        groups=defaultdict(list)
        for original in originals.values():
            for condition in plan["conditions"]:
                groups[(original["author_id"],original["work_id"],condition)]
        for row in rows:
            original=originals[row["passage_id"]]
            groups[(original["author_id"],original["work_id"],row["condition"])].append(row)
            if row["qc_status"]=="fail":
                native=raw.get(row["request_id"],{})
                reason=(native.get("incomplete_details") or {}).get("reason","")
                if not reason:
                    reason=(native.get("promptFeedback") or {}).get("blockReason","")
                if row.get("outcome_type")=="http_content_filter":
                    reason="http_content_filter"
                failures.append({"model_key":model,"passage_id":row["passage_id"],"request_id":row["request_id"],
                   "author_id":original["author_id"],"work_id":original["work_id"],"condition":row["condition"],
                   "qc_flags":row["qc_flags"],"native_failure_reason":reason,"response_id":row["response_id"]})
        for condition in plan["conditions"]:
            subset=[r for r in rows if r["condition"]==condition]
            counts=Counter(r["qc_status"] for r in subset)
            valid=[r for r in subset if r["qc_status"]!="fail"]
            ratios=[float(r["length_ratio"]) for r in valid]
            terminal=sum(r.get("outcome_type")=="http_content_filter" for r in subset)
            summary.append({"model_key":model,"condition":condition,"assigned":len(originals),"accounted":len(subset),
                "native_responses":len(subset)-terminal,"terminal_http_failures":terminal,
                "missing":len(originals)-len(subset),"valid":len(valid),"pass":counts["pass"],"warning":counts["warning"],
                "failed":counts["fail"],"mean_length_ratio":mean(ratios) if ratios else "",
                "median_length_ratio":median(ratios) if ratios else "",
                "minimum_length_ratio":min(ratios) if ratios else "","maximum_length_ratio":max(ratios) if ratios else "",
                "returned_models":";".join(sorted({r["returned_model"] for r in subset})),
                "response_accounting_complete":status.get("accounting_complete",False)})
        for (author,work,condition),subset in sorted(groups.items()):
            counts=Counter(r["qc_status"] for r in subset)
            cells.append({"model_key":model,"author_id":author,"work_id":work,"condition":condition,"assigned":20,
                          "accounted":len(subset),"missing":20-len(subset),"pass":counts["pass"],"warning":counts["warning"],"failed":counts["fail"],
                          "valid_for_human_sampling":counts["pass"]+counts["warning"]})
    write_csv(OUT / "results/generation_summary.csv",summary)
    write_csv(OUT / "results/generation_cells.csv",cells)
    write_csv(OUT / "results/generation_failures.csv",failures,
              ["model_key","passage_id","request_id","author_id","work_id","condition","qc_flags","native_failure_reason","response_id"])
    result={"accounting_complete":len(summary)==len(plan["models"])*3 and all(r["missing"]==0 for r in summary),
            "assigned":sum(r["assigned"] for r in summary),"accounted":sum(r["accounted"] for r in summary),
            "native_responses":sum(r["native_responses"] for r in summary),"terminal_http_failures":sum(r["terminal_http_failures"] for r in summary),
            "failed":len(failures),"warnings":sum(r["warning"] for r in summary),
            "length_warnings_are_included_in_main_available_output_analysis":True,
            "human_sampling_cells_sufficient":len(cells)==len(plan["models"])*54 and all(r["valid_for_human_sampling"]>=5 for r in cells)}
    write_json(OUT / "results/generation_qc_status.json",result)
    print(result)
    return result


if __name__=="__main__":
    run()
