"""Preserve offline returns and compute provisional, provenance-pending sensitivity.

This does not register reviewers, attest independence, or open the final review
gate. Identity-to-packet mapping and completion chronology remain separate from
mechanically valid ratings. The original union-risk rule is never adjudicated away.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from .annotations import RATINGS
from .expanded_primary import DESTINATION as PRIMARY, inputs as primary_inputs
from .expanded_semantic import summarize
from .expanded_study import BASE, effective_plan, now
from .io import ROOT, file_hash, normalized_text, read_csv, read_json
from . import markdown_review as markdown
from .review_app import encode_return, immutable, json_bytes

PRIVATE = BASE / "annotations/private/returned_batches"
PUBLIC = BASE / "review_results"
AGREEMENT_FIELDS = ["model_key", "field", "items", "raw_agreement", "kappa", "weighting",
                    "scope", "block", "reviewer_A", "reviewer_B"]
ADJUDICATION_FIELDS = ["case_id", "reviewer_A", "reviewer_B", "item_id_A", "item_id_B", "field",
                      "rating_A", "rating_B", "supported_rating", "decision", "unresolved_uncertainty"]


def preserve(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("Preserved audit evidence changed; create a separate revision")
    else:
        immutable(path, data)


def csv_bytes(rows, fields=None):
    if not rows and not fields:
        raise ValueError("Empty table requires columns")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def read_batch(path):
    """Read only ten fixed member names, with CRC, duplicate and size checks."""
    raw = Path(path).read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        expected = {f"reviewer_{i:02d}.md" for i in range(1, 11)}
        entries = archive.infolist()
        if len(entries) != 10 or {i.filename for i in entries} != expected:
            raise ValueError("Return archive must contain exactly the ten unique assigned Markdown files")
        if any(i.file_size > 10000000 or i.flag_bits & 1 for i in entries) or sum(i.file_size for i in entries) > 70000000:
            raise ValueError("Return archive is encrypted or exceeds supported size")
        if archive.testzip():
            raise ValueError("Return archive CRC failed")
        contents = {i.filename: archive.read(i) for i in entries}
    for data in contents.values():
        if "\ufffd" in data.decode("utf-8-sig"):
            raise ValueError("Return contains replacement characters; check its encoding")
    return raw, contents


def parse_adjudication(text, returned, disagreements):
    """Validate all disputed fields, linked items, source evidence and rating domains.

    Review 10 was initially a reserved task, not a frozen case packet. Its actual
    cases are checked against the untouched initial returns, not retrospectively
    called an issued packet. Decisions are stored separately from initial ratings.
    """
    text = normalized_text(text).lstrip("\ufeff")
    heads = list(re.finditer(r"^## Disagreement (\d{3}) · ([0-9a-f]{12})\n", text, re.M))
    expected = {(d["item_id_A"], d["item_id_B"], d["field"]): d for d in disagreements}
    if len(expected) != len(disagreements):
        raise ValueError("Duplicate expected disagreement")
    if len(heads) != len({(a, b) for a, b, _ in expected}) or len({h[2] for h in heads}) != len(heads):
        raise ValueError("Adjudication case coverage is incomplete or duplicated")
    if heads and [int(h[1]) for h in heads] != list(range(1, len(heads) + 1)):
        raise ValueError("Adjudication case numbering changed")
    lookup = {name: {row["item_id"]: (index, row) for index, row in enumerate(rows, 1)}
              for name, rows in returned.items()}
    field_names = {markdown.LABELS[field]: field for field in RATINGS}
    results, seen = [], set()
    for index, head in enumerate(heads):
        case = text[head.end(): heads[index + 1].start() if index + 1 < len(heads) else len(text)]
        links = list(re.finditer(
            r"^\[Review (\d{2}) · Pair (\d{3})\]\(reviewer_(\d{2})\.md#pair-(\d{3})--([0-9a-f]{20})\) — `([0-9a-f]{20})`$",
            case, re.M))
        if len(links) != 2:
            raise ValueError("Adjudication must reference two original items")
        linked = []
        for link in links:
            if link[1] != link[3] or link[2] != link[4] or link[5] != link[6]:
                raise ValueError("Adjudication link labels disagree")
            reviewer = "reviewer_" + link[1]
            if reviewer not in lookup or link[5] not in lookup[reviewer]:
                raise ValueError("Unknown adjudication item reference")
            position, row = lookup[reviewer][link[5]]
            if position != int(link[2]):
                raise ValueError("Adjudication link position changed")
            linked.append((reviewer, row))
        (ra, a), (rb, b) = linked
        if a["original_text"] != b["original_text"] or a["rewritten_text"] != b["rewritten_text"]:
            raise ValueError("Adjudication links do not identify the same pair")
        evidence = list(re.finditer(r"^(`{3,})text\n(.*?)^\1$", case, re.M | re.S))
        if len(evidence) != 2 or [m[2].removesuffix("\n") for m in evidence] != [a["original_text"], a["rewritten_text"]]:
            raise ValueError("Adjudication paired evidence changed")
        if "**Original**" not in case[:evidence[0].start()] or "**Rewrite**" not in case[evidence[0].end():evidence[1].start()]:
            raise ValueError("Adjudication evidence labels changed")
        tail = case[evidence[1].end():]
        header = f"| Field | {ra} | {rb} | Supported rating |"
        table = [line for line in tail.splitlines() if line.startswith("|")]
        if len(table) < 3 or table[:2] != [header, "|---|---|---|---|"]:
            raise ValueError("Adjudication decision table is missing or changed")
        decision = re.search(r"^- Decision: (.*?)\n- Unresolved uncertainty: (.*)\Z", tail.strip(), re.M | re.S)
        if not decision or not decision[1].strip() or not decision[2].strip():
            raise ValueError("Adjudication explanation or uncertainty statement missing")
        for line in table[2:]:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) != 4 or cells[0] not in field_names:
                raise ValueError("Unknown adjudication field")
            field = field_names[cells[0]]
            key = a["item_id"], b["item_id"], field
            if key not in expected or key in seen:
                raise ValueError("Invented or duplicate adjudication disagreement")
            original = expected[key]
            if (ra != original["reviewer_A"] or rb != original["reviewer_B"]
                or cells[1:3] != [original["rating_A"], original["rating_B"]]
                or cells[3] not in RATINGS[field]):
                raise ValueError("Adjudication original or supported rating is invalid")
            seen.add(key)
            results.append({"case_id": head[2], **original, "supported_rating": cells[3],
                            "decision": decision[1].strip(), "unresolved_uncertainty": decision[2].strip()})
    if seen != set(expected):
        raise ValueError("Adjudication has missing disputed fields")
    return results


def current_predictions():
    predictions, hashes = [], {}
    for model in effective_plan()["active_models"]:
        folder = PRIMARY / model
        manifest_path = folder / "manifest.json"
        manifest = read_json(manifest_path)
        replay = read_json(folder / "replay_verification.json")
        if (manifest["inputs"] != primary_inputs(model) or not replay["passed"]
            or replay["manifest_sha256"] != file_hash(manifest_path)):
            raise ValueError("Current replay-verified primary results required")
        for relative, expected in manifest["inputs"].items():
            path = ROOT / relative
            if not path.resolve().is_relative_to(ROOT.resolve()) or file_hash(path) != expected:
                raise ValueError("Primary input content changed")
        path = folder / "predictions.csv"
        if file_hash(path) != manifest["output_hashes"]["predictions.csv"]:
            raise ValueError("Primary predictions changed")
        predictions.extend(read_csv(path))
        hashes[model] = {"manifest_sha256": file_hash(manifest_path), "predictions_sha256": file_hash(path)}
    return predictions, hashes


def rating_summary(returned, keys, flags):
    linked = {(k["reviewer"], k["item_id"]): k for k in keys}
    grouped = defaultdict(list)
    for reviewer, rows in returned.items():
        for row in rows:
            grouped[linked[reviewer, row["item_id"]]["model_key"]].append(row)
    result = []
    for model, rows in sorted(grouped.items()):
        pairs = [flag for flag in flags if flag["model_key"] == model]
        unusable = {linked[reviewer, row["item_id"]]["request_id"]
                    for reviewer, items in returned.items() for row in items
                    if row["usable"] == "no" and linked[reviewer, row["item_id"]]["model_key"] == model}
        counts = Counter(row["meaning_preservation"] for row in rows)
        result.append({"model_key": model, "audited_pairs": len(pairs), "ratings": len(rows),
                       "mean_meaning": sum(int(row["meaning_preservation"]) for row in rows) / len(rows),
                       "risk_union_pairs": sum(flag["risk_union"] for flag in pairs),
                       "either_unusable_pairs": len(unusable), **{f"meaning_{s}_ratings": counts[str(s)] for s in range(1, 6)}})
    return result


def run(archive_path):
    raw, contents = read_batch(archive_path)
    archive_hash = hashlib.sha256(raw).hexdigest()
    batch = "provisional_" + archive_hash[:16]
    private, public = PRIVATE / batch, PUBLIC / batch
    returned, sources, packet_hashes = {}, [], {}
    for index in range(1, 10):
        reviewer = f"reviewer_{index:02d}"
        manifest, entry, template, blank = markdown.load_assignment(reviewer)
        rows, errors = markdown.parse_return(contents[reviewer + ".md"].decode("utf-8-sig"), template, entry["kind"], blank)
        if errors:
            raise ValueError(f"Incomplete ratings in {reviewer}")
        packet_hashes[reviewer] = manifest["files_sha256"][entry["packet"]]
        if entry["kind"] == "source":
            sources = rows
        else:
            returned[reviewer] = rows
    keys = read_csv(markdown.PRIVATE / "assignment_key.csv")
    agreements, flags, disagreements, identical = markdown.analyze_partitioned(
        {r: {row["item_id"]: row for row in rows} for r, rows in returned.items()}, keys, manifest["semantic_pairs"])
    adjudication = parse_adjudication(contents["reviewer_10.md"].decode("utf-8-sig"), returned, disagreements)
    predictions, primary_hashes = current_predictions()
    comparisons = summarize(predictions, flags)
    if len(comparisons) != len(primary_hashes) * 3 * 3 * 2:
        raise ValueError("Audited primary coverage is incomplete")
    summaries = rating_summary(returned, keys, flags)
    outputs = {"flags.csv": csv_bytes(flags), "agreement.csv": csv_bytes(agreements, AGREEMENT_FIELDS),
               "rating_summary.csv": csv_bytes(summaries), "comparisons.csv": csv_bytes(comparisons)}
    # Independent deterministic replay from the same immutable inputs; no timestamps
    # in result files, no raw reviewer text or personal identity in public artifacts.
    again_agreement, again_flags, _, _ = markdown.analyze_partitioned(
        {r: {row["item_id"]: row for row in rows} for r, rows in returned.items()}, keys, manifest["semantic_pairs"])
    replay = {"flags.csv": csv_bytes(again_flags), "agreement.csv": csv_bytes(again_agreement, AGREEMENT_FIELDS),
              "rating_summary.csv": csv_bytes(rating_summary(returned, keys, again_flags)),
              "comparisons.csv": csv_bytes(summarize(predictions, again_flags))}
    if outputs != replay:
        raise ValueError("Provisional analysis does not reproduce byte-for-byte")
    preserve(private / "submitted.zip", raw)
    for name, data in contents.items():
        preserve(private / "originals" / name, data)
    for reviewer, rows in returned.items():
        preserve(private / "parsed" / (reviewer + ".csv"), encode_return("semantic_A", rows))
    preserve(private / "parsed/reviewer_09.jsonl", encode_return("source", sources))
    preserve(private / "adjudication.csv", csv_bytes(adjudication, ADJUDICATION_FIELDS))
    for name, data in outputs.items():
        preserve(public / name, data)
    receipt = {"format_version": 1, "stage": "provisional_analysis_pending_reviewer_metadata",
               "submission_ready": False, "review_provenance_complete": False,
               "archive_sha256": archive_hash, "original_return_sha256": {n: hashlib.sha256(d).hexdigest() for n, d in sorted(contents.items())},
               "issued_manifest_sha256": file_hash(markdown.DESTINATION / "issued_manifest.json"),
               "issued_packet_sha256": packet_hashes, "assignment_key_sha256": file_hash(markdown.PRIVATE / "assignment_key.csv"),
               "primary_evidence": primary_hashes,
               "analysis_code_sha256": {p.name: file_hash(p) for p in (Path(__file__), Path(markdown.__file__), Path(summarize.__code__.co_filename))},
               "output_hashes": {n: hashlib.sha256(d).hexdigest() for n, d in sorted(outputs.items())},
               "result_replay_passed": True, "semantic_ratings": sum(len(v) for v in returned.values()),
               "semantic_pairs": len(flags), "risk_union_pairs": sum(f["risk_union"] for f in flags),
               "source_passes": sum(row["verdict"] == "pass" for row in sources), "source_items": len(sources),
               "disputed_fields": len(disagreements), "adjudicated_cases": len({r["case_id"] for r in adjudication}),
               "adjudication_field_coverage_valid": True, "initial_ratings_overwritten": False,
               "identical_rating_blocks": identical,
               "scope": "Descriptive paired audited valid-first-output subset; no new p-values and no certification of unrated outputs.",
               "unresolved": ["Actual people mapped to packet roles and clarification of nine reported people versus ten roles",
                              "Completion dates for these exact final packets issued October 3 Pakistan time",
                              "Informal proficiency labels, training and ethics/consent record details"]}
    preserve(public / "manifest.json", json_bytes(receipt))
    intake = {"received_utc": now(), "source_archive_sha256": archive_hash,
              "origin_status": "investigator_reported_people; role mapping and chronology pending",
              "mechanical_checks_passed": True, "registered_as_completed_independent_review": False}
    if not (private / "intake.json").exists():
        preserve(private / "intake.json", json_bytes(intake))
    return {"public_results": str(public), "private_originals_preserved": True,
            "semantic_pairs": len(flags), "risk_union_pairs": receipt["risk_union_pairs"],
            "source_passes": receipt["source_passes"], "adjudicated_cases": receipt["adjudicated_cases"],
            "disputed_fields": len(disagreements), "comparison_rows": len(comparisons),
            "result_replay_passed": True, "review_provenance_complete": False, "submission_ready": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    print(json.dumps(run(parser.parse_args().zip), indent=2))
