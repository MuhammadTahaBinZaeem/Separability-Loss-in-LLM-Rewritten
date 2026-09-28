"""Regression tests target leakage, false provenance, and inferential mistakes."""
import json
from collections import Counter

import numpy as np
import pytest

from research_v2.analysis import classifier, split_rows
from research_v2.corpus import AUTHORS, bounds, candidates, clean_text, editorial_spans, source_text, words
from research_v2.features import FoldFeatures
from research_v2.generation import parse_response, parse_terminal, terminal_from_event
from research_v2.inference import confusion, f1_from_confusion, holm, paired_uncertainty
from research_v2.io import OUT, digest_text, file_hash, read_csv, read_json


def test_vocabulary_and_scaler_never_see_test_text():
    training=["A quiet walk by the river. "*10,"The river was quiet and the road was long. "*12]
    fitted=FoldFeatures().fit(training,["train-1","train-2"])
    before=fitted.evidence()
    fitted.transform(["zzzzzzz !!! unheard test-only features "*100])
    assert fitted.evidence()==before
    assert "zzz" not in fitted.vocabulary_
    np.testing.assert_allclose(fitted.transform(training).mean(axis=0),0,atol=1e-10)


def test_real_shrinkage_lda():
    model=classifier("lda_ledoit_wolf_shrinkage")
    assert model.solver=="lsqr" and model.shrinkage=="auto"
    np.testing.assert_allclose(model.priors, np.full(6,1/6))


def test_frozen_corpus_exact_source_and_group_isolation():
    originals=read_csv(OUT/"corpus/originals.csv")
    freeze=read_json(OUT/"corpus/freeze.json")
    assert file_hash(OUT/"corpus/originals.csv")==freeze["originals_file_sha256"]
    assert len(originals)==360
    assert Counter(r["author_id"] for r in originals)==Counter({a:60 for a in AUTHORS})
    assert set(Counter((r["author_id"],r["work_id"]) for r in originals).values())=={20}
    sources={int(r["gutenberg_id"]):source_text(int(r["gutenberg_id"])) for r in originals}
    intervals={}
    for row in originals:
        a,b=int(row["source_start_char"]),int(row["source_end_char"])
        assert row["text"]==clean_text(sources[int(row["gutenberg_id"])][a:b])
        assert digest_text(row["text"])==row["text_sha256"]
        assert 450<=words(row["text"])<=650
        for earlier_a,earlier_b in intervals.setdefault(row["gutenberg_id"],[]):
            assert b<=earlier_a or a>=earlier_b
        intervals[row["gutenberg_id"]].append((a,b))
    tested=[]
    for fold in range(3):
        train,test=split_rows(originals,fold)
        assert len(train)==240 and len(test)==120
        assert not ({r["work_id"] for r in train}&{r["work_id"] for r in test})
        tested.extend(r["passage_id"] for r in test)
    assert len(set(tested))==360


def test_source_anchors_fail_closed():
    spec={"start":"Story begins","end":"Notes"}
    with pytest.raises(ValueError):
        bounds(spec,"Story begins. Story begins. Notes")
    assert bounds(spec,"Preface. Story begins. Notes")==(9,23)


def test_illustration_captions_across_paragraphs_are_wholly_excluded():
    raw='Prose. [Illustration:\n\nCaption by illustrator\n\n[_Copyright 1894._]] Real prose.'
    spans=editorial_spans(raw)
    assert len(spans)==1
    a,b=spans[0]
    assert raw[a:b]=='[Illustration:\n\nCaption by illustrator\n\n[_Copyright 1894._]]'
    assert clean_text('A note[3] and a letter[A].')=='A note and a letter.'


def test_newline_hash_is_portable():
    assert digest_text("one\r\ntwo\r\n")==digest_text("one\ntwo\n")


def test_qc_rejects_wrong_ids_truncation_and_model_switches():
    request={"request_id":"abc","passage_id":"p","condition":"simplify","model_key":"m",
             "source_sha256":digest_text("Original"),"request_sha256":"hash","original_words":2,
             "payload":{"model":"expected-model"}}
    record={"received_utc":"2026-09-19T00:00:00+00:00","response":{"id":"provider-id","model":"other-model",
            "choices":[{"finish_reason":"length","message":{"content":json.dumps({"request_id":"wrong","rewritten_text":"New prose"})}}]}}
    row=parse_response(request,record)
    assert row["qc_status"]=="fail"
    for reason in ["request_id_mismatch","incomplete_generation","returned_model_mismatch"]:
        assert reason in row["qc_flags"]


