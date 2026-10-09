"""The exploratory extension must not silently introduce leakage or new samples."""
import json

import numpy as np
import pytest

from research_v2.corpus import AUTHORS, words
from research_v2.io import digest_text
from research_v2.transfer_extension import (DOMAINS, align_records, bootstrap_weights, crop,
                                           geometry, matrix_statistics, panel_records,
                                           save_evidence, tfidf_pipeline)


def toy_rows():
    return [{"passage_id": f"{a}-{w}-{p}", "author_id": a, "work_id": f"{a}-{w}",
             "outer_fold": str(w), "minimum_words": 20,
             "texts": {d: "The day was quiet; a very long road, and another house. " * 3 for d in DOMAINS}}
            for a in AUTHORS for w in range(3) for p in range(2)]


@pytest.mark.parametrize("location", ["prefix", "middle", "suffix"])
def test_crop_is_exact_contiguous_and_equal_length(location):
    text = '“One,” said Anne. Two-things weren’t obvious!\n\nThree, four; five six seven eight.'
    result, a, b = crop(text, 5, location)
    assert result == text[a:b]
    assert words(result) == 5
    assert 0 <= a < b <= len(text)
    if location == "prefix":
        assert a == 0
    if location == "suffix":
        assert b == len(text)
    with pytest.raises(ValueError):
        crop(text, 100, location)


def test_full_text_is_unchanged_and_bad_locations_rejected():
    text = 'A quiet day.\n\n"And then?"'
    assert crop(text, 0, "full") == (text, 0, len(text))
    with pytest.raises(ValueError):
        crop(text, 2, "choose_best")


def test_alignment_excludes_a_passage_in_every_domain_and_preserves_warning():
    original = {"passage_id": "p", "author_id": "poe", "work_id": "w", "outer_fold": "0",
                "text": "Original words.", "text_sha256": digest_text("Original words.")}
    rewrites = [{"passage_id": "p", "condition": d, "source_sha256": original["text_sha256"],
                 "rewritten_text": "New words.", "rewrite_sha256": digest_text("New words."),
                 "qc_status": "warning"} for d in DOMAINS[1:]]
    assert len(align_records([original], rewrites)[0]) == 1
    rewrites[0]["qc_status"] = "fail"
    selected, eligibility = align_records([original], rewrites)
    assert not selected and eligibility[0]["excluded_conditions"] == "paraphrase"
    assert eligibility[0]["valid_all_domains"] == 0
    with pytest.raises(ValueError, match="Duplicate"):
        align_records([original], rewrites + [rewrites[0]])
    with pytest.raises(ValueError, match="missing"):
        align_records([original], rewrites[:2])
    rewrites[0]["source_sha256"] = "altered"
    with pytest.raises(ValueError, match="different source"):
        align_records([original], rewrites)


def test_panel_keeps_work_fold_and_all_versions_paired():
    rows = toy_rows()
    all_works = {(r["author_id"], r["work_id"]) for r in rows}
    selected, views = panel_records(rows, ("test", 10, 10, "middle"), all_works)
    assert len(selected) == len(rows)
    assert len(views) == 4 * len(rows)
    assert {v["word_count"] for v in views} == {10}
    with pytest.raises(ValueError, match="whole author/work"):
        panel_records(rows[:-2], ("test", 10, 10, "middle"), all_works)


def test_tfidf_does_not_fit_on_test_domain():
    texts = ["a sunny day and a quiet house", "a long road and another house"]
    vectorizer, matrix, evidence = tfidf_pipeline(texts, ["train1", "train2"])
    before = json.dumps(evidence, sort_keys=True)
    before_idf = vectorizer.idf_.copy()
    vectorizer.transform(["zzzzzz unseen content " * 30])
    assert "zzz" not in vectorizer.vocabulary_
    assert matrix.shape[0] == 2
    assert json.dumps(evidence, sort_keys=True) == before
    np.testing.assert_array_equal(vectorizer.idf_, before_idf)
    assert evidence["training_text_hashes"] == [digest_text(t) for t in texts]


