import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from research_v2 import session_generation as session
from research_v2 import session_workers as workers
from research_v2.io import digest_text, read_jsonl, write_json, write_jsonl


@pytest.fixture
def dispatch(tmp_path, monkeypatch):
    base = tmp_path / "study"
    folder = base / "generation/astra_session"
    monkeypatch.setattr(workers, "BASE", base)
    monkeypatch.setattr(workers, "OUT", tmp_path)
    monkeypatch.setattr(workers, "AMENDMENT", base / "astra_delegation_amendment.json")
    monkeypatch.setattr(session, "OUT", tmp_path)
    monkeypatch.setattr(session, "FOLDER", folder)
    monkeypatch.setenv("CODEX_THREAD_ID", "test-only-session")
    write_json(tmp_path / "expansion/session_arm_provenance.json", {"synthetic_test": True})
    source = ("The wind was cold. " * 120).strip()
    reqs = [{"request_id": f"r{i}", "request_sha256": f"hash{i}", "source_sha256": digest_text(source),
             "passage_id": f"p{i}", "condition": "modernize", "model_key": "astra_session",
             "requested_model": "GPT-6 Astra via Codex, Extra High", "original_words": 480,
             "assignment_id": f"a{i}", "payload": {"synthetic_test": True}} for i in range(9)]
    monkeypatch.setattr(session, "requests", lambda: reqs)
    workers.authorize()
    return folder


def test_parallel_claims_are_disjoint_and_resumable(dispatch):
    with ThreadPoolExecutor(max_workers=3) as pool:
        issued = list(pool.map(workers.issue, ["astra_a", "astra_b", "astra_c"]))
    ids = [r["request_id"] for batch in issued for r in batch["requests"]]
    assert len(ids) == len(set(ids)) == 9
    assert workers.issue("astra_a") == issued[0]
    assert workers.issue("astra_d")["no_unreserved_assignments"]


def test_worker_ingest_preserves_actual_outputs_and_rejects_other_worker(dispatch, tmp_path):
    batch = workers.issue("astra_a")
    path = tmp_path / "outputs.jsonl"
    outputs = [{"request_id": r["request_id"], "rewritten_text": ("A cold wind blew. " * 120).strip()} for r in batch["requests"]]
    write_jsonl(path, outputs)
    with pytest.raises(ValueError, match="another worker"):
        workers.ingest("astra_b", batch["batch_id"], path)
    result = workers.ingest("astra_a", batch["batch_id"], path)
    assert result["accounted"] == result["valid_outputs"] == 3
    records = read_jsonl(dispatch / "session_outputs.jsonl")
    assert all(r["provider_response_id"] is None and r["token_usage"] is None for r in records)
    assert [json.loads(r["output_json_verbatim"]) for r in records] == outputs
    with pytest.raises(ValueError, match="already recorded"):
        workers.ingest("astra_a", batch["batch_id"], path)


def test_changed_worker_session_rejected(dispatch, monkeypatch):
    workers.issue("astra_a")
    monkeypatch.setenv("CODEX_THREAD_ID", "different-session")
    with pytest.raises(ValueError):
        workers.issue("astra_a")


def test_unused_reservation_can_be_reissued_without_erasing_history(dispatch):
    old = workers.issue("astra_a")
    workers.release_unused(old["batch_id"], "Synthetic worker stopped before producing any text")
    new = workers.issue("astra_b")
    assert new["batch_id"] != old["batch_id"]
    assert new["requests"] == old["requests"]
    assert (dispatch / f"batches/{old['batch_id']}.json").exists()
    with pytest.raises(ValueError, match="released"):
        workers.ingest("astra_a", old["batch_id"], dispatch / "nonexistent.jsonl")
