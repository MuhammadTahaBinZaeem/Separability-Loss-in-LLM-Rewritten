"""Synthetic offline returns only: coverage, text integrity and actual rater identity."""
from datetime import datetime, timezone

import pytest

from research_v2 import markdown_review as m
from research_v2.io import digest_text, read_csv, read_json, write_json


def fixture_inputs():
    forms, keys, originals = {"A": [], "B": []}, [], {}
    for work in range(4):
        for index in range(5):
            pid = f"passage_{work}_{index}"
            originals[pid] = {"author_id": "synthetic", "work_id": f"work_{work}"}
            for slot in ("A", "B"):
                iid = digest_text(f"{slot}:{pid}")[:20]
                forms[slot].append({"item_id": iid, "original_text": f"Original {pid}.\nLiteral ``` and |.",
                                    "rewritten_text": f"Rewrite {pid}.", **{f: "" for f in m.SEMANTIC_FIELDS}})
                keys.append({"slot": slot, "item_id": iid, "model_key": "synthetic_model", "request_id": pid,
                             "passage_id": pid, "condition": "synthetic", "source_sha256": "source", "rewrite_sha256": "rewrite"})
    source = [{"passage_id": "synthetic_source", "text": "Selected source.", "gutenberg_id": "0",
               "author_id": "synthetic", "source_start_char": 10, "source_end_char": 20,
               "verdict": "", "notes": ""}]
    return forms, keys, originals, source


def fill(text, kind="semantic", meaning="5"):
    values = {"added_facts": "0", "omitted_facts": "0", "order_changed": "0", "relationships_changed": "0",
              "tone_drift": "0", "meaning_preservation": meaning, "usable": "yes", "notes": ""}
    if kind == "source":
        values = {"verdict": "pass", "notes": "Synthetic evidence only.\nBoth boundaries checked."}
    fields = ["verdict", "notes"] if kind == "source" else m.SEMANTIC_FIELDS
    return m.RESPONSE_RE.sub(lambda match: f"<!-- response:{match[1]} -->\n{m.response_body(fields, values)}<!-- /response -->", text)


@pytest.fixture
def offline(monkeypatch, tmp_path):
    base = tmp_path / "expanded"
    monkeypatch.setattr(m, "BASE", base)
    monkeypatch.setattr(m, "DESTINATION", base / "review_markdown_20261002")
    monkeypatch.setattr(m, "PRIVATE", base / "annotations/private/markdown_20261002")
    inputs = fixture_inputs()
    monkeypatch.setattr(m, "load_inputs", lambda: inputs)
    monkeypatch.setattr(m, "source_material", lambda row: {"title": "Synthetic work", "before": "Before.",
                                                          "raw_span": "Selected source.", "after": "After."})
    write_json(base / "annotations/issued_manifest.json", {"synthetic": True})
    write_json(base / "source_review/issued_manifest.json", {"synthetic": True})
    m.export()
    return base


def test_balanced_partition_keeps_every_pair_double_rated_in_every_stratum():
    forms, keys, originals, _ = fixture_inputs()
    assigned, mapping = m.assignment_rows(forms, keys, originals)
    assert len(assigned) == 8 and {len(rows) for rows in assigned.values()} == {5}
    for key in keys:
        assert sum(row["slot"] == key["slot"] and row["item_id"] == key["item_id"] for row in mapping) == 1
    for work in range(4):
        subset = [k for k in mapping if originals[k["passage_id"]]["work_id"] == f"work_{work}"]
        assert {k["block"] for k in subset} == {"1", "2", "3", "4"}
    assert {row["item_id"] for values in assigned.values() for row in values} == {row["item_id"] for row in keys}


def test_return_roundtrip_preserves_literal_text_and_multiline_notes():
    forms, _, _, sources = fixture_inputs()
    blank = forms["A"][:2]
    template = m.render_packet("reviewer_01", "semantic", blank)
    completed = fill(template).replace("- Notes: \n", "- Notes: Evidence line one.\nEvidence line two.\n")
    rows, errors = m.parse_return(completed.replace("\n", "\r\n"), template, "semantic", blank)
    assert not errors
    assert rows[0]["original_text"] == blank[0]["original_text"]
    assert rows[0]["notes"] == "Evidence line one.\nEvidence line two."
    context = {"synthetic_source": {"title": "Synthetic", "before": "Before.", "raw_span": "Selected source.", "after": "After."}}
    source_template = m.render_packet("reviewer_09", "source", sources, context)
    rows, errors = m.parse_return(fill(source_template, "source"), source_template, "source", sources)
    assert not errors and rows[0]["verdict"] == "pass"


def test_modified_passage_and_duplicate_items_are_rejected():
    forms, _, _, _ = fixture_inputs()
    blank = forms["A"][:2]
    template = m.render_packet("reviewer_01", "semantic", blank)
    with pytest.raises(ValueError, match="issued passage"):
        m.parse_return(fill(template).replace("Original passage", "Altered passage"), template, "semantic", blank)
    with pytest.raises(ValueError, match="duplicate"):
        m.parse_return(fill(template).replace(blank[1]["item_id"], blank[0]["item_id"]), template, "semantic", blank)


