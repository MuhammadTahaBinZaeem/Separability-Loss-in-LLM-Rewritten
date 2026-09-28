"""No-network checks of provider parsing, secrets and independent-review gates."""
import json

import pytest

from research_v2.annotations import check_ratings,ingest
from research_v2.credentials import read_env
from research_v2.generation import parse_response
from research_v2.io import digest_text,write_text
from research_v2.providers import connection,make_payload,response_view


def request(api):
    return {"api":api,"request_id":"opaque","passage_id":"passage","condition":"modernize","model_key":"test",
            "source_sha256":digest_text("old prose"),"request_sha256":"hash","original_words":2,
            "requested_model":"frozen-model","accepted_returned_models":["frozen-model"],"payload":{}}


@pytest.mark.parametrize("api",["gemini_native","azure_responses"])
def test_native_provider_formats_preserve_provenance_and_ignore_reasoning(api):
    text=json.dumps({"request_id":"opaque","rewritten_text":"New prose"})
    if api=="gemini_native":
        native={"responseId":"native-id","modelVersion":"frozen-model","candidates":[{"finishReason":"STOP","content":{"parts":[{"thought":True,"text":"reasoning not prose"},{"text":text}]}}]}
    else:
        native={"id":"native-id","model":"frozen-model","status":"completed","output":[{"type":"reasoning","summary":[]},{"type":"message","content":[{"type":"output_text","text":text}]}]}
    row=parse_response(request(api),{"response":native,"received_utc":"2026-09-21T00:00:00Z"})
    assert row["qc_status"]=="pass" and row["response_id"]=="native-id"
    assert row["rewritten_text"]=="New prose" and row["outcome_type"]=="native_response"


def test_in_response_content_filter_is_a_retained_failure():
    native={"id":"real-native-id","model":"frozen-model","status":"incomplete","incomplete_details":{"reason":"content_filter"},"output":[]}
    row=parse_response(request("azure_responses"),{"response":native,"received_utc":"2026-09-21T00:00:00Z"})
    assert row["qc_status"]=="fail" and row["response_id"]=="real-native-id"
    assert "incomplete_generation" in row["qc_flags"]


def test_azure_payload_does_not_store_or_share_conversation():
    config={"api":"azure_responses","model":"gpt-5.4-nano","reasoning_effort":"none"}
    payload=make_payload(config,{"temperature":.2,"top_p":1,"max_completion_tokens":4096},"system","one passage")
    assert payload["store"] is False and "previous_response_id" not in payload and "conversation" not in payload
    assert payload["text"]["format"]["strict"] is True


@pytest.mark.parametrize("endpoint",["http://test.openai.azure.com","https://test.openai.azure.com.attacker.test","https://user:pass@test.openai.azure.com","https://attacker.test"])
def test_credentials_never_sent_to_unapproved_azure_origin(endpoint):
    with pytest.raises(ValueError):
        connection({"api":"azure_responses","key_env":"key","endpoint_env":"url"},{"key":"private-value","url":endpoint})


def test_dotenv_is_data_not_executable_and_errors_do_not_leak_values(tmp_path):
    path=tmp_path / "keys.env"
    write_text(path,'KEY="$(do-not-execute)"\n')
    assert read_env(path)=={"KEY":"$(do-not-execute)"}
    write_text(path,"KEY=secret-one\nKEY=secret-two\n")
    with pytest.raises(ValueError) as caught:
        read_env(path)
    assert "secret" not in str(caught.value)


def test_human_attestation_cannot_be_assumed(tmp_path):
    with pytest.raises(ValueError,match="human must explicitly attest"):
        ingest("A",tmp_path / "not-a-real-review.csv","reviewer","2026-09-20T00:00:00Z",False)


def test_flagged_semantic_ratings_require_specific_notes():
    row={"item_id":"opaque","added_facts":"0","omitted_facts":"1","order_changed":"0","relationships_changed":"0",
         "tone_drift":"0","meaning_preservation":"3","usable":"no","notes":""}
    assert check_ratings([row])
    row["notes"]="The rewrite omits the fact that the letter arrived before the visitor."
    assert check_ratings([row])==[]


def test_corpus_freeze_cannot_be_rewritten_after_protocol_change(tmp_path,monkeypatch):
    import research_v2.corpus as module
    from research_v2.io import file_hash,write_json
    write_text(tmp_path / "PROTOCOL.md","frozen protocol")
    write_text(tmp_path / "work_specs.json","[]")
    write_json(tmp_path / "corpus/freeze.json",{"protocol_sha256_at_freeze":file_hash(tmp_path / "PROTOCOL.md"),"work_specs_sha256":file_hash(tmp_path / "work_specs.json")})
    write_text(tmp_path / "PROTOCOL.md","quietly changed protocol")
    monkeypatch.setattr(module,"OUT",tmp_path)
    with pytest.raises(ValueError,match="Frozen protocol"):
        module.build()


def test_identical_reviews_need_a_separate_dated_human_provenance_check(tmp_path):
    from datetime import datetime,timedelta,timezone
    from research_v2.annotations import independence_check_valid
    from research_v2.io import write_json,file_hash
    now=datetime.now(timezone.utc)
    registry={"A":{"completed_utc":(now-timedelta(days=2)).isoformat()},"B":{"completed_utc":(now-timedelta(days=1)).isoformat()}}
    path=tmp_path / "check.json"; registry_path=tmp_path / "registry.json"
    write_json(registry_path,registry)
    assert not independence_check_valid(path,registry_path,registry)
    # Synthetic unit-test attestations, never copied into study provenance.
    check={"checked_by_human":True,"checker_id":"test-fixture-only","checked_utc":now.isoformat(),
           "registry_sha256":file_hash(registry_path),"outcome":"independence_confirmed","method":"synthetic test","notes":"synthetic test"}
    write_json(path,check)
    assert independence_check_valid(path,registry_path,registry)
    write_json(path,{**check,"checked_by_human":"false"})
    assert not independence_check_valid(path,registry_path,registry)
    write_json(path,{**check,"checked_utc":(now-timedelta(days=3)).isoformat()})
    assert not independence_check_valid(path,registry_path,registry)
