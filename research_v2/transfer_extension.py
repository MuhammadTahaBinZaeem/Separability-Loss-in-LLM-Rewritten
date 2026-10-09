"""Offline, exploratory train/test-domain and length-control study; not frozen v2."""
from __future__ import annotations

import argparse
import gzip
import json
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.svm import LinearSVC
from threadpoolctl import threadpool_limits

from .analysis import classifier, split_rows
from .corpus import AUTHORS, WORD, words
from .features import FoldFeatures, feature_family
from .generation import consolidate, verify_corpus
from .inference import f1_from_confusion
from .io import (OUT, ROOT, digest_bytes, digest_text, file_hash, read_csv,
                 read_json, write_csv, write_json, write_text)

BASE = OUT / "extensions/jql_v1"
DOMAINS = ("original", "paraphrase", "modernize", "simplify")
PIPELINES = ("shared_stylometry_nc", "shared_function_words_nc", "char3_5_tfidf_svm")
# name, minimum words in EVERY domain, crop size (0 means full), crop location
PANELS = (("valid_full", 0, 0, "full"),
          ("matched200_full", 200, 0, "full"),
          ("w200_prefix", 200, 200, "prefix"),
          ("w200_middle", 200, 200, "middle"),
          ("w200_suffix", 200, 200, "suffix"),
          ("matched300_full", 300, 0, "full"),
          ("w300_middle", 300, 300, "middle"))
SEED = 20260922


def crop(text: str, size: int, location: str) -> tuple[str, int, int]:
    """Return an exact, contiguous character slice with the requested word count."""
    if size == 0 and location == "full":
        return text, 0, len(text)
    matches = list(WORD.finditer(text))
    if size <= 0 or len(matches) < size:
        raise ValueError("Insufficient words; never pad or silently shorten a view")
    starts = {"prefix": 0, "middle": (len(matches) - size) // 2,
              "suffix": len(matches) - size}
    if location not in starts:
        raise ValueError("Unknown crop location")
    start_word = starts[location]
    end_word = start_word + size
    # Include punctuation after the last selected word, up to the next word.
    start = 0 if start_word == 0 else matches[start_word].start()
    end = len(text) if end_word == len(matches) else matches[end_word].start()
    view = text[start:end]
    if words(view) != size:
        raise ValueError("Crop changed token count")
    return view, start, end


def align_records(originals: list[dict], rewrites: list[dict]):
    originals_by_id = {r["passage_id"]: r for r in originals}
    if len(originals_by_id) != len(originals):
        raise ValueError("Duplicate source passage")
    for row in originals:
        if digest_text(row["text"]) != row["text_sha256"]:
            raise ValueError("Original text hash mismatch")
    index = {}
    for row in rewrites:
        key = row["passage_id"], row["condition"]
        if key in index or key[0] not in originals_by_id or key[1] not in DOMAINS[1:]:
            raise ValueError("Duplicate, unknown or mislabelled rewrite")
        if row["source_sha256"] != originals_by_id[key[0]]["text_sha256"]:
            raise ValueError("Rewrite bound to a different source")
        if row["qc_status"] in {"pass", "warning"}:
            if digest_text(row["rewritten_text"]) != row["rewrite_sha256"]:
                raise ValueError("Rewrite text hash mismatch")
        index[key] = row
    if len(index) != len(originals) * 3:
        raise ValueError("Complete accounting required; missing rows cannot disappear")
    records, eligibility = [], []
    for original in sorted(originals, key=lambda r: r["passage_id"]):
        pid = original["passage_id"]
        variants = {d: index[pid, d] for d in DOMAINS[1:]}
        failed = [d for d, r in variants.items() if r["qc_status"] not in {"pass", "warning"}]
        texts = {"original": original["text"], **{d: r["rewritten_text"] for d, r in variants.items()}}
        minimum = min(words(t) for t in texts.values())
        info = {k: original[k] for k in ("passage_id", "author_id", "work_id", "outer_fold")}
        eligibility.append({**info, "valid_all_domains": int(not failed),
                            "excluded_conditions": "|".join(failed), "minimum_words": minimum,
                            **{f"{d}_words": words(texts[d]) for d in DOMAINS},
                            **{f"{d}_qc": variants[d]["qc_status"] for d in DOMAINS[1:]}})
        if not failed:
            records.append({**info, "texts": texts, "minimum_words": minimum,
                            "qc": {"original": "source", **{d: r["qc_status"] for d, r in variants.items()}}})
    return records, eligibility


