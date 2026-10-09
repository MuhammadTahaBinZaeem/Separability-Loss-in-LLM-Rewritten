"""Immutable expanded-study packets and validated independently submitted returns."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

from .expanded_study import BASE, effective_plan, freeze_json, now, verify
from .io import OUT, digest_text, file_hash, read_csv, read_json, read_jsonl, write_csv, write_json
from .review_app import ReviewStore, SEMANTIC_FIELDS, immutable, item_id, json_bytes, row_errors
from .review_chronology import completion_window


def source_validation():
    freeze = verify()
    path = BASE / "source_review/private/attestation.json"
    if not path.exists():
        return {"passed": False, "previously_reviewed_unchanged": 356, "replacement_reviews_pending": 4}
    record = read_json(path)
    returned = BASE / "source_review/private/original_return.jsonl"
    if record["return_sha256"] != file_hash(returned) or record["corpus_sha256"] != freeze["corpus_sha256"]:
        raise ValueError("Replacement source review evidence changed")
    manifest = read_json(BASE / "source_review/issued_manifest.json")
    rows = check_return("source", returned, manifest, record)
    flagged = sum(r["verdict"] != "pass" for r in rows)
    return {"passed": flagged == 0, "previously_reviewed_unchanged": 356, "replacement_reviewed": len(rows), "replacement_flagged": flagged,
            "previous_review_sha256": freeze["retained_source_review_sha256"], "replacement_return_sha256": record["return_sha256"]}


def check_return(kind, path, manifest, metadata):
    if metadata.get("attested_independent_human") is not True or not metadata.get("reviewer_id"):
        raise ValueError("Independent completion confirmation is required")
    completion_window(metadata, manifest["issued_utc"])
    if kind == "source":
        blank_path = BASE / "source_review/blank_review.jsonl"
        if file_hash(blank_path) != manifest["blank_sha256"]:
            raise ValueError("Source packet changed")
        blank, rows, fields = read_jsonl(blank_path), read_jsonl(path), {"verdict", "notes"}
    else:
        slot = kind[-1]
        blank_path = BASE / f"annotations/forms/reviewer_{slot}.csv"
        if file_hash(blank_path) != manifest["forms_sha256"][slot]:
            raise ValueError("Blinded packet changed")
        blank, rows, fields = read_csv(blank_path), read_csv(path), set(SEMANTIC_FIELDS)
    expected = {item_id(r): r for r in blank}
    if len(rows) != len(blank) or len({item_id(r) for r in rows}) != len(rows) or {item_id(r) for r in rows} != set(expected):
        raise ValueError("Return coverage does not match the issued packet")
    for row in rows:
        if set(row) != set(expected[item_id(row)]) or any(v != row[k] for k, v in expected[item_id(row)].items() if k not in fields):
            raise ValueError("Source text or immutable identifiers changed")
        if row_errors(kind, row):
            raise ValueError("Incomplete review ratings or notes")
    return rows


def register(session, path, metadata):
    freeze = verify()
    kind = session["kind"]
    folder = BASE / ("source_review" if kind == "source" else "annotations")
    manifest = read_json(folder / "issued_manifest.json")
    if manifest["corpus_sha256"] != freeze["corpus_sha256"]:
        raise ValueError("Review packet belongs to a different corpus")
    rows = check_return(kind, path, manifest, metadata)
    if kind == "source":
        target = folder / "private/original_return.jsonl"
        registry = folder / "private/attestation.json"
    elif kind in {"semantic_A", "semantic_B"}:
        target = folder / f"private/returns/{kind[-1]}.csv"
        registry = folder / f"private/attestation_{kind[-1]}.json"
    else:
        raise ValueError("Packet is not eligible for independent registration")
    record = {**metadata, "corpus_sha256": freeze["corpus_sha256"], "items": len(rows)}
    if target.exists():
        if file_hash(target) != file_hash(path):
            raise ValueError("Another original return exists; do not overwrite it")
    else:
        immutable(target, path.read_bytes())
    freeze_json(registry, record)
    return source_validation() if kind == "source" else semantic_validation()


def agreement_rows(joined):
    import math
    from sklearn.metrics import cohen_kappa_score
    from .annotations import RATINGS
    agreements, flags = [], []
    for model in sorted({key[0] for key in joined}):
        pairs = [pair for key, pair in joined.items() if key[0] == model]
        for field, choices in RATINGS.items():
            a, b = [[pair[slot][1][field] for pair in pairs] for slot in ("A", "B")]
            labels = sorted(choices) if field == "usable" else sorted(map(int, choices))
            if field != "usable":
                a, b = list(map(int, a)), list(map(int, b))
            weights = "quadratic" if field in {"tone_drift", "meaning_preservation"} else None
            value = float(cohen_kappa_score(a, b, labels=labels, weights=weights)) if len(set(a + b)) > 1 else float("nan")
            agreements.append({"model_key": model, "field": field, "items": len(pairs),
                               "raw_agreement": sum(x == y for x, y in zip(a, b)) / len(pairs),
                               "kappa": value if math.isfinite(value) else "undefined_constant_ratings", "weighting": weights or "unweighted"})
        for pair in pairs:
            key, a = pair["A"]
            _, b = pair["B"]
            def risk(r):
                return any(r[f] == "1" for f in ("added_facts", "omitted_facts", "order_changed", "relationships_changed")) or int(r["meaning_preservation"]) <= 3 or r["usable"] == "no"
            flags.append({k: key[k] for k in ("model_key", "request_id", "passage_id", "condition", "source_sha256", "rewrite_sha256")} |
                         {"risk_A": int(risk(a)), "risk_B": int(risk(b)), "risk_union": int(risk(a) or risk(b)),
                          "meaning_A": a["meaning_preservation"], "meaning_B": b["meaning_preservation"]})
    identical = all(all(pair["A"][1][field] == pair["B"][1][field] for field in RATINGS) for pair in joined.values())
    return agreements, flags, identical


def semantic_validation():
    folder = BASE / "annotations"
    markdown_returns = folder / "private/markdown_20261002/returns"
    markdown_received = bool(list(markdown_returns.glob("reviewer_0[1-8]/record.json")))
    whole_packet_received = any((folder / f"private/attestation_{s}.json").exists() for s in ("A", "B"))
    if markdown_received and whole_packet_received:
        raise ValueError("Whole-packet and partitioned returns coexist; resolve the review route without overwriting original evidence")
    if (BASE / "review_markdown_20261002/issued_manifest.json").exists() and not whole_packet_received:
        from .markdown_review import validate_semantic
        return validate_semantic()
    manifest_path = folder / "issued_manifest.json"
    attestations = {s: folder / f"private/attestation_{s}.json" for s in ("A", "B")}
    if not manifest_path.exists() or any(not p.exists() for p in attestations.values()):
        result = {"complete": False, "stage": "awaiting_independent_returns"}
        write_json(folder / "validation.json", result)
        return result
    freeze = verify()
    manifest = read_json(manifest_path)
    if manifest["corpus_sha256"] != freeze["corpus_sha256"] or manifest["models_in_scope"] != effective_plan()["active_models"]:
        raise ValueError("Review scope differs from the corrected study")
    records = {s: read_json(p) for s, p in attestations.items()}
    if records["A"]["reviewer_id"].strip().casefold() == records["B"]["reviewer_id"].strip().casefold():
        raise ValueError("Two review slots cannot represent the same reviewer")
    source_record = BASE / "source_review/private/attestation.json"
    if source_record.exists() and any(r["reviewer_id"].casefold() == read_json(source_record)["reviewer_id"].casefold() for r in records.values()):
        raise ValueError("Source metadata exposure conflicts with blinded review")
    originals = {r["passage_id"]: r for r in read_csv(BASE / "corpus/originals.csv")}
    generated = {}
    for model, expected in manifest["generation_sha256"].items():
        path = BASE / f"generation/{model}/rewrites.csv"
        if file_hash(path) != expected:
            raise ValueError("Rated generation changed")
        generated[model] = {r["request_id"]: r for r in read_csv(path)}
    key_path = folder / "private_join_key.csv"
    if file_hash(key_path) != manifest["join_key_sha256"]:
        raise ValueError("Blinded join key changed")
    keys = read_csv(key_path)
    if len(keys) != 2 * manifest["items_per_reviewer"] or len({(r["slot"], r["item_id"]) for r in keys}) != len(keys):
        raise ValueError("Missing or duplicate blinded assignments")
    returned = {}
    for slot in ("A", "B"):
        path = folder / f"private/returns/{slot}.csv"
        if file_hash(path) != records[slot]["return_sha256"]:
            raise ValueError("Original completed return changed")
        rows = check_return("semantic_" + slot, path, manifest, records[slot])
        returned[slot] = {r["item_id"]: r for r in rows}
        if {k["item_id"] for k in keys if k["slot"] == slot} != set(returned[slot]):
            raise ValueError("Join key does not cover each assigned item")
    joined = defaultdict(dict)
    for key in keys:
        source = originals[key["passage_id"]]
        rewrite = generated[key["model_key"]][key["request_id"]]
        rated = returned[key["slot"]][key["item_id"]]
        if (source["text_sha256"] != key["source_sha256"] or rewrite["source_sha256"] != key["source_sha256"]
                or rewrite["rewrite_sha256"] != key["rewrite_sha256"] or rewrite["condition"] != key["condition"]
                or rewrite["passage_id"] != key["passage_id"] or rewrite["qc_status"] not in {"pass", "warning"}
                or source["text"] != rated["original_text"] or rewrite["rewritten_text"] != rated["rewritten_text"]):
            raise ValueError("Rated texts do not match their original generation lineage")
        joined[key["model_key"], key["request_id"]][key["slot"]] = key, rated
    if len(joined) != manifest["items_per_reviewer"] or any(set(p) != {"A", "B"} for p in joined.values()):
        raise ValueError("Reviewers did not rate exactly the same underlying pairs")
    agreements, flags, identical = agreement_rows(joined)
    write_csv(folder / "agreement.csv", agreements)
    # An identical return pair is not automatically declared fraudulent or independent.
    write_csv(folder / ("provisional_flags.csv" if identical else "verified_flags.csv"), flags)
    result = {"complete": not identical, "stage": "independence_followup_required" if identical else "validated_independent_attested_returns",
              "items_per_reviewer": len(joined), "entire_rating_sets_identical": identical,
              "attestation_hashes": {s: file_hash(p) for s, p in attestations.items()},
              "form_manifest_sha256": file_hash(manifest_path), "no_identity_certification": True,
              "semantic_sensitivity_still_required": True, "submission_ready": False}
    write_json(folder / "validation.json", result)
    return result


def attach_source_followup():
    verify()
    original = ReviewStore()
    expanded = ReviewStore(BASE / "private/review_app", BASE, source_archive=OUT, registrar=register)
    source = [s for s in original.sessions() if s["kind"] == "source" and s["mode"] == "human"]
    if len(source) != 1:
        raise ValueError("Expected one existing source reviewer account")
    existing = [s for s in expanded.sessions() if s["kind"] == "source" and s["mode"] == "human"]
    target = existing[0] if existing else expanded.create("source", "human", source[0]["reviewer_id"])
    if len(existing) > 1 or target["reviewer_id"] != source[0]["reviewer_id"]:
        raise ValueError("Source follow-up ownership conflicts")
    link_path = expanded.private / "account_links.json"
    expected = {"from_research": str(original.research), "from_session_id": source[0]["id"], "to_session_id": target["id"]}
    if link_path.exists():
        links = read_json(link_path)
        if len(links) != 1 or links[0]["from_session_id"] != expected["from_session_id"] or links[0]["to_session_id"] != expected["to_session_id"] or original.recorded_path(links[0]["from_research"]) != original.research:
            raise ValueError("Existing source-account link does not match")
    else:
        freeze_json(link_path, [expected])
    return {"attached": True, "items": target["total"], "existing_credentials_unchanged": True, "source_session_id": source[0]["id"], "followup_session_id": target["id"]}


def attach_semantic(reserve_only=False):
    """Attach only a fully issued batch; preserve prior assignments and use the same logins."""
    manifest = BASE / "annotations/issued_manifest.json"
    if not manifest.exists() and not reserve_only:
        raise ValueError("Full expanded forms have not been issued")
    original = ReviewStore()
    expanded = ReviewStore(BASE / "private/review_app", BASE, source_archive=OUT, registrar=register)
    links = read_jsonl(expanded.private / "account_link_additions.jsonl")
    from .generation import append_record
    results = []
    for slot in ("A", "B"):
        parents = [s for s in original.sessions() if s["kind"] == "semantic_" + slot and s["mode"] == "human"]
        if len(parents) != 1:
            raise ValueError("Expected the existing pair of reviewer accounts")
        parent = parents[0]
        existing = [s for s in expanded.sessions() if s["kind"] == parent["kind"] and s["mode"] == "human"]
        target = existing[0] if existing else expanded.create(parent["kind"], "human", parent["reviewer_id"])
        if len(existing) > 1 or target["reviewer_id"] != parent["reviewer_id"]:
            raise ValueError("Review slot ownership conflicts")
        if target["status"] == "awaiting_packet" and not reserve_only:
            target = expanded.activate(target["id"])
        link = {"from_research": str(original.research), "from_session_id": parent["id"], "to_session_id": target["id"]}
        if not any(existing["from_session_id"] == link["from_session_id"] and existing["to_session_id"] == link["to_session_id"] and original.recorded_path(existing["from_research"]) == original.research for existing in links):
            append_record(expanded.private / "account_link_additions.jsonl", link)
        results.append({"slot": slot, "items": target["total"], "session_id": target["id"], "status": target["status"], "existing_credentials_unchanged": True})
    return results


def prepare_semantic():
    freeze = verify()
    plan = effective_plan()
    from .expanded_generation import consolidate
    originals = {r["passage_id"]: r for r in read_csv(BASE / "corpus/originals.csv")}
    sampled, missing = [], []
    for model in plan["active_models"]:
        folder = BASE / "generation" / model
        if (folder / "RUNNING.lock").exists():
            missing.append(model); continue
        if model == "astra_session":
            from .session_generation import consolidate as consolidate_session
            status = consolidate_session()
        else:
            status = consolidate(model)
        if not status["accounting_complete"]:
            missing.append(model); continue
        cells = defaultdict(list)
        for row in read_csv(folder / "rewrites.csv"):
            if row["qc_status"] not in {"pass", "warning"}:
                continue
            source = originals[row["passage_id"]]
            if source["text_sha256"] != row["source_sha256"] or digest_text(row["rewritten_text"]) != row["rewrite_sha256"]:
                raise ValueError("Review text lineage changed")
            cells[source["author_id"], source["work_id"], row["condition"]].append(row)
        expected = {(r["author_id"], r["work_id"], c) for r in originals.values() for c in plan["conditions"]}
        if set(cells) != expected or any(len(v) < 5 for v in cells.values()):
            raise ValueError("A planned review stratum lacks five valid outputs; no silent sampling change")
        for cell in sorted(cells):
            for row in sorted(cells[cell], key=lambda r: digest_text("expanded_review_v3:" + model + ":" + r["request_id"]))[:5]:
                sampled.append({**row, "original_text": originals[row["passage_id"]]["text"]})
    if missing:
        result = {"complete": False, "stage": "waiting_for_complete_generation", "missing_models": missing, "existing_packets_unchanged": True}
        write_json(BASE / "annotations/status.json", result)
        return result
    keys = []
    for slot in ("A", "B"):
        forms = []
        for row in sampled:
            iid = digest_text(f"expanded_blind_v3:{slot}:{row['model_key']}:{row['request_id']}")[:20]
            forms.append({"item_id": iid, "original_text": row["original_text"], "rewritten_text": row["rewritten_text"], **{f: "" for f in SEMANTIC_FIELDS}})
            keys.append({"slot": slot, "item_id": iid, **{k: row[k] for k in ("model_key", "request_id", "passage_id", "condition", "source_sha256", "rewrite_sha256")}})
        forms.sort(key=lambda r: digest_text("expanded_display:" + r["item_id"]))
        path = BASE / f"annotations/forms/reviewer_{slot}.csv"
        if path.exists() and read_csv(path) != forms:
            raise ValueError("Issued form changed; preserve original packet")
        if not path.exists():
            write_csv(path, forms)
    key_path = BASE / "annotations/private_join_key.csv"
    if key_path.exists() and read_csv(key_path) != keys:
        raise ValueError("Issued join key changed")
    if not key_path.exists():
        write_csv(key_path, keys)
    path = BASE / "annotations/issued_manifest.json"
    manifest = {"corpus_sha256": freeze["corpus_sha256"], "models_in_scope": plan["active_models"], "items_per_reviewer": len(sampled),
                "forms_sha256": {s: file_hash(BASE / f"annotations/forms/reviewer_{s}.csv") for s in ("A", "B")},
                "join_key_sha256": file_hash(key_path), "generation_sha256": {m: file_hash(BASE / f"generation/{m}/rewrites.csv") for m in plan["active_models"]},
                "issued_utc": read_json(path)["issued_utc"] if path.exists() else now()}
    freeze_json(path, manifest)
    return {"complete": False, "stage": "awaiting_independent_returns", "items_per_reviewer": len(sampled)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("source-status", "attach-source", "prepare", "attach-semantic", "reserve-semantic", "validate"))
    args = parser.parse_args()
    print(json.dumps({"source-status": source_validation, "attach-source": attach_source_followup, "prepare": prepare_semantic, "attach-semantic": attach_semantic, "reserve-semantic": lambda: attach_semantic(True), "validate": semantic_validation}[args.action](), indent=2))


if __name__ == "__main__":
    main()
