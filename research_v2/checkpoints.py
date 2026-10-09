"""Import immutable GitHub generation artifacts without losing local responses."""
from __future__ import annotations

import argparse
from pathlib import Path

from .generation import append_record, consolidate
from .io import OUT, file_hash, read_jsonl, write_json


def merge(model: str, downloaded: Path, run_id: str = "") -> dict:
    target=OUT / f"generation/{model}"
    for filename in ("requests.jsonl","request_manifest.json"):
        if file_hash(downloaded / filename)!=file_hash(target / filename):
            raise ValueError(f"Downloaded artifact uses different frozen inputs: {filename}")
    local={r["request_id"]:r for r in read_jsonl(target / "raw_responses.jsonl")}
    incoming=read_jsonl(downloaded / "raw_responses.jsonl")
    if len({r["request_id"] for r in incoming})!=len(incoming):
        raise ValueError("Duplicate incoming response IDs")
    for row in incoming:
        if row["request_id"] in local and local[row["request_id"]]!=row:
            raise ValueError("Conflicting provider responses; preserve separately and investigate")
    for row in incoming:
        if row["request_id"] not in local:
            append_record(target / "raw_responses.jsonl",row)
    events=read_jsonl(target / "transport_events.jsonl")
    for event in read_jsonl(downloaded / "transport_events.jsonl"):
        if event not in events:
            append_record(target / "transport_events.jsonl",event)
            events.append(event)
    result=consolidate(model)
    if run_id:
        if not run_id.isdigit():
            raise ValueError("A GitHub run ID must be numeric")
        write_json(target / f"runs/{run_id}.json",{"run_id":run_id,"model_key":model,
            "url":f"https://github.com/MuhammadTahaBinZaeem/Separability-Loss-in-LLM-Rewritten/actions/runs/{run_id}",
            "artifact_raw_sha256":file_hash(downloaded / "raw_responses.jsonl") if incoming else "",
            "received":len(incoming),"transport_events":len(read_jsonl(downloaded / "transport_events.jsonl"))})
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",choices=["gptoss120","qwen27"],required=True)
    parser.add_argument("--directory",type=Path,required=True)
    parser.add_argument("--run-id",default="")
    args=parser.parse_args()
    print(merge(args.model,args.directory,args.run_id))


if __name__=="__main__":
    main()