def panel_coverage(records: list[dict], panel: tuple, all_works: set):
    """Unavailable length controls remain planned and visible, never silently relaxed."""
    selected = [r for r in records if r["minimum_words"] >= panel[1]]
    counts = Counter((r["author_id"], r["work_id"]) for r in selected)
    if set(counts) - all_works:
        raise ValueError("Unexpected work in panel")
    missing = sorted(all_works - set(counts))
    return {"panel": panel[0], "minimum_words": panel[1], "crop_size": panel[2], "location": panel[3],
            "status": "not_estimable" if missing else "estimable", "eligible_passages": len(selected),
            "reason": "entire_author_work_unavailable" if missing else "all_planned_works_present",
            "missing_works": [list(w) for w in missing],
            "work_counts": [{"author_id": a, "work_id": w, "passages": counts[a, w]} for a, w in sorted(all_works)]}


def panel_records(records: list[dict], panel: tuple, all_works: set):
    _, minimum, size, location = panel
    selected = [r for r in records if r["minimum_words"] >= minimum]
    if {(r["author_id"], r["work_id"]) for r in selected} != all_works:
        raise ValueError("A whole author/work is unavailable in this panel")
    views, result = [], []
    for row in selected:
        texts = {}
        for domain in DOMAINS:
            text, start, end = crop(row["texts"][domain], size, location)
            texts[domain] = text
            views.append({"panel": panel[0], "passage_id": row["passage_id"], "domain": domain,
                          "source_text_sha256": digest_text(row["texts"][domain]),
                          "start_char": start, "end_char": end,
                          "view_sha256": digest_text(text), "word_count": words(text)})
        result.append({**row, "texts": texts})
    for fold in range(3):
        split_rows(result, fold)
    return result, views


def tfidf_pipeline(texts: list[str], ids: list[str]):
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), lowercase=True,
                                 min_df=2, max_features=30000, sublinear_tf=True,
                                 smooth_idf=True, norm="l2")
    matrix = vectorizer.fit_transform(texts)
    evidence = {"training_ids": ids, "training_text_hashes": [digest_text(t) for t in texts],
                "feature_names": vectorizer.get_feature_names_out().tolist(),
                "idf": vectorizer.idf_.tolist(), "fit_scope": "selected_training_domain_training_works_only",
                "parameters": {"analyzer": "char", "ngram_range": [3, 5], "lowercase": True,
                               "min_df": 2, "max_features": 30000, "sublinear_tf": True,
                               "smooth_idf": True, "norm": "l2"}}
    return vectorizer, matrix, evidence


def save_evidence(path: Path, evidence: dict):
    # Deterministic gzip includes neither a filename nor a changing timestamp.
    data = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(data, mtime=0))


def bootstrap_weights(rows: list[dict], count: int, seed: int = SEED) -> np.ndarray:
    if count < 2 or len({r["passage_id"] for r in rows}) != len(rows):
        raise ValueError("Need bootstrap replicates and unique paired passages")
    groups = []
    for author in AUTHORS:
        works = sorted({r["work_id"] for r in rows if r["author_id"] == author})
        if len(works) != 3:
            raise ValueError("All three works of every fixed author are required")
        groups.append([np.array([i for i, r in enumerate(rows)
                                 if r["author_id"] == author and r["work_id"] == work]) for work in works])
    rng = np.random.default_rng(seed)
    weights = np.zeros((count, len(rows)), dtype=np.int32)
    for b in range(count):
        for author_groups in groups:
            for chosen in rng.integers(0, 3, size=3):
                indices = author_groups[chosen]
                sampled = rng.choice(indices, size=len(indices), replace=True)
                np.add.at(weights[b], sampled, 1)
    return weights


