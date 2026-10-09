"""Prompt/output receipts for actual Codex-session rewrites; never synthetic API receipts."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .corpus import words
from .expanded_study import BASE, freeze_json, now, verify
from .generation import FIELDS, append_record
from .io import OUT, digest_text, file_hash, read_csv, read_json, read_jsonl, write_csv, write_json

MODEL = "astra_session"
FOLDER = BASE / "generation" / MODEL


def requests():
    from .expanded_generation import checked_requests
    return checked_requests(MODEL)


def next_batch(limit=3):
    if not 1 <= limit <= 12:
        raise ValueError("Use a bounded session batch of 1–12 actual rewrites")
    done = {r["request_id"] for r in read_jsonl(FOLDER / "session_outputs.jsonl")}
    pending = [r for r in requests() if r["request_id"] not in done][:limit]
    if not pending:
        return {"complete": True, "requests": []}
    bid = digest_text(":".join(r["request_id"] for r in pending))[:20]
    path = FOLDER / f"batches/{bid}.json"
    batch = {"batch_id": bid, "issued_utc": read_json(path)["issued_utc"] if path.exists() else now(),
             "provenance_sha256": file_hash(OUT / "expansion/session_arm_provenance.json"),
             "session_id": os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID"),
             "requests": pending}
    freeze_json(path, batch)
    # Print only the exact blinded generation payloads, not author/work identifiers.
    return {"batch_id": bid, "requests": [{"request_id": r["request_id"], **r["payload"]} for r in pending]}


def score(request, record):
    obj = json.loads(record["output_json_verbatim"])
    flags = []
    if set(obj) != {"request_id", "rewritten_text"}:
        flags.append("schema_mismatch")
    if obj.get("request_id") != request["request_id"]:
        flags.append("request_id_mismatch")
    text = obj.get("rewritten_text")
    if not isinstance(text, str):
        text = ""; flags.append("text_not_string")
    text = text.strip()
    if not text:
        flags.append("empty_text")
    if digest_text(text) == request["source_sha256"]:
        flags.append("identical_to_original")
    failed = bool(flags)
    ratio = words(text) / request["original_words"]
    if abs(ratio - 1) > .20:
        flags.append("length_deviation_over_20pct")
    elif abs(ratio - 1) > .15:
        flags.append("length_deviation_over_15pct")
    row = {f: "" for f in FIELDS}
    row.update({k: request[k] for k in ("request_id", "passage_id", "condition", "model_key", "requested_model", "source_sha256", "request_sha256", "original_words")})
    row.update(returned_model="", response_id="", received_utc=record["recorded_utc"], finish_reason="session_output_recorded",
               rewritten_text=text, rewrite_sha256=digest_text(text), rewrite_words=words(text), length_ratio=round(ratio, 8),
               qc_status="fail" if failed else "warning" if flags else "pass", qc_flags=";".join(flags),
               raw_record_sha256=digest_text(json.dumps(record, ensure_ascii=False, sort_keys=True)), outcome_type="codex_session_output",
               assignment_id=request["assignment_id"], delivery="codex_session")
    return row


def ingest(path, batch_id):
    batch_path = FOLDER / f"batches/{batch_id}.json"
    batch = read_json(batch_path)
    if batch["provenance_sha256"] != file_hash(OUT / "expansion/session_arm_provenance.json"):
        raise ValueError("Session provenance changed since these prompts were issued")
    current_session = os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
    if not batch["session_id"] or batch["session_id"] != current_session:
        raise ValueError("Session identity differs from prompt issuance")
    source_requests = {r["request_id"]: r for r in requests()}
    expected = {r["request_id"]: r for r in batch["requests"]}
    outputs = read_jsonl(Path(path))
    if len({r.get("request_id") for r in outputs}) != len(outputs) or set(r.get("request_id") for r in outputs) != set(expected):
        raise ValueError("Output batch must match every issued request exactly once")
    for rid, request in expected.items():
        if source_requests[rid] != request:
            raise ValueError("Issued session prompt changed")
    done = {r["request_id"] for r in read_jsonl(FOLDER / "session_outputs.jsonl")}
    if done.intersection(expected):
        raise ValueError("Session output already recorded; preserve the first output")
    for output in outputs:
        if set(output) != {"request_id", "rewritten_text"} or not isinstance(output["rewritten_text"], str):
            raise ValueError("Use the exact two-field output schema")
    # Preserve the actual submitted file, separately from parsed text/QC exports.
    original_path = FOLDER / f"batches/{batch_id}.outputs.jsonl"
    if original_path.exists():
        if original_path.read_bytes() != Path(path).read_bytes():
            raise ValueError("Original session output file already exists and differs")
    else:
        original_path.parent.mkdir(parents=True, exist_ok=True)
        with original_path.open("xb") as stream:
            stream.write(Path(path).read_bytes())
    lines = [line for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    for line in lines:
        output = json.loads(line)
        request = expected[output["request_id"]]
        record = {"request_id": request["request_id"], "request_sha256": request["request_sha256"],
                  "source_sha256": request["source_sha256"], "recorded_utc": now(), "session_id": current_session,
                  "batch_id": batch_id, "batch_sha256": file_hash(batch_path), "original_output_file_sha256": file_hash(original_path),
                  "output_json_verbatim": line, "output_json_sha256": digest_text(line),
                  "model_label": "GPT-6 Astra via Codex, Extra High", "verification_scope": "interface_model_selection",
                  "provenance_sha256": batch["provenance_sha256"], "provider_response_id": None, "token_usage": None,
                  "persistent_context": True, "quality_verified": False}
        append_record(FOLDER / "session_outputs.jsonl", record)
    return consolidate()


def consolidate():
    reqs = {r["request_id"]: r for r in requests()}
    rows, seen = [], set()
    for record in read_jsonl(FOLDER / "session_outputs.jsonl"):
        rid = record["request_id"]
        if rid not in reqs or rid in seen or reqs[rid]["request_sha256"] != record["request_sha256"]:
            raise ValueError("Session receipt does not match a unique frozen request")
        batch_path = FOLDER / f"batches/{record['batch_id']}.json"
        output_path = FOLDER / f"batches/{record['batch_id']}.outputs.jsonl"
        if file_hash(batch_path) != record["batch_sha256"] or file_hash(output_path) != record["original_output_file_sha256"] or digest_text(record["output_json_verbatim"]) != record["output_json_sha256"]:
            raise ValueError("Session transcript evidence changed")
        seen.add(rid); rows.append(score(reqs[rid], record))
    rows.sort(key=lambda r: r["assignment_id"])
    write_csv(FOLDER / "rewrites.csv", rows, FIELDS + ["assignment_id", "delivery"])
    result = {"model_key": MODEL, "expected": len(reqs), "accounted": len(rows), "missing": len(reqs) - len(rows),
              "valid_outputs": sum(r["qc_status"] in {"pass", "warning"} for r in rows), "fail": sum(r["qc_status"] == "fail" for r in rows),
              "accounting_complete": len(rows) == len(reqs), "review_complete": False,
              "api_comparison_eligible": False, "parsed_sha256": file_hash(FOLDER / "rewrites.csv")}
    write_json(FOLDER / "completion.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("next", "ingest", "consolidate"))
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--batch")
    args = parser.parse_args()
    result = next_batch(args.limit) if args.action == "next" else ingest(args.file, args.batch) if args.action == "ingest" else consolidate()
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
