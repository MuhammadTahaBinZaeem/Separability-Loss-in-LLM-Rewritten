import pytest

from research_v2.corpus import AUTHORS
from research_v2.expanded_semantic import summarize


def test_semantic_sensitivity_never_treats_unaudited_as_clean():
    predictions, flags = [], []
    for index, author in enumerate(AUTHORS):
        for suffix in ("audited", "unaudited"):
            for condition in ("original", "paraphrase"):
                predictions.append({"model_key": "test", "classifier": "test", "passage_id": author+suffix,
                                    "author_id": author, "condition": condition, "feature_set": "full", "predicted_author": author})
        flags.append({"model_key": "test", "passage_id": author+"audited", "condition": "paraphrase", "risk_union": int(index == 0)})
    result = summarize(predictions, flags)
    assert result[0]["audited_pairs"] == result[0]["paired_rows"] == 6
    assert result[1]["paired_rows"] == 5
    assert result[1]["status"] == "not_estimable_missing_authors"
    assert result[1]["macro_f1_loss"] == ""
    with pytest.raises(ValueError, match="Duplicate"):
        summarize(predictions, flags + flags[:1])
