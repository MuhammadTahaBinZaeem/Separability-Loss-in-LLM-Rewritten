"""
E1 Groq free-model generation runner.

This script runs one Groq-hosted model at a time using an API key supplied via
GitHub Actions secrets or local environment variables. It keeps outputs separate
from the frozen Gemini Flash core dataset.

Run locally, for example:

    GROQ_LLAMA_API_KEY=... python scripts/36_run_e1_groq_free_generation.py --target llama --passages-per-author 3 --resume

Targets:

    llama  -> llama-3.3-70b-versatile, secret/env GROQ_LLAMA_API_KEY
    qwen   -> qwen/qwen3-32b by default, secret/env GROQ_QWEN_API_KEY
    gptoss -> openai/gpt-oss-120b, secret/env GROQ_GPTOSS_API_KEY

No keys are stored in the repository.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "scripts" / "26_e1_multillm_batch_manager.py"
spec = importlib.util.spec_from_file_location("e1_helper", HELPER_PATH)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)  # type: ignore[union-attr]

OUT_ROOT = ROOT / "data" / "interim" / "e1_free_model_replication" / "groq_generation"
META = ROOT / "metadata"
LOGS = ROOT / "logs"

TARGETS = {
    "llama": {
        "replication_model_id": "groq_llama_3_3_70b_free",
        "provider_model_name": "llama-3.3-70b-versatile",
        "provider_label": "Groq Llama 3.3 70B free-tier run",
        "api_key_env": "GROQ_LLAMA_API_KEY",
    },
    "qwen": {
        "replication_model_id": "groq_qwen_32b_free",
        "provider_model_name": "qwen/qwen3-32b",
        "provider_label": "Groq Qwen 32B free-tier run",
        "api_key_env": "GROQ_QWEN_API_KEY",
    },
    "gptoss": {
        "replication_model_id": "groq_gpt_oss_120b_free",
        "provider_model_name": "openai/gpt-oss-120b",
        "provider_label": "Groq GPT-OSS 120B free-tier run",
        "api_key_env": "GROQ_GPTOSS_API_KEY",
    },
}

CONDITIONS = ["paraphrase", "modernize", "simplify"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def balanced_originals(passages_per_author: int) -> list[dict[str, str]]:
    originals = helper.load_originals()
    by_author: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in originals:
        by_author[row["author_id"]].append(row)
    chosen = []
    for author in sorted(by_author):
        rows = sorted(by_author[author], key=lambda r: r["passage_id"])
        if len(rows) < passages_per_author:
            raise RuntimeError(f"Author {author} has only {len(rows)} original passages.")
        chosen.extend(rows[:passages_per_author])
    chosen.sort(key=lambda r: (r["author_id"], r["passage_id"]))
    return chosen


def build_requests(target: str, provider_model_name: str, passages_per_author: int) -> list[dict[str, Any]]:
    target_cfg = TARGETS[target]
    originals = balanced_originals(passages_per_author)
    prompt_hash = sha256_text(helper.SYSTEM_PROMPT + json.dumps(helper.CONDITION_INSTRUCTIONS, sort_keys=True))
    requests = []
    for original in originals:
        original_wc = int(float(original["text_word_count"]))
        for condition in CONDITIONS:
            request_id = "|".join([target_cfg["replication_model_id"], "run_1", original["passage_id"], condition])
            requests.append({
                "request_id": request_id,
                "replication_model_id": target_cfg["replication_model_id"],
                "provider": "groq",
                "provider_label": target_cfg["provider_label"],
                "provider_model_name": provider_model_name,
                "run_id": "run_1",
                "passage_id": original["passage_id"],
                "condition": condition,
                "temperature": 0.2,
                "top_p": 1.0,
                "prompt_template_sha256": prompt_hash,
                "source_text_sha256": original["text_sha256"],
                "original_word_count": original_wc,
                "system_prompt": helper.SYSTEM_PROMPT,
                "user_prompt": helper.user_prompt(original["passage_id"], condition, original["text"], original_wc),
            })
    return requests


def completed_ids(raw_path: Path) -> set[str]:
    return {row.get("request_id", "") for row in read_jsonl(raw_path) if row.get("status") == "ok"}


def call_groq(api_key: str, req: dict[str, Any], provider_model_name: str, timeout: int = 180) -> dict[str, Any]:
    payload = {
        "model": provider_model_name,
        "messages": [
            {"role": "system", "content": req["system_prompt"]},
            {"role": "user", "content": req["user_prompt"]},
        ],
        "temperature": req["temperature"],
        "top_p": req["top_p"],
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def extract_response_text(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    return content if isinstance(content, str) else ""


def parse_and_qc(raw_rows: list[dict[str, Any]], request_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    parsed_rows = []
    for raw in raw_rows:
        if raw.get("status") != "ok":
            continue
        req = request_map.get(raw["request_id"])
        if not req:
            continue
        response_text = extract_response_text(raw.get("response") or {})
        parse_status, parsed_obj = helper.parse_model_json(response_text)
        q = helper.qc(req, parsed_obj, parse_status)
        parsed_rows.append({
            "request_id": req["request_id"],
            "replication_model_id": req["replication_model_id"],
            "provider": req["provider"],
            "provider_label": req["provider_label"],
            "provider_model_name": req["provider_model_name"],
            "provider_model_version": raw.get("provider_model_name", req["provider_model_name"]),
            "run_id": req["run_id"],
            "passage_id": req["passage_id"],
            "condition": req["condition"],
            "rewritten_text": q["rewritten_text"],
            "temperature": req["temperature"],
            "top_p": req["top_p"],
            "source_text_sha256": req["source_text_sha256"],
            "rewritten_text_sha256": q["rewritten_text_sha256"],
            "original_word_count": req["original_word_count"],
            "rewritten_word_count": q["rewritten_word_count"],
            "length_ratio": q["length_ratio"],
            "qc_status": q["qc_status"],
            "qc_flags": q["qc_flags"],
            "parse_status": q["parse_status"],
            "created_utc": raw.get("created_utc", ""),
        })
    return parsed_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    parser.add_argument("--provider-model-name", default=None)
    parser.add_argument("--passages-per-author", type=int, default=3)
    parser.add_argument("--max-requests", type=int, default=None)
    parser.add_argument("--sleep-seconds", type=float, default=15.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = TARGETS[args.target]
    provider_model_name = args.provider_model_name or cfg["provider_model_name"]
    api_key = os.environ.get(cfg["api_key_env"], "")
    if not api_key and not args.dry_run:
        print(f"Missing required environment variable/secret: {cfg['api_key_env']}", file=sys.stderr)
        return 2

    out_dir = OUT_ROOT / cfg["replication_model_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "raw_responses.jsonl"
    parsed_path = out_dir / "parsed_outputs.csv"
    request_path = out_dir / "requests_used.jsonl"
    proof_path = LOGS / f"e1_groq_{args.target}_generation_report.md"

    requests = build_requests(args.target, provider_model_name, args.passages_per_author)
    if args.max_requests is not None:
        requests = requests[: args.max_requests]
    done = completed_ids(raw_path) if args.resume else set()
    pending = [req for req in requests if req["request_id"] not in done]

    with request_path.open("w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False, sort_keys=True) + "\n")

    completed_this_run = 0
    for req in pending:
        if args.dry_run:
            raw_record = {
                "request_id": req["request_id"],
                "status": "dry_run",
                "provider_model_name": provider_model_name,
                "created_utc": utc_now(),
                "response": {},
            }
        else:
            status = "error"
            error = ""
            response = None
            for attempt in range(1, 6):
                try:
                    response = call_groq(api_key, req, provider_model_name)
                    status = "ok"
                    break
                except urllib.error.HTTPError as exc:
                    body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
                    error = f"HTTPError {exc.code}: {body[:800]}"
                    if exc.code in {429, 500, 502, 503, 504}:
                        time.sleep(max(args.sleep_seconds, 15.0) * attempt)
                        continue
                    break
                except Exception as exc:  # noqa: BLE001
                    error = repr(exc)
                    time.sleep(max(args.sleep_seconds, 15.0) * attempt)
            raw_record = {
                "request_id": req["request_id"],
                "status": status,
                "error": error,
                "provider_model_name": provider_model_name,
                "created_utc": utc_now(),
                "response": response,
            }
        append_jsonl(raw_path, raw_record)
        completed_this_run += 1
        if not args.dry_run:
            time.sleep(args.sleep_seconds)

    raw_rows = read_jsonl(raw_path)
    request_map = {req["request_id"]: req for req in requests}
    parsed_rows = parse_and_qc(raw_rows, request_map)
    write_csv(parsed_path, parsed_rows, [
        "request_id", "replication_model_id", "provider", "provider_label", "provider_model_name",
        "provider_model_version", "run_id", "passage_id", "condition", "rewritten_text",
        "temperature", "top_p", "source_text_sha256", "rewritten_text_sha256", "original_word_count",
        "rewritten_word_count", "length_ratio", "qc_status", "qc_flags", "parse_status", "created_utc",
    ])

    pass_rows = sum(1 for r in parsed_rows if r["qc_status"] == "pass")
    warning_rows = sum(1 for r in parsed_rows if r["qc_status"] == "warning")
    fail_rows = sum(1 for r in parsed_rows if r["qc_status"] == "fail")
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text(
        "# E1 Groq Free-Model Generation Report\n\n"
        f"Generated UTC: {utc_now()}\n\n"
        f"- target: {args.target}\n"
        f"- replication_model_id: {cfg['replication_model_id']}\n"
        f"- provider_model_name: {provider_model_name}\n"
        f"- passages_per_author: {args.passages_per_author}\n"
        f"- planned_requests_this_scope: {len(requests)}\n"
        f"- pending_at_start: {len(pending)}\n"
        f"- completed_this_run: {completed_this_run}\n"
        f"- raw_rows_total: {len(raw_rows)}\n"
        f"- parsed_rows_total: {len(parsed_rows)}\n"
        f"- qc_pass_rows: {pass_rows}\n"
        f"- qc_warning_rows: {warning_rows}\n"
        f"- qc_fail_rows: {fail_rows}\n"
        f"- raw_path: {raw_path.relative_to(ROOT)}\n"
        f"- parsed_path: {parsed_path.relative_to(ROOT)}\n"
        f"- request_path: {request_path.relative_to(ROOT)}\n",
        encoding="utf-8",
    )

    print(f"Target: {args.target}")
    print(f"Provider model: {provider_model_name}")
    print(f"Completed this run: {completed_this_run}")
    print(f"Parsed rows total: {len(parsed_rows)}")
    print(f"QC pass/warning/fail: {pass_rows}/{warning_rows}/{fail_rows}")
    print(f"Report: {proof_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
