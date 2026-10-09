"""Register investigator-reported reviews; produce a de-identified local release.

Never infer names from roster order, alter issuance logs, certify non-use of
tools, or convert participant agreement into institutional ethics approval.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timezone, timedelta
import hashlib
import json
from pathlib import Path

from . import markdown_review as markdown
from . import expanded_review, expanded_semantic
from .annotations import RATINGS
from .expanded_study import BASE
from .io import file_hash, read_csv, read_json, write_json
from .review_app import json_bytes
from .review_chronology import completion_window
from .review_return_audit import (AGREEMENT_FIELDS, current_predictions, csv_bytes, parse_adjudication,
                                  preserve, rating_summary, read_batch)

PUBLIC = BASE / "review_release"
KEY_FIELDS = ["reviewer", "slot", "block", "item_id", "model_key", "request_id", "passage_id",
              "condition", "source_sha256", "rewrite_sha256"]


def validate_statement(record):
    roster = record.get("named_roster_not_linked_by_guess_to_packet_numbers", [])
    if (record.get("reported_distinct_people") != 10 or len(roster) != 10
        or len({r["name"].strip().casefold() for r in roster}) != 10
        or any(not r["name"].strip() or type(r.get("paid_as_reported")) is not bool for r in roster)):
        raise ValueError("A consistent ten-person investigator record is required")
    for field in ("one_numbered_packet_per_person", "all_over_18_reported", "separate_work_reported",
                  "verbal_consent_for_research_use_reported", "statement_usable_for_self_reported_review_registration"):
        if record.get(field) is not True:
            raise ValueError("Missing reported reviewer eligibility, consent or independence")
    if record.get("independence_objectively_verified") is not False:
        raise ValueError("Self-report must not be described as objectively verified")


def reported_window(statement, issued):
    # Bounds are not fabricated completion instants: one is actual issuance, the
    # other is the end of the investigator's reported Pakistan completion date.
    last_date = date.fromisoformat(statement["general_review_period_local"]["end"])
    last = datetime.combine(last_date, time.max, timezone(timedelta(hours=5))).astimezone(timezone.utc)
    window = {"precision": "bounded_interval", "earliest_utc": issued, "latest_utc": last.isoformat(),
              "basis": f"Investigator confirms final-packet recheck after actual issuance and completion by the reported {last_date.isoformat()} Pakistan date; bounds are not exact reviewer completion timestamps."}
    completion_window({"completion_window": window}, issued)
    return window


def replay_ratings(ratings, expected_pairs):
    """Reconstruct flags/agreement from released numeric ratings, not private notes."""
    returned, keys = {}, []
    for row in ratings:
        keys.append({f: row[f] for f in KEY_FIELDS})
        values = {f: row[f] for f in RATINGS}
        if any(values[f] not in RATINGS[f] for f in RATINGS):
            raise ValueError("Invalid released rating")
        items = returned.setdefault(row["reviewer"], {})
        if row["item_id"] in items:
            raise ValueError("Duplicate released rating item")
        items[row["item_id"]] = values
    return markdown.analyze_partitioned(returned, keys, expected_pairs)


def run(statement_path, zip_path):
    statement_path = Path(statement_path)
    statement = read_json(statement_path)
    validate_statement(statement)
    statement_hash = file_hash(statement_path)
    raw, contents = read_batch(zip_path)
    zip_hash = hashlib.sha256(raw).hexdigest()
    old_public = BASE / "review_results" / ("provisional_" + zip_hash[:16])
    old = read_json(old_public / "manifest.json")
    if old["archive_sha256"] != zip_hash:
        raise ValueError("Submitted ZIP differs from the preserved audit")
    for name, expected in old["original_return_sha256"].items():
        if hashlib.sha256(contents[name]).hexdigest() != expected:
            raise ValueError("Original returned packet changed")
    parsed, entries, packet_manifest = {}, {}, None
    for index in range(1, 10):
        reviewer = f"reviewer_{index:02d}"
        packet_manifest, entry, template, blank = markdown.load_assignment(reviewer)
        rows, errors = markdown.parse_return(contents[reviewer + ".md"].decode("utf-8-sig"), template, entry["kind"], blank)
        if errors:
            raise ValueError("Returned packet still has missing ratings")
        parsed[reviewer], entries[reviewer] = rows, entry
    window = reported_window(statement, packet_manifest["issued_utc"])
    keys = read_csv(markdown.PRIVATE / "assignment_key.csv")
    initial = {r: {row["item_id"]: row for row in rows} for r, rows in parsed.items() if r != "reviewer_09"}
    agreements, flags, disagreements, identical = markdown.analyze_partitioned(initial, keys, packet_manifest["semantic_pairs"])
    if identical:
        raise ValueError("Identical complete rating blocks need independence follow-up")
    adjudication = parse_adjudication(contents["reviewer_10.md"].decode("utf-8-sig"),
                                     {r: rows for r, rows in parsed.items() if r != "reviewer_09"}, disagreements)
    predictions, primary_hashes = current_predictions()
    comparisons = expanded_semantic.summarize(predictions, flags)
    summaries = rating_summary({r: rows for r, rows in parsed.items() if r != "reviewer_09"}, keys, flags)
    old_outputs = {"flags.csv": csv_bytes(flags), "agreement.csv": csv_bytes(agreements, AGREEMENT_FIELDS),
                   "comparisons.csv": csv_bytes(comparisons), "rating_summary.csv": csv_bytes(summaries)}
    for name, data in old_outputs.items():
        if hashlib.sha256(data).hexdigest() != old["output_hashes"][name] or (old_public / name).read_bytes() != data:
            raise ValueError("Final calculation differs from preserved provisional results")
    if any((BASE / f"annotations/private/attestation_{s}.json").exists() for s in ("A", "B")):
        raise ValueError("Whole-packet and partitioned review routes must not be mixed")
    note = (f"Investigator clarification dated {statement['statement_date']}, SHA-256 {statement_hash}: ten distinct actual people, "
            "one numbered packet per person, separate work and prohibited assistance denied by self-report. "
            "Assignment-bound participant pseudonym; no name inferred from roster order. "
            "Final packet rechecked against earlier work and previously unreviewed items assessed. "
            "No independently verified identity, tool non-use or exact completion time; no institutional ethics approval inferred.")
    # Preflight every original record before creating any new registration.
    for reviewer in parsed:
        record_path = markdown.PRIVATE / f"returns/{reviewer}/record.json"
        if record_path.exists():
            record = read_json(record_path)
            markdown.check_metadata(record, packet_manifest["issued_utc"])
            if (record["reviewer_id"] != "participant_" + reviewer[-2:] or record["provenance_note"] != note
                or record.get("completion_window") != window
                or record["raw_md_sha256"] != hashlib.sha256(contents[reviewer + ".md"]).hexdigest()):
                raise ValueError("Existing reviewer provenance conflicts; do not overwrite it")
    source_attestation = BASE / "source_review/private/attestation.json"
    if source_attestation.exists() and read_json(source_attestation)["reviewer_id"] != "participant_09":
        raise ValueError("An existing source identity conflicts; do not replace it")
    private_batch = BASE / "annotations/private/returned_batches" / ("provisional_" + zip_hash[:16])
    preserve(private_batch / "submitted.zip", raw)
    for reviewer in parsed:
        original = private_batch / "originals" / (reviewer + ".md")
        preserve(original, contents[reviewer + ".md"])
        if not (markdown.PRIVATE / f"returns/{reviewer}/record.json").exists():
            markdown.ingest(reviewer, original, "participant_" + reviewer[-2:], None,
                            "independent_person", note, reported_window=window)
    validation = markdown.validate_semantic()
    source = expanded_review.source_validation()
    if not validation["complete"] or not source["passed"]:
        raise ValueError("Registered source/semantic review did not pass")
    adjudication_record = {"reviewer": "reviewer_10", "reviewer_id": "participant_10", "origin": "independent_person",
                           "completion_window": window, "provenance_note": note, "investigator_statement_sha256": statement_hash,
                           "raw_md_sha256": hashlib.sha256(contents["reviewer_10.md"]).hexdigest(),
                           "cases": len({r["case_id"] for r in adjudication}), "fields": len(adjudication),
                           "initial_ratings_overwritten": False, "identity_is_assignment_bound_pseudonym": True}
    markdown.check_metadata(adjudication_record, packet_manifest["issued_utc"])
    preserve(markdown.PRIVATE / "adjudication/record.json", json_bytes(adjudication_record))
    sensitivity = expanded_semantic.run()
    if not sensitivity["complete"] or file_hash(BASE / "semantic_sensitivity/comparisons.csv") != old["output_hashes"]["comparisons.csv"]:
        raise ValueError("Review-gated sensitivity does not reproduce")
    ratings = [{**{f: k[f] for f in KEY_FIELDS}, **{f: initial[k["reviewer"]][k["item_id"]][f] for f in RATINGS}} for k in keys]
    replay_agreement, replay_flags, replay_disputes, replay_identical = replay_ratings(ratings, len(flags))
    if (csv_bytes(replay_flags) != old_outputs["flags.csv"]
        or csv_bytes(replay_agreement, AGREEMENT_FIELDS) != old_outputs["agreement.csv"]
        or replay_disputes != disagreements or replay_identical
        or csv_bytes(expanded_semantic.summarize(predictions, replay_flags)) != old_outputs["comparisons.csv"]):
        raise ValueError("Released numeric ratings do not independently reproduce the results")
    method = {"statement_date": statement["statement_date"], "participants": 10, "initial_raters": 8,
              "source_reviewer": 1, "adjudicator": 1, "one_packet_per_person": True,
              "identity_reference": "Assignment-bound pseudonyms; investigator confirms ten distinct actual people. Names not inferred from list order.",
              "age": "All over 18, investigator-reported", "education": "University undergraduates, investigator-reported",
              "proficiency": "Informal investigator assessment; no calibrated CEFR score established",
              "recruitment": "Convenience requests to classmates/acquaintances who know one another",
              "compensated": sum(r["paid_as_reported"] for r in statement["named_roster_not_linked_by_guess_to_packet_numbers"]),
              "uncompensated": sum(not r["paid_as_reported"] for r in statement["named_roster_not_linked_by_guess_to_packet_numbers"]),
              "compensation_rates": "Not supplied; not inferred per packet", "consent": "Verbal research-use consent reported; written confirmation not received",
              "instructions": "Separate work, no help from each other and no prohibited assistance, investigator-reported",
              "formal_calibration": "Not documented", "independence_basis": "Investigator/reviewer self-report, not objective verification",
              "review_workflow": "Earlier judgments rechecked against the final packet; newly encountered final-packet content assessed",
              "general_review_period_local": statement["general_review_period_local"], "final_packet_recheck_completion_window": window,
              "issue_logs_changed": False, "ethics_approval_or_exemption": "Not documented; basic ethics agreement is not institutional approval",
              "submission_ethics_gate_satisfied": False, "raw_notes_public": False, "names_public": False}
    decisions = [{k: v for k, v in r.items() if k not in {"decision", "unresolved_uncertainty"}} for r in adjudication]
    sources = [{"passage_id": r["passage_id"], "verdict": r["verdict"], "reviewer": "reviewer_09"} for r in parsed["reviewer_09"]]
    decision_fields = ["case_id", "reviewer_A", "reviewer_B", "item_id_A", "item_id_B", "field", "rating_A", "rating_B", "supported_rating"]
    outputs = {**old_outputs, "ratings.csv": csv_bytes(ratings), "adjudication_decisions.csv": csv_bytes(decisions, decision_fields),
               "source_verdicts.csv": csv_bytes(sources), "participant_methods.json": json_bytes(method)}
    folder = PUBLIC / ("self_reported_" + statement_hash[:16])
    for name, data in outputs.items():
        preserve(folder / name, data)
    modules = (Path(__file__), Path(markdown.__file__), Path(expanded_review.__file__), Path(expanded_semantic.__file__),
               Path(completion_window.__code__.co_filename), Path(__file__).with_name("review_return_audit.py"),
               Path(__file__).with_name("annotations.py"), Path(__file__).with_name("review_app.py"), Path(__file__).with_name("io.py"))
    receipt = {"format_version": 1, "stage": "registered_investigator_reported_reviews", "review_complete": True,
               "submission_ready": False, "submission_ethics_gate_satisfied": False, "independence_objectively_verified": False,
               "investigator_statement_sha256": statement_hash, "source_zip_sha256": zip_hash,
               "source_member_sha256": old["original_return_sha256"], "issued_manifest_sha256": file_hash(markdown.DESTINATION / "issued_manifest.json"),
               "assignment_key_sha256": file_hash(markdown.PRIVATE / "assignment_key.csv"), "primary_evidence": primary_hashes,
               "registered_return_record_sha256": {r: file_hash(markdown.PRIVATE / f"returns/{r}/record.json") for r in parsed},
               "adjudication_record_sha256": file_hash(markdown.PRIVATE / "adjudication/record.json"),
               "source_validation": source, "semantic_validation_sha256": file_hash(BASE / "annotations/validation.json"),
               "analysis_code_sha256": {p.name: file_hash(p) for p in modules},
               "output_hashes": {n: hashlib.sha256(d).hexdigest() for n, d in sorted(outputs.items())},
               "result_replay_passed": True, "public_ratings_replay_passed": True, "same_results_as_preserved_provisional_audit": True,
               "ratings": len(ratings), "semantic_pairs": len(flags), "risk_union_pairs": sum(f["risk_union"] for f in flags),
               "adjudicated_cases": adjudication_record["cases"], "disputed_fields": len(disagreements),
               "scope": sensitivity["scope"], "initial_ratings_overwritten": False,
               "remaining": ["Document the actual applicable institutional ethics approval/exemption basis and any consent documentation required for submission/deposit",
                             "Investigator rights/license, authorship/contribution and assistance disclosures",
                             "Actual archival deposit/DOI and journal submission checks", "Manuscript writing, explicitly deferred"]}
    preserve(folder / "manifest.json", json_bytes(receipt))
    result = {"complete": True, "review_basis": "investigator_reported_not_objectively_certified",
              "release_folder": folder.relative_to(BASE).as_posix(), "manifest_sha256": file_hash(folder / "manifest.json"),
              "ratings": len(ratings), "semantic_pairs": len(flags), "risk_union_pairs": receipt["risk_union_pairs"],
              "source_followup_passed": True, "adjudication_complete": True, "public_ratings_replay_passed": True,
              "comparison_rows": len(comparisons), "submission_ready": False, "remaining": receipt["remaining"]}
    write_json(PUBLIC / "status.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statement", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.statement, args.zip), indent=2))
