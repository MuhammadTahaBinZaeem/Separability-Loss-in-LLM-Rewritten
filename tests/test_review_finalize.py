import pytest

from research_v2.review_finalize import validate_statement, replay_ratings
from research_v2 import markdown_review as m
from research_v2.io import digest_text


def statement():
    return {"reported_distinct_people": 10,
            "named_roster_not_linked_by_guess_to_packet_numbers": [
                {"name": f"Synthetic participant {i}", "paid_as_reported": i < 3} for i in range(10)],
            "one_numbered_packet_per_person": True, "all_over_18_reported": True, "separate_work_reported": True,
            "verbal_consent_for_research_use_reported": True, "statement_usable_for_self_reported_review_registration": True,
            "independence_objectively_verified": False}


def test_ten_role_references_do_not_need_or_infer_roster_order():
    data = statement()
    validate_statement(data)
    data["named_roster_not_linked_by_guess_to_packet_numbers"].reverse()
    validate_statement(data)
    assert "exact_roster_name_to_packet_key" not in data


@pytest.mark.parametrize("field", ["one_numbered_packet_per_person", "all_over_18_reported", "separate_work_reported",
                                  "verbal_consent_for_research_use_reported", "statement_usable_for_self_reported_review_registration"])
def test_missing_confirmation_cannot_be_converted_into_review_completion(field):
    data = statement()
    data[field] = False
    with pytest.raises(ValueError, match="Missing reported"):
        validate_statement(data)


def test_duplicate_people_and_objective_certification_claim_are_rejected():
    data = statement()
    data["named_roster_not_linked_by_guess_to_packet_numbers"][1]["name"] = " SYNTHETIC PARTICIPANT 0 "
    with pytest.raises(ValueError, match="ten-person"):
        validate_statement(data)
    data = statement()
    data["independence_objectively_verified"] = True
    with pytest.raises(ValueError, match="objectively"):
        validate_statement(data)


def test_released_numeric_ratings_reconstruct_original_union_risk_without_private_notes():
    ratings = []
    for index in range(1, 9):
        block = str((index + 1) // 2)
        ratings.append({"reviewer": f"reviewer_{index:02d}", "slot": "A" if index % 2 else "B", "block": block,
                        "item_id": digest_text(str(index))[:20], "model_key": "synthetic", "request_id": block,
                        "passage_id": block, "condition": "test", "source_sha256": "source", "rewrite_sha256": "rewrite",
                        "added_facts": "0", "omitted_facts": "0", "order_changed": "0", "relationships_changed": "0",
                        "tone_drift": "0", "meaning_preservation": "5", "usable": "no" if index == 1 else "yes"})
    agreement, flags, disputes, identical = replay_ratings(ratings, 4)
    assert sum(f["risk_union"] for f in flags) == 1
    assert len(disputes) == 1 and disputes[0]["field"] == "usable"
    assert "1" not in identical
    assert all(r["kappa"] == "not_reported_pooled_across_different_people" for r in agreement if r["scope"] == "pooled_role_descriptive_only")
    assert all("notes" not in r for r in ratings)
    with pytest.raises(ValueError, match="Duplicate"):
        replay_ratings(ratings + ratings[:1], 4)
