"""Offline review packets, strict Markdown returns and per-reviewer provenance."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import zipfile

from .expanded_study import BASE, freeze_json, now, verify
from .io import OUT, digest_text, file_hash, normalized_text, read_csv, read_json, read_jsonl, write_csv, write_json
from .review_app import SEMANTIC_FIELDS, encode_return, immutable, item_id, json_bytes, row_errors
from .review_chronology import completion_window

DESTINATION = BASE / "review_markdown_20261002"
PRIVATE = BASE / "annotations/private/markdown_20261002"
LABELS = {
    "added_facts": "Added facts", "omitted_facts": "Omitted facts",
    "order_changed": "Event order changed", "relationships_changed": "Relationships changed",
    "tone_drift": "Tone drift", "meaning_preservation": "Meaning preservation",
    "usable": "Usable for style comparison", "verdict": "Verdict", "notes": "Notes",
}
MEANING_TASKS = """Assess each original/rewrite pair for meaning preservation.

- Added facts, omitted facts, changed event order and changed relationships: 0 = no; 1 = yes. Relationships include speakers, characters, ownership, causes and who did what.
- Tone drift: 0 = none; 1 = noticeable; 2 = substantial change in emotion, seriousness, irony or narrative stance.
- Meaning preservation: 5 = all material meaning retained; 4 = minor nonmaterial differences; 3 = localized material distortion; 2 = several material distortions; 1 = meaning largely changed or missing.
- Usable for style comparison: yes = meaning changes do not materially confound the comparison; no = they do.
- Notes: identify the affected fact, event, speaker or relationship. An explanation is required for a factual, order or relationship change, a meaning score of 1–3, or an unusable rewrite.
"""
SOURCE_TASKS = """Assess each selected passage and its source context for correct attribution and suitability.

