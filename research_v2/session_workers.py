"""Serialized dispatch for explicitly authorized Codex Astra rewrite workers.

No provider is called here. Agents must write their actual outputs themselves.
The original session receipt format and all previously recorded outputs stay intact.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sqlite3

from . import session_generation as session
from .expanded_study import BASE, freeze_json, now
from .io import OUT, digest_text, file_hash, read_json, read_jsonl

AMENDMENT = BASE / "astra_delegation_amendment.json"


@contextmanager
def dispatch_lock():
    path = BASE / "private/astra_dispatch.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=120)
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def authorize():
    existing = read_json(AMENDMENT) if AMENDMENT.exists() else None
    data = {
        "recorded_utc": existing["recorded_utc"] if existing else now(),
        "user_authorization": "continue n ys u can use subagents for astra rewrites",
        "selected_model": "gpt-6-astra", "reasoning_effort": "xhigh",
        "delivery": "Codex collaboration subagents; no Astra API requests",
        "verification_scope": "interface/orchestrator model selection, not backend checkpoint attestation",
        "original_provenance_sha256": file_hash(OUT / "expansion/session_arm_provenance.json"),
        "existing_outputs_at_amendment": existing["existing_outputs_at_amendment"] if existing else len(read_jsonl(session.FOLDER / "session_outputs.jsonl")),
        "batch_size": 3,
        "assignment_rule": "Next unrecorded, unreserved frozen assignment in existing request order; no condition-specialist workers",
        "context": "Fresh worker conversation per spawn, then persistent within worker; inherited system/tool scaffolding, no study history fork",
        "comparison_status": "Separate exploratory workflow arm; do not pool as controlled API condition",
        "first_output_preserved": True, "independent_review_completed": False,
    }
    freeze_json(AMENDMENT, data)
    return data


def worker_identity(worker):
    if not re.fullmatch(r"astra_[a-z0-9_]{1,48}", worker):
        raise ValueError("Invalid worker identifier")
    amendment = read_json(AMENDMENT)
    if amendment["selected_model"] != "gpt-6-astra":
        raise ValueError("Unexpected model selection")
    sid = os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
    if not sid:
        raise ValueError("An actual Codex session identifier is required")
    path = session.FOLDER / f"workers/{worker}.json"
    old = read_json(path) if path.exists() else None
    identity = {"worker_id": worker, "session_id": sid,
                "registered_utc": old["registered_utc"] if old else now(),
                "delegation_sha256": file_hash(AMENDMENT),
                "selected_model": amendment["selected_model"],
                "reasoning_effort": amendment["reasoning_effort"]}
    freeze_json(path, identity)
    return identity


def issue(worker):
    with dispatch_lock():
        identity = worker_identity(worker)
        done = {r["request_id"] for r in read_jsonl(session.FOLDER / "session_outputs.jsonl")}
        released = {r["batch_id"] for r in read_jsonl(session.FOLDER / "released_batches.jsonl")}
        batches = [read_json(p) for p in sorted((session.FOLDER / "batches").glob("*.json")) if p.stem not in released]
        pending = [b for b in batches if b.get("worker_id") == worker and any(r["request_id"] not in done for r in b["requests"])]
        if len(pending) > 1:
            raise ValueError("Worker has conflicting pending batches")
        if pending:
            batch = pending[0]
            if any(r["request_id"] in done for r in batch["requests"]):
                raise ValueError("Partially ingested batch requires explicit recovery")
        else:
            reserved = {r["request_id"] for b in batches for r in b["requests"]}
            selected = [r for r in session.requests() if r["request_id"] not in done | reserved][:3]
            if not selected:
                return {"no_unreserved_assignments": True, "recorded": len(done)}
            bid = digest_text(worker + ":" + ":".join(r["request_id"] for r in selected))[:20]
            batch = {"batch_id": bid, "issued_utc": now(), "session_id": identity["session_id"],
                     "provenance_sha256": file_hash(OUT / "expansion/session_arm_provenance.json"),
                     "worker_id": worker, "worker_identity_sha256": file_hash(session.FOLDER / f"workers/{worker}.json"),
                     "delegation_sha256": file_hash(AMENDMENT), "requests": selected}
            freeze_json(session.FOLDER / f"batches/{bid}.json", batch)
        return {"batch_id": batch["batch_id"], "worker_id": worker,
                "requests": [{"request_id": r["request_id"], **r["payload"]} for r in batch["requests"]]}


def ingest(worker, batch_id, path):
    with dispatch_lock():
        if batch_id in {r["batch_id"] for r in read_jsonl(session.FOLDER / "released_batches.jsonl")}:
            raise ValueError("This unused reservation was released; it cannot receive an output")
        identity = worker_identity(worker)
        batch = read_json(session.FOLDER / f"batches/{batch_id}.json")
        if batch.get("worker_id") != worker or batch["session_id"] != identity["session_id"]:
            raise ValueError("Output belongs to another worker")
        if batch["delegation_sha256"] != file_hash(AMENDMENT) or batch["worker_identity_sha256"] != file_hash(session.FOLDER / f"workers/{worker}.json"):
            raise ValueError("Worker provenance changed")
        return session.ingest(path, batch_id)


def release_unused(batch_id, reason):
    """Keep the issued batch but release a stopped worker's unproduced assignments."""
    if not reason or len(reason.strip()) < 15:
        raise ValueError("Record the actual reason and stopped-worker evidence")
    with dispatch_lock():
        released = read_jsonl(session.FOLDER / "released_batches.jsonl")
        if batch_id in {r["batch_id"] for r in released}:
            return {"already_released": True, "batch_id": batch_id}
        path = session.FOLDER / f"batches/{batch_id}.json"
        batch = read_json(path)
        if not batch.get("worker_id"):
            raise ValueError("Only delegated unused reservations may be released")
        if (session.FOLDER / f"submissions/{batch_id}.jsonl").exists() or (session.FOLDER / f"batches/{batch_id}.outputs.jsonl").exists():
            raise ValueError("Existing output evidence requires recovery, not release")
        done = {r["request_id"] for r in read_jsonl(session.FOLDER / "session_outputs.jsonl")}
        if done.intersection(r["request_id"] for r in batch["requests"]):
            raise ValueError("An output is already recorded")
        record = {"batch_id": batch_id, "worker_id": batch["worker_id"], "recorded_utc": now(),
                  "batch_sha256": file_hash(path), "reason": reason,
                  "request_ids": [r["request_id"] for r in batch["requests"]],
                  "produced_output_available": False, "original_batch_preserved": True}
        from .generation import append_record
        append_record(session.FOLDER / "released_batches.jsonl", record)
        return record


