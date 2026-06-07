"""
Repair E1 Groq QC warning rows without changing the original generation files.

The completed model outputs remain frozen in their model directories. This
script writes a separate audit trail under:

    data/interim/e1_free_model_replication/groq_generation/qc_repairs/

Rows that only needed loose JSON repair can be canonicalized without an API
call. Other warning/fail rows are regenerated with the same Groq target model
and a stricter repair prompt. API keys are read from environment variables and
are never written to output files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import socket
import sys
import time
import urllib.error
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

HELPER_PATH = ROOT / "scripts" / "26_e1_multillm_batch_manager.py"
helper_spec = importlib.util.spec_from_file_location("e1_helper", HELPER_PATH)
helper = importlib.util.module_from_spec(helper_spec)
helper_spec.loader.exec_module(helper)  # type: ignore[union-attr]

GROQ_RUNNER_PATH = ROOT / "scripts" / "36_run_e1_groq_free_generation.py"
groq_spec = importlib.util.spec_from_file_location("e1_groq_runner", GROQ_RUNNER_PATH)
groq_runner = importlib.util.module_from_spec(groq_spec)
groq_spec.loader.exec_module(groq_runner)  # type: ignore[union-attr]

OUT_ROOT = ROOT / "data" / "interim" / "e1_free_model_replication" / "groq_generation"
REPAIR_ROOT = OUT_ROOT / "qc_repairs"
LOGS = ROOT / "logs"

TARGET_ORDER = ["llama", "qwen", "gptoss"]
DEFAULT_SLEEP_SECONDS = {
    "llama": 8.0,
    "qwen": 15.0,
    "gptoss": 12.0,
}
REPAIR_VERSION = "qc_repair_v1"
SAFETY_SHUTDOWN_SECONDS = 90


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def get_api_key(env_name: str) -> str:
    return os.environ.get(env_name, "")


def target_list(value: str) -> list[str]:
    if value == "all":
        return TARGET_ORDER
    return [value]


def repair_dir(target: str) -> Path:
    cfg = groq_runner.TARGETS[target]
    return REPAIR_ROOT / cfg["replication_model_id"]


def original_output_dir(target: str) -> Path:
    cfg = groq_runner.TARGETS[target]
    return OUT_ROOT / cfg["replication_model_id"]


def load_original_parsed(target: str) -> list[dict[str, str]]:
    path = original_output_dir(target) / "parsed_outputs.csv"
    if not path.exists():
        raise RuntimeError(f"Missing original parsed output: {path.relative_to(ROOT)}")
    return read_csv(path)


def load_request_map(target: str, passages_per_author: int) -> dict[str, dict[str, Any]]:
    cfg = groq_runner.TARGETS[target]
    rows = groq_runner.build_requests(target, cfg["provider_model_name"], passages_per_author)
    return {row["request_id"]: row for row in rows}


def canonical_response_text(req: dict[str, Any], rewritten_text: str) -> str:
    return json.dumps({
        "passage_id": req["passage_id"],
        "condition": req["condition"],
        "rewritten_text": rewritten_text,
    }, ensure_ascii=False)


def qc_from_text(req: dict[str, Any], response_text: str) -> dict[str, Any]:
    parse_status, parsed_obj = helper.parse_model_json(response_text)
    q = helper.qc(req, parsed_obj, parse_status)
    return {
        "parse_status": q["parse_status"],
        "qc_status": q["qc_status"],
        "qc_flags": q["qc_flags"],
        "rewritten_text": q["rewritten_text"],
        "rewritten_text_sha256": q["rewritten_text_sha256"],
        "rewritten_word_count": q["rewritten_word_count"],
        "length_ratio": q["length_ratio"],
    }


def repair_prompt(req: dict[str, Any], old_row: dict[str, str]) -> str:
    original_wc = int(float(req["original_word_count"]))
    low = int(original_wc * 0.85 + 0.9999)
    high = int(original_wc * 1.15)
    source_text = extract_source_text(req["user_prompt"])
    prompt = f"""Repair this controlled literary rewrite so it passes the dataset QC checks.