def matrix_statistics(rows: list[dict], predictions: dict, weights: np.ndarray):
    labels = {a: i for i, a in enumerate(AUTHORS)}
    y = np.array([labels[r["author_id"]] for r in rows])
    n_labels = len(AUTHORS)
    scores, distributions, metrics = {}, {}, []
    for train_domain in DOMAINS:
        for test_domain in DOMAINS:
            key = train_domain, test_domain
            pred = np.array([labels[p] for p in predictions[key]])
            if len(pred) != len(rows):
                raise ValueError("Matrix cells must have identical paired observations")
            contributions = np.zeros((len(rows), n_labels * n_labels))
            contributions[np.arange(len(rows)), y * n_labels + pred] = 1
            boot_confusions = (weights @ contributions).reshape(-1, n_labels, n_labels)
            distributions[key] = f1_from_confusion(boot_confusions)
            score = float(f1_score(y, pred, labels=list(range(n_labels)), average="macro", zero_division=0))
            scores[key] = score
            low, high = np.quantile(distributions[key], [.025, .975])
            metrics.append({"train_domain": train_domain, "test_domain": test_domain,
                            "passages": len(rows), "work_blocks": 18, "macro_f1": score,
                            "ci_low": float(low), "ci_high": float(high),
                            "accuracy": float(accuracy_score(y, pred)),
                            "confusion_json": json.dumps(confusion_matrix(y, pred, labels=range(n_labels)).tolist())})
    contrasts = []
    for domain in DOMAINS[1:]:
        pairs = {"transfer_loss": (("original", "original"), ("original", domain)),
                 "adaptation_gain": ((domain, domain), ("original", domain)),
                 "within_domain_gap": (("original", "original"), (domain, domain))}
        for name, (first, second) in pairs.items():
            low, high = np.quantile(distributions[first] - distributions[second], [.025, .975])
            contrasts.append({"rewrite_domain": domain, "contrast": name,
                              "first_cell": "->".join(first), "second_cell": "->".join(second),
                              "difference_macro_f1": scores[first] - scores[second],
                              "ci_low": float(low), "ci_high": float(high),
                              "passages": len(rows), "work_blocks": 18,
                              "bootstrap_replicates": len(weights), "bootstrap_seed": SEED,
                              "scope": "exploratory_marginal_fixed_authors_conditional_fitted_models"})
    return metrics, contrasts