def audit():
    """Check receipt links without treating interface selection as backend proof."""
    with dispatch_lock():
        records = read_jsonl(session.FOLDER / "session_outputs.jsonl")
        reqs = {r["request_id"]: r for r in session.requests()}
        launch_path = session.FOLDER / "delegation_launches.json"
        extra_launches = session.FOLDER / "delegation_additional_launches.jsonl"
        launch_rows = read_json(launch_path)["launches"] + read_jsonl(extra_launches)
        launches = {r["worker_id"]: r for r in launch_rows}
        if len(launches) != len(launch_rows):
            raise ValueError("Conflicting worker launch identities")
        seen, counts, evidence = set(), {}, {str(AMENDMENT.relative_to(BASE)): file_hash(AMENDMENT),
                                           str(launch_path.relative_to(BASE)): file_hash(launch_path)}
        if extra_launches.exists():
            evidence[str(extra_launches.relative_to(BASE))] = file_hash(extra_launches)
        released_path = session.FOLDER / "released_batches.jsonl"
        released = read_jsonl(released_path)
        if released_path.exists():
            evidence[str(released_path.relative_to(BASE))] = file_hash(released_path)
        for release in released:
            path = session.FOLDER / f"batches/{release['batch_id']}.json"
            if file_hash(path) != release["batch_sha256"] or any(r["batch_id"] == release["batch_id"] for r in records):
                raise ValueError("Released reservation history conflicts with actual outputs")
            evidence[str(path.relative_to(BASE))] = file_hash(path)
        for record in records:
            rid = record["request_id"]
            if rid not in reqs or rid in seen:
                raise ValueError("Unknown or duplicate session receipt")
            seen.add(rid)
            batch_path = session.FOLDER / f"batches/{record['batch_id']}.json"
            batch = read_json(batch_path)
            if file_hash(batch_path) != record["batch_sha256"]:
                raise ValueError("Issued batch changed")
            issued = {r["request_id"]: r for r in batch["requests"]}
            if issued.get(rid) != reqs[rid] or record["session_id"] != batch["session_id"]:
                raise ValueError("Receipt/session does not match its exact issued request")
            if record["source_sha256"] != reqs[rid]["source_sha256"] or record["request_sha256"] != reqs[rid]["request_sha256"]:
                raise ValueError("Source or request receipt mismatch")
            if record["provider_response_id"] is not None or record["token_usage"] is not None:
                raise ValueError("A session output cannot invent API metadata")
            worker = batch.get("worker_id", "original_main_session")
            if worker != "original_main_session":
                launch = launches.get(worker)
                if not launch or launch["model"] != "gpt-6-astra" or launch["reasoning_effort"] != "xhigh":
                    raise ValueError("No matching requested Astra launch")
                worker_path = session.FOLDER / f"workers/{worker}.json"
                identity = read_json(worker_path)
                if file_hash(worker_path) != batch["worker_identity_sha256"] or identity["session_id"] != batch["session_id"]:
                    raise ValueError("Worker identity evidence changed")
                if batch["delegation_sha256"] != file_hash(AMENDMENT) or identity["delegation_sha256"] != file_hash(AMENDMENT):
                    raise ValueError("Delegation evidence changed")
                evidence[str(worker_path.relative_to(BASE))] = file_hash(worker_path)
            counts[worker] = counts.get(worker, 0) + 1
            output_path = session.FOLDER / f"batches/{record['batch_id']}.outputs.jsonl"
            if file_hash(output_path) != record["original_output_file_sha256"]:
                raise ValueError("Original output submission changed")
            if digest_text(record["output_json_verbatim"]) != record["output_json_sha256"]:
                raise ValueError("Verbatim output changed")
            if record["output_json_verbatim"] not in output_path.read_text(encoding="utf-8").splitlines():
                raise ValueError("Receipt is not present in the preserved original submission")
            for path in (batch_path, output_path):
                evidence[str(path.relative_to(BASE))] = file_hash(path)
        return {"passed": True, "recorded": len(records), "expected": len(reqs),
                "accounting_complete": len(records) == len(reqs), "worker_counts": counts,
                "verification_scope": "recorded prompt/output and requested orchestration identity",
                "quality_verified": False, "evidence_sha256": evidence}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("authorize", "next", "ingest", "audit", "release"))
    parser.add_argument("--worker")
    parser.add_argument("--batch")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--reason")
    args = parser.parse_args()
    if args.action in {"next", "ingest"} and not args.worker:
        parser.error("A worker identifier is required")
    if args.action == "ingest" and not (args.batch and args.file):
        parser.error("The original submission file and issued batch are required")
    result = (authorize() if args.action == "authorize" else audit() if args.action == "audit" else
              release_unused(args.batch, args.reason) if args.action == "release" else
              issue(args.worker) if args.action == "next" else ingest(args.worker, args.batch, args.file))
    if args.action == "audit":
        result = {k: v for k, v in result.items() if k != "evidence_sha256"}
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
