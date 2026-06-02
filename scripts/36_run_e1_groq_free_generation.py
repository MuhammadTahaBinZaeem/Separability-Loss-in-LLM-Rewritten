"""
E1 Groq free-model generation runner.

This script runs one Groq-hosted model at a time using an API key supplied via
GitHub Actions secrets or local environment variables. It keeps outputs separate
from the frozen Gemini Flash core dataset.

It is designed for free/limited Groq plans:
- resumes from existing successful raw responses;
- handles 429 rate limits using retry-after / x-ratelimit-reset headers;
- waits for short token-window resets;
- exits cleanly before the GitHub Actions job timeout when a reset is too long,
  so partial outputs can be committed and the next run can resume.

Run locally, for example:

    GROQ_LLAMA_API_KEY=... python scripts/36_run_e1_groq_free_generation.py --target llama --passages-per-author 55 --resume

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
import socket
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "scripts" / "26_e1_multillm_batch_manager.py"
spec = importlib.util.spec_from_file_location("e1_helper", HELPER_PATH)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)  # type: ignore[union-attr]

OUT_ROOT = ROOT / "data" / "interim" / "e1_free_model_replication" / "groq_generation"
LOGS = ROOT / "logs"

TARGETS = {
    "llama": {
        "replication_model_id": "groq_llama_3_3_70b_free",
        "provider_model_name": "llama-3.3-70b-versatile",
        "provider_label": "Groq Llama 3.3 70B free-tier run",
        "api_key_env": "GROQ_LLAMA_API_KEY",
        "recommended_sleep_seconds": 8.0,
    },
    "qwen": {
        "replication_model_id": "groq_qwen_32b_free",
        "provider_model_name": "qwen/qwen3-32b",
        "provider_label": "Groq Qwen 32B free-tier run",
        "api_key_env": "GROQ_QWEN_API_KEY",
        "recommended_sleep_seconds": 15.0,
    },
    "gptoss": {
        "replication_model_id": "groq_gpt_oss_120b_free",
        "provider_model_name": "openai/gpt-oss-120b",
        "provider_label": "Groq GPT-OSS 120B free-tier run",
        "api_key_env": "GROQ_GPTOSS_API_KEY",
        "recommended_sleep_seconds": 12.0,
    },
}

CONDITIONS = ["paraphrase", "modernize", "simplify"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MAX_RUNTIME_MINUTES = 320
SAFETY_SHUTDOWN_SECONDS = 240
MAX_SINGLE_WAIT_SECONDS = 1800


class RateLimitWait(Exception):
    def __init__(self, wait_seconds: float, reason: str):
        super().__init__(reason)
        self.wait_seconds = wait_seconds
        self.reason = reason


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


def scoped_completed_ids(raw_path: Path, request_ids: set[str]) -> set[str]:
    return completed_ids(raw_path) & request_ids


def first_successful_rows(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped = []
    for row in raw_rows:
        if row.get("status") != "ok":
            continue
        request_id = row.get("request_id", "")
        if not request_id or request_id in seen:
            continue
        seen.add(request_id)
        deduped.append(row)
    return deduped


def parse_duration_seconds(value: str | None) -> float | None:
    if not value:
        return None
    value = str(value).strip().lower()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        pass
    total = 0.0
    # Supports strings such as 7.66s, 2m59.56s, 1h2m3s.
    matches = re.findall(r"([0-9]+(?:\.[0-9]+)?)(ms|s|m|h)", value)
    if not matches:
        return None
    for amount, unit in matches:
        num = float(amount)
        if unit == "ms":
            total += num / 1000.0
        elif unit == "s":
            total += num
        elif unit == "m":
            total += num * 60.0
        elif unit == "h":
            total += num * 3600.0
    return total if total > 0 else None


def header_wait_seconds(headers: Any, body: str) -> tuple[float, str]:
    retry_after = parse_duration_seconds(headers.get("retry-after") if headers else None)
    reset_tokens = parse_duration_seconds(headers.get("x-ratelimit-reset-tokens") if headers else None)
    reset_requests = parse_duration_seconds(headers.get("x-ratelimit-reset-requests") if headers else None)

    candidates = []
    if retry_after is not None:
        candidates.append((retry_after, "retry-after"))
    if reset_tokens is not None:
        candidates.append((reset_tokens, "x-ratelimit-reset-tokens"))
    if reset_requests is not None:
        candidates.append((reset_requests, "x-ratelimit-reset-requests"))

    # Groq error bodies often include phrasing like "try again in 1m23.4s".
    match = re.search(r"try again in\s+([0-9hms\. ]+)", body.lower())
    if match:
        parsed = parse_duration_seconds(match.group(1).replace(" ", ""))
        if parsed is not None:
            candidates.append((parsed, "body_try_again_in"))

    if not candidates:
        return 65.0, "fallback_65s"
    wait, reason = max(candidates, key=lambda item: item[0])
    return max(wait + 3.0, 1.0), reason


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
            "User-Agent": "litpaper-e1-groq-generation/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        if exc.code == 429:
            wait_seconds, reason = header_wait_seconds(exc.headers, body)
            raise RateLimitWait(wait_seconds, f"429 rate limit via {reason}: {body[:300]}") from exc
        exc.body_text = body  # type: ignore[attr-defined]
        raise


def extract_response_text(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    return content if isinstance(content, str) else ""


def parse_and_qc(raw_rows: list[dict[str, Any]], request_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    parsed_rows = []
    for raw in first_successful_rows(raw_rows):
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


def write_outputs(
    target: str,
    cfg: dict[str, Any],
    provider_model_name: str,
    args: argparse.Namespace,
    raw_path: Path,
    parsed_path: Path,
    request_path: Path,
    proof_path: Path,
    requests: list[dict[str, Any]],
    completed_this_run: int,
    exit_reason: str,
) -> None:
    raw_rows = read_jsonl(raw_path)
    request_map = {req["request_id"]: req for req in requests}
    parsed_rows = parse_and_qc(raw_rows, request_map)
    write_csv(parsed_path, parsed_rows, [
        "request_id", "replication_model_id", "provider", "provider_label", "provider_model_name",
        "provider_model_version", "run_id", "passage_id", "condition", "rewritten_text",
        "temperature", "top_p", "source_text_sha256", "rewritten_text_sha256", "original_word_count",
        "rewritten_word_count", "length_ratio", "qc_status", "qc_flags", "parse_status", "created_utc",
    ])

    counts = Counter(r["qc_status"] for r in parsed_rows)
    request_ids = {req["request_id"] for req in requests}
    raw_ok_rows_total = len(scoped_completed_ids(raw_path, request_ids))
    remaining = len(requests) - raw_ok_rows_total
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text(
        "# E1 Groq Free-Model Generation Report\n\n"
        f"Generated UTC: {utc_now()}\n\n"
        f"- target: {target}\n"
        f"- replication_model_id: {cfg['replication_model_id']}\n"
        f"- provider_model_name: {provider_model_name}\n"
        f"- passages_per_author: {args.passages_per_author}\n"
        f"- planned_requests_this_scope: {len(requests)}\n"
        f"- completed_this_run: {completed_this_run}\n"
        f"- raw_ok_rows_total: {raw_ok_rows_total}\n"
        f"- remaining_requests: {remaining}\n"
        f"- parsed_rows_total: {len(parsed_rows)}\n"
        f"- qc_pass_rows: {counts.get('pass', 0)}\n"
        f"- qc_warning_rows: {counts.get('warning', 0)}\n"
        f"- qc_fail_rows: {counts.get('fail', 0)}\n"
        f"- exit_reason: {exit_reason}\n"
        f"- raw_path: {raw_path.relative_to(ROOT)}\n"
        f"- parsed_path: {parsed_path.relative_to(ROOT)}\n"
        f"- request_path: {request_path.relative_to(ROOT)}\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    parser.add_argument("--provider-model-name", default=None)
    parser.add_argument("--passages-per-author", type=int, default=55)
    parser.add_argument("--max-requests", type=int, default=None)
    parser.add_argument("--sleep-seconds", type=float, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-runtime-minutes", type=int, default=DEFAULT_MAX_RUNTIME_MINUTES)
    parser.add_argument("--max-single-wait-seconds", type=int, default=MAX_SINGLE_WAIT_SECONDS)
    args = parser.parse_args()

    started = time.monotonic()
    cfg = TARGETS[args.target]
    provider_model_name = args.provider_model_name or cfg["provider_model_name"]
    sleep_seconds = args.sleep_seconds if args.sleep_seconds is not None else float(cfg["recommended_sleep_seconds"])
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
    exit_reason = "completed_all_pending_requests"

    for req in pending:
        elapsed = time.monotonic() - started
        remaining_runtime = args.max_runtime_minutes * 60 - elapsed
        if remaining_runtime < SAFETY_SHUTDOWN_SECONDS:
            exit_reason = "stopped_before_actions_timeout_resume_later"
            break

        if args.dry_run:
            raw_record = {
                "request_id": req["request_id"],
                "status": "dry_run",
                "provider_model_name": provider_model_name,
                "created_utc": utc_now(),
                "response": {},
            }
            append_jsonl(raw_path, raw_record)
            completed_this_run += 1
            continue

        server_error_attempts = 0
        while True:
            elapsed = time.monotonic() - started
            remaining_runtime = args.max_runtime_minutes * 60 - elapsed
            if remaining_runtime < SAFETY_SHUTDOWN_SECONDS:
                exit_reason = "stopped_before_actions_timeout_resume_later"
                break
            try:
                response = call_groq(api_key, req, provider_model_name)
                raw_record = {
                    "request_id": req["request_id"],
                    "status": "ok",
                    "error": "",
                    "provider_model_name": provider_model_name,
                    "created_utc": utc_now(),
                    "response": response,
                }
                append_jsonl(raw_path, raw_record)
                completed_this_run += 1
                time.sleep(max(sleep_seconds, 0.0))
                break
            except RateLimitWait as exc:
                wait_seconds = min(exc.wait_seconds, float(args.max_single_wait_seconds))
                if exc.wait_seconds > remaining_runtime - SAFETY_SHUTDOWN_SECONDS:
                    append_jsonl(raw_path, {
                        "request_id": req["request_id"],
                        "status": "paused_rate_limit_wait_exceeds_remaining_runtime",
                        "error": exc.reason,
                        "requested_wait_seconds": exc.wait_seconds,
                        "created_utc": utc_now(),
                    })
                    exit_reason = "rate_limit_wait_exceeds_remaining_runtime_resume_later"
                    pending = []
                    break
                if exc.wait_seconds > args.max_single_wait_seconds:
                    append_jsonl(raw_path, {
                        "request_id": req["request_id"],
                        "status": "paused_rate_limit_wait_too_long",
                        "error": exc.reason,
                        "requested_wait_seconds": exc.wait_seconds,
                        "created_utc": utc_now(),
                    })
                    exit_reason = "rate_limit_wait_too_long_resume_later"
                    pending = []
                    break
                print(f"Rate limited; waiting {wait_seconds:.1f}s ({exc.reason})", flush=True)
                time.sleep(wait_seconds)
            except urllib.error.HTTPError as exc:
                body = getattr(exc, "body_text", None)
                if body is None:
                    body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
                if 500 <= exc.code < 600:
                    wait_seconds = min(max(sleep_seconds, 15.0) * (2 ** server_error_attempts), 300.0)
                    server_error_attempts += 1
                    if wait_seconds > remaining_runtime - SAFETY_SHUTDOWN_SECONDS:
                        append_jsonl(raw_path, {
                            "request_id": req["request_id"],
                            "status": "paused_server_error_wait_exceeds_remaining_runtime",
                            "error": f"HTTPError {exc.code}: {body[:800]}",
                            "requested_wait_seconds": wait_seconds,
                            "provider_model_name": provider_model_name,
                            "created_utc": utc_now(),
                        })
                        exit_reason = "server_error_wait_exceeds_remaining_runtime_resume_later"
                        break
                    print(f"Server error {exc.code}; retrying in {wait_seconds:.1f}s", flush=True)
                    time.sleep(wait_seconds)
                    continue
                append_jsonl(raw_path, {
                    "request_id": req["request_id"],
                    "status": "http_error",
                    "error": f"HTTPError {exc.code}: {body[:800]}",
                    "provider_model_name": provider_model_name,
                    "created_utc": utc_now(),
                })
                exit_reason = f"stopped_on_http_error_{exc.code}"
                break
            except (TimeoutError, socket.timeout) as exc:
                wait_seconds = max(min(sleep_seconds, 30.0), 5.0)
                print(f"Transient timeout; retrying in {wait_seconds:.1f}s ({exc})", flush=True)
                time.sleep(wait_seconds)
                continue
            except urllib.error.URLError as exc:
                reason_text = str(getattr(exc, "reason", exc))
                if "timed out" in reason_text.lower():
                    wait_seconds = max(min(sleep_seconds, 30.0), 5.0)
                    print(f"Transient URL timeout; retrying in {wait_seconds:.1f}s ({reason_text})", flush=True)
                    time.sleep(wait_seconds)
                    continue
                append_jsonl(raw_path, {
                    "request_id": req["request_id"],
                    "status": "url_error",
                    "error": repr(exc),
                    "provider_model_name": provider_model_name,
                    "created_utc": utc_now(),
                })
                exit_reason = "stopped_on_url_error"
                break
            except Exception as exc:  # noqa: BLE001
                append_jsonl(raw_path, {
                    "request_id": req["request_id"],
                    "status": "error",
                    "error": repr(exc),
                    "provider_model_name": provider_model_name,
                    "created_utc": utc_now(),
                })
                exit_reason = "stopped_on_unhandled_error"
                break

        if exit_reason != "completed_all_pending_requests" and "resume_later" in exit_reason:
            break
        if exit_reason.startswith("stopped_on_"):
            break

    write_outputs(
        args.target,
        cfg,
        provider_model_name,
        args,
        raw_path,
        parsed_path,
        request_path,
        proof_path,
        requests,
        completed_this_run,
        exit_reason,
    )

    parsed_rows = parse_and_qc(read_jsonl(raw_path), {req["request_id"]: req for req in requests})
    counts = Counter(r["qc_status"] for r in parsed_rows)
    print(f"Target: {args.target}")
    print(f"Provider model: {provider_model_name}")
    print(f"Completed this run: {completed_this_run}")
    request_ids = {req["request_id"] for req in requests}
    print(f"Raw OK rows total: {len(scoped_completed_ids(raw_path, request_ids))}/{len(requests)}")
    print(f"Parsed rows total: {len(parsed_rows)}")
    print(f"QC pass/warning/fail: {counts.get('pass', 0)}/{counts.get('warning', 0)}/{counts.get('fail', 0)}")
    print(f"Exit reason: {exit_reason}")
    print(f"Report: {proof_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
