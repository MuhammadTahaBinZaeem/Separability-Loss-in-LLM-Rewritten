"""Rebuild the study offline from archived sources/responses; never calls a model API."""
from __future__ import annotations

import argparse
import json
from threadpoolctl import threadpool_limits

from . import analysis,annotations,corpus,legacy_audit,qc_report,release
from .io import OUT,read_json,write_json


def run(rebuild_corpus: bool=True, allow_partial: bool=False) -> dict:
    plan=read_json(OUT / "generation_plan.json")
    if any((OUT / f"generation/{m}/RUNNING.lock").exists() for m in plan["models"]):
        raise ValueError("Generation is active; wait for checkpoint writers to finish before rebuilding")
    environment=release.check_environment()
    if not environment["passed"]:
        raise ValueError("Install the exact hashed dependency lock with Python 3.12.11")
    if rebuild_corpus:
        corpus.build()
    release.corpus_checks()
    from .source_review import prepare as prepare_source_review
    prepare_source_review()
    historical=legacy_audit.run()
    if not historical["consistent"]:
        raise ValueError("Historical QC reconciliation failed")
    qc=qc_report.run()
    if not qc["accounting_complete"] and not allow_partial:
        result={"completed":False,"stage":"missing_generation_outcomes","qc":qc,
                "message":"Offline reproduction cannot obtain missing API responses; no partial results promoted to final."}
        write_json(OUT / "verification/reproduction.json",result)
        return result
    with threadpool_limits(limits=1):
        analysis.run()
    annotation_status=annotations.prepare()
    readiness=release.evaluate(run_test_suite=True)
    from .paper_assets import run as build_paper
    paper_status=build_paper()
    result={"completed":readiness["computational_work_complete"],"stage":"computational_work_complete" if readiness["computational_work_complete"] else "incomplete",
            "ready_for_submission":False,"annotation_stage":annotation_status["stage"],
            "blockers":readiness["blockers"],"paper":paper_status}
    write_json(OUT / "verification/reproduction.json",result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-corpus-rebuild",action="store_true")
    parser.add_argument("--allow-partial",action="store_true",help="Diagnostic only; never makes an incomplete study ready")
    args=parser.parse_args()
    result=run(not args.skip_corpus_rebuild,args.allow_partial)
    print(json.dumps(result,indent=2))
    if not result["completed"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