Return only a valid JSON object with exactly these fields:
{{
  "passage_id": "{req["passage_id"]}",
  "condition": "{req["condition"]}",
  "rewritten_text": "..."
}}

Do not include markdown, notes, commentary, headings, bullets, analysis, or text outside the JSON object.
The JSON must parse with Python json.loads without repair.
Inside rewritten_text, avoid literal double quote characters; use single quotation marks for dialogue or quoted speech.

Original QC flags: {old_row.get("qc_flags", "")}
Original length ratio: {old_row.get("length_ratio", "")}
Original word count: {original_wc}
Target rewritten word-count range for pass: {low} to {high} words inclusive.

Keep the same passage_id and condition.
Apply the original condition instruction:
{helper.CONDITION_INSTRUCTIONS[req["condition"]]}

Do not mention Project Gutenberg, Gutenberg, dataset, experiment, prompt, authors, or titles.
Preserve the same events, objects, characters, speaker relationships, and narrative sequence.
Do not add plot information. Do not remove material facts. Do not summarize.

Original passage:
<<<PASSAGE_START>>>
{source_text}
<<<PASSAGE_END>>>

Previous rewrite with QC warning:
<<<OLD_REWRITE_START>>>
{old_row.get("rewritten_text", "")}
<<<OLD_REWRITE_END>>>
"""
    if req["replication_model_id"] == groq_runner.TARGETS["qwen"]["replication_model_id"]:
        return groq_runner.QWEN_USER_PREFIX + prompt + groq_runner.QWEN_USER_SUFFIX
    return prompt


def extract_source_text(user_prompt: str) -> str:
    start = "<<<PASSAGE_START>>>"
    end = "<<<PASSAGE_END>>>"
    if start in user_prompt and end in user_prompt:
        return user_prompt.split(start, 1)[1].split(end, 1)[0].strip()
    return user_prompt


def build_repair_request(target: str, req: dict[str, Any], old_row: dict[str, str]) -> tuple[dict[str, Any], str]:
    system_prompt = helper.SYSTEM_PROMPT + """

