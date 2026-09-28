"""Finish offline computation once the existing generation writers stop; no API retries."""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime,timezone
from pathlib import Path

from .io import OUT,read_json,write_json


def finish(wait_minutes=190,env_file=None):
    watch=OUT / "verification/watch_status.json"
    plan=read_json(OUT / "generation_plan.json")
    deadline=time.monotonic()+wait_minutes*60
    def progress(stage,**fields):
        report={"stage":stage,"updated_utc":datetime.now(timezone.utc).isoformat(),**fields}
        write_json(watch,report)
        print(json.dumps(report),flush=True)
    progress("waiting_for_existing_generation_writers")
    while any((OUT / f"generation/{m}/RUNNING.lock").exists() for m in plan["models"]):
        if time.monotonic()>=deadline:
            progress("wait_deadline_reached",message="A writer lock remains; no lock removed and no results promoted")
            return 2
        time.sleep(15)
    progress("generation_writers_stopped")
    # Load the final analysis code only after the long wait, not a stale in-memory
    # version from when the watcher was started.
    from . import annotations,archive,generation,paper_assets,qc_report,release,reproduce
    completed={m:generation.consolidate(m) for m in plan["models"]}
    if not all(r["accounting_complete"] for r in completed.values()):
        result=reproduce.run(allow_partial=True)
        candidate=archive.build(env_file)
        progress("blocked_missing_provider_outcomes",missing={m:r["missing"] for m,r in completed.items()},
                 blockers=result["blockers"],review_package=candidate["local_package"])
        return 2
    progress("offline_reproduction_running")
    result=reproduce.run()
    candidate=archive.build(env_file)
    progress("computational_work_complete" if result["completed"] else "computational_validation_failed",
             blockers=result["blockers"],review_package=candidate["local_package"],
             human_recruitment_not_started=True,zenodo_not_published=True)
    return 0 if result["completed"] else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-minutes",type=float,default=190)
    parser.add_argument("--env-file",type=Path)
    args=parser.parse_args()
    try:
        code=finish(args.wait_minutes,args.env_file)
    except Exception as exc:
        # Avoid potentially account-bearing exception details in unattended logs.
        write_json(OUT / "verification/watch_status.json",{"stage":"failed","error_type":type(exc).__name__,
                   "updated_utc":datetime.now(timezone.utc).isoformat(),"requires_inspection":True})
        print(f"Offline finisher failed: {type(exc).__name__}; no completion asserted",flush=True)
        raise SystemExit(2) from None
    raise SystemExit(code)


if __name__=="__main__":
    main()