- Check whether the passage belongs to the stated work's fictional body.
- Identify prefatory or editorial material, footnotes, heading fragments, borrowed compositions, mixed authorship and uncertain boundaries.
- Verdict: pass = suitable and correctly attributed; needs_correction = a problem or unresolved uncertainty.
- Notes: explain the finding for every passage and identify any problematic words or boundaries.
"""


def source_material(row):
    path = OUT / f"sources/pg{row['gutenberg_id']}.txt"
    metadata = read_json(path.with_suffix(".json"))
    if file_hash(path) != metadata["raw_sha256"]:
        raise ValueError("Archived source changed")
    raw = path.read_text(encoding="utf-8-sig")
    a, b = int(row["source_start_char"]), int(row["source_end_char"])
    if not 0 <= a < b <= len(raw):
        raise ValueError("Source boundaries outside the archive")
    return {"title": metadata["volume_title"], "before": raw[max(0, a - 2500):a],
            "raw_span": raw[a:b], "after": raw[b:b + 2500]}


def fence(text):
    longest = max((len(m.group()) for m in re.finditer(r"`+", text)), default=0)
    marker = "`" * max(3, longest + 1)
    return f"{marker}text\n{text}\n{marker}\n"


def response_body(fields, values=None):
    values = values or {}
    return "".join(f"- {LABELS[f]}: {values.get(f, '')}\n" for f in fields)


def render_packet(reviewer, kind, rows, contexts=None):
    fields = ["verdict", "notes"] if kind == "source" else SEMANTIC_FIELDS
    unit = "passages" if kind == "source" else "pairs"
    parts = [f"# Review {reviewer[-2:]}\n\n{len(rows)} {unit}.\n\n",
             SOURCE_TASKS if kind == "source" else MEANING_TASKS]
    for index, row in enumerate(rows, 1):
        iid = item_id(row)
        parts.append(f"\n## {'Passage' if kind == 'source' else 'Pair'} {index:03d} · {iid}\n\n")
        if kind == "source":
            context = contexts[iid]
            parts.append(f"Work: {context['title']}\n\nAuthor: {row['author_id'].title()}\n\n")
            parts.append(f"Archived source: pg{row['gutenberg_id']}\n\n"
                         f"Selected span: characters {row['source_start_char']}–{row['source_end_char']}\n\n")
            for heading, text in (("Selected passage", row["text"]), ("Preceding context", context["before"]),
                                  ("Selected raw source span", context["raw_span"]), ("Following context", context["after"])):
                parts.append(f"### {heading}\n\n{fence(text)}\n")
        else:
            parts.append(f"### Original passage\n\n{fence(row['original_text'])}\n"
                         f"### Rewritten passage\n\n{fence(row['rewritten_text'])}\n")
        parts.append(f"### Responses\n\n<!-- response:{iid} -->\n{response_body(fields)}<!-- /response -->\n")
    return "".join(parts)


RESPONSE_RE = re.compile(r"^<!-- response:([^\r\n]+) -->\n(.*?)^<!-- /response -->$", re.M | re.S)


def check_return_structure(text, template, kind, rows):
    """Allow only verified count summaries/blank header lines; keep the body exact.

    Submitted packets are never rewritten. A missing source count is harmless;
    a semantic summary is accepted only if every count matches the parsed ratings.
    Titles, task wording, item order, IDs, evidence and response labels stay fixed.
    """
    heading = r"^## " + ("Passage" if kind == "source" else "Pair") + r" "
    actual_start = re.search(heading, text, re.M)
    issued_start = re.search(heading, template, re.M)
    if not actual_start or not issued_start:
        raise ValueError("An issued passage heading is missing")
    actual = [line for line in text[:actual_start.start()].splitlines() if line]
    issued = [line for line in template[:issued_start.start()].splitlines() if line]
    accepted = [issued]
    if kind == "source":
        accepted.append([issued[0], *issued[2:]])
    else:
        meaning = Counter(row["meaning_preservation"] for row in rows)
        usable = Counter(row["usable"] for row in rows)
        counts = ", ".join(f"{score}: {meaning[str(score)]}" for score in range(1, 6))
        summary = (f"{len(rows)} completed pair reviews. Meaning scores: {counts}. "
                   f"Usable: {usable['yes']}; unusable: {usable['no']}.")
        accepted.append([issued[0], summary, *issued[2:]])
    if actual not in accepted:
        raise ValueError("An issued instruction/title changed or the header summary does not match the ratings")
    if text[actual_start.start():].rstrip("\n") != template[issued_start.start():].rstrip("\n"):
        raise ValueError("An issued passage, identifier, instruction or source context changed")


def parse_return(text, template, kind, rows):
    """Preserve evidence exactly; accept response values and checked header summaries."""
    text, template = normalized_text(text).lstrip("\ufeff"), normalized_text(template)
    fields = ["verdict", "notes"] if kind == "source" else SEMANTIC_FIELDS
    matches = list(RESPONSE_RE.finditer(text))
    expected = {item_id(r): r for r in rows}
    if len(matches) != len(rows) or len({m[1] for m in matches}) != len(rows) or {m[1] for m in matches} != set(expected):
        raise ValueError("Missing, duplicate or unknown response items")
    returned, errors = [], []
    for match in matches:
        remainder, values = match[2], {}
        for field in fields[:-1]:
            prefix = f"- {LABELS[field]}:"
            line, separator, remainder = remainder.partition("\n")
            if not separator or not line.startswith(prefix):
                raise ValueError(f"Response field missing or reordered: {LABELS[field]}")
            values[field] = line[len(prefix):].strip()
        prefix = "- Notes:"
        if not remainder.startswith(prefix):
            raise ValueError("Notes field is missing")
        values["notes"] = remainder[len(prefix):].strip()
        if any(len(value) > 20000 for value in values.values()):
            raise ValueError("Response exceeds the supported length")
        row = {**expected[match[1]], **values}
        returned.append(row)
        for error in row_errors(kind, row):
            errors.append({"item_id": match[1], "error": error})
    def blank(match):
        return f"<!-- response:{match[1]} -->\n{response_body(fields)}<!-- /response -->"
    check_return_structure(RESPONSE_RE.sub(blank, text), template, kind, returned)
    lookup = {item_id(r): r for r in returned}
    return [lookup[item_id(r)] for r in rows], errors


def assignment_rows(forms, keys, originals):
    """Four balanced blocks; five items per stratum, with every block represented."""
    by_id = {s: {r["item_id"]: r for r in forms[s]} for s in ("A", "B")}
    grouped, cells = defaultdict(dict), defaultdict(list)
    for key in keys:
        grouped[key["model_key"], key["request_id"]][key["slot"]] = key
    if any(set(pair) != {"A", "B"} for pair in grouped.values()):
        raise ValueError("Every sampled pair needs both original review slots")
    for pair, linked in grouped.items():
        key = linked["A"]
        source = originals[key["passage_id"]]
        cells[key["model_key"], source["author_id"], source["work_id"], key["condition"]].append(pair)
        a, b = [by_id[s][linked[s]["item_id"]] for s in ("A", "B")]
        if any(a[f] != b[f] for f in ("original_text", "rewritten_text")):
            raise ValueError("The two original review slots contain different texts")
    if any(len(items) != 5 for items in cells.values()):
        raise ValueError("The fixed five-per-stratum sample changed")
    assigned, mapping = {f"reviewer_{i:02d}": [] for i in range(1, 9)}, []
    for cell_index, (cell, pairs) in enumerate(sorted(cells.items())):
        pairs.sort(key=lambda p: digest_text("markdown_partition_v1:" + ":".join(p)))
        for index, pair in enumerate(pairs):
            block = (cell_index + index) % 4
            for slot, offset in (("A", 1), ("B", 2)):
                reviewer = f"reviewer_{2 * block + offset:02d}"
                key = grouped[pair][slot]
                assigned[reviewer].append(by_id[slot][key["item_id"]])
                mapping.append({"reviewer": reviewer, "block": str(block + 1), **key})
    if len({len(rows) for rows in assigned.values()}) != 1:
        raise ValueError("The planned four blocks are not equal in size")
    for reviewer in assigned:
        assigned[reviewer].sort(key=lambda r: digest_text("markdown_order:" + reviewer + ":" + r["item_id"]))
    return assigned, mapping


def load_inputs():
    frozen = verify()
    manifest = read_json(BASE / "annotations/issued_manifest.json")
    if manifest["corpus_sha256"] != frozen["corpus_sha256"]:
        raise ValueError("Issued semantic review uses a different corpus")
    forms = {}
    for slot in ("A", "B"):
        path = BASE / f"annotations/forms/reviewer_{slot}.csv"
        if file_hash(path) != manifest["forms_sha256"][slot]:
            raise ValueError("Original issued semantic form changed")
        forms[slot] = read_csv(path)
        if len(forms[slot]) != manifest["items_per_reviewer"]:
            raise ValueError("Original issued semantic form coverage changed")
    key_path = BASE / "annotations/private_join_key.csv"
    if file_hash(key_path) != manifest["join_key_sha256"]:
        raise ValueError("Original blinded key changed")
    generated = {}
    for model, expected in manifest["generation_sha256"].items():
        if file_hash(BASE / f"generation/{model}/rewrites.csv") != expected:
            raise ValueError("Rated generation changed")
        generated[model] = {r["request_id"]: r for r in read_csv(BASE / f"generation/{model}/rewrites.csv")}
    keys = read_csv(key_path)
    originals = {r["passage_id"]: r for r in read_csv(BASE / "corpus/originals.csv")}
    lookup = {s: {r["item_id"]: r for r in rows} for s, rows in forms.items()}
    if (len(keys) != 2 * manifest["items_per_reviewer"] or len({(k["slot"], k["item_id"]) for k in keys}) != len(keys)
        or any({k["item_id"] for k in keys if k["slot"] == s} != set(lookup[s]) for s in ("A", "B"))):
        raise ValueError("Original review key does not cover both forms exactly")
    for key in keys:
        original = originals[key["passage_id"]]
        rewrite = generated[key["model_key"]][key["request_id"]]
        form = lookup[key["slot"]][key["item_id"]]
        if (original["text_sha256"] != key["source_sha256"] or rewrite["source_sha256"] != key["source_sha256"]
            or rewrite["rewrite_sha256"] != key["rewrite_sha256"] or digest_text(rewrite["rewritten_text"]) != key["rewrite_sha256"]
            or rewrite["passage_id"] != key["passage_id"] or rewrite["condition"] != key["condition"]
            or rewrite["qc_status"] not in {"pass", "warning"} or form["original_text"] != original["text"]
            or form["rewritten_text"] != rewrite["rewritten_text"]):
            raise ValueError("A reviewed pair differs from its frozen source or rewrite")
    source_manifest = read_json(BASE / "source_review/issued_manifest.json")
    source_path = BASE / "source_review/blank_review.jsonl"
    if file_hash(source_path) != source_manifest["blank_sha256"] or source_manifest["corpus_sha256"] != frozen["corpus_sha256"]:
        raise ValueError("Original issued source packet changed")
    return forms, keys, originals, read_jsonl(source_path)


def export():
    forms, keys, originals, sources = load_inputs()
    assigned, mapping = assignment_rows(forms, keys, originals)
    assigned["reviewer_09"] = sources
    public_hashes, assignments = {}, {}
    contexts = {item_id(r): source_material(r) for r in sources}
    for reviewer, rows in assigned.items():
        kind = "source" if reviewer == "reviewer_09" else "semantic"
        text = render_packet(reviewer, kind, rows, contexts)
        path = DESTINATION / f"{reviewer}.md"
        if path.exists():
            if path.read_bytes() != text.encode("utf-8"):
                raise ValueError("An issued Markdown packet changed; preserve it")
        else:
            immutable(path, text.encode("utf-8"))
        public_hashes[path.name] = file_hash(path)
        assignments[reviewer] = {"kind": kind, "items": len(rows), "packet": path.name}
    summary = "# Review assignments\n\n" + "\n".join(
        f"- [Review {r[-2:]}]({r}.md): {a['items']} {'source passages' if a['kind'] == 'source' else 'original/rewrite pairs'}."
        for r, a in assignments.items())
    summary += "\n- [Review 10](reviewer_10.md): resolve disagreements after the other reviews are complete.\n"
    reserved = """# Review 10