Repair mode:
You are fixing a previous generated rewrite that triggered QC warnings.
Preserve the scientific protocol and rewrite condition. Do not explain the repair.
Return only valid JSON."""
    if target == "qwen":
        system_prompt += groq_runner.QWEN_SYSTEM_SUFFIX
    user_prompt = repair_prompt(req, old_row)
    prompt_hash = sha256_text(system_prompt + user_prompt)
    repair_req = dict(req)
    repair_req.update({
        "request_id": repair_id(req["request_id"], "model_regenerated", 1),
        "source_request_id": req["request_id"],
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "prompt_template_sha256": prompt_hash,
        "temperature": 0.2,
        "top_p": 1.0,
    })
    return repair_req, prompt_hash


def repair_id(request_id: str, action: str, attempt: int) -> str:
    return f"{request_id}|{REPAIR_VERSION}|{action}|attempt_{attempt}"


def source_request_id(repair_id_value: str) -> str:
    marker = f"|{REPAIR_VERSION}|"
    if marker in repair_id_value:
        return repair_id_value.split(marker, 1)[0]
    return repair_id_value


def build_candidates(target: str, parsed_rows: list[dict[str, str]], request_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for row in parsed_rows:
        if row.get("qc_status") == "pass":
            continue
        req = request_map.get(row["request_id"])
        if not req:
            continue
        candidates.append({
            "target": target,
            "request_id": row["request_id"],
            "replication_model_id": row["replication_model_id"],
            "provider_model_name": row["provider_model_name"],
            "passage_id": row["passage_id"],
            "condition": row["condition"],
            "original_word_count": row["original_word_count"],
            "old_rewritten_word_count": row["rewritten_word_count"],
            "old_length_ratio": row["length_ratio"],
            "old_qc_status": row["qc_status"],
            "old_qc_flags": row["qc_flags"],
            "old_parse_status": row["parse_status"],
            "old_rewritten_text_sha256": row["rewritten_text_sha256"],
            "old_rewritten_text": row["rewritten_text"],
        })
    return candidates


def raw_text_from_response(response: dict[str, Any]) -> str:
    return groq_runner.extract_response_text(response)


def successful_repairs(raw_rows: list[dict[str, Any]]) -> set[str]:
    return {
        source_request_id(row.get("repair_id", ""))
        for row in raw_rows
        if row.get("status") == "ok" and row.get("repair_id")
    }


def best_repair_rows(target: str, raw_rows: list[dict[str, Any]], request_map: dict[str, dict[str, Any]], old_by_id: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    seen_pass: set[str] = set()
    for raw in raw_rows:
        if raw.get("status") != "ok":
            continue
        req_id = raw.get("source_request_id") or source_request_id(raw.get("repair_id", ""))
        if not req_id or req_id in seen_pass:
            continue
        req = request_map.get(req_id)
        old = old_by_id.get(req_id)
        if not req or not old:
            continue
        response_text = raw.get("response_text")
        if not isinstance(response_text, str):
            response_text = raw_text_from_response(raw.get("response") or {})
        q = qc_from_text(req, response_text)
        row = {
            "repair_id": raw.get("repair_id", ""),
            "source_request_id": req_id,
            "target": target,
            "replication_model_id": req["replication_model_id"],
            "provider_model_name": raw.get("provider_model_name", req["provider_model_name"]),
            "passage_id": req["passage_id"],
            "condition": req["condition"],
            "repair_action": raw.get("repair_action", ""),
            "repair_version": REPAIR_VERSION,
            "repair_prompt_sha256": raw.get("repair_prompt_sha256", ""),
            "old_qc_status": old.get("qc_status", ""),
            "old_qc_flags": old.get("qc_flags", ""),
            "old_parse_status": old.get("parse_status", ""),
            "old_length_ratio": old.get("length_ratio", ""),
            "old_rewritten_word_count": old.get("rewritten_word_count", ""),
            "old_rewritten_text_sha256": old.get("rewritten_text_sha256", ""),
            "old_rewritten_text": old.get("rewritten_text", ""),
            "original_word_count": req["original_word_count"],
            "new_qc_status": q["qc_status"],
            "new_qc_flags": q["qc_flags"],
            "new_parse_status": q["parse_status"],
            "new_length_ratio": q["length_ratio"],
            "new_rewritten_word_count": q["rewritten_word_count"],
            "new_rewritten_text_sha256": q["rewritten_text_sha256"],
            "new_rewritten_text": q["rewritten_text"],
            "created_utc": raw.get("created_utc", ""),
        }
        rows.append(row)
        if q["qc_status"] == "pass":
            seen_pass.add(req_id)
    rows.sort(key=lambda row: (row["source_request_id"], row["repair_action"], row["repair_id"]))
    return rows


def write_target_report(
    target: str,
    candidates: list[dict[str, Any]],
    parsed_repairs: list[dict[str, Any]],
    completed_this_run: int,
    exit_reason: str,
) -> None:
    out = LOGS / f"e1_groq_qc_repair_{target}_report.md"
    LOGS.mkdir(parents=True, exist_ok=True)
    old_flags = Counter(row["old_qc_flags"] for row in candidates)
    new_status = Counter(row["new_qc_status"] for row in parsed_repairs)
    pass_source_ids = {row["source_request_id"] for row in parsed_repairs if row["new_qc_status"] == "pass"}
    repaired_warning_ids = {row["source_request_id"] for row in parsed_repairs}
    remaining = len({row["request_id"] for row in candidates} - pass_source_ids)
    lines = [
        f"# E1 Groq QC Repair Report: {target}",
        "",
        f"- generated_utc: {utc_now()}",
        f"- repair_version: {REPAIR_VERSION}",
        f"- warning_or_fail_candidates: {len(candidates)}",
        f"- attempted_or_canonicalized_candidates_total: {len(repaired_warning_ids)}",
        f"- candidates_fixed_to_pass_total: {len(pass_source_ids)}",
        f"- remaining_not_pass_total: {remaining}",
        f"- completed_this_run: {completed_this_run}",
        f"- exit_reason: {exit_reason}",
        "",
        "## Original QC flags",
    ]
    for key, count in sorted(old_flags.items()):
        lines.append(f"- {key or '(none)'}: {count}")
    lines.extend(["", "## New repair QC status"])
    for key, count in sorted(new_status.items()):
        lines.append(f"- {key}: {count}")
    lines.extend([
        "",
        "## Files",
        f"- {repair_dir(target).relative_to(ROOT).as_posix()}/repair_candidates.csv",
        f"- {repair_dir(target).relative_to(ROOT).as_posix()}/repair_raw_responses.jsonl",
        f"- {repair_dir(target).relative_to(ROOT).as_posix()}/repair_parsed_outputs.csv",
    ])
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(targets: list[str]) -> None:
    rows = []
    for target in targets:
        parsed_path = repair_dir(target) / "repair_parsed_outputs.csv"
        candidate_path = repair_dir(target) / "repair_candidates.csv"
        if not parsed_path.exists() or not candidate_path.exists():
            continue
        parsed = read_csv(parsed_path)
        candidates = read_csv(candidate_path)
        fixed_ids = {row["source_request_id"] for row in parsed if row["new_qc_status"] == "pass"}
        statuses = Counter(row["new_qc_status"] for row in parsed)
        rows.append({
            "target": target,
            "warning_or_fail_candidates": len(candidates),
            "repair_rows_total": len(parsed),
            "fixed_to_pass_source_request_ids": len(fixed_ids),
            "new_pass_rows": statuses.get("pass", 0),
            "new_warning_rows": statuses.get("warning", 0),
            "new_fail_rows": statuses.get("fail", 0),
            "remaining_not_pass_source_request_ids": len({row["request_id"] for row in candidates} - fixed_ids),
            "generated_utc": utc_now(),
        })
    if not rows:
        return
    summary_csv = ROOT / "metadata" / "e1_groq_qc_repair_summary.csv"
    write_csv(summary_csv, rows, [
        "target",
        "warning_or_fail_candidates",
        "repair_rows_total",
        "fixed_to_pass_source_request_ids",
        "new_pass_rows",
        "new_warning_rows",
        "new_fail_rows",
        "remaining_not_pass_source_request_ids",
        "generated_utc",
    ])
    report = LOGS / "e1_groq_qc_repair_summary_report.md"
    lines = ["# E1 Groq QC Repair Summary", "", f"- generated_utc: {utc_now()}", ""]
    for row in rows:
        lines.append(
            "- {target}: candidates={warning_or_fail_candidates}, fixed_to_pass={fixed_to_pass_source_request_ids}, "
            "repair_rows={repair_rows_total}, new_pass/warning/fail={new_pass_rows}/{new_warning_rows}/{new_fail_rows}, "
            "remaining={remaining_not_pass_source_request_ids}".format(**row)
        )
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def process_target(target: str, args: argparse.Namespace) -> tuple[int, str]:
    cfg = groq_runner.TARGETS[target]
    request_map = load_request_map(target, args.passages_per_author)
    parsed_rows = load_original_parsed(target)
    old_by_id = {row["request_id"]: row for row in parsed_rows}
    candidates = build_candidates(target, parsed_rows, request_map)

    out_dir = repair_dir(target)
    raw_path = out_dir / "repair_raw_responses.jsonl"
    candidate_path = out_dir / "repair_candidates.csv"
    parsed_path = out_dir / "repair_parsed_outputs.csv"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(candidate_path, candidates, [
        "target", "request_id", "replication_model_id", "provider_model_name", "passage_id", "condition",
        "original_word_count", "old_rewritten_word_count", "old_length_ratio", "old_qc_status",
        "old_qc_flags", "old_parse_status", "old_rewritten_text_sha256", "old_rewritten_text",
    ])

    raw_rows = read_jsonl(raw_path)
    fixed_or_attempted = successful_repairs(raw_rows) if args.resume else set()
    completed_this_run = 0
    exit_reason = "completed_all_pending_repairs"
    started = time.monotonic()

    for candidate in candidates:
        if args.max_repairs is not None and completed_this_run >= args.max_repairs:
            exit_reason = "stopped_after_max_repairs"
            break
        req_id = candidate["request_id"]
        if req_id in fixed_or_attempted:
            continue
        req = request_map[req_id]
        flags = set(filter(None, candidate["old_qc_flags"].split(";")))
        json_only = flags == {"json_repaired_loose_rewritten_text"}

        if json_only and not args.model_only:
            response_text = canonical_response_text(req, candidate["old_rewritten_text"])
            repair_record = {
                "repair_id": repair_id(req_id, "json_canonicalized_no_text_change", 1),
                "source_request_id": req_id,
                "status": "ok",
                "repair_action": "json_canonicalized_no_text_change",
                "repair_prompt_sha256": "",
                "provider_model_name": cfg["provider_model_name"],
                "created_utc": utc_now(),
                "response_text": response_text,
                "notes": "No model call. Original rewritten_text preserved; response envelope canonicalized as valid JSON.",
            }
            append_jsonl(raw_path, repair_record)
            fixed_or_attempted.add(req_id)
            completed_this_run += 1
            continue

        if args.canonical_only:
            continue

        elapsed = time.monotonic() - started
        remaining_runtime = args.max_runtime_minutes * 60 - elapsed
        if remaining_runtime < SAFETY_SHUTDOWN_SECONDS:
            exit_reason = "stopped_before_runtime_limit_resume_later"
            break

        api_key = get_api_key(cfg["api_key_env"])
        if not api_key:
            exit_reason = f"missing_env_{cfg['api_key_env']}"
            break

        repair_req, prompt_hash = build_repair_request(target, req, candidate)
        server_error_attempts = 0
        while True:
            elapsed = time.monotonic() - started
            remaining_runtime = args.max_runtime_minutes * 60 - elapsed
            if remaining_runtime < SAFETY_SHUTDOWN_SECONDS:
                exit_reason = "stopped_before_runtime_limit_resume_later"
                break
            try:
                response = groq_runner.call_groq(api_key, repair_req, cfg["provider_model_name"])
                append_jsonl(raw_path, {
                    "repair_id": repair_req["request_id"],
                    "source_request_id": req_id,
                    "status": "ok",
                    "repair_action": "model_regenerated_qc_repair_v1",
                    "repair_prompt_sha256": prompt_hash,
                    "provider_model_name": cfg["provider_model_name"],
                    "created_utc": utc_now(),
                    "response": response,
                })
                fixed_or_attempted.add(req_id)
                completed_this_run += 1
                time.sleep(max(args.sleep_seconds if args.sleep_seconds is not None else DEFAULT_SLEEP_SECONDS[target], 0.0))
                break
            except groq_runner.RateLimitWait as exc:
                wait_seconds = min(exc.wait_seconds, float(args.max_single_wait_seconds))
                if exc.wait_seconds > args.max_single_wait_seconds or exc.wait_seconds > remaining_runtime - SAFETY_SHUTDOWN_SECONDS:
                    append_jsonl(raw_path, {
                        "repair_id": repair_req["request_id"],
                        "source_request_id": req_id,
                        "status": "paused_rate_limit_resume_later",
                        "repair_action": "model_regenerated_qc_repair_v1",
                        "error": exc.reason,
                        "requested_wait_seconds": exc.wait_seconds,
                        "provider_model_name": cfg["provider_model_name"],
                        "created_utc": utc_now(),
                    })
                    exit_reason = "rate_limit_wait_resume_later"
                    break
                print(f"{target}: rate limited; waiting {wait_seconds:.1f}s", flush=True)
                time.sleep(wait_seconds)
            except urllib.error.HTTPError as exc:
                body = getattr(exc, "body_text", "")
                if 500 <= exc.code < 600:
                    wait_seconds = min(max(DEFAULT_SLEEP_SECONDS[target], 15.0) * (2 ** server_error_attempts), 300.0)
                    server_error_attempts += 1
                    if wait_seconds > remaining_runtime - SAFETY_SHUTDOWN_SECONDS:
                        exit_reason = "server_error_wait_resume_later"
                        break
                    print(f"{target}: server error {exc.code}; retrying in {wait_seconds:.1f}s", flush=True)
                    time.sleep(wait_seconds)
                    continue
                append_jsonl(raw_path, {
                    "repair_id": repair_req["request_id"],
                    "source_request_id": req_id,
                    "status": "http_error",
                    "repair_action": "model_regenerated_qc_repair_v1",
                    "error": f"HTTPError {exc.code}: {body[:800]}",
                    "provider_model_name": cfg["provider_model_name"],
                    "created_utc": utc_now(),
                })
                exit_reason = f"stopped_on_http_error_{exc.code}"
                break
            except (TimeoutError, socket.timeout, ConnectionResetError, ConnectionAbortedError, BrokenPipeError, urllib.error.URLError) as exc:
                wait_seconds = max(min(DEFAULT_SLEEP_SECONDS[target], 30.0), 5.0)
                print(f"{target}: transient network error; retrying in {wait_seconds:.1f}s ({exc})", flush=True)
                time.sleep(wait_seconds)
                continue

        if exit_reason != "completed_all_pending_repairs":
            break

    raw_rows = read_jsonl(raw_path)
    parsed_repairs = best_repair_rows(target, raw_rows, request_map, old_by_id)
    write_csv(parsed_path, parsed_repairs, [
        "repair_id", "source_request_id", "target", "replication_model_id", "provider_model_name",
        "passage_id", "condition", "repair_action", "repair_version", "repair_prompt_sha256",
        "old_qc_status", "old_qc_flags", "old_parse_status", "old_length_ratio",
        "old_rewritten_word_count", "old_rewritten_text_sha256", "old_rewritten_text",
        "original_word_count", "new_qc_status", "new_qc_flags", "new_parse_status",
        "new_length_ratio", "new_rewritten_word_count", "new_rewritten_text_sha256",
        "new_rewritten_text", "created_utc",
    ])
    write_target_report(target, candidates, parsed_repairs, completed_this_run, exit_reason)

    counts = Counter(row["new_qc_status"] for row in parsed_repairs)
    print(
        f"{target}: candidates={len(candidates)} repair_rows={len(parsed_repairs)} "
        f"new pass/warning/fail={counts.get('pass', 0)}/{counts.get('warning', 0)}/{counts.get('fail', 0)} "
        f"completed_this_run={completed_this_run} exit_reason={exit_reason}",
        flush=True,
    )
    return completed_this_run, exit_reason


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair E1 Groq QC warning rows in separate audit files.")
    parser.add_argument("--target", choices=["all", *TARGET_ORDER], default="all")
    parser.add_argument("--passages-per-author", type=int, default=20)
    parser.add_argument("--sleep-seconds", type=float, default=None)
    parser.add_argument("--max-runtime-minutes", type=float, default=60)
    parser.add_argument("--max-single-wait-seconds", type=float, default=1800)
    parser.add_argument("--max-repairs", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--canonical-only", action="store_true")
    parser.add_argument("--model-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    targets = target_list(args.target)
    for target in targets:
        _completed, exit_reason = process_target(target, args)
        if "missing_env_" in exit_reason or exit_reason.startswith("stopped_on_http_error"):
            write_summary(targets)
            return 1
    write_summary(targets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
