from research_v2.analysis import CLASSIFIERS
from research_v2.corpus import AUTHORS
import pytest
from research_v2.expanded_primary import check_output_hash, infer, outcome_coverage


def test_primary_inference_requires_every_planned_work():
    originals = [{"passage_id": f"{a}_{w}", "author_id": a, "work_id": str(w)} for a in AUTHORS for w in range(3)]
    predictions = []
    for name in CLASSIFIERS:
        for condition in ("original", "paraphrase"):
            for source in originals:
                if condition == "paraphrase" and source["work_id"] == "2":
                    continue
                predictions.append({**source, "classifier": name, "feature_set": "full", "condition": condition,
                                    "predicted_author": source["author_id"], "qc_status": "pass"})
    comparisons, sensitivity = infer(predictions, originals, "synthetic", ["paraphrase"], 10, 10)
    assert len(comparisons) == 3
    assert all(r["status"] == "not_estimable_missing_works" for r in comparisons)
    assert all("p_work_swap_two_sided" not in r for r in comparisons)
    assert all(r["paired_rows"] == 12 for r in sensitivity)


def test_primary_coverage_retains_zero_output_cells():
    originals = [{"passage_id": "p", "author_id": "a", "work_id": "w"}]
    rows = [{"passage_id": "p", "condition": "paraphrase", "qc_status": "fail"}]
    result = outcome_coverage(originals, rows, ["paraphrase", "simplify"])
    assert result[0]["failed"] == 1 and result[0]["expected"] == 1
    assert result[1]["accounted"] == 0 and result[1]["expected"] == 1


def test_http_filter_is_absent_text_not_an_empty_model_rewrite():
    row = {"outcome_type": "http_content_filter", "qc_status": "fail", "rewritten_text": "", "rewrite_sha256": ""}
    check_output_hash(row)
    with pytest.raises(ValueError, match="fabricated"):
        check_output_hash({**row, "rewritten_text": "invented"})
    with pytest.raises(ValueError, match="hash differs"):
        check_output_hash({**row, "outcome_type": "native_response"})
