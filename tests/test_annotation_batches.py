"""Synthetic staged reviews: a completed batch must not certify missing models."""
from datetime import datetime, timedelta, timezone

import pytest

from research_v2 import annotations
from research_v2.io import digest_text, file_hash, read_csv, read_json, write_csv, write_json


@pytest.fixture
def batch_study(tmp_path, monkeypatch):
    folder = tmp_path / "annotations"
    monkeypatch.setattr(annotations, "OUT", tmp_path)
    monkeypatch.setattr(annotations, "FOLDER", folder)
    monkeypatch.setattr(annotations, "verify_corpus", lambda: {"corpus_sha256": "synthetic-corpus"})
    def consolidated(model):
        assert model == "ready", "The unissued model must not be consolidated for this batch"
        return {"accounting_complete": True}
    monkeypatch.setattr(annotations, "consolidate", consolidated)
    write_json(tmp_path / "generation_plan.json", {"models": {"ready": {}, "pending": {}}, "conditions": ["paraphrase"]})
    originals, rewrites = [], []
    for i in range(6):
        text, rewrite = f"Synthetic original {i}.", f"Synthetic rewrite {i}."
        originals.append({"passage_id": f"p{i}", "author_id": "fixture", "work_id": "fixture-work", "text": text, "text_sha256": digest_text(text)})
        rewrites.append({"request_id": f"r{i}", "passage_id": f"p{i}", "condition": "paraphrase", "qc_status": "pass", "rewritten_text": rewrite, "rewrite_sha256": digest_text(rewrite)})
    write_csv(tmp_path / "corpus/originals.csv", originals)
    write_csv(tmp_path / "generation/ready/rewrites.csv", rewrites)
    write_json(tmp_path / "generation/ready/completion.json", {"accounting_complete": True})
    write_json(folder / "review_scope.json", {"batch_id": "synthetic-ready-batch", "models": ["ready"], "sampling_rule": "human_audit_v2"})
    return tmp_path, folder


def test_ready_model_is_issued_once_without_pending_provider(batch_study):
    _, folder = batch_study
    result = annotations.prepare()
    assert result["items_per_reviewer"] == 5
    assert result["models_in_scope"] == ["ready"] and result["pending_models"] == ["pending"]
    assert result["complete"] is False
    issued = read_json(folder / "issued_manifest.json")
    assert set(issued["generation_sha256"]) == {"ready"}
    assert issued["review_scope_sha256"] == file_hash(folder / "review_scope.json")
    a, b = [read_csv(folder / f"forms/reviewer_{reviewer}.csv") for reviewer in ("A", "B")]
    assert {r["item_id"] for r in a}.isdisjoint({r["item_id"] for r in b})
    assert {(r["original_text"], r["rewritten_text"]) for r in a} == {(r["original_text"], r["rewritten_text"]) for r in b}
    assert all(all(r[f] == "" for f in annotations.RATINGS) for r in a + b)
    before = (folder / "issued_manifest.json").read_bytes()
    annotations.prepare()
    assert before == (folder / "issued_manifest.json").read_bytes()


def test_default_remains_all_models_and_incomplete_scope_is_blocked(batch_study, monkeypatch):
    _, folder = batch_study
    monkeypatch.setattr(annotations, "consolidate", lambda _: {"accounting_complete": False})
    assert annotations.prepare()["missing_models"] == ["ready"]
    assert not (folder / "issued_manifest.json").exists()
    (folder / "review_scope.json").unlink()
    result = annotations.prepare()
    assert set(result["missing_models"]) == {"ready", "pending"}


def test_issued_batch_cannot_expand_or_lose_scope_record(batch_study):
    _, folder = batch_study
    annotations.prepare()
    before = (folder / "forms/reviewer_A.csv").read_bytes()
    scope = read_json(folder / "review_scope.json")
    write_json(folder / "review_scope.json", {**scope, "models": ["ready", "pending"]})
    with pytest.raises(ValueError, match="scope changed"):
        annotations.prepare()
    assert before == (folder / "forms/reviewer_A.csv").read_bytes()
    (folder / "review_scope.json").unlink()
    with pytest.raises(ValueError, match="scope is missing"):
        annotations.prepare()


def test_two_valid_batch_returns_do_not_complete_full_study(batch_study):
    _, folder = batch_study
    annotations.prepare()
    issued = read_json(folder / "issued_manifest.json")
    issued["issued_utc"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    write_json(folder / "issued_manifest.json", issued)
    for reviewer in ("A", "B"):
        rows = read_csv(folder / f"forms/reviewer_{reviewer}.csv")
        for i, row in enumerate(rows):
            row.update({field: "0" for field in annotations.RATINGS})
            row.update(meaning_preservation="5", usable="yes", notes="Synthetic test response only.")
            row["tone_drift"] = "1" if reviewer == "B" and i == 0 else "0"
        path = folder / f"synthetic_{reviewer}.csv"
        write_csv(path, rows, annotations.FORM_FIELDS)
        annotations.ingest(reviewer, path, f"synthetic-person-{reviewer}", datetime.now(timezone.utc).isoformat(), True)
    result = annotations.validate()
    assert result["batch_complete"] is True and result["complete"] is False
    assert result["models_in_scope"] == ["ready"] and result["pending_models"] == ["pending"]
    assert result["stage"] == "review_batch_complete_additional_models_pending"