Resolve differences identified in the completed passage reviews.

- Determine the supported rating for each disputed field.
- Explain the decision with evidence from the paired passages.
- Identify any unresolved uncertainty.

The disputed passages and original ratings will be supplied after reviews 01–08 are complete. There are no assigned items at this stage.
"""
    for name, text in (("START_HERE.md", summary), ("reviewer_10.md", reserved)):
        path = DESTINATION / name
        if path.exists() and path.read_bytes() != text.encode("utf-8"):
            raise ValueError("An issued Markdown handout changed")
        if not path.exists():
            immutable(path, text.encode("utf-8"))
        public_hashes[name] = file_hash(path)
    key_path = PRIVATE / "assignment_key.csv"
    if key_path.exists() and read_csv(key_path) != mapping:
        raise ValueError("Partitioned assignment key changed")
    if not key_path.exists():
        write_csv(key_path, mapping)
    manifest_path = DESTINATION / "issued_manifest.json"
    issued = read_json(manifest_path)["issued_utc"] if manifest_path.exists() else now()
    manifest = {"format_version": 1, "issued_utc": issued, "assignments": assignments, "files_sha256": public_hashes,
                "semantic_pairs": len(forms["A"]), "ratings_per_pair": 2, "semantic_reviewers": 8,
                "source_reviewers": 1, "reserved_reviewers": 1,
                "original_semantic_manifest_sha256": file_hash(BASE / "annotations/issued_manifest.json"),
                "original_source_manifest_sha256": file_hash(BASE / "source_review/issued_manifest.json")}
    freeze_json(manifest_path, manifest)
    freeze_json(PRIVATE / "assignment_manifest.json", {"public_manifest_sha256": file_hash(manifest_path),
                                                     "assignment_key_sha256": file_hash(key_path)})
    zip_path = DESTINATION.parent / "review_markdown_20261002.zip"
    names = sorted([*public_hashes, "issued_manifest.json"])
    if not zip_path.exists():
        with zipfile.ZipFile(zip_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in names:
                archive.writestr(name, (DESTINATION / name).read_bytes())
    with zipfile.ZipFile(zip_path) as archive:
        if set(archive.namelist()) != set(names) or archive.testzip() or any(
            archive.read(name) != (DESTINATION / name).read_bytes() for name in names
        ):
            raise ValueError("Markdown delivery archive changed")
    return {"directory": str(DESTINATION), "zip": str(zip_path), "assignments": assignments, "reserved": "reviewer_10",
            "ratings_per_pair": 2, "responses_prefilled": False}


def load_assignment(reviewer):
    manifest_path = DESTINATION / "issued_manifest.json"
    manifest = read_json(manifest_path)
    evidence = read_json(PRIVATE / "assignment_manifest.json")
    key_path = PRIVATE / "assignment_key.csv"
    if (file_hash(manifest_path) != evidence["public_manifest_sha256"] or file_hash(key_path) != evidence["assignment_key_sha256"]
        or file_hash(BASE / "annotations/issued_manifest.json") != manifest["original_semantic_manifest_sha256"]
        or file_hash(BASE / "source_review/issued_manifest.json") != manifest["original_source_manifest_sha256"]):
        raise ValueError("Issued Markdown lineage changed")
    entry = manifest["assignments"].get(reviewer)
    if entry is None:
        raise ValueError("Unknown or not-yet-issued reviewer assignment")
    path = DESTINATION / entry["packet"]
    if path.parent != DESTINATION or file_hash(path) != manifest["files_sha256"][entry["packet"]]:
        raise ValueError("Issued Markdown template changed")
    forms, keys, originals, source = load_inputs()
    if entry["kind"] == "source":
        rows = source
    else:
        assigned, mapping = assignment_rows(forms, keys, originals)
        if mapping != read_csv(key_path):
            raise ValueError("Markdown mapping does not reproduce from the original sample")
        rows = assigned[reviewer]
    if len(rows) != entry["items"]:
        raise ValueError("Markdown assignment coverage changed")
    return manifest, entry, path.read_text(encoding="utf-8"), rows


def check(reviewer, path):
    _, entry, template, rows = load_assignment(reviewer)
    parsed, errors = parse_return(Path(path).read_text(encoding="utf-8-sig"), template, entry["kind"], rows)
    return {"reviewer": reviewer, "items": len(parsed), "complete": not errors,
            "items_needing_responses": len({e["item_id"] for e in errors}), "errors": errors[:20]}


def check_metadata(record, issued):
    completion_window(record, issued)
    if not isinstance(record.get("reviewer_id"), str) or not record["reviewer_id"].strip():
        raise ValueError("An actual reviewer identity reference is required")
    if record.get("origin") != "independent_person" or not record.get("provenance_note", "").strip():
        raise ValueError("Independent origin requires a separately recorded investigator provenance basis")


def ingest(reviewer, path, reviewer_id, completed_utc, origin, provenance_note, *, reported_window=None):
    manifest, entry, template, blank = load_assignment(reviewer)
    raw = Path(path).read_bytes()
    rows, errors = parse_return(raw.decode("utf-8-sig"), template, entry["kind"], blank)
    if errors:
        raise ValueError(f"{len({e['item_id'] for e in errors})} items still require ratings or notes")
    record = {"reviewer": reviewer, "reviewer_id": reviewer_id.strip(),
              "received_utc": now(), "origin": origin, "provenance_note": provenance_note.strip(),
              "packet_sha256": manifest["files_sha256"][entry["packet"]], "original_md_sha256": digest_text(raw.decode("utf-8-sig")),
              "raw_md_sha256": hashlib.sha256(raw).hexdigest(), "kind": entry["kind"], "items": len(rows),
              "completion_confirmation_basis": "investigator_record_separate_from_markdown_content"}
    if completed_utc:
        record["completed_utc"] = completed_utc
    if reported_window is not None:
        record["completion_window"] = reported_window
    if origin not in {"independent_person", "assisted"} or not record["provenance_note"]:
        raise ValueError("A declared origin and its investigator provenance basis are required")
    if origin == "independent_person":
        check_metadata(record, manifest["issued_utc"])
        known = [read_json(p) for p in (PRIVATE / "returns").glob("*/record.json") if p.parent.name != reviewer]
        source_record = BASE / "source_review/private/attestation.json"
        if source_record.exists() and entry["kind"] != "source":
            known.append(read_json(source_record))
        if any(r.get("reviewer_id", "").strip().casefold() == record["reviewer_id"].casefold() for r in known):
            raise ValueError("Different assignments require different people; source exposure conflicts with blinded meaning review")
    folder = PRIVATE / "returns" / reviewer
    extension = "jsonl" if entry["kind"] == "source" else "csv"
    parsed_bytes = encode_return("source" if entry["kind"] == "source" else "semantic_A", rows)
    record["parsed_sha256"] = hashlib.sha256(parsed_bytes).hexdigest()
    if folder.exists():
        raise ValueError("An original return already exists; corrections must be recorded separately")
    immutable(folder / "original.md", raw)
    immutable(folder / f"parsed.{extension}", parsed_bytes)
    immutable(folder / "record.json", json_bytes(record))
    if entry["kind"] == "source" and origin == "independent_person":
        from .expanded_review import register
        metadata = {**record, "attested_independent_human": True, "return_sha256": file_hash(folder / "parsed.jsonl"),
                    "actor": "investigator_markdown_intake"}
        register({"kind": "source"}, folder / "parsed.jsonl", metadata)
    return {"reviewer": reviewer, "items": len(rows), "origin": origin, "preserved": True,
            "original_md_sha256": record["raw_md_sha256"], "review_complete": entry["kind"] == "source" and origin == "independent_person"}


def analyze_partitioned(returned, keys, expected_pairs):
    """Pure rating analysis, without inferring person identity or provenance."""
    from .expanded_review import agreement_rows
    joined, blocks = defaultdict(dict), defaultdict(dict)
    for key in keys:
        pair = key["model_key"], key["request_id"]
        if key["slot"] in joined[pair]:
            raise ValueError("Duplicate partitioned assignment")
        value = key, returned[key["reviewer"]][key["item_id"]]
        joined[pair][key["slot"]] = value
        blocks[key["block"]][pair] = joined[pair]
    if len(joined) != expected_pairs or any(set(pair) != {"A", "B"} for pair in joined.values()):
        raise ValueError("Each sampled pair must have exactly two distinct completed ratings")
    pooled, flags, _ = agreement_rows(joined)
    for flag in flags:
        pair = joined[flag["model_key"], flag["request_id"]]
        flag.update(reviewer_A=pair["A"][0]["reviewer"], reviewer_B=pair["B"][0]["reviewer"], block=pair["A"][0]["block"])
    for row in pooled:
        row.update(scope="pooled_role_descriptive_only", kappa="not_reported_pooled_across_different_people")
    agreements, identical_blocks, disagreements = list(pooled), [], []
    for block, pairs in sorted(blocks.items()):
        values, _, identical = agreement_rows(pairs)
        for row in values:
            row.update(scope="fixed_reviewer_pair_within_block", block=block,
                       reviewer_A=f"reviewer_{2 * int(block) - 1:02d}", reviewer_B=f"reviewer_{2 * int(block):02d}")
        agreements.extend(values)
        if identical:
            identical_blocks.append(block)
    from .annotations import RATINGS
    for pair in joined.values():
        key, a = pair["A"]
        _, b = pair["B"]
        for field in RATINGS:
            if a[field] != b[field]:
                disagreements.append({"item_id_A": key["item_id"], "item_id_B": pair["B"][0]["item_id"],
                                      "reviewer_A": key["reviewer"], "reviewer_B": pair["B"][0]["reviewer"],
                                      "field": field, "rating_A": a[field], "rating_B": b[field]})
    return agreements, flags, disagreements, identical_blocks


def validate_semantic():
    """Preserve each actual reviewer; never impersonate two whole-packet reviewers."""
    manifest = read_json(DESTINATION / "issued_manifest.json")
    records, returned, pending = {}, {}, []
    for index in range(1, 9):
        reviewer = f"reviewer_{index:02d}"
        record_path = PRIVATE / f"returns/{reviewer}/record.json"
        if not record_path.exists():
            pending.append(reviewer)
            continue
        _, entry, template, blank = load_assignment(reviewer)
        record = read_json(record_path)
        check_metadata(record, manifest["issued_utc"])
        raw_path = record_path.parent / "original.md"
        parsed_path = record_path.parent / "parsed.csv"
        if file_hash(raw_path) != record["raw_md_sha256"] or file_hash(parsed_path) != record["parsed_sha256"]:
            raise ValueError("Original Markdown return changed")
        rows, errors = parse_return(raw_path.read_text(encoding="utf-8-sig"), template, entry["kind"], blank)
        if errors or rows != read_csv(parsed_path) or record["packet_sha256"] != manifest["files_sha256"][entry["packet"]]:
            raise ValueError("Completed return no longer reproduces from its issued Markdown")
        records[reviewer] = record
        returned[reviewer] = {r["item_id"]: r for r in rows}
    if pending:
        result = {"complete": False, "stage": "awaiting_partitioned_returns", "pending_reviewers": pending,
                  "reviewers_received": len(records), "semantic_pairs": manifest["semantic_pairs"], "ratings_per_pair": 2}
        write_json(BASE / "annotations/validation.json", result)
        return result
    ids = [r["reviewer_id"].strip().casefold() for r in records.values()]
    if len(set(ids)) != 8:
        raise ValueError("Eight partitioned assignments must represent eight distinct reviewers")
    source_path = BASE / "source_review/private/attestation.json"
    if source_path.exists() and read_json(source_path)["reviewer_id"].strip().casefold() in set(ids):
        raise ValueError("Source reviewer cannot also supply blinded meaning ratings")
    agreements, flags, disagreements, identical_blocks = analyze_partitioned(
        returned, read_csv(PRIVATE / "assignment_key.csv"), manifest["semantic_pairs"])
    fields = ["model_key", "field", "items", "raw_agreement", "kappa", "weighting", "scope", "block", "reviewer_A", "reviewer_B"]
    write_csv(BASE / "annotations/agreement.csv", agreements, fields)
    write_csv(BASE / f"annotations/{'provisional_flags' if identical_blocks else 'verified_flags'}.csv", flags)
    write_csv(PRIVATE / "disagreements.csv", disagreements,
              ["item_id_A", "item_id_B", "reviewer_A", "reviewer_B", "field", "rating_A", "rating_B"])
    result = {"complete": not identical_blocks, "stage": "independence_followup_required" if identical_blocks else "validated_partitioned_returns",
              "actual_semantic_reviewers": 8, "semantic_pairs": len(flags), "ratings_per_pair": 2,
              "identical_rating_blocks": identical_blocks, "disputed_fields": len(disagreements),
              "original_return_hashes": {r: v["raw_md_sha256"] for r, v in records.items()},
              "agreement_scope": "within_fixed_reviewer_pairs; pooled_raw_agreement_descriptive_only",
              "semantic_sensitivity_still_required": True, "submission_ready": False}
    write_json(BASE / "annotations/validation.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("export")
    sub.add_parser("validate")
    for action in ("check", "ingest"):
        command = sub.add_parser(action)
        command.add_argument("--reviewer", required=True)
        command.add_argument("--file", type=Path, required=True)
        if action == "ingest":
            command.add_argument("--reviewer-id", required=True)
            date = command.add_mutually_exclusive_group(required=True)
            date.add_argument("--completed-utc")
            date.add_argument("--completion-window-json", type=Path)
            command.add_argument("--origin", choices=("independent_person", "assisted"), required=True)
            command.add_argument("--provenance-note", required=True)
    args = parser.parse_args()
    if args.action == "export":
        result = export()
    elif args.action == "validate":
        result = validate_semantic()
    elif args.action == "check":
        result = check(args.reviewer, args.file)
    else:
        result = ingest(args.reviewer, args.file, args.reviewer_id, args.completed_utc, args.origin, args.provenance_note,
                        reported_window=read_json(args.completion_window_json) if args.completion_window_json else None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