def geometry(rows: list[dict], matrices: dict, names: list[str]):
    result, changes = [], []
    masks = {"all_features": np.ones(len(names), dtype=bool),
             "function_words": np.array([feature_family(n) == "function_word" for n in names])}
    groups = [np.array([i for i, r in enumerate(rows) if r["author_id"] == a]) for a in AUTHORS]
    if any(len(g) == 0 for g in groups):
        raise ValueError("Geometry requires all six authors")
    all_centroids = {d: np.array([matrix[g].mean(axis=0) for g in groups]) for d, matrix in matrices.items()}
    for domain in DOMAINS:
        for family, mask in masks.items():
            c = all_centroids[domain][:, mask]
            original = all_centroids["original"][:, mask]
            delta = c - original
            global_shift = delta.mean(axis=0)
            between = float(np.mean((c - c.mean(axis=0)) ** 2))
            within = float(np.mean([np.mean((matrices[domain][g][:, mask] - c[i]) ** 2)
                                    for i, g in enumerate(groups)]))
            baseline_between = float(np.mean((original - original.mean(axis=0)) ** 2))
            result.append({"domain": domain, "feature_family": family, "passages": len(rows),
                           "feature_count": int(mask.sum()), "between_centroid_mean_square": between,
                           "within_author_mean_square": within,
                           "between_within_ratio": between / within if within else "",
                           "between_ratio_to_original": between / baseline_between if baseline_between else "",
                           "common_shift_rms": float(np.sqrt(np.mean(global_shift ** 2))),
                           "differential_shift_rms": float(np.sqrt(np.mean((delta - global_shift) ** 2)))})
        if domain != "original":
            for ai, author in enumerate(AUTHORS):
                work = rows[groups[ai][0]]["work_id"]
                for j, name in enumerate(names):
                    changes.append({"domain": domain, "author_id": author, "work_id": work,
                                    "feature": name, "family": feature_family(name),
                                    "original_mean_z": float(all_centroids["original"][ai, j]),
                                    "rewrite_mean_z": float(all_centroids[domain][ai, j]),
                                    "delta_z": float(all_centroids[domain][ai, j] - all_centroids["original"][ai, j])})
    return result, changes


def fingerprints(model: str, study: Path = OUT, extension_base: Path = BASE):
    folder = study / f"generation/{model}"
    paths = [extension_base / "PLAN.md", study / "corpus/originals.csv", study / "corpus/freeze.json",
             study / "generation_plan.json", study / "PROTOCOL.md",
             ROOT / "requirements-v2.lock", ROOT / "scripts/13_extract_stylometric_features.py"]
    paths += [study / name for name in ("AMENDMENTS.md", "scope_amendment.json", "corpus/lineage.csv") if (study / name).exists()]
    paths += [ROOT / f"research_v2/{name}.py" for name in
              ("transfer_extension", "analysis", "features", "inference", "corpus", "generation", "providers", "io")]
    paths += [folder / name for name in ("requests.jsonl", "raw_responses.jsonl", "terminal_outcomes.jsonl",
                                         "rewrites.csv", "completion.json", "request_manifest.json", "assignments.jsonl",
                                         "outcomes.jsonl", "session_outputs.jsonl") if (folder / name).exists()]
    if study != OUT:
        paths += [ROOT / f"research_v2/{name}.py" for name in ("expanded_study", "expanded_generation", "session_generation", "expanded_analysis")]
        if model == "astra_session":
            paths.append(OUT / "expansion/session_arm_provenance.json")
        else:
            from .expanded_study import effective_plan
            reused = effective_plan()["models"][model].get("reuse_v2_model")
            if reused:
                paths += [OUT / f"generation/{reused}/{name}" for name in ("request_manifest.json", "requests.jsonl", "rewrites.csv", "raw_responses.jsonl", "terminal_outcomes.jsonl") if (OUT / f"generation/{reused}/{name}").exists()]
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths}


