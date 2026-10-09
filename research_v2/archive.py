"""Local, deterministic review packages. Never upload, publish or invent a DOI."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from .credentials import read_env
from .io import OUT,ROOT,digest_text,file_hash,read_json,write_json

DIRECTORIES=("research_v2","tests","review_app","revision/sources","revision/corpus","revision/results","revision/paper_assets","revision/legacy")
EXPLICIT=("requirements.txt","requirements-v2.in","requirements-v2.lock","environment.yml",".gitattributes",
          "revision/PROTOCOL.md","revision/AMENDMENTS.md","revision/REPRODUCE.md","revision/STATUS.md",
          "revision/LITERATURE_CHECK.md","revision/generation_plan.json","revision/work_specs.json",
          "revision/manuscript_v2_template.md","revision/annotations/INSTRUCTIONS.md","revision/annotations/review_scope.json",
          "revision/annotations/RECRUITMENT.md","revision/source_review/INSTRUCTIONS.md",
          "scripts/09_validate_rewrite_outputs.py","scripts/13_extract_stylometric_features.py",
          "scripts/build_manuscript_docx.py","scripts/export_manuscript_pdf.ps1","scripts/resume_and_finish_v2.ps1","scripts/start_review_app.ps1",
          "data/processed/selected_original_passages.csv","data/interim/rewrite_responses_parsed.csv","metadata/rewrite_qc_report.csv")
GENERATION=("requests.jsonl","request_manifest.json","raw_responses.jsonl","terminal_outcomes.jsonl",
            "transport_events.jsonl","attempts.jsonl","rewrites.csv","completion.json","runner_status.json")
DISALLOWED={".env","api.env","RUNNING.lock","STOP_AFTER_CURRENT","reviewer_registry.json","private_join_key.csv"}
SECRET_PATTERNS=(rb"AIza[0-9A-Za-z_-]{30,}",rb"(?:ghp_|github_pat_)[0-9A-Za-z_]{30,}",rb"sk-(?:proj-)?[0-9A-Za-z_-]{32,}")


def package_files():
    paths={ROOT / name for name in EXPLICIT}
    for directory in DIRECTORIES:
        paths.update(p for p in (ROOT / directory).rglob("*") if p.is_file())
    for model in read_json(OUT / "generation_plan.json")["models"]:
        paths.update(OUT / f"generation/{model}/{name}" for name in GENERATION if (OUT / f"generation/{model}/{name}").exists())
    # Select research extensions through their explicit result manifests, never
    # by recursively collecting arbitrary notes, private returns or live files.
    extension=OUT / "extensions/jql_v1"
    paths.update(extension / name for name in ("PLAN.md","EXPLANATORY_MODEL_PLAN.md","ASSESSMENT.md","NEXT_VALIDATION.md")
                 if (extension / name).exists())
    for model in ("azure_replication","gem31lite"):
        for folder in (extension / model,extension / model / "explanatory_model"):
            manifest_path=folder / "manifest.json"
            if not manifest_path.exists():
                continue
            paths.add(manifest_path)
            manifest=read_json(manifest_path)
            for relative,expected in manifest["output_hashes"].items():
                path=folder / relative
                if not path.resolve().is_relative_to(folder.resolve()) or file_hash(path)!=expected:
                    raise ValueError("Extension archive member is unsafe or differs from its manifest")
                paths.add(path)
            for relative,expected in manifest["inputs"].items():
                if not (ROOT / relative).resolve().is_relative_to(ROOT.resolve()) or file_hash(ROOT / relative)!=expected:
                    raise ValueError("Extension inputs changed; recompute before packaging")
            for filename in ("verification.json","replay_verification.json"):
                verification=folder / filename
                if verification.exists():
                    if read_json(verification).get("manifest_sha256")!=file_hash(manifest_path):
                        raise ValueError("Extension verification is stale")
                    paths.add(verification)
    selected=[]
    for path in sorted(paths):
        relative=path.relative_to(ROOT)
        if "__pycache__" in relative.parts or path.suffix==".pyc":
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Unsafe archive member path")
        if not path.exists():
            raise ValueError(f"Required archive input is missing: {relative.as_posix()}")
        if path.name in DISALLOWED or path.suffix==".env":
            raise ValueError("Private/credential file in package selection")
        selected.append(path)
    return selected


def scan(paths,env_file=None):
    # Exact supplied credentials stay in memory; only matching filenames are reported.
    values=read_env(env_file) if env_file else {}
    needles=[v.encode("utf-8") for k,v in values.items() if len(v)>=12 and any(word in k.lower() for word in ("key","token","gemchat","gemtest"))]
    matches=[]
    for path in paths:
        data=path.read_bytes()
        if any(needle in data for needle in needles) or any(re.search(pattern,data) for pattern in SECRET_PATTERNS):
            matches.append(path.relative_to(ROOT).as_posix())
    return {"passed":not matches,"matched_files":matches,"files_scanned":len(paths),"exact_credential_scan":bool(needles),
            "scope":"Selected package bytes only; not proof that all possible secrets or private reviewer notes are absent."}


def build(env_file=None):
    if any((OUT / f"generation/{m}/RUNNING.lock").exists() for m in read_json(OUT / "generation_plan.json")["models"]):
        raise ValueError("Do not package live append-only generation ledgers")
    if list((OUT / "extensions").rglob("RUNNING.lock")):
        raise ValueError("Do not package an actively running research extension")
    document=OUT / "paper_assets/manuscript_REVIEW_DRAFT.docx"
    if document.exists():
        reading_copy=read_json(OUT / "paper_assets/document_build.json")
        if reading_copy["source_sha256"]!=file_hash(OUT / "paper_assets/manuscript_REVIEW_DRAFT.md") or reading_copy["docx_sha256"]!=file_hash(document):
            raise ValueError("Reading copy is stale; rebuild DOCX/PDF from the current generated Markdown before packaging")
    paths=package_files()
    security=scan(paths,env_file)
    write_json(OUT / "verification/package_secret_scan.json",security)
    if not security["passed"]:
        raise ValueError("Possible credential found; package not created. Only filenames are in the restricted scan report.")
    hashes={p.relative_to(ROOT).as_posix():file_hash(p) for p in paths}
    package_id=digest_text(json.dumps(hashes,sort_keys=True))
    archive=OUT / f"archive/REVIEW_ONLY_v2_{package_id[:16]}.zip"
    archive.parent.mkdir(parents=True,exist_ok=True)
    manifest={"package_id":package_id,"files_sha256":hashes,"publication_status":"not_published",
              "human_returns_included":False,"license":"not_assigned_pending_investigator_rights_review",
              "note":"Local computational review package, not a final submission/archive deposit. No DOI asserted."}
    members={name:(ROOT / name).read_bytes() for name in hashes}
    members["PACKAGE_MANIFEST.json"]=(json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode()
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as output:
        for name,data in sorted(members.items()):
            entry=zipfile.ZipInfo(name,date_time=(2026,9,15,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED; entry.create_system=3; entry.external_attr=0o100644<<16
            output.writestr(entry,data,compresslevel=6)
    with zipfile.ZipFile(archive) as check:
        if check.testzip() is not None or set(check.namelist())!=set(members):
            raise ValueError("Archive verification failed")
        for name,expected in hashes.items():
            if hashlib.sha256(check.read(name)).hexdigest()!=expected:
                raise ValueError("Archive member differs from selected input")
    report={"local_package":archive.relative_to(ROOT).as_posix(),"package_sha256":file_hash(archive),
            "package_bytes":archive.stat().st_size,"file_count":len(hashes),"publication_status":"not_published",
            "final_archive_ready":False,"private_human_returns_included":False,"secret_scan":security}
    write_json(OUT / "archive/candidate.json",report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file",type=Path,help="Optional local secret file for exact-value scan; values never enter package/logs")
    args=parser.parse_args()
    print(json.dumps(build(args.env_file),indent=2))


if __name__=="__main__":
    main()
