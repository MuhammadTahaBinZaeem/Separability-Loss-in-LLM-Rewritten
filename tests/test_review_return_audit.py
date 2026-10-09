"""Synthetic audit fixtures: returned text is evidence, not inferred person identity."""
from pathlib import Path
import zipfile

import pytest

from research_v2 import review_return_audit as audit
from research_v2 import markdown_review as m
from research_v2.io import digest_text, read_csv, read_json, write_csv, write_json


def evidence_case():
    a = {"item_id": "a" * 20, "original_text": "Original synthetic passage.", "rewritten_text": "Synthetic rewrite."}
    b = {**a, "item_id": "b" * 20}
    dispute = {"item_id_A": a["item_id"], "item_id_B": b["item_id"], "reviewer_A": "reviewer_01",
               "reviewer_B": "reviewer_02", "field": "meaning_preservation", "rating_A": "4", "rating_B": "5"}
    text = ("# Review 10\n\n## Disagreement 001 · abcdef012345\n\n"
            f"[Review 01 · Pair 001](reviewer_01.md#pair-001--{a['item_id']}) — `{a['item_id']}`\n\n"
            f"[Review 02 · Pair 001](reviewer_02.md#pair-001--{b['item_id']}) — `{b['item_id']}`\n\n"
            f"**Original**\n\n{m.fence(a['original_text'])}\n**Rewrite**\n\n{m.fence(a['rewritten_text'])}\n"
            "| Field | reviewer_01 | reviewer_02 | Supported rating |\n|---|---|---|---|\n"
            "| Meaning preservation | 4 | 5 | 4 |\n\n"
            "- Decision: Synthetic passage evidence only.\n- Unresolved uncertainty: Synthetic uncertainty.\n")
    return text, {"reviewer_01": [a], "reviewer_02": [b]}, [dispute]


def test_adjudication_keeps_all_initial_fields_and_checks_evidence():
    text, returns, disputes = evidence_case()
    rows = audit.parse_adjudication(text, returns, disputes)
    assert rows[0]["rating_A"] == "4" and rows[0]["rating_B"] == "5" and rows[0]["supported_rating"] == "4"
    assert disputes[0]["rating_B"] == "5"
    for bad, message in (
        (text.replace("Original synthetic passage.", "Tampered evidence."), "evidence"),
        (text.replace("| 4 | 5 | 4 |", "| 4 | 5 | 9 |"), "rating"),
        (text.replace("| 4 | 5 | 4 |", "| 5 | 5 | 4 |"), "rating"),
        (text.replace("Meaning preservation", "Tone drift"), "disagreement"),
        (text.replace("Pair 001](reviewer_02.md#pair-001", "Pair 002](reviewer_02.md#pair-002"), "position"),
        (text.replace("- Unresolved uncertainty: Synthetic uncertainty.", ""), "uncertainty"),
        (text.replace("| Meaning preservation | 4 | 5 | 4 |", "| Meaning preservation | 4 | 5 | 4 |\n| Meaning preservation | 4 | 5 | 4 |"), "duplicate"),
    ):
        with pytest.raises(ValueError, match=message):
            audit.parse_adjudication(bad, returns, disputes)
    with pytest.raises(ValueError, match="coverage"):
        audit.parse_adjudication(text.split("## Disagreement")[0], returns, disputes)


def test_zip_intake_rejects_duplicate_and_traversal_members(tmp_path):
    path = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(path, "w") as z:
        for index in range(1, 11):
            z.writestr(f"reviewer_{index:02d}.md", "Synthetic evidence only.")
    raw, files = audit.read_batch(path)
    assert len(files) == 10 and raw == path.read_bytes()
    with zipfile.ZipFile(path, "a") as z:
        z.writestr("../private.json", "not allowed")
    with pytest.raises(ValueError, match="exactly"):
        audit.read_batch(path)


