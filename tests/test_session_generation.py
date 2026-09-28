import json

from research_v2.generation import FIELDS
from research_v2.io import digest_text
from research_v2.session_generation import score


def test_session_score_does_not_invent_native_receipts():
    source = ("The wind was cold. " * 120).strip()
    text = ("A cold wind blew. " * 120).strip()
    request = {"request_id": "r", "passage_id": "p", "condition": "modernize", "model_key": "astra_session",
               "requested_model": "GPT-6 Astra via Codex, Extra High", "source_sha256": digest_text(source),
               "request_sha256": "request-hash", "original_words": 480, "assignment_id": "assignment"}
    record = {"recorded_utc": "2026-09-26T00:00:00+00:00", "output_json_verbatim": json.dumps({"request_id": "r", "rewritten_text": text})}
    row = score(request, record)
    assert row["qc_status"] == "pass"
    assert row["response_id"] == row["returned_model"] == ""
    assert row["outcome_type"] == "codex_session_output"
    assert set(FIELDS) <= set(row)
    record["output_json_verbatim"] = json.dumps({"request_id": "r", "rewritten_text": source})
    assert score(request, record)["qc_status"] == "fail"
    record["output_json_verbatim"] = json.dumps({"request_id": "wrong", "rewritten_text": text})
    assert "request_id_mismatch" in score(request, record)["qc_flags"]
