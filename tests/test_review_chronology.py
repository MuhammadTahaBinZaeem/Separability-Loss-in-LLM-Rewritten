from datetime import datetime, timezone

import pytest

from research_v2.review_chronology import completion_window


ISSUED = "2026-10-02T19:02:16+00:00"
CURRENT = datetime(2026, 10, 6, tzinfo=timezone.utc)


def interval():
    return {"precision": "bounded_interval", "earliest_utc": ISSUED,
            "latest_utc": "2026-10-04T18:59:59.999999+00:00",
            "basis": "Synthetic final-packet recheck after issue and completion by Oct 4 Pakistan date; not an exact time."}


def test_exact_and_bounded_completion_are_distinct_and_truthfully_preserved():
    record = {"completion_window": interval()}
    lower, upper = completion_window(record, ISSUED, current_utc=CURRENT)
    assert lower < upper and "completed_utc" not in record
    t, u = completion_window({"completed_utc": "2026-10-03T15:00:00+05:00"}, ISSUED, current_utc=CURRENT)
    assert t == u


@pytest.mark.parametrize("change", [
    {"earliest_utc": "2026-09-25T00:00:00+00:00"},
    {"latest_utc": "2026-10-07T00:00:00+00:00"},
    {"latest_utc": "2026-10-01T00:00:00+00:00"},
    {"earliest_utc": "2026-10-03T00:00:00"},
    {"basis": ""}, {"precision": "exact"},
])
def test_window_cannot_backdate_reviews_or_claim_unsupported_precision(change):
    with pytest.raises(ValueError, match="completion"):
        completion_window({"completion_window": {**interval(), **change}}, ISSUED, current_utc=CURRENT)


def test_missing_or_conflicting_completion_evidence_is_rejected():
    for record in ({}, {"completed_utc": "2026-10-04T00:00:00+00:00", "completion_window": interval()}):
        with pytest.raises(ValueError, match="exactly one"):
            completion_window(record, ISSUED, current_utc=CURRENT)
