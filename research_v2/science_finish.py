"""Bounded offline scientific finisher; never writes prose or calls a model API."""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

from .io import OUT, file_hash, read_json, write_json


def active_writers(plan):
    return [OUT / f"generation/{m}/RUNNING.lock" for m in plan["models"]
            if (OUT / f"generation/{m}/RUNNING.lock").exists()] + list((OUT / "extensions").rglob("RUNNING.lock"))


def finish(wait_minutes=100):
    plan = read_json(OUT / "generation_plan.json")
    deadline = time.monotonic() + wait_minutes * 60
    def progress(stage, **fields):
        value = {"stage": stage, "updated_utc": datetime.now(timezone.utc).isoformat(),
                 "manuscript_writing_paused": True, "submission_ready": False, **fields}
        write_json(OUT / "verification/research_watch_status.json", value)
        print(json.dumps(value), flush=True)
    progress("waiting_for_existing_writers")
    while active_writers(plan):
        if time.monotonic() >= deadline:
            progress("bounded_wait_expired")
            return 2
        time.sleep(15)
    # Import scientific modules after the wait so subsequent code fixes are used.
    from . import analysis, annotations, generation, legacy_audit, qc_report, release, source_review
    from . import shift_contraction, transfer_extension, transfer_verify
    from threadpoolctl import threadpool_limits
    completed = {m: generation.consolidate(m) for m in plan["models"]}
    if not all(s["accounting_complete"] for s in completed.values()):
        readiness = release.evaluate(run_test_suite=True)
        progress("incomplete_provider_outcomes", missing={m: s["missing"] for m, s in completed.items()},
                 blockers=readiness["blockers"], new_api_calls=0,
                 message="Native observations preserved. No partial model promoted to completed research.")
        return 2
    if not release.check_environment()["passed"]:
        raise ValueError("Exact scientific environment required")
    release.corpus_checks()
    if not legacy_audit.run()["consistent"]:
        raise ValueError("Historical QC reconciliation failed")
    source_review.prepare()
    qc_report.run()
    progress("both_providers_accounted_recomputing_frozen_v2")
    with threadpool_limits(limits=1):
        analysis.run()
    for model in plan["models"]:
        progress("running_exploratory_extensions", model_key=model)
        folder = transfer_extension.BASE / model
        manifest_path = folder / "manifest.json"
        current = manifest_path.exists() and read_json(manifest_path)["inputs"] == transfer_extension.fingerprints(model)
        if not current:
            transfer_extension.run(model)
        transfer_verify.replay_and_verify(model)
        shift_contraction.run(model)
        shift_contraction.replay_and_verify(model)
    annotation_status = annotations.prepare()
    readiness = release.evaluate(run_test_suite=True)
    progress("scientific_computation_complete" if readiness["computational_work_complete"] else "validation_incomplete",
             blockers=readiness["blockers"], annotation_stage=annotation_status["stage"],
             human_reviews_performed=False, new_api_calls=0, zenodo_published=False,
             note="No manuscript rebuild, hiring, upload, budget increase or submission was performed.")
    return 0 if readiness["computational_work_complete"] else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-minutes", type=float, default=100)
    args = parser.parse_args()
    try:
        code = finish(args.wait_minutes)
    except Exception as exc:
        write_json(OUT / "verification/research_watch_status.json",
                   {"stage": "failed_requires_inspection", "error_type": type(exc).__name__,
                    "updated_utc": datetime.now(timezone.utc).isoformat(),
                    "manuscript_writing_paused": True, "submission_ready": False})
        print(f"Scientific finisher stopped: {type(exc).__name__}; no completion asserted", flush=True)
        raise SystemExit(2) from None
    raise SystemExit(code)