def paired_rows(identical=False):
    return [{"passage_id":f"{author}-{w}-{p}","author_id":author,"work_id":f"{author}-{w}",
             "original_prediction":author,"rewrite_prediction":author if identical else AUTHORS[(i+1)%6]}
            for i,author in enumerate(AUTHORS) for w in range(3) for p in range(2)]


def test_null_comparison_has_zero_loss_and_p_one():
    result=paired_uncertainty(paired_rows(True),bootstraps=40,permutations=100,seed=11)
    assert result["macro_f1_loss"]==result["loss_ci_low"]==result["loss_ci_high"]==0
    assert result["p_work_swap_two_sided"]==1
    assert result["work_blocks"]==18


def test_permutation_p_is_never_zero_and_ci_keeps_pairs():
    result=paired_uncertainty(paired_rows(),bootstraps=40,permutations=100,seed=11)
    assert result["macro_f1_loss"]==1
    assert result["loss_ci_low"]==result["loss_ci_high"]==1
    assert 0<result["p_work_swap_two_sided"]<=1
    assert result["work_blocks"]==18 and result["paired_passages"]==36


def test_missing_author_not_silently_dropped():
    with pytest.raises(ValueError):
        paired_uncertainty([r for r in paired_rows() if r["author_id"]!="wilde"],10,10)


def test_holm_correction_uses_full_predeclared_family():
    assert holm([.01,.02,.5])==pytest.approx([.03,.04,.5])
    assert holm([.01],family_size=18)==pytest.approx([.18])


def test_macro_f1_keeps_all_six_labels():
    matrix=confusion(np.array([0]),np.array([0]))
    assert f1_from_confusion(matrix)==pytest.approx(1/6)


def test_http_refusal_is_not_a_fabricated_model_completion():
    request={"request_id":"blocked","passage_id":"p","condition":"simplify","model_key":"azure",
             "requested_model":"gpt-5.4-nano","source_sha256":"source","request_sha256":"request","original_words":500}
    event={"request_id":"blocked","http_status":400,"error_code":"content_filter","timestamp":"2026-09-20T09:14:23+00:00"}
    record=terminal_from_event(request,event)
    row=parse_terminal(request,record)
    assert row["qc_status"]=="fail" and row["outcome_type"]=="http_content_filter"
    assert row["response_id"]==row["returned_model"]==row["rewritten_text"]==row["rewrite_sha256"]==""
    assert "response" not in record and "response_body" not in record
    with pytest.raises(ValueError):
        terminal_from_event(request,{**event,"http_status":429})
    with pytest.raises(ValueError):
        terminal_from_event(request,{**event,"request_id":"other"})


def test_terminal_accounting_rejects_duplicates_and_unsupported_evidence(tmp_path,monkeypatch):
    import research_v2.generation as module
    from research_v2.io import write_jsonl,write_json
    folder=tmp_path / "generation/test"
    request={"request_id":"blocked","passage_id":"p","condition":"simplify","model_key":"azure",
             "requested_model":"gpt-5.4-nano","source_sha256":"source","request_sha256":"request","original_words":500}
    event={"request_id":"blocked","http_status":400,"error_code":"content_filter","timestamp":"2026-09-20T09:14:23+00:00"}
    record=terminal_from_event(request,event)
    write_jsonl(folder / "requests.jsonl",[request])
    write_json(folder / "request_manifest.json",{"requests_sha256":file_hash(folder / "requests.jsonl")})
    write_jsonl(folder / "transport_events.jsonl",[event])
    write_jsonl(folder / "terminal_outcomes.jsonl",[record])
    monkeypatch.setattr(module,"OUT",tmp_path)
    monkeypatch.setattr(module,"verify_corpus",lambda: {})
    result=module.consolidate("test")
    assert result["accounting_complete"] and not result["complete"] and not result["responses_complete"]
    assert result["received"]==0 and result["terminal_http_failures"]==result["fail"]==1
    write_jsonl(folder / "terminal_outcomes.jsonl",[record,record])
    with pytest.raises(ValueError,match="Duplicate"):
        module.consolidate("test")
    write_jsonl(folder / "terminal_outcomes.jsonl",[{**record,"received_utc":"invented"}])
    with pytest.raises(ValueError,match="supported"):
        module.consolidate("test")
