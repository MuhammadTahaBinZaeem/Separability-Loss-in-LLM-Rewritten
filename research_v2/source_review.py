"""A real person's source review is separate from automated source correspondence."""
from __future__ import annotations

import argparse
import json
from datetime import datetime,timezone
from pathlib import Path

from .generation import verify_corpus
from .io import OUT,file_hash,read_csv,read_json,read_jsonl,write_json,write_jsonl


def prepare():
    freeze=verify_corpus()
    rows=[{k:r[k] for k in ("passage_id","author_id","work_id","gutenberg_id",
            "source_start_char","source_end_char","text_sha256","text")}
          for r in read_csv(OUT / "corpus/originals.csv")]
    for row in rows:
        row.update(verdict="",notes="")
    folder=OUT / "source_review"
    path=folder / "blank_review.jsonl"
    if path.exists() and read_jsonl(path)!=rows:
        raise ValueError("Source review packet would change; do not replace issued evidence")
    write_jsonl(path,rows)
    manifest=folder / "issued_manifest.json"
    expected={"corpus_sha256":freeze["corpus_sha256"],"blank_sha256":file_hash(path),"items":len(rows)}
    if manifest.exists():
        if {k:v for k,v in read_json(manifest).items() if k!="issued_utc"}!=expected:
            raise ValueError("Issued source review manifest changed")
    else:
        write_json(manifest,{**expected,"issued_utc":datetime.now(timezone.utc).isoformat()})
    return expected


def check_return(path,manifest,reviewer_id,completed_utc,attested):
    if attested is not True or not str(reviewer_id).strip():
        raise ValueError("A real named/pseudonymous human must explicitly attest the source review")
    completed=datetime.fromisoformat(completed_utc.replace("Z","+00:00"))
    issued=datetime.fromisoformat(manifest["issued_utc"])
    if completed.tzinfo is None or not issued<=completed<=datetime.now(timezone.utc):
        raise ValueError("Source-review date must be actual, timezone-aware and after issue")
    blank=read_jsonl(OUT / "source_review/blank_review.jsonl")
    expected={r["passage_id"]:r for r in blank}
    rows=read_jsonl(path)
    if len(rows)!=len(expected) or len({r.get("passage_id") for r in rows})!=len(rows) or {r.get("passage_id") for r in rows}!=set(expected):
        raise ValueError("Every frozen passage must be reviewed exactly once")
    for row in rows:
        original=expected[row["passage_id"]]
        if any(row.get(k)!=v for k,v in original.items() if k not in {"verdict","notes"}):
            raise ValueError("Reviewed source identifiers, offsets or text changed")
        if row.get("verdict") not in {"pass","needs_correction"} or not str(row.get("notes","")).strip():
            raise ValueError("Each source needs an explicit verdict and substantive review note")
    return rows


def ingest(path: Path,reviewer_id: str,completed_utc: str,attested: bool):
    prepare()
    folder=OUT / "source_review"
    manifest=read_json(folder / "issued_manifest.json")
    rows=check_return(path,manifest,reviewer_id,completed_utc,attested)
    target=folder / "private/original_return.jsonl"
    registry=folder / "private/attestation.json"
    if target.exists() or registry.exists():
        raise ValueError("A registered source review already exists; preserve it, do not overwrite")
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("xb") as stream:
        stream.write(path.read_bytes())
    write_json(registry,{"reviewer_id":reviewer_id,"completed_utc":completed_utc,"attested_human":attested,
                        "corpus_sha256":manifest["corpus_sha256"],"return_sha256":file_hash(target),"items":len(rows)})
    return validate()


def validate():
    folder=OUT / "source_review"
    if not (folder / "private/attestation.json").exists():
        return {"passed":False,"reason":"No registered human source review of all 360 passages"}
    record=read_json(folder / "private/attestation.json")
    manifest=read_json(folder / "issued_manifest.json")
    freeze=verify_corpus()
    if (record["corpus_sha256"]!=freeze["corpus_sha256"] or manifest["corpus_sha256"]!=freeze["corpus_sha256"]
        or manifest["blank_sha256"]!=file_hash(folder / "blank_review.jsonl")
        or record["return_sha256"]!=file_hash(folder / "private/original_return.jsonl")):
        raise ValueError("Source-review evidence does not match the frozen artifacts")
    rows=check_return(folder / "private/original_return.jsonl",manifest,record["reviewer_id"],record["completed_utc"],record["attested_human"])
    flagged=sum(r["verdict"]!="pass" for r in rows)
    return {"passed":not flagged,"reviewed":len(rows),"flagged":flagged,"return_sha256":record["return_sha256"],
            "scope":"Human-attested review, not cryptographic proof of who did the reading"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["prepare","ingest","validate"])
    parser.add_argument("--file",type=Path)
    parser.add_argument("--reviewer-id")
    parser.add_argument("--completed-utc")
    parser.add_argument("--attest-human",action="store_true")
    args=parser.parse_args()
    if args.action=="prepare":
        result=prepare()
    elif args.action=="validate":
        result=validate()
    else:
        if not all((args.file,args.reviewer_id,args.completed_utc)):
            parser.error("Ingest requires file, reviewer ID and actual completed UTC timestamp")
        result=ingest(args.file,args.reviewer_id,args.completed_utc,args.attest_human)
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
