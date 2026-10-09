"""Allowlisted, secret-scanned local v3 packages; no upload and no claimed DOI."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from .archive import SECRET_PATTERNS, scan
from .credentials import read_env
from .expanded_primary import DESTINATION, inputs as primary_inputs
from .expanded_study import BASE, effective_plan
from .io import OUT, ROOT, digest_text, file_hash, read_json, read_jsonl, write_json
from .session_workers import audit as session_audit
from .transfer_extension import fingerprints

GENERATION_FILES = ("requests.jsonl", "request_manifest.json", "assignments.jsonl", "outcomes.jsonl", "attempts.jsonl",
                    "rewrites.csv", "completion.json", "all_native_attempts.csv", "failed_visible_outputs.jsonl",
                    "session_outputs.jsonl", "delegation_launches.json", "delegation_additional_launches.jsonl",
                    "delegation_continuations.jsonl", "delegation_tool_events.jsonl", "released_batches.jsonl",
                    "generation_completion_20260928.json")
PRIVATE_NAMES = {"private", "returns", "__pycache__", ".git", ".venv", "private_join_key.csv", "reviewer_registry.json",
                 "credentials.json", "access.txt", "api.env", "RUNNING.lock", "STOP_AFTER_CURRENT"}
REVIEWED_OUTPUTS = {"flags.csv", "agreement.csv", "rating_summary.csv", "comparisons.csv", "ratings.csv",
                    "adjudication_decisions.csv", "source_verdicts.csv", "participant_methods.json"}


def safe_member(path, root=ROOT):
    path, root = Path(path), Path(root)
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError("Unsafe archive path")
    relative = path.relative_to(root)
    lower = {p.casefold() for p in relative.parts}
    if lower.intersection(n.casefold() for n in PRIVATE_NAMES) or path.suffix.lower() in {".env", ".sqlite", ".sqlite3", ".db", ".pyc", ".zip"} or path.name.lower().startswith(".env") or "private_access" in path.name.lower():
        raise ValueError("Private or live member selected for archive")
    if not path.is_file():
        raise ValueError("Missing archive input")
    return path


def include_manifest(folder, paths, expected_inputs=None, replay_required=True):
    manifest_path = folder / "manifest.json"
    manifest = read_json(manifest_path)
    if expected_inputs is not None and manifest["inputs"] != expected_inputs:
        raise ValueError("Stale analysis inputs")
    paths.add(safe_member(manifest_path))
    for relative, expected in manifest["inputs"].items():
        path = safe_member(ROOT / relative)
        if file_hash(path) != expected:
            raise ValueError("Archived analysis input changed")
        paths.add(path)
    for relative, expected in manifest["output_hashes"].items():
        path = safe_member(folder / relative)
        if not path.resolve().is_relative_to(folder.resolve()) or file_hash(path) != expected:
            raise ValueError("Archived analysis output changed or escaped its folder")
        paths.add(path)
    for name in ("verification.json", "replay_verification.json"):
        path = folder / name
        if path.exists():
            receipt = read_json(path)
            if not receipt.get("passed") or receipt.get("manifest_sha256") != file_hash(manifest_path):
                raise ValueError("Analysis verification is stale or failed")
            paths.add(safe_member(path))
        elif name == "replay_verification.json" and replay_required:
            raise ValueError("Replay evidence is required before packaging")


def include_returned_review_results(paths):
    """Only pseudonymous derived tables; never intake records or reviewer notes."""
    if (BASE / "review_release/status.json").exists():
        include_current_review_release(paths)
        return  # Historical provisional receipts remain preserved, not re-certified.
    allowed = {"flags.csv", "agreement.csv", "rating_summary.csv", "comparisons.csv"}
    for manifest_path in sorted((BASE / "review_results").glob("provisional_*/manifest.json")):
        manifest = read_json(manifest_path)
        if (manifest.get("stage") != "provisional_analysis_pending_reviewer_metadata"
            or manifest.get("review_provenance_complete") is not False
            or manifest.get("submission_ready") is not False
            or not manifest.get("result_replay_passed")
            or set(manifest.get("output_hashes", {})) != allowed):
            raise ValueError("Unexpected returned-review release scope")
        for name, expected in manifest["analysis_code_sha256"].items():
            path = safe_member(ROOT / "research_v2" / name)
            if path.parent != ROOT / "research_v2" or file_hash(path) != expected:
                raise ValueError("Returned-review analysis code changed")
        for name, expected in manifest["output_hashes"].items():
            path = safe_member(manifest_path.parent / name)
            if path.parent != manifest_path.parent or file_hash(path) != expected:
                raise ValueError("Returned-review derived output changed")
            paths.add(path)
        paths.add(safe_member(manifest_path))


def include_current_review_release(paths):
    status_path = BASE / "review_release/status.json"
    status = read_json(status_path)
    folder = BASE / status["release_folder"]
    if not folder.resolve().is_relative_to((BASE / "review_release").resolve()):
        raise ValueError("Reviewed release escaped its allowed folder")
    manifest_path = safe_member(folder / "manifest.json")
    manifest = read_json(manifest_path)
    if (not status.get("complete") or file_hash(manifest_path) != status["manifest_sha256"]
        or manifest.get("stage") != "registered_investigator_reported_reviews" or manifest.get("review_complete") is not True
        or manifest.get("submission_ready") is not False or manifest.get("submission_ethics_gate_satisfied") is not False
        or manifest.get("independence_objectively_verified") is not False
        or not manifest.get("public_ratings_replay_passed") or not manifest.get("result_replay_passed")
        or set(manifest.get("output_hashes", {})) != REVIEWED_OUTPUTS or not manifest.get("analysis_code_sha256")):
        raise ValueError("Unexpected reviewed release scope or provenance claim")
    for name, expected in manifest["analysis_code_sha256"].items():
        path = safe_member(ROOT / "research_v2" / name)
        if path.parent != ROOT / "research_v2" or file_hash(path) != expected:
            raise ValueError("Reviewed-release analysis code changed")
    for name, expected in manifest["output_hashes"].items():
        path = safe_member(folder / name)
        if path.parent != folder or file_hash(path) != expected:
            raise ValueError("Reviewed-release derived output changed")
        paths.add(path)
    if file_hash(BASE / "annotations/validation.json") != manifest["semantic_validation_sha256"]:
        raise ValueError("Registered review validation changed")
    for relative in ("annotations/verified_flags.csv", "annotations/agreement.csv", "annotations/validation.json",
                     "semantic_sensitivity/comparisons.csv", "semantic_sensitivity/status.json"):
        paths.add(safe_member(BASE / relative))
    if (file_hash(BASE / "annotations/verified_flags.csv") != manifest["output_hashes"]["flags.csv"]
        or file_hash(BASE / "semantic_sensitivity/comparisons.csv") != manifest["output_hashes"]["comparisons.csv"]):
        raise ValueError("Registered review and released calculations disagree")
    paths.update({manifest_path, safe_member(status_path)})


def package_files():
    plan = effective_plan()
    if list(BASE.rglob("RUNNING.lock")):
        raise ValueError("Wait for all live generation/analysis writers")
    for model in plan["active_models"]:
        if not read_json(BASE / f"generation/{model}/completion.json")["accounting_complete"]:
            raise ValueError("All six intended arms must have complete accounting")
    evidence = session_audit()
    if not evidence["passed"] or not evidence["accounting_complete"]:
        raise ValueError("Astra session receipts are incomplete")
    paths = {ROOT / name for name in ("requirements-v2.lock", "requirements-v2.in", "scripts/13_extract_stylometric_features.py")}
    paths.update((ROOT / "research_v2").glob("*.py"))
    paths.update((ROOT / "tests").glob("*.py"))
    paths.update(ROOT / f"review_app/{name}" for name in ("index.html", "app.js", "style.css", "README.md"))
    include_returned_review_results(paths)
    markdown = BASE / "review_markdown_20261002"
    if (markdown / "issued_manifest.json").exists():
        receipt = read_json(markdown / "issued_manifest.json")
        for name, expected in receipt["files_sha256"].items():
            path = safe_member(markdown / name)
            if path.parent != markdown or file_hash(path) != expected:
                raise ValueError("Issued Markdown review handout changed")
            paths.add(path)
        paths.add(safe_member(markdown / "issued_manifest.json"))
        paths.add(safe_member(BASE / "MARKDOWN_REVIEW_HANDOFF.md"))
        paths.add(safe_member(BASE / "MARKDOWN_REVIEW_AMENDMENT.md"))
    paths.update(p for p in (OUT / "sources").rglob("*") if p.is_file())
    paths.update(OUT / name for name in ("corpus/originals.csv", "corpus/freeze.json",
                                        "source_review/INSTRUCTIONS.md", "source_review/blank_review.jsonl",
                                        "source_review/issued_manifest.json", "annotations/INSTRUCTIONS.md"))
    paths.update(BASE / name for name in ("PROTOCOL.md", "PRIMARY_ANALYSIS_PLAN.md", "generation_plan.json", "scope_amendment.json",
                                         "astra_delegation_amendment.json", "corpus/originals.csv", "corpus/freeze.json", "corpus/lineage.csv"))
    paths.add(OUT / "expansion/session_arm_provenance.json")
    for model in plan["active_models"]:
        folder = BASE / "generation" / model
        paths.update(folder / name for name in GENERATION_FILES if (folder / name).exists())
        if model == "astra_session":
            paths.update(p for p in (folder / "batches").glob("*") if p.is_file())
            paths.update(p for p in (folder / "workers").glob("*.json") if p.is_file())
        include_manifest(DESTINATION / model, paths, primary_inputs(model))
        extension = BASE / "extensions/jql_v1"
        include_manifest(extension / model, paths, fingerprints(model, BASE, extension))
        include_manifest(extension / model / "explanatory_model", paths)
    # Only blank forms, neutral instructions, and aggregate derived evidence;
    # no private reviewer records, free-text returns, tokens or join keys.
    for relative in ("README.md", "RETURNED_REVIEW_RESULTS.md", "PUBLICATION_ASSESSMENT_20261006.md", "POST_REVIEW_HANDOFF.md",
                     "annotations/REVIEWER_GUIDE.md", "source_review/REVIEWER_GUIDE.md",
                     "annotations/forms/reviewer_A.csv", "annotations/forms/reviewer_B.csv",
                     "annotations/issued_manifest.json", "source_review/blank_review.jsonl", "source_review/issued_manifest.json",
                     "failures/visible_failure_index.jsonl", "failures/visible_failure_index_status.json",
                     "primary_analysis/all_models_comparisons.csv", "primary_analysis/status.json",
                     "verification/tests_current.json", "verification/tests_current.xml",
                     "verification/astra_generation_complete_20260928.json", "verification/local_delivery.json"):
        path = BASE / relative
        if path.exists():
            paths.add(path)
    return [safe_member(p) for p in sorted(paths)]


def scan_package(paths, env_file):
    """Classify one known regex false positive in provider-encrypted reasoning.

    Exact supplied credentials are still checked against every raw package byte.
    The only pattern exception is an encrypted_content field in a reasoning item;
    the duplicate native response_body must decode to the same response object.
    """
    result = scan(paths, env_file)
    if result["passed"]:
        return result
    relative = "revision/expanded_v3/generation/codex51/outcomes.jsonl"
    if result["matched_files"] != [relative]:
        return result
    path = ROOT / relative
    raw = path.read_bytes()
    values = read_env(env_file)
    if any(value.encode("utf-8") in raw for key, value in values.items()
           if len(value) >= 12 and any(word in key.lower() for word in ("key", "token", "gemchat", "gemtest"))):
        return result
    classified = 0
    for event in read_jsonl(path):
        response = event.get("response")
        body = event.get("response_body")
        if response is not None and body is not None:
            if json.loads(body) != response:
                return result
            del event["response_body"]
        if isinstance(response, dict):
            for item in response.get("output", []):
                if item.get("type") == "reasoning" and isinstance(item.get("encrypted_content"), str):
                    if any(re.search(pattern, item["encrypted_content"].encode()) for pattern in SECRET_PATTERNS):
                        classified += 1
                    del item["encrypted_content"]
        public_fields = json.dumps(event, ensure_ascii=False, sort_keys=True).encode("utf-8")
        if any(re.search(pattern, public_fields) for pattern in SECRET_PATTERNS):
            return result
    if not classified:
        return result
    return {**result, "passed": True, "matched_files": [],
            "encrypted_reasoning_pattern_exception": {"file": relative, "records": classified,
                                                       "body_equivalence_checked": True},
            "note": "Raw exact-value scan passed; only provider-encrypted reasoning matched the generic sk- pattern."}


def build(env_file):
    if not env_file:
        raise ValueError("Supply the private env path for an exact-value credential scan")
    paths = package_files()
    security = scan_package(paths, env_file)
    if not security["passed"] or not security["exact_credential_scan"]:
        raise ValueError("Exact-value credential scan failed; no package created")
    hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths}
    package_id = digest_text(json.dumps(hashes, sort_keys=True))
    review_status = BASE / "review_release/status.json"
    reviewed = review_status.exists() and read_json(review_status).get("complete") is True
    manifest = {"package_id": package_id, "files_sha256": hashes,
                "publication_status": "local_reviewed_release_candidate_not_published" if reviewed else "local_review_only_not_published", "doi": None,
                "private_review_returns_included": False, "license": "pending_investigator_rights_review",
                "deidentified_numeric_ratings_included": reviewed, "review_basis": "investigator_reported_not_objectively_certified" if reviewed else "pending",
                "review_complete": reviewed, "submission_ethics_gate_satisfied": False, "submission_ready": False}
    prefix = "REVIEWED" if reviewed else "REVIEW_ONLY"
    archive = BASE / f"archive/{prefix}_v3_{package_id[:16]}.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        members = [(name, (ROOT / name).read_bytes()) for name in hashes]
        members.append(("PACKAGE_MANIFEST.json", (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()))
        for name, data in sorted(members):
            if name in hashes and hashlib.sha256(data).hexdigest() != hashes[name]:
                raise ValueError("Package input changed during collection")
            entry = zipfile.ZipInfo(name, date_time=(2026, 9, 27, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            output.writestr(entry, data, compresslevel=6)
    with zipfile.ZipFile(archive) as check:
        if check.testzip() or set(check.namelist()) != set(hashes) | {"PACKAGE_MANIFEST.json"}:
            raise ValueError("Package member verification failed")
        for name, expected in hashes.items():
            if hashlib.sha256(check.read(name)).hexdigest() != expected:
                raise ValueError("Package hash verification failed")
    result = {"local_package": archive.relative_to(ROOT).as_posix(), "package_sha256": file_hash(archive),
              "files": len(hashes), "bytes": archive.stat().st_size, "secret_scan": security,
              "publication_status": "not_published", "review_complete": reviewed,
              "submission_ethics_gate_satisfied": False, "submission_ready": False}
    write_json(BASE / "archive/candidate.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.env_file), indent=2))