def test_only_accurate_summary_headers_are_accepted():
    forms, _, _, _ = fixture_inputs()
    blank = forms["A"][:2]
    template = m.render_packet("reviewer_01", "semantic", blank)
    summary = "2 completed pair reviews. Meaning scores: 1: 0, 2: 0, 3: 0, 4: 0, 5: 2. Usable: 2; unusable: 0."
    returned = fill(template).replace("2 pairs.", summary).replace("# Review 01\n\n", "# Review 01\n\n\n")
    rows, errors = m.parse_return(returned, template, "semantic", blank)
    assert len(rows) == 2 and not errors
    for bad in (returned.replace("5: 2", "5: 1"), returned.replace("Usable: 2", "Usable: 1"),
                returned.replace("# Review 01", "# Review 02"), returned.replace("meaning retained", "meaning inferred"),
                returned.replace(summary, "Two excellent reviews.")):
        with pytest.raises(ValueError, match="instruction/title|summary"):
            m.parse_return(bad, template, "semantic", blank)
    with pytest.raises(ValueError, match="issued passage"):
        m.parse_return(returned.replace("Original passage", "Original evidence"), template, "semantic", blank)


def test_source_count_omission_does_not_relax_source_context_checks():
    _, _, _, sources = fixture_inputs()
    context = {"synthetic_source": {"title": "Synthetic", "before": "Before.", "raw_span": "Selected source.", "after": "After."}}
    template = m.render_packet("reviewer_09", "source", sources, context)
    returned = fill(template, "source").replace("1 passages.\n", "")
    _, errors = m.parse_return(returned, template, "source", sources)
    assert not errors
    with pytest.raises(ValueError, match="issued passage"):
        m.parse_return(returned.replace("Before.", "Changed context."), template, "source", sources)
    with pytest.raises(ValueError, match="instruction/title"):
        m.parse_return(returned.replace("1 = yes", "1 = no").replace("# Review 09", "# Review 08"), template, "source", sources)


def test_blanks_and_unsupported_ratings_do_not_count_as_complete():
    forms, _, _, _ = fixture_inputs()
    blank = forms["A"][:1]
    template = m.render_packet("reviewer_01", "semantic", blank)
    _, errors = m.parse_return(template, template, "semantic", blank)
    assert errors
    _, errors = m.parse_return(fill(template, meaning="9"), template, "semantic", blank)
    assert any("meaning preservation" in row["error"] for row in errors)
    _, errors = m.parse_return(fill(template, meaning="2"), template, "semantic", blank)
    assert any("Notes" in row["error"] for row in errors)


def test_export_is_repeatable_and_contains_no_private_mapping(offline):
    receipt = read_json(m.DESTINATION / "issued_manifest.json")
    assert receipt["ratings_per_pair"] == 2
    assert len(receipt["assignments"]) == 9
    m.export()
    import zipfile
    with zipfile.ZipFile(m.DESTINATION.parent / "review_markdown_20261002.zip") as archive:
        assert "assignment_key.csv" not in archive.namelist()
        assert {f"reviewer_{i:02d}.md" for i in range(1, 11)} <= set(archive.namelist())
    assert "synthetic_model" not in (m.DESTINATION / "reviewer_01.md").read_text()


def test_intake_preserves_eight_people_and_within_pair_agreement(offline):
    for index in range(1, 9):
        reviewer = f"reviewer_{index:02d}"
        template = (m.DESTINATION / f"{reviewer}.md").read_text(encoding="utf-8")
        path = offline / f"returned_{reviewer}.md"
        path.write_text(fill(template, meaning="5" if index % 2 else "4"), encoding="utf-8")
        m.ingest(reviewer, path, f"synthetic-person-{index}", datetime.now(timezone.utc).isoformat(),
                 "independent_person", "Synthetic fixture provenance; not a production review.")
    result = m.validate_semantic()
    assert result["complete"] and result["actual_semantic_reviewers"] == 8 and result["semantic_pairs"] == 20
    agreement = read_csv(offline / "annotations/agreement.csv")
    assert {r["block"] for r in agreement if r["scope"] == "fixed_reviewer_pair_within_block"} == {"1", "2", "3", "4"}
    assert all(r["kappa"] == "not_reported_pooled_across_different_people" for r in agreement if r["scope"] == "pooled_role_descriptive_only")
    assert not (offline / "annotations/private/attestation_A.json").exists()
    assert len(read_csv(offline / "annotations/verified_flags.csv")) == 20
    with pytest.raises(ValueError, match="already exists"):
        m.ingest("reviewer_08", path, "synthetic-person-8", datetime.now(timezone.utc).isoformat(),
                 "independent_person", "Synthetic fixture.")


def test_same_person_cannot_be_registered_as_two_reviewers(offline):
    for index in (1, 2):
        reviewer = f"reviewer_{index:02d}"
        path = offline / f"returned_{reviewer}.md"
        path.write_text(fill((m.DESTINATION / f"{reviewer}.md").read_text(encoding="utf-8")), encoding="utf-8")
        if index == 1:
            m.ingest(reviewer, path, "same-person", datetime.now(timezone.utc).isoformat(), "independent_person", "Synthetic fixture.")
        else:
            with pytest.raises(ValueError, match="different people"):
                m.ingest(reviewer, path, "SAME-PERSON", datetime.now(timezone.utc).isoformat(), "independent_person", "Synthetic fixture.")


def test_completed_markdown_does_not_infer_independent_origin(offline):
    reviewer = "reviewer_01"
    path = offline / "returned.md"
    path.write_text(fill((m.DESTINATION / f"{reviewer}.md").read_text(encoding="utf-8")), encoding="utf-8")
    m.ingest(reviewer, path, "synthetic-assisted", datetime.now(timezone.utc).isoformat(), "assisted", "Synthetic fixture.")
    with pytest.raises(ValueError, match="Independent origin"):
        m.validate_semantic()