def test_missing_work_panel_is_visible_not_relaxed():
    from research_v2.transfer_extension import panel_coverage
    rows = toy_rows()
    works = {(r["author_id"], r["work_id"]) for r in rows}
    full = panel_coverage(rows, ("control", 10, 10, "middle"), works)
    assert full["status"] == "estimable" and not full["missing_works"]
    unavailable = panel_coverage(rows[:-2], ("control", 10, 10, "middle"), works)
    assert unavailable["status"] == "not_estimable"
    assert unavailable["missing_works"] == [[rows[-1]["author_id"], rows[-1]["work_id"]]]
    assert sum(r["passages"] == 0 for r in unavailable["work_counts"]) == 1
    empty = panel_coverage(rows, ("control", 300, 300, "middle"), works)
    assert empty["eligible_passages"] == 0 and len(empty["missing_works"]) == 18
    assert empty["minimum_words"] == 300


def test_bootstrap_is_paired_fixed_author_and_deterministic():
    rows = toy_rows()
    weights = bootstrap_weights(rows, 20, seed=10)
    np.testing.assert_array_equal(weights, bootstrap_weights(rows, 20, seed=10))
    for author in AUTHORS:
        mask = [r["author_id"] == author for r in rows]
        assert np.all(weights[:, mask].sum(axis=1) == 6)
    with pytest.raises(ValueError):
        bootstrap_weights(rows[:-2], 10)


def test_transfer_loss_decomposes_and_identity_comparisons_are_zero():
    rows = toy_rows()
    actual = [r["author_id"] for r in rows]
    wrong = [AUTHORS[(AUTHORS.index(a) + 1) % 6] for a in actual]
    predictions = {(a, b): actual if a == b else wrong for a in DOMAINS for b in DOMAINS}
    metrics, contrasts = matrix_statistics(rows, predictions, bootstrap_weights(rows, 20))
    assert len(metrics) == 16 and len(contrasts) == 9
    for d in DOMAINS[1:]:
        indexed = {r["contrast"]: r for r in contrasts if r["rewrite_domain"] == d}
        assert indexed["transfer_loss"]["difference_macro_f1"] == 1
        assert indexed["adaptation_gain"]["difference_macro_f1"] == 1
        assert indexed["within_domain_gap"]["difference_macro_f1"] == 0
        assert indexed["within_domain_gap"]["ci_low"] == indexed["within_domain_gap"]["ci_high"] == 0
    identity = {(a, b): actual for a in DOMAINS for b in DOMAINS}
    _, null = matrix_statistics(rows, identity, bootstrap_weights(rows, 10))
    assert all(r["difference_macro_f1"] == r["ci_low"] == r["ci_high"] == 0 for r in null)


def test_geometry_separates_common_translation_from_relative_author_change():
    rows = [r for r in toy_rows() if r["outer_fold"] == "0"]
    matrix = np.array([[AUTHORS.index(r["author_id"]) + .1 * (i % 2), i % 2]
                       for i, r in enumerate(rows)], dtype=float)
    shifted = matrix + 3
    result, changes = geometry(rows, {"original": matrix, "paraphrase": shifted,
                                     "modernize": matrix, "simplify": matrix}, ["fw_the", "fw_and"])
    # Legacy fixed-feature names are fw_<word>; this test also exercises family routing.
    chosen = next(r for r in result if r["domain"] == "paraphrase" and r["feature_family"] == "all_features")
    assert chosen["common_shift_rms"] == pytest.approx(3)
    assert chosen["differential_shift_rms"] == pytest.approx(0, abs=1e-12)
    assert chosen["between_ratio_to_original"] == pytest.approx(1)
    assert all(r["delta_z"] == pytest.approx(3) for r in changes if r["domain"] == "paraphrase")


def test_transform_evidence_is_byte_reproducible(tmp_path):
    first, second = tmp_path / "a.gz", tmp_path / "b.gz"
    evidence = {"training_ids": ["one"], "values": [1, 2.5]}
    save_evidence(first, evidence)
    save_evidence(second, evidence)
    assert first.read_bytes() == second.read_bytes()