def test_provisional_intake_cannot_register_or_publish_identities(tmp_path, monkeypatch):
    base = tmp_path / "expanded"
    monkeypatch.setattr(audit, "PRIVATE", base / "annotations/private/returned_batches")
    monkeypatch.setattr(audit, "PUBLIC", base / "review_results")
    monkeypatch.setattr(m, "DESTINATION", base / "issued")
    monkeypatch.setattr(m, "PRIVATE", base / "annotations/private/assignments")
    keys, blanks, contents = [], {}, {}
    for index in range(1, 9):
        reviewer = f"reviewer_{index:02d}"
        pair = str((index + 1) // 2)
        iid = digest_text(reviewer)[:20]
        blank = {"item_id": iid, "original_text": f"Original {pair}.", "rewritten_text": f"Rewrite {pair}.",
                 **{field: "" for field in m.SEMANTIC_FIELDS}}
        blanks[reviewer] = [blank]
        keys.append({"reviewer": reviewer, "block": pair, "slot": "A" if index % 2 else "B", "item_id": iid,
                     "model_key": "synthetic", "request_id": pair, "passage_id": pair, "condition": "paraphrase",
                     "source_sha256": "source", "rewrite_sha256": "rewrite"})
    source = {"passage_id": "source", "text": "Synthetic source.", "gutenberg_id": "0", "author_id": "synthetic",
              "source_start_char": 0, "source_end_char": 5, "verdict": "", "notes": ""}
    blanks["reviewer_09"] = [source]
    context = {"source": {"title": "Synthetic", "before": "Before.", "raw_span": "Synthetic source.", "after": "After."}}
    for reviewer, rows in blanks.items():
        kind = "source" if reviewer == "reviewer_09" else "semantic"
        template = m.render_packet(reviewer, kind, rows, context)
        values = {"added_facts": "0", "omitted_facts": "0", "order_changed": "0", "relationships_changed": "0",
                  "tone_drift": "0", "meaning_preservation": "5", "usable": "yes", "notes": "Synthetic only.", "verdict": "pass"}
        fields = ["verdict", "notes"] if kind == "source" else m.SEMANTIC_FIELDS
        completed = m.RESPONSE_RE.sub(lambda match: f"<!-- response:{match[1]} -->\n{m.response_body(fields, values)}<!-- /response -->", template)
        contents[reviewer + ".md"] = completed
    contents["reviewer_10.md"] = "# Review 10\n\nNo disputed synthetic fields.\n"
    manifest = {"semantic_pairs": 4, "files_sha256": {name: digest_text(data) for name, data in contents.items()}}
    write_json(m.DESTINATION / "issued_manifest.json", manifest)
    write_csv(m.PRIVATE / "assignment_key.csv", keys)
    def assignment(reviewer):
        kind = "source" if reviewer == "reviewer_09" else "semantic"
        return manifest, {"packet": reviewer + ".md", "kind": kind}, m.render_packet(reviewer, kind, blanks[reviewer], context), blanks[reviewer]
    monkeypatch.setattr(m, "load_assignment", assignment)
    monkeypatch.setattr(audit, "current_predictions", lambda: ([], {"synthetic": {"manifest_sha256": "fixture"}}))
    monkeypatch.setattr(audit, "summarize", lambda p, f: [{"synthetic_comparison": i} for i in range(18)])
    def forbidden(*args, **kwargs):
        raise AssertionError("Provisional intake must never register a person or completed review")
    monkeypatch.setattr(m, "ingest", forbidden)
    monkeypatch.setattr(m, "validate_semantic", forbidden)
    path = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(path, "w") as z:
        for name, text in contents.items():
            z.writestr(name, text)
    result = audit.run(path)
    assert result["result_replay_passed"] and not result["submission_ready"] and not result["review_provenance_complete"]
    public = Path(result["public_results"])
    assert read_json(public / "manifest.json")["initial_ratings_overwritten"] is False
    assert len(read_csv(public / "flags.csv")) == 4
    assert not (base / "annotations/verified_flags.csv").exists()
    assert not (base / "annotations/private/assignments/returns").exists()
    assert audit.run(path) == result
