"""Bounded concurrent execution of immutable requests with shared quota backoff."""
from __future__ import annotations

import argparse
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime,timezone
from pathlib import Path

from .credentials import read_env
from .generation import append_record, consolidate, parse_response, prepare, recover_terminal_events, terminal_from_event
from .io import OUT, digest_bytes, read_json, read_jsonl, write_json
from .provider_probe import NoRedirect
from .providers import connection


def quota_summary(error: dict) -> list[dict]:
    """Retain only documented quota names/limits, never project IDs or messages."""
    found=[]
    for detail in error.get("details",[]) if isinstance(error,dict) else []:
        if not isinstance(detail,dict) or not str(detail.get("@type","")).endswith("google.rpc.QuotaFailure"):
            continue
        for violation in detail.get("violations",[]):
            if not isinstance(violation,dict):
                continue
            name=str(violation.get("quotaId",""))
            value=str(violation.get("quotaValue",""))
            if re.fullmatch(r"[A-Za-z0-9_.-]{1,180}",name) and re.fullmatch(r"[0-9.]{1,30}",value):
                found.append({"quota_id":name,"quota_value":value})
    return found


def credential_config(config: dict, credential_variable: str | None = None) -> dict:
    """Select one explicit transport credential without mutating the frozen plan."""
    selected = config["key_env"] if credential_variable is None else credential_variable
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", selected):
        raise ValueError("Credential variable must be an environment variable name")
    return {**config, "key_env": selected}


