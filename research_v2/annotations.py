"""Blinded independent-review forms, immutable returns, and recomputed agreement."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import cohen_kappa_score

from .generation import consolidate, verify_corpus
from .io import OUT, digest_text, file_hash, read_csv, read_json, write_csv, write_json, write_text

RATINGS = {"added_facts": {"0","1"}, "omitted_facts": {"0","1"}, "order_changed": {"0","1"},
           "relationships_changed": {"0","1"}, "tone_drift": {"0","1","2"},
           "meaning_preservation": {"1","2","3","4","5"}, "usable": {"yes","no"}}
FORM_FIELDS = ["item_id","original_text","rewritten_text",*RATINGS,"notes"]
FOLDER = OUT / "annotations"


def prepare() -> dict:
    verify_corpus()
    originals = {r["passage_id"]:r for r in read_csv(OUT / "corpus/originals.csv")}
    plan = read_json(OUT / "generation_plan.json")
    missing, sampled = [], []
    for model in plan["models"]:
        if not (OUT / f"generation/{model}/completion.json").exists() or not consolidate(model)["complete"]:
            missing.append(model)
            continue
        cells = defaultdict(list)
        for row in read_csv(OUT / f"generation/{model}/rewrites.csv"):
            original = originals[row["passage_id"]]
            cells[(original["author_id"],original["work_id"],row["condition"])].append(row)
        for cell,rows in sorted(cells.items()):
            chosen = sorted(rows,key=lambda r:digest_text("human_audit_v2:"+model+":"+r["request_id"]))[:5]
            if len(chosen)!=5:
                raise ValueError("Incomplete annotation sampling cell")
            for row in chosen:
                original=originals[row["passage_id"]]
                sampled.append({"model_key":model,"request_id":row["request_id"],"passage_id":row["passage_id"],
                                "author_id":original["author_id"],"work_id":original["work_id"],"condition":row["condition"],
                                "source_sha256":original["text_sha256"],"rewrite_sha256":row["rewrite_sha256"],
                                "original_text":original["text"],"rewritten_text":row["rewritten_text"]})
    if missing:
        status={"complete":False,"stage":"waiting_for_complete_generation","missing_models":missing,
                "reason":"Forms are issued once for the frozen complete corpus, not silently expanded after ratings."}
        write_json(FOLDER / "status.json",status)
        return status
    keys=[]
    for annotator in ("A","B"):
        forms=[]
        for row in sampled:
            item_id=digest_text(f"blind_v2:{annotator}:{row['model_key']}:{row['request_id']}")[:20]
            forms.append({"item_id":item_id,"original_text":row["original_text"],"rewritten_text":row["rewritten_text"],
                          **{field:"" for field in RATINGS},"notes":""})
            keys.append({"annotator_id":annotator,"item_id":item_id,
                         **{k:v for k,v in row.items() if k not in {"original_text","rewritten_text"}}})
        forms.sort(key=lambda r:digest_text("display_order:"+r["item_id"]))
        path=FOLDER / f"forms/reviewer_{annotator}.csv"
        if path.exists() and read_csv(path)!=forms:
            raise ValueError("Blinded form would change; preserve existing review provenance")
        write_csv(path,forms,FORM_FIELDS)
    write_csv(FOLDER / "private_join_key.csv",keys)
    status={"complete":False,"stage":"awaiting_two_independent_human_reviews","items_per_reviewer":len(sampled),
            "forms_sha256":{a:file_hash(FOLDER / f"forms/reviewer_{a}.csv") for a in ("A","B")}}
    write_json(FOLDER / "status.json",status)
    return status


def check_ratings(rows: list[dict]) -> list[str]:
    errors=[]
    for row in rows:
        for field,allowed in RATINGS.items():
            if row.get(field) not in allowed:
                errors.append(f"{row.get('item_id')}: invalid or missing {field}")
        requires_note=any(row.get(f)=="1" for f in ("added_facts","omitted_facts","order_changed","relationships_changed"))
        requires_note |= row.get("usable")=="no" or row.get("meaning_preservation") in {"1","2","3"}
        if requires_note and not row.get("notes","").strip():
            errors.append(f"{row.get('item_id')}: explanation required for flagged meaning/factual change")
    return errors


def ingest(annotator: str, path: Path, reviewer_id: str, completed_utc: str, attested: bool) -> None:
    if not attested:
        raise ValueError("A human must explicitly attest independent completion; an agent cannot provide that attestation")
    completed=datetime.fromisoformat(completed_utc.replace("Z","+00:00"))
    if completed.tzinfo is None or completed>datetime.now(timezone.utc):
        raise ValueError("Provide an actual past completion timestamp with timezone")
    if not reviewer_id.strip():
        raise ValueError("A distinct pseudonymous reviewer identity is required")
    template=read_csv(FOLDER / f"forms/reviewer_{annotator}.csv")
    returned=read_csv(path)
    expected={r["item_id"]:r for r in template}
    if len(returned)!=len(expected) or {r["item_id"] for r in returned}!=set(expected):
        raise ValueError("Returned file must have exactly one row per assigned item")
    for row in returned:
        for field in ("original_text","rewritten_text"):
            if row[field]!=expected[row["item_id"]][field]:
                raise ValueError("Source/rewrite text changed in a returned annotation form")
    errors=check_ratings(returned)
    if errors:
        raise ValueError("; ".join(errors[:10]))
    source_sha=file_hash(path)
    dest=FOLDER / f"returns/{annotator}_{source_sha}.csv"
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and file_hash(dest)!=source_sha:
        raise ValueError("Immutable annotation source already exists with different content")
    dest.write_bytes(path.read_bytes())
    registry_path=FOLDER / "reviewer_registry.json"
    registry=read_json(registry_path) if registry_path.exists() else {}
    other="B" if annotator=="A" else "A"
    if registry.get(other,{}).get("reviewer_id")==reviewer_id:
        raise ValueError("Two annotator IDs cannot represent the same person")
    record={"reviewer_id":reviewer_id,"completed_utc":completed.isoformat(),"independent_human_attestation":True,
            "source_file":dest.relative_to(OUT).as_posix(),"source_sha256":source_sha,
            "form_sha256":file_hash(FOLDER / f"forms/reviewer_{annotator}.csv")}
    if annotator in registry and registry[annotator]!=record:
        raise ValueError("Do not overwrite a registered original review; record corrections separately")
    registry[annotator]=record
    write_json(registry_path,registry)
    print(f"Registered immutable human review {annotator}: {source_sha}")


def validate() -> dict:
    errors=[]
    registry_path=FOLDER / "reviewer_registry.json"
    if not registry_path.exists() or not (FOLDER / "private_join_key.csv").exists():
        status={"complete":False,"stage":"missing_independent_human_reviews", "errors":["Two registered original human review files are required."]}
        write_json(FOLDER / "validation.json",status)
        return status
    registry=read_json(registry_path)
    if set(registry)!={"A","B"}:
        errors.append("Exactly two distinct human reviewer registrations are required")
    elif registry["A"]["reviewer_id"]==registry["B"]["reviewer_id"]:
        errors.append("Reviewer identities are identical")
    returned={}
    for annotator in ("A","B"):
        record=registry.get(annotator,{})
        if not record.get("independent_human_attestation"):
            errors.append(f"Reviewer {annotator}: missing independent-human attestation")
            continue
        path=(OUT / record["source_file"]).resolve()
        if not path.is_relative_to((FOLDER / "returns").resolve()) or not path.exists() or file_hash(path)!=record["source_sha256"]:
            errors.append(f"Reviewer {annotator}: original source file missing or altered")
            continue
        rows=read_csv(path)
        errors.extend(check_ratings(rows))
        template={r["item_id"]:r for r in read_csv(FOLDER / f"forms/reviewer_{annotator}.csv")}
        if len(rows)!=len(template) or {r["item_id"] for r in rows}!=set(template):
            errors.append(f"Reviewer {annotator}: incomplete or duplicate item IDs")
        if file_hash(FOLDER / f"forms/reviewer_{annotator}.csv")!=record["form_sha256"]:
            errors.append(f"Reviewer {annotator}: form hash changed")
        for row in rows:
            if row["item_id"] in template and any(row[f]!=template[row["item_id"]][f] for f in ("original_text","rewritten_text")):
                errors.append(f"Reviewer {annotator}: rated text differs from issued text")
        returned[annotator]={r["item_id"]:r for r in rows}
    if errors:
        status={"complete":False,"stage":"invalid_human_review_provenance","errors":errors}
        write_json(FOLDER / "validation.json",status)
        return status
    joined=defaultdict(dict)
    for key in read_csv(FOLDER / "private_join_key.csv"):
        joined[(key["model_key"],key["request_id"])][key["annotator_id"]]=(key,returned[key["annotator_id"]][key["item_id"]])
    agreements, flags, disagreements=[],[],[]
    for model in sorted({k[0] for k in joined}):
        items=[r for k,r in joined.items() if k[0]==model]
        for field in RATINGS:
            a=[r["A"][1][field] for r in items]; b=[r["B"][1][field] for r in items]
            weights="quadratic" if field in {"tone_drift","meaning_preservation"} else None
            if field!="usable":
                a,b=list(map(int,a)),list(map(int,b))
            value=float(cohen_kappa_score(a,b,weights=weights)) if len(set(a+b))>1 else float("nan")
            agreements.append({"model_key":model,"field":field,"items":len(items),
                               "raw_agreement":sum(x==y for x,y in zip(a,b))/len(items),
                               "kappa":value if np.isfinite(value) else "undefined_constant_ratings",
                               "weighting":weights or "unweighted"})
        for item in items:
            key,a=item["A"]; _,b=item["B"]
            risk=lambda row:any(row[f]=="1" for f in ("added_facts","omitted_facts","order_changed","relationships_changed")) or int(row["meaning_preservation"])<=3 or row["usable"]=="no"
            flags.append({"model_key":model,"request_id":key["request_id"],"passage_id":key["passage_id"],
                          "condition":key["condition"],"source_sha256":key["source_sha256"],"rewrite_sha256":key["rewrite_sha256"],
                          "risk_A":int(risk(a)),"risk_B":int(risk(b)),"risk_union":int(risk(a) or risk(b)),
                          "meaning_A":a["meaning_preservation"],"meaning_B":b["meaning_preservation"]})
            for field in RATINGS:
                if a[field]!=b[field]:
                    disagreements.append({"model_key":model,"request_id":key["request_id"],"field":field,
                                          "reviewer_A":a[field],"reviewer_B":b[field],"adjudicated_value":"","adjudicator_id":"","completed_utc":"","reason":""})
    write_csv(FOLDER / "agreement.csv",agreements)
    write_csv(FOLDER / "verified_flags.csv",flags)
    path=FOLDER / "disagreements.csv"
    if not path.exists():
        write_csv(path,disagreements,["model_key","request_id","field","reviewer_A","reviewer_B","adjudicated_value","adjudicator_id","completed_utc","reason"])
    identical=all(r["raw_agreement"]==1 for r in agreements)
    status={"complete":True,"stage":"two_independent_human_reviews_registered","items":len(flags),
            "disagreements":len(disagreements),"identical_choices_all_fields":identical,
            "sensitivity_rule":"predeclared_union_of_reviewers_no_adjudication_needed_for_exclusion",
            "limitations":"Identity/independence are human attestations, not cryptographic proof of who performed the review."}
    write_json(FOLDER / "validation.json",status)
    return status


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["prepare","ingest","validate"])
    parser.add_argument("--annotator",choices=["A","B"])
    parser.add_argument("--file",type=Path)
    parser.add_argument("--reviewer-id")
    parser.add_argument("--completed-utc")
    parser.add_argument("--attest-independent-human",action="store_true")
    args=parser.parse_args()
    if args.action=="prepare":
        print(prepare())
    elif args.action=="validate":
        result=validate(); print(result)
        if not result["complete"]:
            raise SystemExit(2)
    else:
        if not all([args.annotator,args.file,args.reviewer_id,args.completed_utc]):
            parser.error("Ingest requires --annotator, --file, --reviewer-id and --completed-utc")
        ingest(args.annotator,args.file,args.reviewer_id,args.completed_utc,args.attest_independent_human)


if __name__=="__main__":
    main()
