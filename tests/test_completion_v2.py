"""Final-stage evidence must remain separate from human attestations and quotas."""
from datetime import datetime,timezone,timedelta

import pytest

from research_v2.io import write_jsonl


def test_quota_report_excludes_account_and_message():
    from research_v2.parallel_generation import quota_summary
    result=quota_summary({"message":"private key/account description","details":[
        {"@type":"type.googleapis.com/google.rpc.QuotaFailure","violations":[
            {"quotaId":"GenerateRequestsPerDayPerProjectPerModel-FreeTier","quotaValue":"500",
             "quotaDimensions":{"project":"private-project"},"description":"private"}]}]})
    assert result==[{"quota_id":"GenerateRequestsPerDayPerProjectPerModel-FreeTier","quota_value":"500"}]
    assert "private" not in str(result)


def test_unstructured_quota_metadata_is_not_copied():
    from research_v2.parallel_generation import quota_summary
    assert quota_summary({"details":[{"@type":"google.rpc.QuotaFailure","violations":[
        {"quotaId":"private URL https://example.invalid/key","quotaValue":"500"}]}]})==[]


def test_missing_human_source_review_is_not_complete(tmp_path,monkeypatch):
    import research_v2.source_review as module
    monkeypatch.setattr(module,"OUT",tmp_path)
    assert module.validate()["passed"] is False


def test_source_return_requires_real_human_attestation(tmp_path,monkeypatch):
    import research_v2.source_review as module
    monkeypatch.setattr(module,"OUT",tmp_path)
    with pytest.raises(ValueError,match="human"):
        module.check_return(tmp_path / "none",{},"reviewer","2026-01-01T00:00:00+00:00",False)


def test_source_return_cannot_change_source_text(tmp_path,monkeypatch):
    import research_v2.source_review as module
    monkeypatch.setattr(module,"OUT",tmp_path)
    now=datetime.now(timezone.utc)
    issued={"issued_utc":(now-timedelta(minutes=5)).isoformat()}
    row={"passage_id":"one","text":"preserved source","verdict":"","notes":""}
    write_jsonl(tmp_path / "source_review/blank_review.jsonl",[row])
    path=tmp_path / "return.jsonl"
    write_jsonl(path,[{**row,"text":"altered source","verdict":"pass","notes":"reviewed"}])
    with pytest.raises(ValueError,match="text changed"):
        module.check_return(path,issued,"real-reviewer",(now-timedelta(minutes=1)).isoformat(),True)


def test_future_source_review_date_rejected(tmp_path,monkeypatch):
    import research_v2.source_review as module
    monkeypatch.setattr(module,"OUT",tmp_path)
    now=datetime.now(timezone.utc)
    with pytest.raises(ValueError,match="date"):
        module.check_return(tmp_path / "none",{"issued_utc":now.isoformat()},"reviewer",(now+timedelta(days=1)).isoformat(),True)
