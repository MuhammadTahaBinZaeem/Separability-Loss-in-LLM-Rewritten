"""Frozen requests, resumable provider calls and recomputed QC without outcome selection."""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .corpus import words
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
          "qc_status", "qc_flags", "raw_record_sha256"]


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
        requests = []
        for row in originals:
            for condition in plan["conditions"]:
                opaque = digest_text(f"{freeze['corpus_sha256']}:{row['passage_id']}:{condition}")[:24]
                user = f"{INSTRUCTIONS[condition]}\n\nrequest_id: {opaque}\noriginal_word_count: {words(row['text'])}\n\nPassage:\n{row['text']}"
                payload = {"model": config["model"], "messages": [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": user}], "temperature": plan["temperature"],
                           "top_p": plan["top_p"], "max_completion_tokens": plan["max_completion_tokens"],
                           "response_format": {"type": "json_object"}}
                for option in ("reasoning_effort", "reasoning_format"):
                    if option in config:
                        payload[option] = config[option]
                serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                requests.append({"request_id": opaque, "passage_id": row["passage_id"], "condition": condition,
                                 "source_sha256": row["text_sha256"], "original_words": words(row["text"]),
                                 "model_key": key, "payload": payload, "request_sha256": digest_text(serialized)})
        # Interleave authors/conditions deterministically to avoid a partial run covering only one author.
        requests.sort(key=lambda r: digest_text(f"20260915:{r['request_id']}"))
        path = OUT / f"generation/{key}/requests.jsonl"
        if path.exists() and read_jsonl(path) != requests:
            raise ValueError(f"Refusing to change frozen generation requests for {key}")
        write_jsonl(path, requests)
        write_json(path.with_name("request_manifest.json"), {"model_key": key, "model": config["model"],
                   "request_count": len(requests), "requests_sha256": file_hash(path),
                   "corpus_sha256": freeze["corpus_sha256"], "plan_sha256": file_hash(OUT / "generation_plan.json")})
        print(f"Prepared {len(requests)} frozen requests for {key}", flush=True)


def parse_response(request: dict, record: dict) -> dict:
    response = record["response"]
    choice = (response.get("choices") or [{}])[0]
    content = choice.get("message", {}).get("content") or ""
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
    if choice.get("finish_reason") != "stop":
        flags.append("incomplete_generation")
    if response.get("model") != request["payload"]["model"]:
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
            "requested_model": request["payload"]["model"], "returned_model": response.get("model", ""),
            "source_sha256": request["source_sha256"], "request_sha256": request["request_sha256"],
            "response_id": response.get("id", ""), "received_utc": record["received_utc"],
            "finish_reason": choice.get("finish_reason", ""), "rewritten_text": rewritten,
            "rewrite_sha256": digest_text(rewritten), "original_words": request["original_words"],
            "rewrite_words": words(rewritten), "length_ratio": round(ratio, 8),
            "qc_status": "fail" if failures else ("warning" if flags else "pass"),
            "qc_flags": ";".join(flags),
            "raw_record_sha256": digest_text(json.dumps(record, ensure_ascii=False, sort_keys=True))}


def consolidate(key: str) -> dict:
    verify_corpus()
    folder = OUT / f"generation/{key}"
    requests = read_jsonl(folder / "requests.jsonl")
    if file_hash(folder / "requests.jsonl") != read_json(folder / "request_manifest.json")["requests_sha256"]:
        raise ValueError("Request manifest hash mismatch")
    by_id = {r["request_id"]: r for r in requests}
    raw = read_jsonl(folder / "raw_responses.jsonl")
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
        response_id = record["response"].get("id")
        if not response_id or response_id in response_ids:
            raise ValueError("Missing/duplicate provider response ID")
        seen.add(rid); response_ids.add(response_id)
        parsed.append(parse_response(by_id[rid], record))
    parsed.sort(key=lambda r: r["request_id"])
    write_csv(folder / "rewrites.csv", parsed, FIELDS)
    counts = Counter(r["qc_status"] for r in parsed)
    manifest = {"model_key": key, "expected": len(requests), "received": len(raw),
                "missing": len(requests) - len(raw), "pass": counts["pass"], "warning": counts["warning"],
                "fail": counts["fail"], "complete": len(raw) == len(requests) and counts["fail"] == 0,
                "request_manifest_sha256": file_hash(folder / "request_manifest.json"),
                "parsed_sha256": file_hash(folder / "rewrites.csv"),
                "raw_sha256": file_hash(folder / "raw_responses.jsonl") if raw else "",
                "qc_version": "v2.0", "qc_rules": "research_v2/generation.py:parse_response"}
    write_json(folder / "completion.json", manifest)
    return manifest


