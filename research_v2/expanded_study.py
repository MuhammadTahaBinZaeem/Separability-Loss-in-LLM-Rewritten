"""Versioned corrections and prospective expansion; never mutate the frozen v2 study."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .corpus import AUTHORS, clean_text, source_text, words
from .generation import INSTRUCTIONS, SYSTEM, verify_corpus
from .io import OUT, ROOT, digest_text, file_hash, read_csv, read_json, read_jsonl, write_csv, write_json, write_jsonl
from .providers import make_payload, response_view

BASE = OUT / "expanded_v3"
# Exact candidate spans inspected with preceding/following context, 26 September 2026.
# Entire affected Twain chapters are excluded, not just the flagged fragment.
CORRECTIONS = {
    "V2_austen_pride_and_prejudice_020": (716057, 718650, "replace_edition_formatting_markup"),
    "V2_twain_connecticut_yankee_002": (42388, 44845, "replace_embedded_Malory_passage_outside_chapter_III"),
    "V2_twain_connecticut_yankee_008": (231513, 234194, "replace_mixed_authorship_outside_chapter_XIX"),
    "V2_twain_tom_sawyer_013": (252454, 254884, "replace_borrowed_composition_outside_chapter_XXI"),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def effective_plan():
    plan = read_json(BASE / "generation_plan.json")
    amendment = BASE / "scope_amendment.json"
    if amendment.exists():
        changes = read_json(amendment)
        if changes["base_plan_sha256"] != file_hash(BASE / "generation_plan.json"):
            raise ValueError("Scope amendment refers to a different frozen plan")
        for key, config in changes["additional_models"].items():
            if key in plan["models"]:
                raise ValueError("An amendment cannot replace an existing model config")
            plan["models"][key] = config
        plan["active_models"] = changes["active_models"]
    else:
        plan["active_models"] = list(plan["models"])
    return plan


def freeze_json(path: Path, value, lines=False):
    if path.exists():
        if (read_jsonl(path) if lines else read_json(path)) != value:
            raise ValueError(f"Frozen expansion artifact would change: {path.name}")
    elif lines:
        write_jsonl(path, value)
    else:
        write_json(path, value)


def corrected_rows(originals, replacements):
    """Keep unchanged IDs/hashes; give replaced texts new IDs and explicit lineage."""
    if not set(replacements) <= {r["passage_id"] for r in originals}:
        raise ValueError("Unknown replacement target")
    result, lineage = [], []
    for original in originals:
        pid = original["passage_id"]
        row = dict(original)
        if pid in replacements:
            changes = replacements[pid]
            row.update({k: changes[k] for k in ("source_start_char", "source_end_char", "text")})
            row["passage_id"] = pid.replace("V2_", "V3_", 1)
            row["word_count"] = words(row["text"])
            row["text_sha256"] = digest_text(row["text"])
            if row["text_sha256"] == original["text_sha256"]:
                raise ValueError("Replacement must actually change the source span")
        if not 450 <= words(row["text"]) <= 650 or digest_text(row["text"]) != row["text_sha256"]:
            raise ValueError("Invalid corrected source text")
        result.append(row)
        lineage.append({"passage_id": row["passage_id"], "v2_passage_id": pid,
                        "source_sha256": row["text_sha256"], "v2_source_sha256": original["text_sha256"],
                        "disposition": "replacement" if pid in replacements else "unchanged_exact_text",
                        "reason": replacements[pid]["reason"] if pid in replacements else "retained_reviewed_source"})
    for i, row in enumerate(result):
        for other in result[i + 1:]:
            if row["work_id"] == other["work_id"] and int(row["source_start_char"]) < int(other["source_end_char"]) and int(row["source_end_char"]) > int(other["source_start_char"]):
                raise ValueError("Corrected passages overlap within a work")
    if len({r["text_sha256"] for r in result}) != len(result):
        raise ValueError("Duplicate corrected passage")
    return result, lineage


def prepare_corpus():
    from .source_review import validate
    old_freeze = verify_corpus()
    review = validate()
    returns = read_jsonl(OUT / "source_review/private/original_return.jsonl")
    flagged = {r["passage_id"] for r in returns if r["verdict"] != "pass"}
    if review["reviewed"] != 360 or flagged != set(CORRECTIONS):
        raise ValueError("Correction targets no longer match the registered source review")
    originals = read_csv(OUT / "corpus/originals.csv")
    replacements = {}
    for row in originals:
        if row["passage_id"] not in CORRECTIONS:
            continue
        a, b, reason = CORRECTIONS[row["passage_id"]]
        raw = source_text(int(row["gutenberg_id"]))
        replacements[row["passage_id"]] = {"source_start_char": a, "source_end_char": b,
                                            "text": clean_text(raw[a:b]), "reason": reason}
    rows, lineage = corrected_rows(originals, replacements)
    if Counter(r["author_id"] for r in rows) != Counter({a: 60 for a in AUTHORS}):
        raise ValueError("Author balance changed")
    path = BASE / "corpus/originals.csv"
    if path.exists():
        if read_csv(path) != [{k: str(v) for k, v in r.items()} for r in rows]:
            raise ValueError("Corrected corpus is frozen; create another version")
    else:
        write_csv(path, rows)
        write_csv(BASE / "corpus/lineage.csv", lineage)
    freeze = {"version": 3, "passage_count": 360, "work_count": 18, "author_count": 6,
              "originals_file_sha256": file_hash(path), "v2_corpus_sha256": old_freeze["corpus_sha256"],
              "corpus_sha256": digest_text("\n".join(f"{r['passage_id']}:{r['text_sha256']}:{r['outer_fold']}" for r in rows)),
              "lineage_sha256": file_hash(BASE / "corpus/lineage.csv"),
              "retained_source_review_sha256": review["return_sha256"],
              "unchanged_passages": 356, "replacement_passages": 4,
              "correction_method": "AI-assisted exact-span inspection; replacement source review pending",
              "protocol_sha256": file_hash(BASE / "PROTOCOL.md")}
    freeze_json(BASE / "corpus/freeze.json", freeze)
    packet = [{k: r[k] for k in ("passage_id", "author_id", "work_id", "gutenberg_id", "source_start_char", "source_end_char", "text_sha256", "text")} | {"verdict": "", "notes": ""}
              for r in rows if r["passage_id"].startswith("V3_")]
    freeze_json(BASE / "source_review/blank_review.jsonl", packet, lines=True)
    manifest_path = BASE / "source_review/issued_manifest.json"
    manifest = {"corpus_sha256": freeze["corpus_sha256"], "blank_sha256": file_hash(BASE / "source_review/blank_review.jsonl"),
                "items": 4, "scope": "four_replacements_only", "previous_review_sha256": review["return_sha256"]}
    if manifest_path.exists():
        manifest["issued_utc"] = read_json(manifest_path)["issued_utc"]
    else:
        manifest["issued_utc"] = now()
    freeze_json(manifest_path, manifest)
    return freeze


def verify():
    freeze = read_json(BASE / "corpus/freeze.json")
    for path, field in (("corpus/originals.csv", "originals_file_sha256"), ("corpus/lineage.csv", "lineage_sha256"), ("PROTOCOL.md", "protocol_sha256")):
        if file_hash(BASE / path) != freeze[field]:
            raise ValueError("Frozen expansion input changed")
    verify_corpus()
    if file_hash(OUT / "source_review/private/original_return.jsonl") != freeze["retained_source_review_sha256"]:
        raise ValueError("Original source review changed")
    return freeze


def prepare():
    freeze = prepare_corpus()
    plan = effective_plan()
    originals = read_csv(BASE / "corpus/originals.csv")
    for key, config in plan["models"].items():
        if key not in plan["active_models"]:
            continue
        legacy = config.get("reuse_v2_model")
        old_requests = { (r["passage_id"], r["condition"]): r for r in read_jsonl(OUT / f"generation/{legacy}/requests.jsonl")} if legacy else {}
        assignments, requests = [], []
        for row in originals:
            for condition in plan["conditions"]:
                aid = digest_text(f"v3:{freeze['corpus_sha256']}:{key}:{row['passage_id']}:{condition}")[:24]
                old = old_requests.get((row["passage_id"], condition))
                common = {"assignment_id": aid, "passage_id": row["passage_id"], "condition": condition,
                          "model_key": key, "source_sha256": row["text_sha256"]}
                if old:
                    if old["source_sha256"] != row["text_sha256"]:
                        raise ValueError("Only exact unchanged sources may reuse observations")
                    assignments.append({**common, "delivery": "reused_v2_observation", "v2_model_key": legacy,
                                        "request_id": old["request_id"], "request_sha256": old["request_sha256"]})
                    continue
                user = f"{INSTRUCTIONS[condition]}\n\nrequest_id: {aid}\noriginal_word_count: {words(row['text'])}\n\nPassage:\n{row['text']}"
                if config["api"] == "codex_session":
                    payload = {"system": SYSTEM, "user": user}
                else:
                    payload = make_payload(config, plan, SYSTEM, user)
                    if config.get("omit_sampling_parameters"):
                        payload.pop("temperature", None); payload.pop("top_p", None)
                request = {**common, "request_id": aid, "original_words": words(row["text"]),
                           "payload": payload, "requested_model": config["model"], "api": config["api"],
                           "accepted_returned_models": config.get("accepted_returned_models", [config["model"]]),
                           "request_sha256": digest_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))}
                requests.append(request)
                assignments.append({**common, "delivery": config["api"], "request_id": aid, "request_sha256": request["request_sha256"]})
        requests.sort(key=lambda r: digest_text("20260926:" + r["request_id"]))
        folder = BASE / "generation" / key
        freeze_json(folder / "assignments.jsonl", assignments, lines=True)
        freeze_json(folder / "requests.jsonl", requests, lines=True)
        manifest = {"assignments": len(assignments), "new_requests": len(requests),
                    "reused_v2_observations": len(assignments) - len(requests), "corpus_sha256": freeze["corpus_sha256"],
                    "plan_sha256": file_hash(BASE / "generation_plan.json"), "requests_sha256": file_hash(folder / "requests.jsonl"),
                    "assignments_sha256": file_hash(folder / "assignments.jsonl")}
        if key not in read_json(BASE / "generation_plan.json")["models"]:
            manifest["scope_amendment_sha256"] = file_hash(BASE / "scope_amendment.json")
        freeze_json(folder / "request_manifest.json", manifest)
    return {"corpus": freeze, "models": plan["active_models"],
            "study_generation_started": any(BASE.glob("generation/*/outcomes.jsonl"))}


def historical_failures():
    """Keep actual visible failed outputs even if the required JSON could not be parsed."""
    records = []
    for model in ("gem31lite", "azure_replication"):
        folder = OUT / "generation" / model
        requests = {r["request_id"]: r for r in read_jsonl(folder / "requests.jsonl")}
        raw = {r["request_id"]: r for r in read_jsonl(folder / "raw_responses.jsonl")}
        for row in read_csv(folder / "rewrites.csv"):
            if row["qc_status"] != "fail":
                continue
            native = raw.get(row["request_id"])
            visible = response_view(requests[row["request_id"]], native["response"])["content"] if native else ""
            records.append({"model_key": model, "request_id": row["request_id"], "passage_id": row["passage_id"],
                            "condition": row["condition"], "outcome_type": row["outcome_type"], "qc_flags": row["qc_flags"],
                            "visible_output_verbatim": visible, "visible_output_sha256": digest_text(visible),
                            "parsed_rewritten_text": row["rewritten_text"],
                            "native_record_sha256": row["raw_record_sha256"],
                            "text_availability": "retained_native_visible_output" if native else "no_generated_text_recorded_HTTP_refusal",
                            "historical_HTTP_body_available": False if not native else None})
    freeze_json(BASE / "failures/v2_failed_outputs.jsonl", records, lines=True)
    write_json(BASE / "failures/status.json", {"failed_observations": len(records), "native_visible_text_records": sum(bool(r["visible_output_verbatim"]) for r in records),
               "limitation": "Historical HTTP error bodies were not retained by the old runner; hashes/events remain. Missing text is not reconstructed.",
               "v2_rewrite_hashes": {m: file_hash(OUT / f"generation/{m}/rewrites.csv") for m in ("gem31lite", "azure_replication")}})
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "verify", "failures"))
    args = parser.parse_args()
    print(json.dumps({"prepare": prepare, "verify": verify, "failures": historical_failures}[args.action](), indent=2))


if __name__ == "__main__":
    main()
