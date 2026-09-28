"""Fail-closed computational, human-provenance and actual archive readiness gates."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
import urllib.request
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score,f1_score

from .analysis import CLASSIFIERS,FAMILIES,analysis_fingerprint,split_rows
from .annotations import validate as validate_annotations
from .corpus import AUTHORS,clean_text,source_text,words
from .generation import consolidate,verify_corpus
from .inference import holm
from .io import OUT,ROOT,digest_text,file_hash,read_csv,read_json,write_json


def code_fingerprint():
    paths=sorted((ROOT / "research_v2").glob("*.py"))+sorted((ROOT / "tests").glob("*.py"))
    paths += [ROOT / "requirements-v2.lock",ROOT / "scripts/13_extract_stylometric_features.py"]
    return digest_text("\n".join(f"{p.relative_to(ROOT).as_posix()}:{file_hash(p)}" for p in paths))


def check_environment():
    pins=re.findall(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)", (ROOT / "requirements-v2.lock").read_text(),re.M)
    mismatches=[]
    for name,version in pins:
        try:
            actual=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual="missing"
        if actual!=version:
            mismatches.append(f"{name}: expected {version}; got {actual}")
    if platform.python_version()!="3.12.11":
        mismatches.append("Python must be 3.12.11")
    return {"passed":not mismatches,"mismatches":mismatches,"locked_distributions":len(pins),"python":platform.python_version()}


def run_tests():
    result=subprocess.run([sys.executable,"-m","pytest","-q","tests"],cwd=ROOT,text=True,capture_output=True)
    report={"passed":result.returncode==0,"code_fingerprint":code_fingerprint(),"environment":check_environment(),
            "completed_utc":datetime.now(timezone.utc).isoformat(),"output":result.stdout+result.stderr}
    write_json(OUT / "verification/tests.json",report)
    return report


def corpus_checks():
    freeze=verify_corpus()
    if file_hash(OUT / "work_specs.json")!=freeze["work_specs_sha256"]:
        raise ValueError("Work boundary specifications changed after freeze")
    if file_hash(OUT / "PROTOCOL.md")!=freeze["protocol_sha256_at_freeze"]:
        raise ValueError("Original frozen protocol changed; amendments must remain separate")
    rows=read_csv(OUT / "corpus/originals.csv")
    if len(rows)!=360 or len({r["passage_id"] for r in rows})!=360 or len({r["text_sha256"] for r in rows})!=360:
        raise ValueError("Corpus cardinality/uniqueness failure")
    if Counter(r["author_id"] for r in rows)!=Counter({a:60 for a in AUTHORS}):
        raise ValueError("Author balance failure")
    if set(Counter((r["author_id"],r["work_id"]) for r in rows).values())!={20}:
        raise ValueError("Work balance failure")
    source={r["gutenberg_id"]:source_text(int(r["gutenberg_id"])) for r in rows}
    intervals=defaultdict(list)
    for row in rows:
        start,end=int(row["source_start_char"]),int(row["source_end_char"])
        if row["text"]!=clean_text(source[row["gutenberg_id"]][start:end]) or digest_text(row["text"])!=row["text_sha256"] or not 450<=words(row["text"])<=650:
            raise ValueError("Passage is not an exact clean-text transform of its archived source range")
        if any(start<b and end>a for a,b in intervals[row["gutenberg_id"]]):
            raise ValueError("Source passages overlap")
        intervals[row["gutenberg_id"]].append((start,end))
    for fold in range(3):
        train,test=split_rows(rows,fold)
        if len(train)!=240 or len(test)!=120:
            raise ValueError("Unexpected work-grouped split size")
    legacy=read_csv(OUT / "corpus/legacy_360_audit.csv")
    if len(legacy)!=360 or len({r["legacy_passage_id"] for r in legacy})!=360:
        raise ValueError("Historical audit does not cover all 360 passages")
    return {"passed":True,"passages":360,"works":18,"legacy_audit_rows":360,
            "review_method":"AI-assisted source-boundary audit; not claimed to be independent human review"}


def analysis_checks(allow_partial=False):
    status=read_json(OUT / "results/analysis_status.json")
    plan=read_json(OUT / "generation_plan.json")
    models=[m for m in plan["models"] if status.get("model_status",{}).get(m,{}).get("accounting_complete")]
    if status.get("analysis_fingerprint")!=analysis_fingerprint():
        raise ValueError("Analysis was not run with the current code/protocol/plan")
    if not allow_partial and (not status.get("analysis_complete") or status.get("comparison_count")!=18):
        raise ValueError("Both complete-response model analyses and all 18 comparisons are required")
    if not models or status.get("comparison_count")!=len(models)*9:
        raise ValueError("Completed-model diagnostic comparisons are missing")
    if status.get("bootstraps")!=5000 or status.get("permutations")!=9999 or not status.get("ablations_included"):
        raise ValueError("Final inference/ablation settings were not used")
    for relative,expected in status.get("output_hashes",{}).items():
        path=(OUT / "results" / relative).resolve()
        if not path.is_relative_to((OUT / "results").resolve()) or not path.exists() or file_hash(path)!=expected:
            raise ValueError(f"Analysis artifact changed: {relative}")
    originals={r["passage_id"]:r for r in read_csv(OUT / "corpus/originals.csv")}
    predictions=read_csv(OUT / "results/predictions.csv")
    plan=read_json(OUT / "generation_plan.json")
    groups=defaultdict(list); seen=set()
    for row in predictions:
        key=(row["model_key"],row["classifier"],row["feature_set"],row["condition"],row["passage_id"])
        if key in seen:
            raise ValueError("Repeated out-of-fold prediction")
        seen.add(key)
        original=originals[row["passage_id"]]
        if any(row[k]!=original[k] for k in ("author_id","work_id")) or row["fold"]!=original["outer_fold"]:
            raise ValueError("Prediction is assigned to the wrong source or fold")
        if row["predicted_author"] not in AUTHORS:
            raise ValueError("Unexpected predicted label")
        groups[key[:4]].append(row)
    expected_group_keys=set()
    for model in models:
        completion=read_json(OUT / f"generation/{model}/completion.json")
        if status["model_status"].get(model)!=completion:
            raise ValueError("Analysis uses different generation accounting/hashes")
        rewritten=read_csv(OUT / f"generation/{model}/rewrites.csv")
        expected_by_condition={"original":set(originals)}
        expected_by_condition.update({c:{r["passage_id"] for r in rewritten if r["condition"]==c and r["qc_status"]!="fail"} for c in plan["conditions"]})
        for name in CLASSIFIERS:
            for features in ["full"]+[f"without_{f}" for f in FAMILIES]:
                for condition,expected_ids in expected_by_condition.items():
                    key=(model,name,features,condition)
                    expected_group_keys.add(key)
                    if {r["passage_id"] for r in groups.get(key,[])}!=expected_ids:
                        raise ValueError("Prediction coverage differs from all eligible frozen pairs")
    if set(groups)!=expected_group_keys:
        raise ValueError("Unexpected model/classifier/feature/condition predictions")
    for row in read_csv(OUT / "results/metrics.csv"):
        rr=groups[(row["model_key"],row["classifier"],row["feature_set"],row["condition"])]
        rr=rr if row["fold"]=="pooled" else [r for r in rr if r["fold"]==row["fold"]]
        y,p=[r["author_id"] for r in rr],[r["predicted_author"] for r in rr]
        if len(rr)!=int(row["rows"]) or not np.isclose(float(row["macro_f1"]),f1_score(y,p,labels=AUTHORS,average="macro",zero_division=0),rtol=0,atol=1e-12) or not np.isclose(float(row["accuracy"]),accuracy_score(y,p),rtol=0,atol=1e-12):
            raise ValueError("Reported metric differs from retained predictions")
    for path in (OUT / "results/folds").glob("*.json"):
        fold=int(path.stem.rsplit("_",1)[1]); evidence=read_json(path)
        train,_=split_rows(list(originals.values()),fold)
        expected=[r["passage_id"] for r in train]
        if evidence["training_ids"]!=expected or evidence["sample_count"]!=240:
            raise ValueError("Preprocessing training-fold leakage/provenance mismatch")
        if evidence["training_text_hashes"]!=[r["text_sha256"] for r in train]:
            raise ValueError("Fitted training text hashes changed")
    comparisons=read_csv(OUT / "results/primary_comparisons.csv")
    expected_comparisons={(m,n,c) for m in models for n in CLASSIFIERS for c in plan["conditions"]}
    if len(comparisons)!=len(expected_comparisons) or {(r["model_key"],r["classifier"],r["condition"]) for r in comparisons}!=expected_comparisons:
        raise ValueError("Primary comparison family is incomplete/duplicated")
    adjusted=holm([float(r["p_work_swap_two_sided"]) for r in comparisons],family_size=18)
    for row,adjusted_p in zip(comparisons,adjusted):
        if not 0<float(row["p_work_swap_two_sided"])<=float(row["p_holm"])<=1:
            raise ValueError("Invalid permutation/multiplicity result")
        if int(row["work_blocks"])!=18:
            raise ValueError("A comparison is missing at least one work; inspect failed-output selection")
        rewritten=groups[(row["model_key"],row["classifier"],"full",row["condition"])]
        original={r["passage_id"]:r for r in groups[(row["model_key"],row["classifier"],"full","original")]}
        y=[r["author_id"] for r in rewritten]
        original_f1=f1_score(y,[original[r["passage_id"]]["predicted_author"] for r in rewritten],labels=AUTHORS,average="macro",zero_division=0)
        rewrite_f1=f1_score(y,[r["predicted_author"] for r in rewritten],labels=AUTHORS,average="macro",zero_division=0)
        if (int(row["paired_passages"])!=len(rewritten) or int(row["failed_outputs_excluded"])!=360-len(rewritten)
            or not np.allclose([float(row["original_macro_f1"]),float(row["rewrite_macro_f1"]),float(row["macro_f1_loss"]),float(row["p_holm"])],
                               [original_f1,rewrite_f1,original_f1-rewrite_f1,adjusted_p],rtol=0,atol=1e-12)):
            raise ValueError("Paired comparison/adjusted p-value differs from retained evidence")
    return {"passed":True,"comparisons":len(comparisons),"prediction_rows":len(predictions),"estimand":status["estimand"],
            "full_study_complete":bool(status.get("analysis_complete")),"models_included":models}


def published_archive_check():
    path=OUT / "archive/published_record.json"
    if not path.exists():
        return {"passed":False,"reason":"No published archival record and checksum evidence yet"}
    evidence=read_json(path)
    record_id=str(evidence["record_id"])
    if not record_id.isdigit():
        raise ValueError("Invalid archival record ID")
    # Only Zenodo's published-record endpoint, not draft/deposit/prereserved IDs.
    with urllib.request.urlopen(f"https://zenodo.org/api/records/{record_id}",timeout=30) as response:
        record=json.load(response)
    if str(record.get("id"))!=record_id or record.get("doi",record.get("metadata",{}).get("doi"))!=evidence["doi"]:
        raise ValueError("Actual published record DOI does not match evidence")
    archive=(ROOT / evidence["local_package"]).resolve()
    if not archive.is_relative_to((OUT / "archive").resolve()) or file_hash(archive)!=evidence["package_sha256"]:
        raise ValueError("Local archived package changed")
    md5="md5:"+hashlib.md5(archive.read_bytes(),usedforsecurity=False).hexdigest()
    if not any(f.get("key")==archive.name and f.get("checksum")==md5 for f in record.get("files",[])):
        raise ValueError("Published record does not contain this exact package")
    return {"passed":True,"doi":evidence["doi"],"record_url":f"https://zenodo.org/records/{record_id}"}


def evaluate(run_test_suite=False):
    checks={}
    def check(name,fn):
        try:
            checks[name]=fn()
        except Exception as exc:
            checks[name]={"passed":False,"reason":str(exc) if isinstance(exc,(ValueError,FileNotFoundError)) else type(exc).__name__}
    check("environment",check_environment)
    check("corpus",corpus_checks)
    for model in read_json(OUT / "generation_plan.json")["models"]:
        def generation_check(model=model):
            result=consolidate(model)
            return {"passed":result["accounting_complete"],"received":result["received"],"terminal_http_failures":result["terminal_http_failures"],"accounted":result["accounted"],"expected":result["expected"],"failed":result["fail"],"warning":result["warning"]}
        check(f"generation_{model}",generation_check)
    check("analysis",analysis_checks)
    def test_check():
        result=run_tests() if run_test_suite else read_json(OUT / "verification/tests.json")
        return {"passed":result["passed"] and result["code_fingerprint"]==code_fingerprint() and result["environment"]["passed"],
                "completed_utc":result["completed_utc"]}
    check("tests",test_check)
    def human_check():
        result=validate_annotations()
        return {"passed":result["complete"],"stage":result["stage"]}
    check("independent_human_reviews",human_check)
    from .source_review import validate as validate_source_review
    check("human_source_review",validate_source_review)
    def semantic_check():
        result=read_json(OUT / "results/semantic_sensitivity_status.json")
        valid=result["complete"] and result.get("predictions_sha256")==file_hash(OUT / "results/predictions.csv") and result.get("flags_sha256")==file_hash(OUT / "annotations/verified_flags.csv")
        return {"passed":valid}
    check("verified_semantic_sensitivity",semantic_check)
    check("published_archive",published_archive_check)
    computational=[k for k in checks if k not in {"independent_human_reviews","human_source_review","verified_semantic_sensitivity","published_archive"}]
    result={"checked_utc":datetime.now(timezone.utc).isoformat(),"checks":checks,
            "computational_work_complete":all(checks[k]["passed"] for k in computational),
            "ready_for_archive":all(v["passed"] for k,v in checks.items() if k!="published_archive"),
            "ready_for_writing":all(v["passed"] for v in checks.values()),
            "blockers":[k for k,v in checks.items() if not v["passed"]],
            "no_journal_acceptance_guarantee":True}
    write_json(OUT / "readiness.json",result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-tests",action="store_true")
    args=parser.parse_args()
    result=evaluate(args.run_tests)
    print(json.dumps(result,indent=2))
    if not result["ready_for_writing"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
