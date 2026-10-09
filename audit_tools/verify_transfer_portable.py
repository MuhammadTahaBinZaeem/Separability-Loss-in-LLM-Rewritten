"""Portable companion: preserve exact checks except up to eight ULPs in refitted IDF.

Derived from the frozen transfer verifier; the frozen source is not modified.
This does not refit the classifiers or replace stored predictions/results.
"""
from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from threadpoolctl import threadpool_limits

from research_v2.analysis import split_rows
from research_v2.corpus import AUTHORS
from research_v2.features import FoldFeatures
from research_v2.io import OUT, file_hash, read_csv, read_json, write_json
from research_v2.transfer_extension import (BASE, DOMAINS, PANELS, PIPELINES, align_records,
                                 bootstrap_weights, fingerprints, matrix_statistics,
                                 panel_records, panel_coverage, tfidf_pipeline)


def verify(model: str, study: Path = OUT, extension_base: Path = BASE):
    folder = extension_base / model
    if (folder / "RUNNING.lock").exists() or (study / f"generation/{model}/RUNNING.lock").exists():
        raise ValueError("Do not verify evidence while it is being written")
    manifest = read_json(folder / "manifest.json")
    if manifest["inputs"] != fingerprints(model, study, extension_base):
        raise ValueError("Stale analysis: data, plan or code changed")
    for relative, expected in manifest["output_hashes"].items():
        if file_hash(folder / relative) != expected:
            raise ValueError(f"Changed extension artifact: {relative}")
    originals = read_csv(study / "corpus/originals.csv")
    records, eligibility = align_records(originals, read_csv(study / f"generation/{model}/rewrites.csv"))
    works = {(r["author_id"], r["work_id"]) for r in originals}
    coverage = [panel_coverage(records, p, works) for p in PANELS]
    if read_json(folder / "panel_status.json") != coverage:
        raise ValueError("Panel availability does not match source/QC/length evidence")
    available = [r["panel"] for r in coverage if r["status"] == "estimable"]
    if manifest.get("estimable_panels") != available or manifest.get("not_estimable_panels") != [r for r in coverage if r["status"] == "not_estimable"] or manifest["panels"] != [p[0] for p in PANELS]:
        raise ValueError("Planned or unavailable panels were omitted or relabelled")
    actual_eligibility = read_csv(folder / "eligibility.csv")
    if [{k: str(v) for k, v in row.items()} for row in eligibility] != actual_eligibility:
        raise ValueError("Eligibility differs from raw QC and source data")
    predictions = read_csv(folder / "predictions.csv")
    metrics = read_csv(folder / "metrics.csv")
    contrasts = read_csv(folder / "contrasts.csv")
    views = read_csv(folder / "views.csv")
    grouped = defaultdict(list)
    for row in predictions:
        grouped[row["panel"], row["pipeline"], row["train_domain"], row["test_domain"]].append(row)
    metric_index = {(r["panel"], r["pipeline"], r["train_domain"], r["test_domain"]): r for r in metrics}
    contrast_index = {(r["panel"], r["pipeline"], r["rewrite_domain"], r["contrast"]): r for r in contrasts}
    expected_cells = {(p, pipeline, a, b) for p in available for pipeline in PIPELINES for a in DOMAINS for b in DOMAINS}
    if set(grouped) != expected_cells or set(metric_index) != expected_cells or len(metric_index) != len(metrics):
        raise ValueError("Missing, extra or duplicate matrix cells")
    if len(contrast_index) != len(available) * len(PIPELINES) * 9 or len(contrast_index) != len(contrasts):
        raise ValueError("Missing or duplicated contrast")
    expected_views, refitted = [], 0
    roundoff_records = []
    with threadpool_limits(limits=1):
        for panel in PANELS:
            name = panel[0]
            if name not in available:
                continue
            selected, panel_views = panel_records(records, panel, works)
            expected_views.extend(panel_views)
            source = {r["passage_id"]: r for r in selected}
            hashes = {(v["passage_id"], v["domain"]): v["view_sha256"] for v in panel_views}
            for fold in range(3):
                train, test = split_rows(selected, fold)
                ids = [r["passage_id"] for r in train]
                common = {"panel": name, "fold": fold, "test_ids": [r["passage_id"] for r in test],
                          "training_works": sorted({r["work_id"] for r in train}),
                          "test_works": sorted({r["work_id"] for r in test})}
                shared = FoldFeatures().fit([r["texts"]["original"] for r in train], ids)
                evidence = json.loads(gzip.decompress((folder / f"transforms/{name}_fold{fold}_shared.json.gz").read_bytes()))
                if evidence != {**common, **shared.evidence(), "fit_domain": "original"}:
                    raise ValueError("Shared scaling/vocabulary is not exactly training-original-fitted")
                refitted += 1
                for domain in DOMAINS:
                    _, _, fitted = tfidf_pipeline([r["texts"][domain] for r in train], ids)
                    evidence = json.loads(gzip.decompress((folder / f"transforms/{name}_fold{fold}_{domain}_tfidf.json.gz").read_bytes()))
                    new_evidence = {**common, **fitted, "fit_domain": domain}
                    if evidence != new_evidence:
                        # All cohort, feature-order and settings metadata stays exact.
                        old_meta = {k:v for k,v in evidence.items() if k != "idf"}
                        new_meta = {k:v for k,v in new_evidence.items() if k != "idf"}
                        if old_meta != new_meta:
                            raise ValueError("TF-IDF non-IDF evidence differs")
                        old_idf = np.asarray(evidence["idf"], dtype=np.float64)
                        new_idf = np.asarray(new_evidence["idf"], dtype=np.float64)
                        if old_idf.shape != new_idf.shape or not np.all(np.isfinite(new_idf)) or not np.all(np.isfinite(old_idf)):
                            raise ValueError("TF-IDF IDF shape or finiteness differs")
                        difference = np.abs(old_idf - new_idf)
                        ulp = np.spacing(np.maximum(1.0, np.abs(old_idf)))
                        if not np.all(difference <= 8 * ulp):
                            raise ValueError("TF-IDF IDF difference exceeds eight ULPs")
                        roundoff_records.append({"panel":name, "fold":fold, "domain":domain,
                            "different_idf_values":int(np.count_nonzero(difference)),
                            "max_absolute_difference":float(difference.max()),
                            "max_ulps":float((difference / ulp).max())})
                    refitted += 1
            weights = bootstrap_weights(selected, manifest["bootstrap_replicates"])
            for pipeline in PIPELINES:
                preds = {}
                for a in DOMAINS:
                    for b in DOMAINS:
                        rows = grouped[name, pipeline, a, b]
                        lookup = {r["passage_id"]: r for r in rows}
                        if set(lookup) != set(source) or len(lookup) != len(rows):
                            raise ValueError("Prediction row pairing or coverage changed")
                        for row in rows:
                            original = source[row["passage_id"]]
                            if any(row[k] != original[k] for k in ("author_id", "work_id")) or int(row["fold"]) != int(original["outer_fold"]):
                                raise ValueError("Prediction is on a different work/fold/author")
                            if row["view_sha256"] != hashes[row["passage_id"], b] or row["qc_status"] != original["qc"][b]:
                                raise ValueError("Prediction text view or QC does not match the observation")
                        pred = [lookup[r["passage_id"]]["predicted_author"] for r in selected]
                        y = [r["author_id"] for r in selected]
                        metric = metric_index[name, pipeline, a, b]
                        if not np.isclose(float(metric["macro_f1"]), f1_score(y, pred, labels=AUTHORS, average="macro", zero_division=0), atol=1e-12):
                            raise ValueError("Macro-F1 cannot be reconstructed from predictions")
                        if not np.isclose(float(metric["accuracy"]), accuracy_score(y, pred), atol=1e-12):
                            raise ValueError("Accuracy cannot be reconstructed")
                        if json.loads(metric["confusion_json"]) != confusion_matrix(y, pred, labels=AUTHORS).tolist():
                            raise ValueError("Confusion matrix cannot be reconstructed")
                        preds[a, b] = pred
                recomputed_metrics, recomputed_contrasts = matrix_statistics(selected, preds, weights)
                for row in recomputed_metrics:
                    actual = metric_index[name, pipeline, row["train_domain"], row["test_domain"]]
                    for k in ("macro_f1", "ci_low", "ci_high", "passages", "work_blocks", "accuracy"):
                        if not np.isclose(float(actual[k]), row[k], rtol=0, atol=1e-12):
                            raise ValueError("Matrix uncertainty/coverage cannot be reconstructed")
                for row in recomputed_contrasts:
                    actual = contrast_index[name, pipeline, row["rewrite_domain"], row["contrast"]]
                    for k, value in row.items():
                        if isinstance(value, (float, int)):
                            if not np.isclose(float(actual[k]), value, rtol=0, atol=1e-12):
                                raise ValueError("Contrast or paired uncertainty cannot be reconstructed")
                        elif actual[k] != value:
                            raise ValueError("Contrast definition differs")
            print(f"Verified {model}: {name}, predictions, transforms and paired uncertainty", flush=True)
    if [{k: str(v) for k, v in row.items()} for row in expected_views] != views:
        raise ValueError("Cropped views do not match exact source character slices")
    result = {"idf_comparison": "all metadata exact; finite IDF values within eight ULPs",
              "idf_roundoff_records": roundoff_records, "classifier_predictions_refitted": False,
              "passed": True, "verified_utc": datetime.now(timezone.utc).isoformat(),
              "model_key": model, "manifest_sha256": file_hash(folder / "manifest.json"),
              "verifier_sha256": file_hash(Path(__file__)),
              "prediction_rows": len(predictions), "matrix_cells": len(metrics),
              "contrast_rows": len(contrasts), "transforms_refitted": refitted,
              "verified_scope": "hashes_cohorts_views_fold_alignment_transform_refits_scores_and_paired_CIs",
              "not_independent_human_review": True, "submission_ready": False}
    write_json(folder / "verification.json", result)
    return result


