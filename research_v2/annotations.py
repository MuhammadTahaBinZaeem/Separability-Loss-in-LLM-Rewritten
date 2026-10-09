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


def review_scope(plan: dict) -> tuple[list[str], dict]:
    """A fixed review batch may cover a completed subset of the planned models."""
    path = FOLDER / "review_scope.json"
    manifest_path = FOLDER / "issued_manifest.json"
    issued = read_json(manifest_path) if manifest_path.exists() else None
    if not path.exists():
        if issued and "review_scope_sha256" in issued:
            raise ValueError("Issued review scope is missing; preserve the original batch")
        return list(plan["models"]), {}
    scope = read_json(path)
    models = scope.get("models")
    if (not isinstance(models, list) or not models or any(not isinstance(m, str) for m in models)
            or len(models) != len(set(models)) or not set(models) <= set(plan["models"])
            or not isinstance(scope.get("batch_id"), str) or not scope["batch_id"].strip()
            or scope.get("sampling_rule") != "human_audit_v2"):
        raise ValueError("Invalid fixed review scope")
    scope_hash = file_hash(path)
    if issued and issued.get("review_scope_sha256") != scope_hash:
        raise ValueError("Issued review scope changed; create a separate batch instead")
    return models, {"review_scope_sha256": scope_hash, "batch_id": scope["batch_id"], "models_in_scope": models}


