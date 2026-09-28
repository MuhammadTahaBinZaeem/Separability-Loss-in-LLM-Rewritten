"""Lossless visible failure text index; private HTTP bodies are never published blindly."""
from __future__ import annotations

import json

from .expanded_study import BASE, effective_plan, now
from .io import OUT, digest_text, file_hash, read_csv, read_jsonl, write_json, write_jsonl


def visible_segments(api, response):
    """Preserve provider-exposed refusal text as well as malformed/partial output prose."""
    segments = []
    if api == "azure_responses":
        for item in response.get("output", []):
            if item.get("type") != "message":
                continue
            for part in item.get("content", []):
                field = "refusal" if part.get("type") == "refusal" else "text" if part.get("type") == "output_text" else None
                if field and isinstance(part.get(field), str):
                    segments.append({"kind": field, "text": part[field]})
    elif api == "gemini_native":
        for i, candidate in enumerate(response.get("candidates", [])):
            for part in candidate.get("content", {}).get("parts", []):
                if not part.get("thought") and isinstance(part.get("text"), str):
                    segments.append({"kind": "text", "candidate_index": i, "text": part["text"]})
    return [{**r, "text_sha256": digest_text(r["text"])} for r in segments]


def build():
    plan = effective_plan()
    records = []
    for study, models in ((OUT, ("gem31lite", "azure_replication")), (BASE, plan["active_models"])):
        for model in models:
            if model == "astra_session":
                continue
            folder = study / "generation" / model
            # Do not take an inconsistent snapshot while append-only evidence is being written.
            if (folder / "RUNNING.lock").exists():
                continue
            requests = {r["request_id"]: r for r in read_jsonl(folder / "requests.jsonl")}
            if study == OUT:
                failed = {r["request_id"] for r in read_csv(folder / "rewrites.csv") if r["qc_status"] == "fail"}
                events = read_jsonl(folder / "raw_responses.jsonl")
                events += read_jsonl(folder / "transport_events.jsonl")
            else:
                failed = {r["request_id"] for r in read_csv(folder / "all_native_attempts.csv") if r["qc_status"] == "fail"} if (folder / "all_native_attempts.csv").exists() else set()
                events = read_jsonl(folder / "outcomes.jsonl")
            for event in events:
                rid = event.get("request_id")
                native = event.get("response")
                if native is not None and rid not in failed:
                    continue
                if rid not in requests:
                    continue
                segments = visible_segments(requests[rid]["api"], native) if native is not None else []
                records.append({"study": "v2" if study == OUT else "v3", "model_key": model, "request_id": rid,
                                "request_sha256": requests[rid]["request_sha256"], "attempt": event.get("attempt"),
                                "received_utc": event.get("received_utc", event.get("timestamp")),
                                "event_sha256": digest_text(json.dumps(event, ensure_ascii=False, sort_keys=True)),
                                "http_status": event.get("http_status"), "error_code": event.get("error_code"),
                                "visible_segments": segments, "has_native_response": native is not None,
                                "http_body_publicly_included": False,
                                "private_original_http_body_retained": bool(event.get("private_error_body") or event.get("private_raw_body")),
                                "historical_body_unavailable": study == OUT and native is None})
    path = BASE / "failures/visible_failure_index.jsonl"
    write_jsonl(path, records)
    result = {"built_utc": now(), "record_count": len(records), "sha256": file_hash(path),
              "active_models_omitted_until_stable": [m for m in plan["active_models"] if (BASE / f"generation/{m}/RUNNING.lock").exists()],
              "no_missing_failure_text_reconstructed": True, "private_HTTP_bodies_require_secret_review_before_any_release": True}
    write_json(BASE / "failures/visible_failure_index_status.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
