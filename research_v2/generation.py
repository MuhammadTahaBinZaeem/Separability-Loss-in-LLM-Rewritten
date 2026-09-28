"""Frozen requests, resumable provider calls and recomputed QC without outcome selection."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from .corpus import words
from .providers import make_payload, response_view
from .io import OUT, digest_text, file_hash, read_csv, read_json, read_jsonl, write_csv, write_json, write_jsonl

SYSTEM = """You are performing a controlled rewrite of a fiction passage.
Preserve the same meaning, events, characters, objects, speaker relationships,
and narrative sequence. Do not add or omit material facts. Do not summarize.
Keep the rewritten passage within approximately 15 percent of the original
word count. Preserve paragraph structure where reasonably possible.
Return only a JSON object with exactly two keys: request_id and rewritten_text.
The rewritten_text value must contain only prose, without headings or commentary.
Do not identify the source author, title, archive, or experiment.
"""
INSTRUCTIONS = {
    "paraphrase": "Make a light paraphrase. Change wording and local phrasing without making modernization or simplification the main goal.",
    "modernize": "Rewrite in contemporary English. Update archaic phrasing while preserving seriousness, emotion, and narrative situation. Do not simplify more than necessary.",
    "simplify": "Make the passage easier for a general modern reader. Simplify difficult wording and sentence structures. Preserve the narrative and tone; do not use bullet points or make it childish.",
}
FIELDS = ["request_id", "passage_id", "condition", "model_key", "requested_model", "returned_model",
          "source_sha256", "request_sha256", "response_id", "received_utc", "finish_reason",
          "rewritten_text", "rewrite_sha256", "original_words", "rewrite_words", "length_ratio",
          "qc_status", "qc_flags", "raw_record_sha256", "outcome_type"]


def verify_corpus() -> dict:
    freeze = read_json(OUT / "corpus/freeze.json")
    if file_hash(OUT / "corpus/originals.csv") != freeze["originals_file_sha256"]:
        raise ValueError("Frozen corpus hash mismatch")
    return freeze


def prepare() -> None:
    freeze = verify_corpus()
    originals = read_csv(OUT / "corpus/originals.csv")
    plan = read_json(OUT / "generation_plan.json")
    for key, config in plan["models"].items():
        if not config.get("enabled",True):
            print(f"Not prepared: {key}; provider/deployment still pending",flush=True)
            continue
        requests = []
        for row in originals:
            for condition in plan["conditions"]:
                opaque = digest_text(f"{freeze['corpus_sha256']}:{row['passage_id']}:{condition}")[:24]
                user = f"{INSTRUCTIONS[condition]}\n\nrequest_id: {opaque}\noriginal_word_count: {words(row['text'])}\n\nPassage:\n{row['text']}"
                payload = make_payload(config,plan,SYSTEM,user)
                serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                requests.append({"request_id": opaque, "passage_id": row["passage_id"], "condition": condition,
                                 "source_sha256": row["text_sha256"], "original_words": words(row["text"]),
                                 "model_key": key, "payload": payload, "request_sha256": digest_text(serialized),
                                 "requested_model":config["model"],"api":config.get("api","groq_chat"),
                                 "accepted_returned_models":config.get("accepted_returned_models",[config["model"]])})
        # Interleave authors/conditions deterministically to avoid a partial run covering only one author.
        requests.sort(key=lambda r: digest_text(f"20260915:{r['request_id']}"))
        path = OUT / f"generation/{key}/requests.jsonl"
        if path.exists() and read_jsonl(path) != requests:
            raise ValueError(f"Refusing to change frozen generation requests for {key}")
        if not path.exists():
            write_jsonl(path, requests)
        manifest={"model_key": key, "model": config["model"],
                   "request_count": len(requests), "requests_sha256": file_hash(path),
                   "corpus_sha256": freeze["corpus_sha256"], "plan_sha256_at_freeze": file_hash(OUT / "generation_plan.json"),
                   "model_config_sha256":digest_text(json.dumps(config,sort_keys=True))}
        manifest_path=path.with_name("request_manifest.json")
        if manifest_path.exists():
            previous=read_json(manifest_path)
            if any(previous.get(k)!=v for k,v in manifest.items() if k!="plan_sha256_at_freeze"):
                raise ValueError(f"Frozen request provenance changed for {key}")
        else:
            write_json(manifest_path,manifest)
        print(f"Prepared {len(requests)} frozen requests for {key}", flush=True)


def parse_response(request: dict, record: dict) -> dict:
    response = record["response"]
    view=response_view(request,response)
    content=view["content"]
    requested_model=request.get("requested_model",request["payload"].get("model",""))
    flags, rewritten = [], ""
    try:
        obj = json.loads(content)
        if not isinstance(obj, dict) or set(obj) != {"request_id", "rewritten_text"}:
            flags.append("schema_mismatch")
        else:
            if obj["request_id"] != request["request_id"]:
                flags.append("request_id_mismatch")
            if not isinstance(obj["rewritten_text"], str):
                flags.append("text_not_string")
            else:
                rewritten = obj["rewritten_text"].strip()
    except (json.JSONDecodeError, TypeError):
        flags.append("invalid_json")
    if not rewritten:
        flags.append("empty_text")
    if view["finish_reason"] != "stop":
        flags.append("incomplete_generation")
    if view["model"] not in request.get("accepted_returned_models",[requested_model]):
        flags.append("returned_model_mismatch")
    if digest_text(rewritten) == request["source_sha256"]:
        flags.append("identical_to_original")
    failures = bool(flags)
    ratio = words(rewritten) / request["original_words"]
    if abs(ratio - 1) > .20:
        flags.append("length_deviation_over_20pct")
    elif abs(ratio - 1) > .15:
        flags.append("length_deviation_over_15pct")
    return {"request_id": request["request_id"], "passage_id": request["passage_id"],
            "condition": request["condition"], "model_key": request["model_key"],
            "requested_model": requested_model, "returned_model": view["model"],
            "source_sha256": request["source_sha256"], "request_sha256": request["request_sha256"],
            "response_id": view["id"], "received_utc": record["received_utc"],
            "finish_reason": view["native_finish_reason"], "rewritten_text": rewritten,
            "rewrite_sha256": digest_text(rewritten), "original_words": request["original_words"],
            "rewrite_words": words(rewritten), "length_ratio": round(ratio, 8),
            "qc_status": "fail" if failures else ("warning" if flags else "pass"),
            "qc_flags": ";".join(flags),
            "raw_record_sha256": digest_text(json.dumps(record, ensure_ascii=False, sort_keys=True)),
            "outcome_type":"native_response"}


def terminal_from_event(request: dict, event: dict) -> dict:
    """Record an actual HTTP refusal, not a synthetic model response."""
    if event.get("http_status")!=400 or event.get("error_code")!="content_filter" or event.get("request_id")!=request["request_id"]:
        raise ValueError("Only a matching recorded HTTP content-filter refusal is terminal")
    return {"request_id":request["request_id"],"request_sha256":request["request_sha256"],
            "received_utc":event["timestamp"],"outcome_type":"http_content_filter",
            "http_status":400,"error_code":"content_filter",
            "transport_event_sha256":digest_text(json.dumps(event,ensure_ascii=False,sort_keys=True))}


def parse_terminal(request: dict, record: dict) -> dict:
    if record.get("outcome_type")!="http_content_filter" or record.get("http_status")!=400 or record.get("error_code")!="content_filter":
        raise ValueError("Unsupported terminal outcome")
    return {"request_id":request["request_id"],"passage_id":request["passage_id"],
            "condition":request["condition"],"model_key":request["model_key"],
            "requested_model":request["requested_model"],"returned_model":"",
            "source_sha256":request["source_sha256"],"request_sha256":request["request_sha256"],
            "response_id":"","received_utc":record["received_utc"],"finish_reason":"http_content_filter",
            "rewritten_text":"","rewrite_sha256":"","original_words":request["original_words"],
            "rewrite_words":0,"length_ratio":"","qc_status":"fail","qc_flags":"provider_content_filter",
            "raw_record_sha256":digest_text(json.dumps(record,ensure_ascii=False,sort_keys=True)),
            "outcome_type":"http_content_filter"}


def recover_terminal_events(key: str) -> None:
    """Recover recorded refusals after an interrupted/older runner without resending."""
    folder=OUT / f"generation/{key}"
    requests={r["request_id"]:r for r in read_jsonl(folder / "requests.jsonl")}
    done={r["request_id"] for name in ("raw_responses.jsonl","terminal_outcomes.jsonl") for r in read_jsonl(folder / name)}
    for event in read_jsonl(folder / "transport_events.jsonl"):
        rid=event.get("request_id")
        if rid not in done and event.get("http_status")==400 and event.get("error_code")=="content_filter":
            if rid not in requests:
                raise ValueError("Terminal event refers to an unknown request")
            append_record(folder / "terminal_outcomes.jsonl",terminal_from_event(requests[rid],event))
            done.add(rid)


def consolidate(key: str) -> dict:
    verify_corpus()
    folder = OUT / f"generation/{key}"
    requests = read_jsonl(folder / "requests.jsonl")
    if file_hash(folder / "requests.jsonl") != read_json(folder / "request_manifest.json")["requests_sha256"]:
        raise ValueError("Request manifest hash mismatch")
    by_id = {r["request_id"]: r for r in requests}
    if not requests or len(by_id)!=len(requests):
        raise ValueError("Missing/duplicate frozen generation requests")
    raw = read_jsonl(folder / "raw_responses.jsonl")
    terminal=read_jsonl(folder / "terminal_outcomes.jsonl")
    seen, response_ids, parsed = set(), set(), []
    for record in raw:
        rid = record["request_id"]
        if rid in seen or rid not in by_id:
            raise ValueError("Duplicate or unexpected raw response request")
        if record["request_sha256"] != by_id[rid]["request_sha256"]:
            raise ValueError("Request-response provenance mismatch")
        if json.loads(record["response_body"]) != record["response"]:
            raise ValueError("Parsed response differs from retained provider body")
        serialized = json.dumps(by_id[rid]["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if digest_text(serialized) != by_id[rid]["request_sha256"]:
            raise ValueError("Retained request payload hash mismatch")
        response_id = response_view(by_id[rid],record["response"])["id"]
        if not response_id or response_id in response_ids:
            raise ValueError("Missing/duplicate provider response ID")
        seen.add(rid); response_ids.add(response_id)
        parsed.append(parse_response(by_id[rid], record))
    events={digest_text(json.dumps(e,ensure_ascii=False,sort_keys=True)):e for e in read_jsonl(folder / "transport_events.jsonl")}
    for record in terminal:
        rid=record["request_id"]
        if rid in seen or rid not in by_id or record["request_sha256"]!=by_id[rid]["request_sha256"]:
            raise ValueError("Duplicate, unexpected or mismatched terminal outcome")
        event=events.get(record.get("transport_event_sha256"))
        if event is None or terminal_from_event(by_id[rid],event)!=record:
            raise ValueError("Terminal outcome is not supported by its retained transport event")
        seen.add(rid)
        parsed.append(parse_terminal(by_id[rid],record))
    parsed.sort(key=lambda r: r["request_id"])
    write_csv(folder / "rewrites.csv", parsed, FIELDS)
    counts = Counter(r["qc_status"] for r in parsed)
    manifest = {"model_key": key, "expected": len(requests), "received": len(raw),
                "terminal_http_failures":len(terminal),"accounted":len(seen),
                "missing": len(requests) - len(seen), "pass": counts["pass"], "warning": counts["warning"],
                "fail": counts["fail"], "complete": len(raw) == len(requests) and counts["fail"] == 0,
                "responses_complete":len(raw)==len(requests),"valid_outputs":counts["pass"]+counts["warning"],
                "accounting_complete":len(seen)==len(requests),
                "request_manifest_sha256": file_hash(folder / "request_manifest.json"),
                "parsed_sha256": file_hash(folder / "rewrites.csv"),
                "raw_sha256": file_hash(folder / "raw_responses.jsonl") if raw else "",
                "terminal_sha256":file_hash(folder / "terminal_outcomes.jsonl") if terminal else "",
                "qc_version": "v2.1", "qc_rules": "research_v2/generation.py:parse_response,parse_terminal"}
    write_json(folder / "completion.json", manifest)
    return manifest


def append_record(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def run(key: str, limit: int, minutes: float, env_file: Path | None=None, pause: float=0.0) -> None:
    raise SystemExit("Use research_v2.parallel_generation --workers 1 (or up to 4); the legacy serial runner is retired")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run", "consolidate"])
    parser.add_argument("--model")
    parser.add_argument("--limit", type=int, default=0, help="0 means all remaining requests")
    parser.add_argument("--minutes", type=float, default=290)
    parser.add_argument("--env-file",type=Path)
    parser.add_argument("--pause",type=float,default=0.0)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif not args.model:
        parser.error("--model is required")
    elif args.action == "run":
        run(args.model, args.limit, args.minutes,args.env_file,args.pause)
    else:
        print(json.dumps(consolidate(args.model), indent=2))


if __name__ == "__main__":
    main()