def prepare() -> dict:
    freeze=verify_corpus()
    originals = {r["passage_id"]:r for r in read_csv(OUT / "corpus/originals.csv")}
    plan = read_json(OUT / "generation_plan.json")
    models, scope_metadata = review_scope(plan)
    pending_models = sorted(set(plan["models"]) - set(models))
    if any((OUT / f"generation/{model}/RUNNING.lock").exists() for model in models):
        raise ValueError("Wait for generation in this review batch to stop before issuing forms")
    missing, sampled = [], []
    for model in models:
        if not (OUT / f"generation/{model}/completion.json").exists() or not consolidate(model).get("accounting_complete",False):
            missing.append(model)
            continue
        cells = defaultdict(list)
        for row in read_csv(OUT / f"generation/{model}/rewrites.csv"):
            if row["qc_status"]=="fail":
                continue
            original = originals[row["passage_id"]]
            cells[(original["author_id"],original["work_id"],row["condition"])].append(row)
        expected_cells={(r["author_id"],r["work_id"],c) for r in originals.values() for c in plan["conditions"]}
        if set(cells)!=expected_cells:
            raise ValueError("At least one annotation sampling cell has no valid outputs")
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
                "reason":"Forms require complete accounting for every model in the fixed review batch.",
                "models_in_scope":models,"pending_models":pending_models}
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
    key_path=FOLDER / "private_join_key.csv"
    if key_path.exists() and read_csv(key_path)!=keys:
        raise ValueError("Do not change an issued annotation join key")
    write_csv(key_path,keys)
    manifest={"corpus_sha256":freeze["corpus_sha256"],"items_per_reviewer":len(sampled),
              "join_key_sha256":file_hash(key_path),
              "forms_sha256":{a:file_hash(FOLDER / f"forms/reviewer_{a}.csv") for a in ("A","B")},
              "generation_sha256":{m:file_hash(OUT / f"generation/{m}/rewrites.csv") for m in models},
              **scope_metadata}
    manifest_path=FOLDER / "issued_manifest.json"
    if manifest_path.exists():
        previous=read_json(manifest_path)
        if {k:v for k,v in previous.items() if k!="issued_utc"}!=manifest:
            raise ValueError("Issued annotation provenance would change")
    else:
        write_json(manifest_path,{**manifest,"issued_utc":datetime.now(timezone.utc).isoformat()})
    if (FOLDER / "reviewer_registry.json").exists():
        return validate()
    status={"complete":False,"stage":"awaiting_two_independent_human_reviews","items_per_reviewer":len(sampled),
            "models_in_scope":models,"pending_models":pending_models,
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


def independence_check_valid(path: Path, registry_path: Path, registry: dict) -> bool:
    """A flagged identical-rating pair needs a separate, genuine human check."""
    if not path.exists():
        return False
    try:
        record=read_json(path)
        checked=datetime.fromisoformat(record["checked_utc"].replace("Z","+00:00"))
        latest=max(datetime.fromisoformat(r["completed_utc"]) for r in registry.values())
        return (record.get("checked_by_human") is True and bool(record.get("checker_id","").strip())
                and checked.tzinfo is not None and latest<=checked<=datetime.now(timezone.utc)
                and record.get("registry_sha256")==file_hash(registry_path)
                and record.get("outcome")=="independence_confirmed"
                and bool(record.get("method","").strip()) and bool(record.get("notes","").strip()))
    except (KeyError,ValueError,TypeError,AttributeError):
        return False


def ingest(annotator: str, path: Path, reviewer_id: str, completed_utc: str, attested: bool) -> None:
    if annotator not in {"A","B"}:
        raise ValueError("Annotator must be A or B")
    if not attested:
        raise ValueError("A human must explicitly attest independent completion; an agent cannot provide that attestation")
    completed=datetime.fromisoformat(completed_utc.replace("Z","+00:00"))
    if completed.tzinfo is None or completed>datetime.now(timezone.utc):
        raise ValueError("Provide an actual past completion timestamp with timezone")
    reviewer_id=reviewer_id.strip()
    if not reviewer_id:
        raise ValueError("A distinct pseudonymous reviewer identity is required")
    issued=read_json(FOLDER / "issued_manifest.json")
    if completed<datetime.fromisoformat(issued["issued_utc"]):
        raise ValueError("Review completion cannot predate the issued forms")
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
    registry_path=FOLDER / "reviewer_registry.json"
    registry=read_json(registry_path) if registry_path.exists() else {}
    other="B" if annotator=="A" else "A"
    if registry.get(other,{}).get("reviewer_id","").strip().casefold()==reviewer_id.casefold():
        raise ValueError("Two annotator IDs cannot represent the same person")
    record={"reviewer_id":reviewer_id,"completed_utc":completed.isoformat(),"independent_human_attestation":True,
            "source_file":dest.relative_to(OUT).as_posix(),"source_sha256":source_sha,
            "form_sha256":file_hash(FOLDER / f"forms/reviewer_{annotator}.csv")}
    if annotator in registry and registry[annotator]!=record:
        raise ValueError("Do not overwrite a registered original review; record corrections separately")
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and file_hash(dest)!=source_sha:
        raise ValueError("Immutable annotation source already exists with different content")
    dest.write_bytes(path.read_bytes())
    registry[annotator]=record
    write_json(registry_path,registry)
    print(f"Registered immutable human review {annotator}: {source_sha}")


def validate() -> dict:
    errors=[]
    registry_path=FOLDER / "reviewer_registry.json"
    if not registry_path.exists() or not (FOLDER / "private_join_key.csv").exists() or not (FOLDER / "issued_manifest.json").exists():
        status={"complete":False,"stage":"missing_independent_human_reviews", "errors":["Two registered original human review files are required."]}
        write_json(FOLDER / "validation.json",status)
        return status
    registry=read_json(registry_path)
    issued=read_json(FOLDER / "issued_manifest.json")
    scope_models, _ = review_scope(read_json(OUT / "generation_plan.json"))
    if set(issued["generation_sha256"]) != set(scope_models):
        errors.append("Issued models differ from the fixed review scope")
    freeze=verify_corpus()
    if issued["corpus_sha256"]!=freeze["corpus_sha256"] or file_hash(FOLDER / "private_join_key.csv")!=issued["join_key_sha256"]:
        errors.append("Issued annotation source/join-key provenance changed")
    for model,expected_hash in issued["generation_sha256"].items():
        if file_hash(OUT / f"generation/{model}/rewrites.csv")!=expected_hash:
            errors.append(f"Rated generation changed for {model}")
    if set(registry)!={"A","B"}:
        errors.append("Exactly two distinct human reviewer registrations are required")
    elif registry["A"]["reviewer_id"].strip().casefold()==registry["B"]["reviewer_id"].strip().casefold():
        errors.append("Reviewer identities are identical")
    returned={}
    originals={r["passage_id"]:r for r in read_csv(OUT / "corpus/originals.csv")}
    generated={m:{r["request_id"]:r for r in read_csv(OUT / f"generation/{m}/rewrites.csv")}
               for m in issued["generation_sha256"]}
    join_rows=read_csv(FOLDER / "private_join_key.csv")
    join_ids={(r["annotator_id"],r["item_id"]) for r in join_rows}
    if len(join_ids)!=len(join_rows) or len(join_rows)!=2*issued["items_per_reviewer"]:
        errors.append("Annotation join key has duplicate or missing entries")
    for annotator in ("A","B"):
        record=registry.get(annotator,{})
        if record.get("independent_human_attestation") is not True or not record.get("reviewer_id","").strip():
            errors.append(f"Reviewer {annotator}: missing independent-human attestation")
            continue
        try:
            completed=datetime.fromisoformat(record["completed_utc"])
            if completed.tzinfo is None or not datetime.fromisoformat(issued["issued_utc"])<=completed<=datetime.now(timezone.utc):
                errors.append(f"Reviewer {annotator}: invalid completion date")
        except (ValueError,KeyError):
            errors.append(f"Reviewer {annotator}: missing/invalid completion date")
        path=(OUT / record["source_file"]).resolve()
        if not path.is_relative_to((FOLDER / "returns").resolve()) or not path.exists() or file_hash(path)!=record["source_sha256"]:
            errors.append(f"Reviewer {annotator}: original source file missing or altered")
            continue
        rows=read_csv(path)
        errors.extend(check_ratings(rows))
        template={r["item_id"]:r for r in read_csv(FOLDER / f"forms/reviewer_{annotator}.csv")}
        keys=[r for r in join_rows if r["annotator_id"]==annotator]
        if {r["item_id"] for r in keys}!=set(template):
            errors.append(f"Reviewer {annotator}: join key does not match form items")
        for key in keys:
            original=originals.get(key["passage_id"])
            rewrite=generated.get(key["model_key"],{}).get(key["request_id"])
            form=template.get(key["item_id"])
            if not original or not rewrite or not form:
                errors.append(f"Reviewer {annotator}: missing original/rewrite/form linkage")
                continue
            if (rewrite["qc_status"]=="fail" or rewrite["passage_id"]!=key["passage_id"] or rewrite["condition"]!=key["condition"]
                or any(key[f]!=original[f] for f in ("author_id","work_id"))
                or key["source_sha256"]!=original["text_sha256"] or key["rewrite_sha256"]!=rewrite["rewrite_sha256"]
                or form["original_text"]!=original["text"] or form["rewritten_text"]!=rewrite["rewritten_text"]):
                errors.append(f"Reviewer {annotator}: issued item does not match its frozen source/rewrite")
        if len(rows)!=len(template) or {r["item_id"] for r in rows}!=set(template):
            errors.append(f"Reviewer {annotator}: incomplete or duplicate item IDs")
        if file_hash(FOLDER / f"forms/reviewer_{annotator}.csv")!=record["form_sha256"]:
            errors.append(f"Reviewer {annotator}: form hash changed")
        if record["form_sha256"]!=issued["forms_sha256"][annotator]:
            errors.append(f"Reviewer {annotator}: rated form differs from issued manifest")
        for row in rows:
            if row["item_id"] in template and any(row[f]!=template[row["item_id"]][f] for f in ("original_text","rewritten_text")):
                errors.append(f"Reviewer {annotator}: rated text differs from issued text")
        returned[annotator]={r["item_id"]:r for r in rows}
    if errors:
        status={"complete":False,"stage":"invalid_human_review_provenance","errors":errors}
        write_json(FOLDER / "validation.json",status)
        return status
    joined=defaultdict(dict)
    for key in join_rows:
        joined[(key["model_key"],key["request_id"])][key["annotator_id"]]=(key,returned[key["annotator_id"]][key["item_id"]])
    if len(joined)!=issued["items_per_reviewer"] or any(set(r)!={"A","B"} for r in joined.values()):
        status={"complete":False,"stage":"invalid_human_review_provenance","errors":["Both reviewers must independently rate the same underlying pairs"]}
        write_json(FOLDER / "validation.json",status)
        return status
    agreements, flags, disagreements=[],[],[]
    for model in sorted({k[0] for k in joined}):
        items=[r for k,r in joined.items() if k[0]==model]
        for field in RATINGS:
            a=[r["A"][1][field] for r in items]; b=[r["B"][1][field] for r in items]
            weights="quadratic" if field in {"tone_drift","meaning_preservation"} else None
            if field!="usable":
                a,b=list(map(int,a)),list(map(int,b))
            labels=sorted(RATINGS[field]) if field=="usable" else sorted(map(int,RATINGS[field]))
            value=float(cohen_kappa_score(a,b,labels=labels,weights=weights)) if len(set(a+b))>1 else float("nan")
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
    summaries=[]
    for model,condition in sorted({(r["model_key"],r["condition"]) for r in flags}):
        subset=[r for r in flags if r["model_key"]==model and r["condition"]==condition]
        count=len(subset)
        summaries.append({"model_key":model,"condition":condition,"audited_pairs":count,
                          "risk_A":sum(r["risk_A"] for r in subset),"risk_B":sum(r["risk_B"] for r in subset),
                          "risk_union":sum(r["risk_union"] for r in subset),
                          "risk_union_fraction":sum(r["risk_union"] for r in subset)/count,
                          "mean_meaning_A":sum(int(r["meaning_A"]) for r in subset)/count,
                          "mean_meaning_B":sum(int(r["meaning_B"]) for r in subset)/count,
                          "scope":"audited_valid_output_subset_only"})
    write_csv(FOLDER / "semantic_summary.csv",summaries)
    path=FOLDER / "disagreements.csv"
    if not path.exists():
        write_csv(path,disagreements,["model_key","request_id","field","reviewer_A","reviewer_B","adjudicated_value","adjudicator_id","completed_utc","reason"])
    identical=all(r["raw_agreement"]==1 for r in agreements)
    independent=not identical or independence_check_valid(FOLDER / "independence_check.json",registry_path,registry)
    planned_models = set(read_json(OUT / "generation_plan.json")["models"])
    reviewed_models = set(issued["generation_sha256"])
    pending_models = sorted(planned_models - reviewed_models)
    stage = ("review_batch_complete_additional_models_pending" if pending_models else "two_independent_human_reviews_registered") if independent else "identical_choices_require_human_provenance_check"
    status={"complete":independent and not pending_models,"batch_complete":independent,"stage":stage,"items":len(flags),
            "models_in_scope":sorted(reviewed_models),"pending_models":pending_models,
            "disagreements":len(disagreements),"identical_choices_all_fields":identical,
            "identical_choices_provenance_check_required":identical,"provenance_check_satisfied":independent,
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
