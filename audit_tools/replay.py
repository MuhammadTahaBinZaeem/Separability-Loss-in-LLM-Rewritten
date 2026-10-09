"""Offline public audit and numerical replay; no model requests or participant data.

Install the exact requirements-v2.lock environment. This additive entry point
uses the frozen scientific functions and leaves repository evidence unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def checked_manifest(root):
    path = root / "audit/PUBLIC_FILE_MANIFEST.json"
    manifest = read_json(path)
    files = manifest["files"]
    if not isinstance(files, dict) or not files:
        raise ValueError("Public file manifest must contain a nonempty files mapping")
    for name, record in files.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
            raise ValueError("Unsafe manifest member: " + name)
        target = root.joinpath(*relative.parts)
        if not target.resolve().is_relative_to(root.resolve()) or target.is_symlink():
            raise ValueError("Manifest member escapes repository or is a symlink: " + name)
        if not target.is_file() or target.stat().st_size != record["bytes"] or sha(target) != record["sha256"]:
            raise ValueError("Missing or changed published file: " + name)
    return manifest, sha(path)


def check_sources(root):
    from research_v2.corpus import AUTHORS, clean_text, source_text, words
    from research_v2.expanded_study import BASE
    from research_v2.io import digest_text, file_hash, read_csv
    freeze = read_json(BASE / "corpus/freeze.json")
    for name, key in (("corpus/originals.csv", "originals_file_sha256"),
                      ("corpus/lineage.csv", "lineage_sha256"), ("PROTOCOL.md", "protocol_sha256")):
        if file_hash(BASE / name) != freeze[key]:
            raise ValueError("Frozen corpus/protocol differs: " + name)
    originals = read_csv(BASE / "corpus/originals.csv")
    if len(originals) != 360 or Counter(row["author_id"] for row in originals) != Counter({a: 60 for a in AUTHORS}):
        raise ValueError("Unexpected source cardinality/author balance")
    if len({row["passage_id"] for row in originals}) != 360 or len({row["text_sha256"] for row in originals}) != 360:
        raise ValueError("Duplicate source ID or passage hash")
    groups = defaultdict(list)
    raw = {row["gutenberg_id"]: source_text(int(row["gutenberg_id"])) for row in originals}
    for row in originals:
        start, end = int(row["source_start_char"]), int(row["source_end_char"])
        if start < 0 or end <= start or end > len(raw[row["gutenberg_id"]]):
            raise ValueError("Invalid archived source span")
        if clean_text(raw[row["gutenberg_id"]][start:end]) != row["text"]:
            raise ValueError("Selected passage is not reproducible from its source span")
        if digest_text(row["text"]) != row["text_sha256"] or not 450 <= words(row["text"]) <= 650:
            raise ValueError("Passage hash or length differs")
        groups[row["author_id"], row["work_id"]].append(row)
    if len(groups) != 18 or any(len(rows) != 20 for rows in groups.values()):
        raise ValueError("Unexpected work balance")
    for rows in groups.values():
        if len({row["outer_fold"] for row in rows}) != 1:
            raise ValueError("A work is split across outer folds")
        spans = sorted((int(row["source_start_char"]), int(row["source_end_char"])) for row in rows)
        if any(first[1] > second[0] for first, second in zip(spans, spans[1:])):
            raise ValueError("Within-work source spans overlap")
    for fold in ("0", "1", "2"):
        test = [row for row in originals if row["outer_fold"] == fold]
        if len(test) != 120 or Counter(row["author_id"] for row in test) != Counter({a: 20 for a in AUTHORS}):
            raise ValueError("Outer-fold balance differs")
    spec_path = root / "audit_tools/work_specs.json"
    if sha(spec_path) != read_json(root / "revision/corpus/freeze.json")["work_specs_sha256"]:
        raise ValueError("Public work specifications differ from the frozen selection")
    registry = []
    for spec in read_json(spec_path):
        rows = groups[spec["author_id"], spec["work_id"]]
        source = read_json(root / f"revision/sources/pg{spec['source_id']}.json")
        registry.append({"author_id": spec["author_id"], "work_id": spec["work_id"], "title": spec["title"],
                         "gutenberg_id": spec["source_id"], "canonical_url": source["canonical_url"],
                         "download_url": source["download_url"], "source_raw_sha256": source["raw_sha256"],
                         "selected_passages": len(rows), "outer_fold": rows[0]["outer_fold"],
                         "replacement_passages": sum(row["passage_id"].startswith("V3_") for row in rows),
                         "rights_notice": source["copyright_notice"]})
    return originals, registry, {"passed": True, "passages": 360, "works": 18, "folds": 3,
                                 "scope": "Archived spans, hashes, lengths, balance, nonoverlap and held-out-work grouping",
                                 "participant_source_review_verified": False}


def check_generation(originals):
    from research_v2.expanded_study import BASE, effective_plan
    from research_v2.expanded_primary import check_output_hash
    from research_v2.io import digest_text, file_hash, read_csv, read_jsonl
    plan = effective_plan()
    source_index = {row["passage_id"]: row for row in originals}
    results = []
    for model in plan["active_models"]:
        folder = BASE / "generation" / model
        manifest = read_json(folder / "request_manifest.json")
        for name in ("requests", "assignments"):
            if file_hash(folder / f"{name}.jsonl") != manifest[f"{name}_sha256"]:
                raise ValueError("Request/assignment manifest differs: " + model)
        if file_hash(BASE / "generation_plan.json") != manifest["plan_sha256"]:
            raise ValueError("Generation plan differs")
        if "scope_amendment_sha256" in manifest and file_hash(BASE / "scope_amendment.json") != manifest["scope_amendment_sha256"]:
            raise ValueError("Model-scope amendment differs")
        requests = read_jsonl(folder / "requests.jsonl")
        for request in requests:
            payload_hash = digest_text(json.dumps(request["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            if payload_hash != request["request_sha256"]:
                raise ValueError("Recorded request payload differs")
        assignments = read_jsonl(folder / "assignments.jsonl")
        assignment_index = {row["assignment_id"]: row for row in assignments}
        rows = read_csv(folder / "rewrites.csv")
        if len(rows) != 1080 or len(assignment_index) != 1080 or len({row["assignment_id"] for row in rows}) != 1080:
            raise ValueError("Expected exactly 1,080 accounted-for unique assignments per arm")
        expected_pairs = {(row["passage_id"], condition) for row in originals for condition in plan["conditions"]}
        if {(row["passage_id"], row["condition"]) for row in rows} != expected_pairs:
            raise ValueError("Generation passage/instruction grid differs")
        for row in rows:
            assignment = assignment_index[row["assignment_id"]]
            if any(row[key] != assignment[key] for key in ("source_sha256", "passage_id", "request_sha256", "request_id")):
                raise ValueError("Rewrite lineage differs from the assignment")
            if row["source_sha256"] != source_index[row["passage_id"]]["text_sha256"]:
                raise ValueError("Rewrite source hash differs from corrected corpus")
            if row["qc_status"] not in {"pass", "warning", "fail"}:
                raise ValueError("Unknown technical outcome status")
            check_output_hash(row)
        count = Counter(row["qc_status"] for row in rows)
        completion = read_json(folder / "completion.json")
        if not completion["accounting_complete"] or completion["accounted"] != len(rows):
            raise ValueError("Generation completion record differs")
        results.append({"model_key": model, "outcomes": len(rows), "valid": count["pass"] + count["warning"],
                        "passed_technical_qc": count["pass"], "warning": count["warning"], "failed": count["fail"]})
    totals = {key: sum(row[key] for row in results) for key in ("outcomes", "valid", "failed")}
    if totals != {"outcomes": 6480, "valid": 6118, "failed": 362}:
        raise ValueError("Frozen study outcome totals differ")
    return {"passed": True, **totals, "arms": results,
            "scope": "Recorded first-outcome grid, request hashes, corrected-source lineage and output hashes; no regeneration"}


def check_primary():
    from research_v2.corpus import AUTHORS
    from research_v2.expanded_study import BASE, effective_plan
    from research_v2.inference import holm
    from research_v2.io import read_csv
    from sklearn.metrics import f1_score
    grouped = defaultdict(list)
    for model in effective_plan()["active_models"]:
        for row in read_csv(BASE / f"primary_analysis/{model}/predictions.csv"):
            if row["feature_set"] == "full":
                grouped[row["model_key"], row["classifier"], row["condition"]].append(row)
    comparisons = read_csv(BASE / "primary_analysis/all_models_comparisons.csv")
    if len(comparisons) != 54:
        raise ValueError("Incomplete primary test family")
    for row in comparisons:
        original = {item["passage_id"]: item for item in grouped[row["model_key"], row["classifier"], "original"]}
        rewritten = grouped[row["model_key"], row["classifier"], row["condition"]]
        if len({item["passage_id"] for item in rewritten}) != len(rewritten):
            raise ValueError("Duplicate paired primary prediction")
        y = [item["author_id"] for item in rewritten]
        first = f1_score(y, [original[item["passage_id"]]["predicted_author"] for item in rewritten],
                         labels=AUTHORS, average="macro", zero_division=0)
        second = f1_score(y, [item["predicted_author"] for item in rewritten], labels=AUTHORS, average="macro", zero_division=0)
        for key, value in (("original_macro_f1", first), ("rewrite_macro_f1", second), ("macro_f1_loss", first - second)):
            if abs(float(row[key]) - value) > 1e-12:
                raise ValueError("Primary paired estimate differs: " + key)
        if int(row["paired_passages"]) != len(rewritten):
            raise ValueError("Primary paired sample count differs")
    adjusted = holm([float(row["p_work_swap_two_sided"]) for row in comparisons], family_size=54)
    if any(abs(float(row["p_holm"]) - value) > 1e-12 for row, value in zip(comparisons, adjusted)):
        raise ValueError("Family-wide Holm adjustment differs")
    return {"passed": True, "primary_point_estimates": 54, "holm_adjustment_reconstructed": True,
            "classifiers_refitted": False, "raw_permutation_pvalues_and_intervals_recomputed": False,
            "participant_ratings_replayed": False,
            "withheld_review_scope": "Individual ratings, pair-level risk decisions and adjudication remain withheld; review-gated results cannot be independently reconstructed from this public snapshot."}


def check_scientific_manifests(root, public_manifest):
    """Link the public hashes back to unchanged original analysis manifests."""
    from research_v2.expanded_study import BASE, effective_plan
    records = public_manifest["files"]
    manifests, inputs_checked, outputs_checked = 0, 0, 0
    for model in effective_plan()["active_models"]:
        folders = (BASE / f"primary_analysis/{model}", BASE / f"extensions/jql_v1/{model}",
                   BASE / f"extensions/jql_v1/{model}/explanatory_model")
        for folder in folders:
            frozen = read_json(folder / "manifest.json")
            for relative, expected in frozen["inputs"].items():
                if relative not in records or records[relative]["sha256"] != expected:
                    raise ValueError("Published input differs from its original scientific manifest: " + relative)
                inputs_checked += 1
            for relative, expected in frozen["output_hashes"].items():
                member = PurePosixPath(relative)
                if member.is_absolute() or ".." in member.parts or "\\" in relative or ":" in relative:
                    raise ValueError("Unsafe scientific output manifest member")
                published = folder.joinpath(*member.parts).relative_to(root).as_posix()
                if published not in records or records[published]["sha256"] != expected:
                    raise ValueError("Published output differs from its original scientific manifest: " + published)
                outputs_checked += 1
            manifests += 1
    return {"passed": True, "original_scientific_manifests": manifests,
            "input_hash_references_checked": inputs_checked, "output_hash_references_checked": outputs_checked,
            "scope": "Primary, transfer and explanatory files linked to unchanged frozen manifests"}


def primary_replay(model, output):
    from research_v2.expanded_primary import DESTINATION, _run, inputs
    from research_v2.expanded_study import effective_plan
    before = read_json(DESTINATION / model / "manifest.json")
    if inputs(model) != before["inputs"]:
        raise ValueError("Primary inputs differ from frozen scientific manifest")
    target = output / "primary_recomputed" / model
    target.mkdir(parents=True, exist_ok=False)
    after = _run(model, effective_plan(), target, 5000, 9999)
    if before["inputs"] != after["inputs"] or before["output_hashes"] != after["output_hashes"]:
        raise ValueError("Refitted primary results differ from frozen evidence")
    return {"passed": True, "model_key": model, "byte_identical_result_files": len(after["output_hashes"]),
            "folds": 3, "feature_panels": 7, "classifiers": 3, "bootstraps": 5000, "work_swaps": 9999}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("audit", "primary", "transfer", "explanatory"), default="audit")
    parser.add_argument("--models", nargs="+", default=["all"], help="all or distinct active model keys")
    parser.add_argument("--output", type=Path, required=True, help="Fresh directory outside the repository or inside audit_runs/")
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.is_relative_to(repository) and not output.is_relative_to(repository / "audit_runs"):
        raise ValueError("Use an output outside the repository or under its ignored audit_runs directory")
    if output.exists():
        raise ValueError("Output directory must not already exist")
    manifest, manifest_hash = checked_manifest(repository)
    output.mkdir(parents=True, exist_ok=False)
    root = repository
    if args.mode != "audit":
        root = output / "replay_study"
        root.mkdir()
        for name in manifest["files"]:
            destination = root.joinpath(*PurePosixPath(name).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repository.joinpath(*PurePosixPath(name).parts), destination)
        # The manifest does not recursively hash itself; preserve it separately.
        destination = root / "audit/PUBLIC_FILE_MANIFEST.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repository / "audit/PUBLIC_FILE_MANIFEST.json", destination)
        checked_manifest(root)
    sys.path.insert(0, str(root))
    from research_v2.io import ROOT
    from research_v2.expanded_study import BASE, effective_plan
    from research_v2.release import check_environment
    if ROOT.resolve() != root.resolve():
        raise ValueError("Scientific imports did not come from selected public study root")
    environment = check_environment()
    if not environment["passed"]:
        raise ValueError("Use the exact requirements-v2.lock environment: " + json.dumps(environment))
    originals, registry, sources = check_sources(root)
    with (output / "work_registry_current.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(registry[0]))
        writer.writeheader()
        writer.writerows(registry)
    result = {"passed": False, "mode": args.mode, "public_manifest_sha256": manifest_hash,
              "published_files_checked": len(manifest["files"]), "environment": environment,
              "source_check": sources, "generation_check": check_generation(originals), "primary_audit": check_primary(),
              "scientific_manifest_check": check_scientific_manifests(root, manifest),
              "participant_ratings_read": False, "private_inputs_read": False, "model_api_calls": 0,
              "repository_evidence_modified": False, "withheld_paths": manifest.get("withheld_paths", []), "replays": [],
              "scope_limit": "Computational consistency does not verify reviewer identity, independence, consent, ethics approval or the backend identity of session outputs."}
    if args.mode != "audit":
        active = effective_plan()["active_models"]
        selected = active if args.models == ["all"] else args.models
        if len(selected) != len(set(selected)) or not set(selected) <= set(active):
            raise ValueError("Choose distinct active model keys, or all")
        for model in selected:
            if args.mode == "primary":
                receipt = primary_replay(model, output)
            elif args.mode == "transfer":
                sys.path.insert(0, str(root / "audit_tools"))
                from verify_transfer_portable import verify
                receipt = verify(model, study=BASE, extension_base=BASE / "extensions/jql_v1")
                receipt["scope_note"] = "Refits transformations and reconstructs scores/intervals from archived predictions; does not refit transfer classifiers. Finite IDF values may differ within eight ULPs; other metadata must match exactly."
            else:
                from research_v2.shift_contraction import replay_and_verify
                receipt = replay_and_verify(model, study=BASE, extension_base=BASE / "extensions/jql_v1")
            result["replays"].append(receipt)
            print(json.dumps({"mode": args.mode, "model": model, "passed": True}), flush=True)
    # Catch any accidental alteration of published inputs during the audit.
    checked_manifest(repository)
    result["completed_utc"] = datetime.now(timezone.utc).isoformat()
    result["passed"] = True
    write_new(output / "public_audit_report.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
