import pytest

from research_v2.expanded_study import corrected_rows, freeze_json
from research_v2.io import digest_text, read_json


def source(pid, start=0):
    text = ("A tale of wind and water. " * 80).strip()
    return {"passage_id": pid, "work_id": "work", "text": text, "text_sha256": digest_text(text),
            "source_start_char": start, "source_end_char": start + len(text), "word_count": 480}


def test_replacement_has_new_id_and_old_lineage():
    old = source("V2_test")
    text = ("A story of rain and snow. " * 80).strip()
    rows, lineage = corrected_rows([old], {"V2_test": {"source_start_char": 5000, "source_end_char": 5000 + len(text), "text": text, "reason": "borrowed"}})
    assert rows[0]["passage_id"] == "V3_test"
    assert old["passage_id"] == "V2_test"
    assert lineage[0]["v2_source_sha256"] == old["text_sha256"]
    assert lineage[0]["source_sha256"] != old["text_sha256"]


def test_unchanged_text_is_not_reidentified():
    row = source("V2_test")
    result, lineage = corrected_rows([row], {})
    assert result == [row]
    assert lineage[0]["disposition"] == "unchanged_exact_text"


def test_unknown_replacement_and_overlap_fail():
    with pytest.raises(ValueError, match="Unknown"):
        corrected_rows([source("V2_test")], {"bad": {}})
    with pytest.raises(ValueError, match="overlap"):
        corrected_rows([source("V2_test"), source("V2_second", 100)], {})


def test_frozen_artifact_is_idempotent_not_mutable(tmp_path):
    path = tmp_path / "manifest.json"
    freeze_json(path, {"a": 1})
    freeze_json(path, {"a": 1})
    with pytest.raises(ValueError, match="would change"):
        freeze_json(path, {"a": 2})
    assert read_json(path) == {"a": 1}