def report(folder: Path, model: str, metrics: list[dict], contrasts: list[dict], eligibility: list[dict]):
    valid = sum(r["valid_all_domains"] for r in eligibility)
    lines = [f"# Exploratory domain-transfer extension: {model}", "",
             "Not a confirmatory result, human validation or submission-readiness certificate.", "",
             f"Common valid cohort: {valid}/{len(eligibility)} source passages. All panels retain 18 works and six authors.", "",
             "All estimable 4 x 4 matrices from seven planned panels and three pipelines are in metrics.csv. No best pipeline is selected.", "",
             "## Full common-cohort comparisons", "",
             "| Pipeline | Rewrite | O -> O | O -> R | R -> R | Adaptation gain [marginal 95% CI] | Within-domain gap |",
             "|---|---|---:|---:|---:|---|---:|"]
    lookup = {(r["panel"], r["pipeline"], r["train_domain"], r["test_domain"]): r for r in metrics}
    contrast_index = {(r["panel"], r["pipeline"], r["rewrite_domain"], r["contrast"]): r for r in contrasts}
    for pipeline in PIPELINES:
        for d in DOMAINS[1:]:
            vals = [lookup["valid_full", pipeline, a, b]["macro_f1"] for a, b in
                    (("original", "original"), ("original", d), (d, d))]
            gain = contrast_index["valid_full", pipeline, d, "adaptation_gain"]
            gap = contrast_index["valid_full", pipeline, d, "within_domain_gap"]
            lines.append(f"| {pipeline} | {d} | {vals[0]:.3f} | {vals[1]:.3f} | {vals[2]:.3f} | "
                         f"{gain['difference_macro_f1']:+.3f} [{gain['ci_low']:+.3f}, {gain['ci_high']:+.3f}] | {gap['difference_macro_f1']:+.3f} |")
    lines += ["", "## Length-control comparisons (same cohort for full and cropped text)", "",
              "| Pipeline | Rewrite | Control | n | Full transfer loss | Cropped transfer loss | Full within-domain gap | Cropped within-domain gap |",
              "|---|---|---|---:|---:|---:|---:|---:|"]
    for pipeline in PIPELINES:
        for d in DOMAINS[1:]:
            for panel, reference in (("w200_prefix", "matched200_full"), ("w200_middle", "matched200_full"),
                                     ("w200_suffix", "matched200_full"), ("w300_middle", "matched300_full")):
                if (panel, pipeline, d, "transfer_loss") not in contrast_index or (reference, pipeline, d, "transfer_loss") not in contrast_index:
                    lines.append(f"| {pipeline} | {d} | {panel} | — | Not estimable | Not estimable | Not estimable | Not estimable |")
                    continue
                values = [contrast_index[p, pipeline, d, c] for c in ("transfer_loss", "within_domain_gap")
                          for p in (reference, panel)]
                lines.append(f"| {pipeline} | {d} | {panel} | {values[0]['passages']} | " +
                             " | ".join(f"{r['difference_macro_f1']:+.3f}" for r in values) + " |")
    lines += ["", "## Interpretation constraints", "",
              "Positive adaptation gain means this learner recovers some predictive association when trained on rewrites. "
              "It does not prove preserved meaning, pure style or all recoverable information. Negative within-domain gaps "
              "do not establish that rewriting creates author information. Topic, genre, length and feature/learner choice still matter.", "",
              "CIs resample the same held-out passage pairs within works and works within fixed authors; they do not refit "
              "the learners or cover new authors. Intervals across these many overlapping panels are not simultaneous. "
              "No new confirmatory p-values are reported. Equal-length cuts change which content is observed.", "",
              "Planned but unavailable controls are listed in panel_status.json with zero-count works. "
              "Their thresholds and required work coverage are not changed, and no metrics are fabricated.", "",
              "Reproduction: `.venv/Scripts/python.exe -m research_v2.transfer_extension --model " + model + "`. "
              "No API calls. See ../PLAN.md, manifest.json and the original generation ledgers for provenance.", ""]
    write_text(folder / "REPORT.md", "\n".join(lines))