def test_affine_mapping_is_fit_from_training_centroids_and_not_forced_to_contract():
    from research_v2.shift_contraction import fit_mapping, dispersion_identity
    x = np.arange(36, dtype=float).reshape(12, 3)
    shift = np.array([1, -2, 3])
    for factor in (.6, 1, 1.8):
        alpha, intercept = fit_mapping(x, factor * x + shift, "scalar_affine")
        assert alpha == pytest.approx(factor)
        np.testing.assert_allclose(intercept, shift, atol=1e-12)
        unseen = x[:6] + 2
        identity = dispersion_identity(unseen, factor * unseen + shift, alpha, intercept)
        assert identity["closure_error"] == pytest.approx(0, abs=1e-12)
        assert identity["residual_component"] == pytest.approx(0, abs=1e-12)
        assert identity["between_rewrite"] == pytest.approx(factor ** 2 * identity["between_original"])
    before = fit_mapping(x, x + shift, "translation")
    np.testing.assert_allclose(before[1], shift)
    with pytest.raises(ValueError):
        fit_mapping(np.ones((12, 3)), x, "scalar_affine")


def test_work_bootstrap_retains_fixed_author_labels():
    from research_v2.shift_contraction import work_bootstrap
    rows = [{"author_id": a, "work_id": f"{a}-{w}"} for a in AUTHORS for w in range(3)]
    indices = work_bootstrap(rows, 10)
    assert indices.shape == (10, 18)
    for sample in indices:
        assert [rows[int(i)]["author_id"] for i in sample] == [a for a in AUTHORS for _ in range(3)]


def test_scientific_finisher_times_out_without_touching_a_writer(tmp_path, monkeypatch):
    import research_v2.science_finish as module
    from research_v2.io import read_json, write_json, write_text
    write_json(tmp_path / "generation_plan.json", {"models": {"test": {}}})
    lock = tmp_path / "generation/test/RUNNING.lock"
    write_text(lock, "123")
    monkeypatch.setattr(module, "OUT", tmp_path)
    assert module.finish(wait_minutes=0) == 2
    assert lock.read_text() == "123"
    report = read_json(tmp_path / "verification/research_watch_status.json")
    assert report["stage"] == "bounded_wait_expired"
    assert report["manuscript_writing_paused"] and not report["submission_ready"]


def test_identity_rewrite_control_cannot_create_an_attribution_gap():
    from research_v2.analysis import classifier, split_rows
    from research_v2.features import FoldFeatures
    from sklearn.svm import LinearSVC
    rows = toy_rows()
    for i, row in enumerate(rows):
        # Artificial unit-test material only; never enters a research corpus.
        distinctive = ["apple", "garden", "window", "orange", "quiet", "valley"][AUTHORS.index(row["author_id"])]
        row["text"] = (f"The {distinctive} was here and the road was long. " * (8 + i % 3))
    train, test = split_rows(rows, 0)
    texts = [r["text"] for r in train]
    ids = [r["passage_id"] for r in train]
    labels = [r["author_id"] for r in train]
    original = FoldFeatures().fit(texts, ids)
    copied = FoldFeatures().fit(list(texts), list(ids))
    assert original.evidence() == copied.evidence()
    first = classifier("nearest_centroid").fit(original.transform(texts), labels)
    second = classifier("nearest_centroid").fit(copied.transform(texts), labels)
    testing = [r["text"] for r in test]
    np.testing.assert_array_equal(first.predict(original.transform(testing)), second.predict(copied.transform(testing)))
    v1, x1, e1 = tfidf_pipeline(texts, ids)
    v2, x2, e2 = tfidf_pipeline(list(texts), list(ids))
    assert e1 == e2
    svm1 = LinearSVC(C=1, class_weight="balanced", max_iter=10000, dual="auto", random_state=20260922).fit(x1, labels)
    svm2 = LinearSVC(C=1, class_weight="balanced", max_iter=10000, dual="auto", random_state=20260922).fit(x2, labels)
    np.testing.assert_array_equal(svm1.predict(v1.transform(testing)), svm2.predict(v2.transform(testing)))