def run(model: str, env_file: Path, workers: int=4, minutes: float=180, limit: int=0, attempts: int=6, interval_seconds: float=0, credential_variable: str | None=None):
    if not 1<=workers<=4:
        raise ValueError("Use between one and four workers; account limits always take precedence")
    if not 1<=attempts<=6:
        raise ValueError("Attempt bound must be between one and six")
    if not 0<=interval_seconds<=300:
        raise ValueError("Request interval must be between zero and 300 seconds")
    prepare()
    config=read_json(OUT / "generation_plan.json")["models"][model]
    if not config.get("enabled",True):
        raise ValueError("Provider has not been configured")
    values=dict(os.environ); values.update(read_env(env_file))
    transport_config=credential_config(config,credential_variable)
    selected_credential=transport_config["key_env"]
    endpoint,headers=connection(transport_config,values)
    folder=OUT / f"generation/{model}"
    lock_path=folder / "RUNNING.lock"
    with lock_path.open("x",encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    state={"reserved":sum(r.get("reserved_usd",0) for r in read_jsonl(folder / "attempts.jsonl")),
           "backoff_until":0.0,"next_start":0.0,"new":0,"errors":[]}
    mutex=threading.Lock(); stopped=threading.Event()
    deadline=time.monotonic()+minutes*60
    recover_terminal_events(model)
    existing=read_jsonl(folder / "raw_responses.jsonl")+read_jsonl(folder / "terminal_outcomes.jsonl")
    done={r["request_id"] for r in existing}
    requests=read_jsonl(folder / "requests.jsonl")
    pending=[r for r in requests if r["request_id"] not in done][:limit or None]
    stop_path=folder / "STOP_AFTER_CURRENT"

    def item_run(item):
        body=json.dumps(item["payload"],ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
        reservation=(len(body)*config.get("input_usd_per_million",0)+4096*config.get("output_usd_per_million",0))/1e6
        opener=urllib.request.build_opener(NoRedirect)
        for attempt in range(1,attempts+1):
            with mutex:
                scheduled=max(time.monotonic(),state["next_start"])
                state["next_start"]=scheduled+interval_seconds
            while time.monotonic()<scheduled and not stopped.is_set():
                if stop_path.exists() or time.monotonic()>=deadline:
                    stopped.set(); return
                stopped.wait(min(1,scheduled-time.monotonic()))
            while time.monotonic()<state["backoff_until"] and not stopped.is_set():
                if stop_path.exists() or time.monotonic()>=deadline:
                    stopped.set(); return
                stopped.wait(min(1,state["backoff_until"]-time.monotonic()))
            if stopped.is_set() or stop_path.exists() or time.monotonic()>=deadline:
                return
            with mutex:
                if state["reserved"]+reservation>config.get("run_reservation_cap_usd",float("inf")):
                    state["errors"].append("cumulative_spending_reservation_cap"); stopped.set(); return
                state["reserved"]+=reservation
                append_record(folder / "attempts.jsonl",{"request_id":item["request_id"],"attempt":attempt,
                              "started_utc":datetime.now(timezone.utc).isoformat(),"reserved_usd":reservation,"runner":"bounded_parallel",
                              "credential_variable":selected_credential})
            req=urllib.request.Request(endpoint,data=body,headers={**headers,"Content-Type":"application/json","User-Agent":"SeparabilityResearch/2.1"})
            try:
                with opener.open(req,timeout=180) as response:
                    raw=response.read()
                    decoded=json.loads(raw)
                    safe_headers={k.lower():v for k,v in response.headers.items() if k.lower().startswith("x-ratelimit") or k.lower() in {"date","x-request-id","apim-request-id"}}
                record={"request_id":item["request_id"],"request_sha256":item["request_sha256"],
                        "received_utc":datetime.now(timezone.utc).isoformat(),"response":decoded,
                        "response_body":raw.decode("utf-8"),"response_headers":safe_headers,
                        "credential_variable":selected_credential}
                with mutex:
                    append_record(folder / "raw_responses.jsonl",record)
                    state["new"]+=1
                    count=len(done)+state["new"]
                    parsed=parse_response(item,record)
                    print(f"{model}: received {count}/{len(requests)}; QC={parsed['qc_status']}",flush=True)
                    if count%25==0:
                        consolidate(model)
                return
            except urllib.error.HTTPError as exc:
                error_bytes=exc.read()
                error_body=error_bytes.decode("utf-8",errors="replace")
                try:
                    error=json.loads(error_body).get("error",{})
                    code=str(error.get("code",error.get("status",""))) if isinstance(error,dict) else ""
                except (ValueError,AttributeError):
                    error={}
                    code="unparsed_error"
                code=code if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}",code) else "withheld"
                retry=float(exc.headers.get("retry-after","60")) if re.fullmatch(r"[0-9.]+",exc.headers.get("retry-after","60")) else 60.0
                for duration in re.findall(r'"retryDelay"\s*:\s*"([0-9.]+)s"',error_body):
                    retry=max(retry,float(duration))
                with mutex:
                    event={"request_id":item["request_id"],"credential_variable":selected_credential,
                           "timestamp":datetime.now(timezone.utc).isoformat(),"http_status":exc.code,"error_code":code,"attempt":attempt,
                           "error_body_sha256":digest_bytes(error_bytes),
                           "quota_limits":quota_summary(error),"retry_after_seconds":retry,
                           "response_headers":{k.lower():v for k,v in exc.headers.items() if k.lower() in {"date","x-request-id","apim-request-id"}}}
                    append_record(folder / "transport_events.jsonl",event)
                    if exc.code==429 and any("PerDay" in q["quota_id"] for q in event["quota_limits"]):
                        state["errors"].append("daily_quota_exhausted"); stopped.set()
                        print(f"{model}: provider daily quota exhausted; stop until reset, no credential rotation",flush=True)
                        return
                    if exc.code==400 and code=="content_filter":
                        append_record(folder / "terminal_outcomes.jsonl",terminal_from_event(item,event))
                        state["new"]+=1
                        print(f"{model}: accounted {len(done)+state['new']}/{len(requests)}; terminal HTTP content filter; no retry",flush=True)
                        return
                    if exc.code not in {429,500,502,503,504} or attempt==attempts:
                        state["errors"].append(f"HTTP_{exc.code}:{code}"); stopped.set(); return
                    wait=max(retry+2,60*attempt)
                    state["backoff_until"]=max(state["backoff_until"],time.monotonic()+wait)
                    print(f"{model}: shared provider backoff {wait:.0f}s; same credential retained",flush=True)
            except (urllib.error.URLError,TimeoutError,ValueError):
                with mutex:
                    append_record(folder / "transport_events.jsonl",{"request_id":item["request_id"],"timestamp":datetime.now(timezone.utc).isoformat(),
                                  "error_type":"transport_or_unparseable_response","attempt":attempt,
                                  "credential_variable":selected_credential})
                if attempt==attempts:
                    with mutex:
                        state["errors"].append("transport_retry_limit"); stopped.set()
                    return
                stopped.wait(min(30,5*attempt))
    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures=[executor.submit(item_run,item) for item in pending]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    stopped.set()
                    # Never print exception details that might contain a credential/URL.
                    state["errors"].append(type(exc).__name__)
        status=consolidate(model)
        status.update(runner_errors=sorted(set(state["errors"])),reserved_upper_estimate_usd=state["reserved"],workers=workers,
                      credential_variable=selected_credential)
        write_json(folder / "runner_status.json",status)
        print(json.dumps(status,indent=2),flush=True)
    finally:
        lock_path.unlink(missing_ok=True)
    return status


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",required=True)
    parser.add_argument("--env-file",type=Path,required=True)
    parser.add_argument("--workers",type=int,default=4)
    parser.add_argument("--minutes",type=float,default=180)
    parser.add_argument("--limit",type=int,default=0)
    parser.add_argument("--attempts",type=int,default=6,help="One for a bounded quota check; at most six retries per item")
    parser.add_argument("--interval-seconds",type=float,default=0,help="Minimum scheduled spacing across workers; provider backoff also applies")
    parser.add_argument("--credential-variable",help="Use this single credential variable for transport; frozen model and request payloads remain unchanged")
    args=parser.parse_args()
    status=run(args.model,args.env_file,args.workers,args.minutes,args.limit,args.attempts,args.interval_seconds,args.credential_variable)
    if status["runner_errors"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