def run(model: str, bootstraps: int = 5000, study: Path = OUT, extension_base: Path = BASE):
    if (study / f"generation/{model}/RUNNING.lock").exists():
        raise ValueError("Do not read mutable data from an active generator")
    if study == OUT:
        if model not in {"azure_replication", "gem31lite"}:
            raise ValueError("Only the two planned providers may enter the v2 extension")
        verify_corpus()
        completion = consolidate(model)
    else:
        from .expanded_study import BASE as expanded, effective_plan, verify
        if study != expanded or model not in effective_plan()["active_models"]:
            raise ValueError("Unrecognized versioned study/model")
        verify()
        if model == "astra_session":
            from .session_generation import consolidate as expanded_consolidate
            completion = expanded_consolidate()
        else:
            from .expanded_generation import consolidate as expanded_consolidate
            completion = expanded_consolidate(model)
    if not completion["accounting_complete"]:
        raise ValueError("Finish observation accounting before analyzing this provider")
    originals = read_csv(study / "corpus/originals.csv")
    records, eligibility = align_records(originals, read_csv(study / f"generation/{model}/rewrites.csv"))
    all_works = {(r["author_id"], r["work_id"]) for r in originals}
    coverage = [panel_coverage(records, p, all_works) for p in PANELS]
    available = {r["panel"] for r in coverage if r["status"] == "estimable"}
    if "valid_full" not in available:
        raise ValueError("Full paired cohort is not estimable across every planned work")
    folder = extension_base / model
    if bootstraps != 5000:
        raise ValueError("Research runs use the recorded 5000 replicates; unit tests call helpers directly")
    # A lock prevents overlapping extension runs. An interrupted run is not certified.
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / "RUNNING.lock"
    with lock.open("x", encoding="utf-8") as stream:
        import os
        stream.write(str(os.getpid()))
    inputs = fingerprints(model, study, extension_base)
    metrics_all, contrasts_all, predictions_all, views_all, geometry_all, changes_all, counts = [], [], [], [], [], [], []
    files = []
    def emit(name, data):
        path = folder / name
        write_csv(path, data)
        files.append(path)
    try:
        with threadpool_limits(limits=1), warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            for panel in PANELS:
                name = panel[0]
                if name not in available:
                    print(f"{model}: {name} not estimable; missing-work evidence retained", flush=True)
                    continue
                selected, views = panel_records(records, panel, all_works)
                views_all.extend(views)
                counts.extend({"panel": name, "author_id": a, "work_id": w, "passages": n}
                              for (a, w), n in sorted(Counter((r["author_id"], r["work_id"]) for r in selected).items()))
                pids = [r["passage_id"] for r in selected]
                position = {pid: i for i, pid in enumerate(pids)}
                predictions = {p: {(a, b): [None] * len(selected) for a in DOMAINS for b in DOMAINS} for p in PIPELINES}
                for fold in range(3):
                    train, test = split_rows(selected, fold)
                    training_ids = [r["passage_id"] for r in train]
                    common = {"panel": name, "fold": fold,
                              "test_ids": [r["passage_id"] for r in test],
                              "training_works": sorted({r["work_id"] for r in train}),
                              "test_works": sorted({r["work_id"] for r in test})}
                    shared = FoldFeatures().fit([r["texts"]["original"] for r in train], training_ids)
                    training = {d: shared.transform([r["texts"][d] for r in train]) for d in DOMAINS}
                    testing = {d: shared.transform([r["texts"][d] for r in test]) for d in DOMAINS}
                    path = folder / f"transforms/{name}_fold{fold}_shared.json.gz"
                    save_evidence(path, {**common, **shared.evidence(), "fit_domain": "original"})
                    files.append(path)
                    g, c = geometry(test, testing, shared.feature_names_)
                    geometry_all.extend({"panel": name, "fold": fold, **r} for r in g)
                    changes_all.extend({"panel": name, "fold": fold, **r} for r in c)
                    fw_mask = np.array([feature_family(n) == "function_word" for n in shared.feature_names_])
                    for domain in DOMAINS:
                        texts = [r["texts"][domain] for r in train]
                        vectorizer, sparse_train, evidence = tfidf_pipeline(texts, training_ids)
                        path = folder / f"transforms/{name}_fold{fold}_{domain}_tfidf.json.gz"
                        save_evidence(path, {**common, **evidence, "fit_domain": domain})
                        files.append(path)
                        for pipeline in PIPELINES:
                            if pipeline == "char3_5_tfidf_svm":
                                learner = LinearSVC(C=1, class_weight="balanced", tol=1e-4,
                                                    max_iter=10000, dual="auto", random_state=SEED)
                                x_train = sparse_train
                                x_test = {d: vectorizer.transform([r["texts"][d] for r in test]) for d in DOMAINS}
                            else:
                                learner = classifier("nearest_centroid")
                                mask = fw_mask if pipeline == "shared_function_words_nc" else np.ones(len(fw_mask), dtype=bool)
                                x_train = training[domain][:, mask]
                                x_test = {d: testing[d][:, mask] for d in DOMAINS}
                            learner.fit(x_train, [r["author_id"] for r in train])
                            for target in DOMAINS:
                                pred = learner.predict(x_test[target])
                                for row, predicted in zip(test, pred):
                                    idx = position[row["passage_id"]]
                                    if predictions[pipeline][domain, target][idx] is not None:
                                        raise ValueError("Duplicate held-out prediction")
                                    predictions[pipeline][domain, target][idx] = predicted
                                    predictions_all.append({"panel": name, "pipeline": pipeline,
                                                            "train_domain": domain, "test_domain": target,
                                                            "fold": fold, "passage_id": row["passage_id"],
                                                            "author_id": row["author_id"], "work_id": row["work_id"],
                                                            "predicted_author": predicted, "qc_status": row["qc"][target],
                                                            "view_sha256": digest_text(row["texts"][target])})
                weights = bootstrap_weights(selected, bootstraps)
                for pipeline in PIPELINES:
                    if any(None in p for p in predictions[pipeline].values()):
                        raise ValueError("Incomplete out-of-fold matrix")
                    metrics, contrasts = matrix_statistics(selected, predictions[pipeline], weights)
                    metrics_all.extend({"panel": name, "pipeline": pipeline, **r} for r in metrics)
                    contrasts_all.extend({"panel": name, "pipeline": pipeline, **r} for r in contrasts)
                print(f"{model}: {name}, n={len(selected)}, all 48 matrix cells complete", flush=True)
        if fingerprints(model, study, extension_base) != inputs:
            raise ValueError("Source/code inputs changed during the run")
        emit("eligibility.csv", eligibility)
        emit("cohort_counts.csv", counts)
        emit("views.csv", views_all)
        emit("metrics.csv", metrics_all)
        emit("contrasts.csv", contrasts_all)
        emit("predictions.csv", predictions_all)
        emit("geometry.csv", geometry_all)
        emit("feature_changes.csv", changes_all)
        write_json(folder / "panel_status.json", coverage)
        files.append(folder / "panel_status.json")
        report(folder, model, metrics_all, contrasts_all, eligibility)
        files.append(folder / "REPORT.md")
        manifest = {"completed_utc": datetime.now(timezone.utc).isoformat(), "model_key": model,
                    "analysis_kind": "exploratory_after_v2_results", "human_validation_complete": False,
                    "study_root": study.relative_to(ROOT).as_posix(), "session_arm_not_equivalent_to_api": model == "astra_session",
                    "submission_ready": False, "bootstrap_replicates": bootstraps, "seed": SEED,
                    "inputs": inputs, "input_fingerprint": digest_text(json.dumps(inputs, sort_keys=True)),
                    "output_hashes": {p.relative_to(folder).as_posix(): file_hash(p) for p in files},
                    "metric_rows": len(metrics_all), "contrast_rows": len(contrasts_all),
                    "prediction_rows": len(predictions_all), "panels": [p[0] for p in PANELS],
                    "estimable_panels": [p[0] for p in PANELS if p[0] in available],
                    "not_estimable_panels": [r for r in coverage if r["status"] == "not_estimable"],
                    "pipelines": list(PIPELINES), "no_new_confirmatory_tests": True}
        write_json(folder / "manifest.json", manifest)
        print(json.dumps({k: v for k, v in manifest.items() if k not in {"inputs", "output_hashes"}}, indent=2), flush=True)
        return manifest
    finally:
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=("azure_replication", "gem31lite"))
    args = parser.parse_args()
    run(args.model)


if __name__ == "__main__":
    main()
