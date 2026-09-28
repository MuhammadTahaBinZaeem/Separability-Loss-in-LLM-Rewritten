"""Shared-budget v3 generation with durable attempts, honest failures and exact lineage."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sqlite3
import socket
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

from .credentials import read_env
from .expanded_study import BASE, effective_plan, freeze_json, now, verify
from .generation import FIELDS, append_record, parse_response
from .io import OUT, digest_bytes, digest_text, file_hash, read_csv, read_json, read_jsonl, write_csv, write_json
from .provider_probe import NoRedirect
from .providers import connection, response_view


class BudgetExceeded(ValueError):
    pass


class Budget:
    """Atomic process-shared reservation. Unknown usage never releases reserved funds."""
    def __init__(self, path, policy):
        self.path, self.policy = Path(path), policy
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.policy_hash = digest_text(json.dumps(policy, sort_keys=True))
        with self.connect() as con:
            con.execute("CREATE TABLE IF NOT EXISTS policy (id INTEGER PRIMARY KEY CHECK(id=1), hash TEXT NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, model TEXT NOT NULL, request_id TEXT NOT NULL, attempt INTEGER NOT NULL, started TEXT NOT NULL, reserved INTEGER NOT NULL, charge INTEGER NOT NULL, output_reserved INTEGER NOT NULL, output_counted INTEGER NOT NULL, settled INTEGER NOT NULL DEFAULT 0, UNIQUE(model,request_id,attempt))")
            con.execute("INSERT OR IGNORE INTO policy VALUES(1,?)", (self.policy_hash,))
            if con.execute("SELECT hash FROM policy").fetchone()[0] != self.policy_hash:
                raise ValueError("Budget policy changed; preserve the original ledger")

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path, timeout=30)
        try:
            with con:
                yield con
        finally:
            con.close()

    def reserve(self, model, rid, cost, outputs, max_attempts=3):
        if not math.isfinite(cost) or cost <= 0 or type(outputs) is not int or outputs <= 0:
            raise ValueError("Invalid reservation")
        nanos = math.ceil(cost * 1e9)
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            spent, tokens = con.execute("SELECT COALESCE(SUM(charge),0),COALESCE(SUM(CASE WHEN model='codex51' THEN output_counted ELSE 0 END),0) FROM calls").fetchone()
            prior = math.ceil(self.policy["prior_diagnostic_reservations_usd"] * 1e9)
            if spent + prior + nanos > math.floor(self.policy["cap_usd"] * 1e9):
                raise BudgetExceeded("shared_reference_cost_cap")
            if model == "codex51" and tokens + outputs + self.policy["codex_prior_output_reservations"] >= self.policy["codex_output_limit_exclusive"]:
                raise BudgetExceeded("codex_output_token_cap")
            attempt = con.execute("SELECT COUNT(*) FROM calls WHERE model=? AND request_id=?", (model, rid)).fetchone()[0] + 1
            if attempt > max_attempts:
                raise BudgetExceeded("assignment_attempt_limit")
            cur = con.execute("INSERT INTO calls(model,request_id,attempt,started,reserved,charge,output_reserved,output_counted) VALUES(?,?,?,?,?,?,?,?)", (model, rid, attempt, now(), nanos, nanos, outputs, outputs))
            return cur.lastrowid, attempt

    def settle(self, call_id, cost, output_tokens):
        if not math.isfinite(cost) or cost < 0 or type(output_tokens) is not int or output_tokens < 0:
            raise ValueError("Invalid reported usage")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT reserved,output_reserved,settled FROM calls WHERE id=?", (call_id,)).fetchone()
            if row is None or row[2]:
                raise ValueError("Unknown or already settled call")
            charge = math.ceil(cost * 1e9)
            con.execute("UPDATE calls SET charge=?,output_counted=?,settled=1 WHERE id=?", (charge, output_tokens, call_id))
        if charge > row[0] or output_tokens > row[1]:
            raise BudgetExceeded("reported_usage_exceeded_reservation_stop_and_audit")

    def status(self):
        with self.connect() as con:
            counts = con.execute("SELECT model,COUNT(*),SUM(charge),SUM(output_counted),SUM(1-settled) FROM calls GROUP BY model").fetchall()
        spent = self.policy["prior_diagnostic_reservations_usd"] + sum(r[2] for r in counts) / 1e9
        return {"cap_usd": self.policy["cap_usd"], "reference_cost_used_or_reserved_usd": round(spent, 9),
                "reference_cost_remaining_usd": round(self.policy["cap_usd"] - spent, 9),
                "azure_account_tariff_verified": False, "actual_dollar_charges_known": False,
                "models": {r[0]: {"attempts": r[1], "used_or_reserved_usd": r[2] / 1e9, "output_tokens_used_or_reserved": r[3], "unsettled_calls": r[4]} for r in counts}}


def reported_cost(response, config, policy):
    if config["api"] == "gemini_native":
        usage = response.get("usageMetadata", {})
        incoming = usage.get("promptTokenCount")
        visible = usage.get("candidatesTokenCount")
        reasoning = usage.get("thoughtsTokenCount", 0)
        if type(visible) is not int or type(reasoning) is not int or reasoning < 0:
            return None
        outgoing = visible + reasoning
    else:
        usage = response.get("usage", {})
        incoming, outgoing = usage.get("input_tokens"), usage.get("output_tokens")
    if any(type(x) is not int or x < 0 for x in (incoming, outgoing)):
        return None
    cost = (incoming * config["input_usd_per_million"] * policy["input_cache_write_safety_multiplier"] + outgoing * config["output_usd_per_million"]) / 1e6
    return cost, outgoing


def checked_requests(model):
    verify()
    folder = BASE / "generation" / model
    manifest = read_json(folder / "request_manifest.json")
    for name in ("requests", "assignments"):
        if file_hash(folder / f"{name}.jsonl") != manifest[f"{name}_sha256"]:
            raise ValueError("Request/assignment manifest changed")
    if file_hash(BASE / "generation_plan.json") != manifest["plan_sha256"]:
        raise ValueError("Frozen generation plan changed")
    if "scope_amendment_sha256" in manifest and file_hash(BASE / "scope_amendment.json") != manifest["scope_amendment_sha256"]:
        raise ValueError("Frozen model scope amendment changed")
    requests = read_jsonl(folder / "requests.jsonl")
    for r in requests:
        if digest_text(json.dumps(r["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))) != r["request_sha256"]:
            raise ValueError("Request payload changed")
    return requests


def failed_row(request, event):
    """An evidenced terminal HTTP outcome is not a native model completion."""
    if event.get("http_status") != 400 or event.get("error_code") != "content_filter":
        raise ValueError("Only evidenced content filtering is terminal")
    row = {f: "" for f in FIELDS}
    row.update({k: request[k] for k in ("request_id", "passage_id", "condition", "model_key", "source_sha256", "request_sha256", "requested_model", "original_words")})
    row.update(received_utc=event["received_utc"], outcome_type="http_content_filter", qc_status="fail", qc_flags="provider_content_filter", finish_reason="http_content_filter", rewrite_words=0,
               raw_record_sha256=digest_text(json.dumps(event, ensure_ascii=False, sort_keys=True)))
    return row


def consolidate(model):
    requests = {r["request_id"]: r for r in checked_requests(model)}
    folder = BASE / "generation" / model
    assignments = read_jsonl(folder / "assignments.jsonl")
    config = effective_plan()["models"][model]
    old_rows = {r["request_id"]: r for r in read_csv(OUT / f"generation/{model}/rewrites.csv")} if config.get("reuse_v2_model") else {}
    received, all_attempts, failures = {}, [], []
    native_ids = set()
    for event in read_jsonl(folder / "outcomes.jsonl"):
        request = requests.get(event["request_id"])
        if request is None or request["request_sha256"] != event["request_sha256"]:
            raise ValueError("Unexpected/mismatched generation outcome")
        row = None
        if event["outcome_type"] == "native_response":
            if json.loads(event["response_body"]) != event["response"]:
                raise ValueError("Native body differs from parsed object")
            view = response_view(request, event["response"])
            if not view["id"] or view["id"] in native_ids:
                raise ValueError("Missing/duplicate native response identity")
            native_ids.add(view["id"])
            row = parse_response(request, event)
            if row["qc_status"] == "fail":
                failures.append({"request_id": request["request_id"], "attempt": event["attempt"], "qc_flags": row["qc_flags"],
                                 "visible_output_verbatim": view["content"], "visible_output_sha256": digest_text(view["content"]),
                                 "raw_record_sha256": row["raw_record_sha256"]})
        elif event.get("http_status") == 400 and event.get("error_code") == "content_filter":
            row = failed_row(request, event)
        if row:
            all_attempts.append({**row, "attempt": event["attempt"]})
            received.setdefault(request["request_id"], row)
    rows = []
    for a in assignments:
        row = old_rows.get(a["request_id"]) if a["delivery"] == "reused_v2_observation" else received.get(a["request_id"])
        if row is None:
            continue
        if any(row[k] != a[k] for k in ("source_sha256", "passage_id", "request_sha256")):
            raise ValueError("Reused/new observation does not match assignment lineage")
        rows.append({**row, "assignment_id": a["assignment_id"], "delivery": a["delivery"]})
    rows.sort(key=lambda r: r["assignment_id"])
    write_csv(folder / "rewrites.csv", rows, FIELDS + ["assignment_id", "delivery"])
    write_csv(folder / "all_native_attempts.csv", all_attempts, FIELDS + ["attempt"])
    # Derived exports may be rebuilt; source attempt logs are append-only.
    from .io import write_jsonl
    write_jsonl(folder / "failed_visible_outputs.jsonl", failures)
    status = {"model_key": model, "expected": len(assignments), "accounted": len(rows), "missing": len(assignments) - len(rows),
              "valid_outputs": sum(r["qc_status"] in {"pass", "warning"} for r in rows), "fail": sum(r["qc_status"] == "fail" for r in rows),
              "reused_v2_observations": sum(r["delivery"] == "reused_v2_observation" for r in rows),
              "new_native_responses": sum(r["outcome_type"] == "native_response" for r in all_attempts),
              "accounting_complete": len(rows) == len(assignments), "review_complete": False,
              "request_manifest_sha256": file_hash(folder / "request_manifest.json"), "parsed_sha256": file_hash(folder / "rewrites.csv")}
    write_json(folder / "completion.json", status)
    return status


def run_model(model, env_file, limit=0, interval=0, minutes=120):
    requests = checked_requests(model)
    plan = effective_plan()
    if model not in plan["active_models"]:
        raise ValueError("This model was removed from scope; no further calls authorized")
    config = plan["models"][model]
    if config["api"] == "codex_session":
        raise ValueError("Session arm has no API generation route")
    budget = Budget(BASE / "private/budget.sqlite3", plan["budget"])
    values = read_env(Path(env_file))
    endpoint, headers = connection(config, values)
    folder = BASE / "generation" / model
    lock = folder / "RUNNING.lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    deadline = time.monotonic() + minutes * 60
    errors, sent = [], 0
    try:
        consolidate(model)
        done = {r["request_id"] for r in read_csv(folder / "rewrites.csv")}
        for request in requests:
            if request["request_id"] in done:
                continue
            if (limit and sent >= limit) or time.monotonic() >= deadline or (BASE / "STOP_AFTER_CURRENT").exists():
                break
            # A local resolver failure is checked before reserving another paid attempt.
            try:
                socket.getaddrinfo(urlsplit(endpoint).hostname, 443, type=socket.SOCK_STREAM)
            except socket.gaierror as exc:
                append_record(folder / "network_checks.jsonl", {"checked_utc": now(), "resolved": False, "errno": exc.errno, "provider_request_sent": False})
                errors.append("local_dns_unavailable"); break
            backoff_path = folder / "backoff.json"
            if backoff_path.exists() and read_json(backoff_path)["not_before_epoch"] > time.time():
                errors.append("provider_backoff_active"); break
            body = json.dumps(request["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            max_output = plan["max_completion_tokens"]
            # One byte/token plus framing is deliberately conservative; no optimistic cache savings.
            reservation = ((len(body) + 512) * config["input_usd_per_million"] * plan["budget"]["input_cache_write_safety_multiplier"] + max_output * config["output_usd_per_million"]) / 1e6
            try:
                call_id, attempt = budget.reserve(model, request["request_id"], reservation, max_output, plan["maximum_attempts_per_new_assignment"])
            except BudgetExceeded as exc:
                errors.append(str(exc)); break
            sent += 1
            append_record(folder / "attempts.jsonl", {"request_id": request["request_id"], "request_sha256": request["request_sha256"],
                          "attempt": attempt, "budget_call_id": call_id, "started_utc": now(), "reserved_reference_usd": reservation,
                          "credential_variable": config["key_env"]})
            event = {"request_id": request["request_id"], "request_sha256": request["request_sha256"], "attempt": attempt, "budget_call_id": call_id}
            stop = False
            wait_seconds = interval
            req = urllib.request.Request(endpoint, data=body, headers={**headers, "Content-Type": "application/json", "User-Agent": "SeparabilityResearch/3.0"})
            raw = None
            try:
                with urllib.request.build_opener(NoRedirect).open(req, timeout=180) as response:
                    raw = response.read()
                    native = json.loads(raw)
                    safe_headers = {k.lower(): v for k, v in response.headers.items() if k.lower() in {"date", "x-request-id", "apim-request-id"}}
                event.update(received_utc=now(), outcome_type="native_response", response=native, response_body=raw.decode("utf-8"), response_headers=safe_headers)
                append_record(folder / "outcomes.jsonl", event)
                usage = reported_cost(native, config, plan["budget"])
                if usage is not None:
                    budget.settle(call_id, *usage)
                qc = parse_response(request, event)
                print(f"{model}: new response {sent}; attempt {attempt}; QC {qc['qc_status']}; output {qc['rewrite_words']} words", flush=True)
                done.add(request["request_id"])
            except urllib.error.HTTPError as exc:
                raw = exc.read()
                # Error bodies can contain account details; retain original privately, never print.
                error_path = BASE / f"private/http_bodies/{model}_{call_id}.bin"
                error_path.parent.mkdir(parents=True, exist_ok=True)
                with error_path.open("xb") as stream:
                    stream.write(raw)
                try:
                    detail = json.loads(raw).get("error", {})
                    code = str(detail.get("code", detail.get("status", "")))
                except (ValueError, AttributeError):
                    code = "unparsed_error"
                code = code if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", code) else "withheld"
                retry = exc.headers.get("retry-after", "60")
                wait_seconds = max(interval, float(retry) + 2 if re.fullmatch(r"[0-9.]+", retry) else 62)
                event.update(received_utc=now(), outcome_type="http_error", http_status=exc.code, error_code=code,
                             error_body_sha256=digest_bytes(raw), private_error_body=error_path.relative_to(BASE).as_posix(), retry_after_seconds=wait_seconds)
                append_record(folder / "outcomes.jsonl", event)
                print(f"{model}: HTTP {exc.code}, {code}; original error body retained privately", flush=True)
                if exc.code == 400 and code == "content_filter":
                    done.add(request["request_id"])
                else:
                    # Stop this model for diagnosis; restarting honors the persisted backoff below.
                    errors.append(f"HTTP_{exc.code}:{code}"); stop = True
                    write_json(folder / "backoff.json", {"not_before_epoch": time.time() + wait_seconds, "last_call_id": call_id})
            except BudgetExceeded as exc:
                errors.append(str(exc)); stop = True
            except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
                event.update(received_utc=now(), outcome_type="transport_or_invalid_response", error_type=type(exc).__name__)
                reason = getattr(exc, "reason", None)
                event["reason_class"] = type(reason).__name__ if reason is not None else None
                event["reason_errno"] = getattr(reason, "errno", None)
                detail_path = BASE / f"private/transport_details/{model}_{call_id}.json"
                write_json(detail_path, {"error_class": type(exc).__name__, "detail": str(exc)})
                event["private_transport_detail"] = detail_path.relative_to(BASE).as_posix()
                if raw is not None:
                    path = BASE / f"private/http_bodies/{model}_{call_id}_unparsed.bin"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("xb") as stream:
                        stream.write(raw)
                    event.update(raw_body_sha256=digest_bytes(raw), private_raw_body=path.relative_to(BASE).as_posix())
                append_record(folder / "outcomes.jsonl", event)
                print(f"{model}: transport {event['error_type']}; reason {event['reason_class']}; errno {event['reason_errno']}; details retained privately", flush=True)
                errors.append("transport_or_invalid_response"); stop = True
            status = consolidate(model)
            write_json(BASE / "budget_status.json", budget.status())
            if stop:
                break
            if wait_seconds:
                time.sleep(wait_seconds)
        status = consolidate(model)
        status.update(runner_errors=errors, new_attempts=sent, budget=budget.status(), updated_utc=now())
        write_json(folder / "runner_status.json", status)
        return status
    finally:
        lock.unlink(missing_ok=True)


def resume_model(model, env_file, limit=0, minutes=120):
    """Retry only transient transport/backoff stops, never bad credentials or quota changes."""
    deadline = time.monotonic() + minutes * 60
    attempted, stalled = 0, 0
    while True:
        remaining_minutes = max(0, (deadline - time.monotonic()) / 60)
        result = run_model(model, env_file, max(0, limit - attempted) if limit else 0,
                           4.2 if model == "gem31lite" else 0, remaining_minutes)
        attempted += result["new_attempts"]
        errors = result["runner_errors"]
        retryable = all(e in {"local_dns_unavailable", "provider_backoff_active", "transport_or_invalid_response"}
                        or any(e.startswith(f"HTTP_{code}:") for code in (429, 500, 502, 503, 504)) for e in errors)
        if not errors or not retryable or result["accounting_complete"] or (limit and attempted >= limit) or time.monotonic() >= deadline or (BASE / "STOP_AFTER_CURRENT").exists():
            return result
        stalled = stalled + 1 if result["new_attempts"] <= 1 else 0
        if stalled >= 3:
            return result
        backoff = BASE / f"generation/{model}/backoff.json"
        wait = max(30, read_json(backoff)["not_before_epoch"] - time.time() if backoff.exists() else 0)
        if time.monotonic() + wait >= deadline:
            return result
        print(f"{model}: paused for {wait:.0f}s after a transient stop; attempts and reservations preserved", flush=True)
        # Small sleeps keep the stop-file responsive; outer tool calls yield while this runs.
        until = time.monotonic() + wait
        while time.monotonic() < until and not (BASE / "STOP_AFTER_CURRENT").exists():
            time.sleep(min(1, until - time.monotonic()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "consolidate", "status"))
    parser.add_argument("--models", nargs="+", default=["codex51", "luna56", "terra56"])
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--limit", type=int, default=0, help="maximum new attempts per model")
    parser.add_argument("--minutes", type=float, default=120)
    parser.add_argument("--resume-transient", action="store_true")
    args = parser.parse_args()
    if args.action == "status":
        print(json.dumps(Budget(BASE / "private/budget.sqlite3", read_json(BASE / "generation_plan.json")["budget"]).status(), indent=2)); return
    if args.action == "consolidate":
        print(json.dumps([consolidate(m) for m in args.models], indent=2)); return
    if not args.env_file or len(args.models) > 3 or len(set(args.models)) != len(args.models):
        parser.error("Provide an env file and one to three distinct models")
    for model in args.models:
        backoff = BASE / f"generation/{model}/backoff.json"
        if backoff.exists() and read_json(backoff)["not_before_epoch"] > time.time():
            raise SystemExit("Provider backoff is still active; do not retry yet")
    with ThreadPoolExecutor(max_workers=len(args.models)) as executor:
        results = list(executor.map(lambda m: resume_model(m, args.env_file, args.limit, args.minutes) if args.resume_transient
                                   else run_model(m, args.env_file, args.limit, 4.2 if m == "gem31lite" else 0, args.minutes), args.models))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
