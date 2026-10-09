"""
Step 10B: generate controlled rewrites with a local Ollama model.

Run from repository root after request preparation:

    python scripts/08_prepare_rewrite_requests.py
    python scripts/10_run_rewrite_generation_ollama.py --model qwen2.5:7b-instruct

Small test:

    python scripts/10_run_rewrite_generation_ollama.py --model qwen2.5:7b-instruct --limit 6

The script is resumable: existing request_ids in the raw response file are skipped.

Outputs:
- data/interim/rewrite_responses_raw.jsonl
- data/interim/rewrite_responses_parsed.csv
- metadata/rewrite_run_manifest.csv
- logs/step_10_rewrite_generation_report.md
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "data" / "interim" / "rewrite_requests.jsonl"
RAW_OUT = ROOT / "data" / "interim" / "rewrite_responses_raw.jsonl"
PARSED_OUT = ROOT / "data" / "interim" / "rewrite_responses_parsed.csv"
RUN_MANIFEST = ROOT / "metadata" / "rewrite_run_manifest.csv"
REPORT = ROOT / "logs" / "step_10_rewrite_generation_report.md"
OLLAMA_URL = "http://localhost:11434/api/chat"

WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def completed_request_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                ids.add(row.get("request_id", ""))
            except json.JSONDecodeError:
                continue
    return {x for x in ids if x}


def call_ollama(model: str, messages: list[dict[str, str]], options: dict, timeout: int = 300) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": options,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_rewrite_content(content: str) -> tuple[str, dict | None, str]:
    stripped = content.strip()
    try:
        obj = json.loads(stripped)
        return obj.get("rewritten_text", ""), obj, "json_ok"
    except json.JSONDecodeError:
        # Common fallback: model wraps JSON in text. Extract first object.
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                obj = json.loads(stripped[start:end + 1])
                return obj.get("rewritten_text", ""), obj, "json_extracted"
            except json.JSONDecodeError:
                pass
    return stripped, None, "json_parse_failed_used_raw_content"


def write_parsed_from_raw() -> None:
    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    PARSED_OUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "request_id", "passage_id", "condition", "rewritten_text", "model_provider", "model_name",
        "model_version_or_snapshot", "temperature", "top_p", "seed_if_available", "prompt_template_id",
        "prompt_template_sha256", "source_text_sha256", "rewritten_text_sha256", "original_word_count",
        "rewritten_word_count", "length_ratio", "created_utc", "parse_status",
    ]
    rows = []
    if RAW_OUT.exists():
        with RAW_OUT.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                raw = json.loads(line)
                content = raw.get("model_content", "")
                rewritten, parsed_obj, parse_status = parse_rewrite_content(content)
                original_wc = int(raw.get("original_word_count", 0))
                rewritten_wc = word_count(rewritten)
                rows.append({
                    "request_id": raw.get("request_id", ""),
                    "passage_id": raw.get("passage_id", ""),
                    "condition": raw.get("condition", ""),
                    "rewritten_text": rewritten,
                    "model_provider": "ollama",
                    "model_name": raw.get("model", ""),
                    "model_version_or_snapshot": raw.get("model_version_or_snapshot", "local_ollama_model_name_only"),
                    "temperature": raw.get("temperature", ""),
                    "top_p": raw.get("top_p", ""),
                    "seed_if_available": raw.get("seed_if_available", ""),
                    "prompt_template_id": raw.get("prompt_template_id", ""),
                    "prompt_template_sha256": raw.get("user_prompt_template_sha256", ""),
                    "source_text_sha256": raw.get("source_text_sha256", ""),
                    "rewritten_text_sha256": sha_text(rewritten),
                    "original_word_count": original_wc,
                    "rewritten_word_count": rewritten_wc,
                    "length_ratio": round(rewritten_wc / original_wc, 6) if original_wc else 0.0,
                    "created_utc": raw.get("created_utc", ""),
                    "parse_status": parse_status,
                })
    with PARSED_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(model: str, total_requests: int, completed: int, started_utc: str, finished_utc: str) -> None:
    RUN_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"metric": "backend", "value": "ollama"},
        {"metric": "model", "value": model},
        {"metric": "total_requests", "value": total_requests},
        {"metric": "completed_requests", "value": completed},
        {"metric": "raw_response_path", "value": RAW_OUT.relative_to(ROOT).as_posix()},
        {"metric": "raw_response_sha256", "value": sha_file(RAW_OUT)},
        {"metric": "parsed_response_path", "value": PARSED_OUT.relative_to(ROOT).as_posix()},
        {"metric": "parsed_response_sha256", "value": sha_file(PARSED_OUT)},
        {"metric": "started_utc", "value": started_utc},
        {"metric": "finished_utc", "value": finished_utc},
    ]
    with RUN_MANIFEST.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)


def write_report(model: str, total: int, completed: int, started_utc: str, finished_utc: str) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Step 10 Rewrite Generation Report\n\n"
        f"- backend: ollama\n"
        f"- model: {model}\n"
        f"- total requests: {total}\n"
        f"- completed requests: {completed}\n"
        f"- raw responses: `{RAW_OUT.relative_to(ROOT).as_posix()}`\n"
        f"- parsed responses: `{PARSED_OUT.relative_to(ROOT).as_posix()}`\n"
        f"- raw response SHA256: `{sha_file(RAW_OUT)}`\n"
        f"- parsed response SHA256: `{sha_file(PARSED_OUT)}`\n"
        f"- started UTC: {started_utc}\n"
        f"- finished UTC: {finished_utc}\n\n"
        "Run `python scripts/09_validate_rewrite_outputs.py` after generation.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Ollama model name, e.g. qwen2.5:7b-instruct")
    parser.add_argument("--limit", type=int, default=None, help="Optional max new requests to run for testing")
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between requests")
    parser.add_argument("--timeout", type=int, default=300, help="HTTP timeout seconds per request")
    args = parser.parse_args()

    requests = read_jsonl(REQUESTS)
    done = completed_request_ids(RAW_OUT)
    started_utc = now_utc()
    options = {
        "temperature": 0.2,
        "top_p": 1.0,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "seed": 20260526,
    }

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    ran = 0
    with RAW_OUT.open("a", encoding="utf-8") as raw_out:
        for idx, request in enumerate(requests, start=1):
            request_id = request["request_id"]
            if request_id in done:
                continue
            if args.limit is not None and ran >= args.limit:
                break
            try:
                response = call_ollama(args.model, request["messages"], options, timeout=args.timeout)
                content = response.get("message", {}).get("content", "")
                raw_record = {
                    "request_id": request_id,
                    "passage_id": request["passage_id"],
                    "condition": request["condition"],
                    "model": args.model,
                    "model_version_or_snapshot": response.get("model", args.model),
                    "temperature": options["temperature"],
                    "top_p": options["top_p"],
                    "seed_if_available": options["seed"],
                    "prompt_template_id": request["prompt_template_id"],
                    "system_prompt_sha256": request["system_prompt_sha256"],
                    "user_prompt_template_sha256": request["user_prompt_template_sha256"],
                    "source_text_sha256": request["source_text_sha256"],
                    "original_word_count": request["original_word_count"],
                    "model_content": content,
                    "ollama_response": response,
                    "created_utc": now_utc(),
                }
                raw_out.write(json.dumps(raw_record, ensure_ascii=False) + "\n")
                raw_out.flush()
                done.add(request_id)
                ran += 1
                print(f"[{idx}/{len(requests)}] completed {request_id}")
                if args.sleep:
                    time.sleep(args.sleep)
            except (urllib.error.URLError, TimeoutError) as exc:
                print(f"ERROR on {request_id}: {exc}", file=sys.stderr)
                write_parsed_from_raw()
                finished = now_utc()
                write_manifest(args.model, len(requests), len(done), started_utc, finished)
                write_report(args.model, len(requests), len(done), started_utc, finished)
                return 1

    write_parsed_from_raw()
    finished_utc = now_utc()
    write_manifest(args.model, len(requests), len(done), started_utc, finished_utc)
    write_report(args.model, len(requests), len(done), started_utc, finished_utc)
    print(f"Completed {len(done)} of {len(requests)} total requests. New this run: {ran}.")
    return 0 if len(done) == len(requests) or args.limit is not None else 1


if __name__ == "__main__":
    sys.exit(main())
