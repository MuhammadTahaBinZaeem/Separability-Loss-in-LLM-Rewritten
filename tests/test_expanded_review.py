from research_v2.expanded_review import agreement_rows


def ratings():
    return {"added_facts": "0", "omitted_facts": "0", "order_changed": "0", "relationships_changed": "0",
            "tone_drift": "0", "meaning_preservation": "5", "usable": "yes", "notes": ""}


def test_identical_constant_ratings_do_not_prove_independence_or_kappa_one():
    key = {k: "synthetic" for k in ("model_key", "request_id", "passage_id", "condition", "source_sha256", "rewrite_sha256")}
    joined = {("synthetic", "request"): {"A": (key, ratings()), "B": (key, ratings())}}
    agreements, flags, identical = agreement_rows(joined)
    assert identical
    assert all(r["raw_agreement"] == 1 and r["kappa"] == "undefined_constant_ratings" for r in agreements)
    assert flags[0]["risk_union"] == 0
    joined["synthetic", "request"]["B"][1]["added_facts"] = "1"
    agreements, flags, identical = agreement_rows(joined)
    assert not identical and flags[0]["risk_union"] == 1
    assert next(r for r in agreements if r["field"] == "added_facts")["raw_agreement"] == 0