def append_record(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def run(key: str, limit: int, minutes: float) -> None:
    prepare()
    config = read_json(OUT / "generation_plan.json")["models"][key]
    api_key = os.environ.get(config["key_env"], "")
    if not api_key:
        raise SystemExit(f"Missing environment variable {config['key_env']}; no API call made")
    folder = OUT / f"generation/{key}"
    requests = read_jsonl(folder / "requests.jsonl")
    consolidate(key)
    done = {r["request_id"] for r in read_jsonl(folder / "raw_responses.jsonl")}
    pending = [r for r in requests if r["request_id"] not in done]
    deadline, completed = time.monotonic() + minutes * 60, 0
    for item in pending[:limit or None]:
        if time.monotonic() >= deadline:
            break
        payload = json.dumps(item["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        for attempt in range(6):
            req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=payload,
                  headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                           "User-Agent": "SeparabilityResearch/2.0"})
            try:
                with urllib.request.urlopen(req, timeout=180) as response:
                    raw_bytes = response.read()
                    decoded = json.loads(raw_bytes)
                    safe_headers = {k.lower(): v for k, v in response.headers.items()
                                    if k.lower().startswith("x-ratelimit") or k.lower() in {"date", "x-request-id"}}
                append_record(folder / "raw_responses.jsonl", {"request_id": item["request_id"],
                              "request_sha256": item["request_sha256"], "received_utc": datetime.now(timezone.utc).isoformat(),
                              "response": decoded, "response_body": raw_bytes.decode("utf-8"), "response_headers": safe_headers})
                completed += 1
                parsed = parse_response(item, {"response": decoded, "received_utc": datetime.now(timezone.utc).isoformat()})
                print(f"{key}: received {len(done)+completed}/{len(requests)}; QC={parsed['qc_status']}", flush=True)
                break
            except urllib.error.HTTPError as exc:
                # Error bodies can contain account identifiers; retain only code/type and reset delay.
                body = exc.read().decode("utf-8", errors="replace")
                try:
                    err = json.loads(body).get("error", {})
                except json.JSONDecodeError:
                    err = {}
                append_record(folder / "transport_events.jsonl", {"request_id": item["request_id"],
                              "timestamp": datetime.now(timezone.utc).isoformat(), "http_status": exc.code,
                              "error_type": err.get("type", ""), "error_code": err.get("code", ""), "attempt": attempt+1})
                if exc.code not in {429, 500, 502, 503, 504}:
                    consolidate(key)
                    raise SystemExit(f"Provider rejected request: HTTP {exc.code}; type={err.get('type','')}; code={err.get('code','')}")
                wait = 65.0 * (attempt + 1)
                retry_after = exc.headers.get("retry-after", "")
                if retry_after.replace(".", "", 1).isdigit():
                    wait = max(wait, float(retry_after) + 1)
                duration = re.search(r"try again in\s+((?:[\d.]+[hms]\s*)+)", body, re.I)
                if duration:
                    parsed_wait = sum(float(n) * {"h":3600,"m":60,"s":1}[unit] for n, unit in re.findall(r"([\d.]+)([hms])", duration.group(1)))
                    wait = max(wait, parsed_wait + 3)
                if attempt == 5 or time.monotonic() + wait >= deadline:
                    consolidate(key)
                    raise SystemExit("Rate limit/provider outage exceeds this run; checkpoint preserved for resume")
                print(f"{key}: provider rate limit/unavailability; waiting {wait:.0f}s", flush=True)
                time.sleep(wait)
            except (urllib.error.URLError, TimeoutError) as exc:
                append_record(folder / "transport_events.jsonl", {"request_id": item["request_id"],
                              "timestamp": datetime.now(timezone.utc).isoformat(), "error_type": type(exc).__name__, "attempt": attempt+1})
                if attempt == 5:
                    consolidate(key)
                    raise
                time.sleep(min(60, 5 * 2**attempt))
        if completed % 20 == 0:
            consolidate(key)
        time.sleep(2)
    print(json.dumps(consolidate(key), indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run", "consolidate"])
    parser.add_argument("--model", choices=["gptoss120", "qwen27"])
    parser.add_argument("--limit", type=int, default=0, help="0 means all remaining requests")
    parser.add_argument("--minutes", type=float, default=290)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif not args.model:
        parser.error("--model is required")
    elif args.action == "run":
        run(args.model, args.limit, args.minutes)
    else:
        print(json.dumps(consolidate(args.model), indent=2))


if __name__ == "__main__":
    main()
