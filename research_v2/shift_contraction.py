"""Exploratory unseen-work prediction of shift/contraction, not a linguistic law."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import numpy as np
from threadpoolctl import threadpool_limits

from .analysis import split_rows
from .corpus import AUTHORS
from .features import FoldFeatures, feature_family
from .io import OUT, ROOT, digest_text, file_hash, read_csv, read_json, write_csv, write_json, write_jsonl, write_text
from .transfer_extension import BASE, DOMAINS, PANELS, SEED, align_records, fingerprints, panel_records

MODELS = ("identity", "translation", "scalar_affine")
SELECTED_PANELS = ("valid_full", "w200_middle", "w300_middle")


def fit_mapping(x: np.ndarray, y: np.ndarray, kind: str):
    if x.shape != y.shape or x.ndim != 2 or len(x) < 2:
        raise ValueError("Matched nonempty training centroid matrices required")
    if kind == "identity":
        return 1.0, np.zeros(x.shape[1])
    if kind == "translation":
        return 1.0, np.mean(y - x, axis=0)
    if kind != "scalar_affine":
        raise ValueError("Unknown mapping")
    centered_x, centered_y = x - x.mean(axis=0), y - y.mean(axis=0)
    denominator = np.sum(centered_x ** 2)
    if denominator <= 1e-15:
        raise ValueError("No training work-centroid variation")
    alpha = float(np.sum(centered_x * centered_y) / denominator)
    return alpha, y.mean(axis=0) - alpha * x.mean(axis=0)


def dispersion_identity(x, y, alpha, intercept):
    residual = y - (alpha * x + intercept)
    xc, yc, ec = (v - v.mean(axis=0) for v in (x, y, residual))
    bx, by, be, covariance = (float(np.mean(v)) for v in (xc ** 2, yc ** 2, ec ** 2, xc * ec))
    rhs = alpha ** 2 * bx + be + 2 * alpha * covariance
    return {"between_original": bx, "between_rewrite": by,
            "scaled_original_component": alpha ** 2 * bx, "residual_component": be,
            "cross_component": 2 * alpha * covariance,
            "closure_error": by - rhs}


def work_centroids(rows, matrix):
    keys = sorted({(r["author_id"], r["work_id"]) for r in rows})
    result = np.array([matrix[[i for i, r in enumerate(rows) if (r["author_id"], r["work_id"]) == key]].mean(axis=0)
                       for key in keys])
    return keys, result


def work_bootstrap(rows, count=5000):
    keys = [(r["author_id"], r["work_id"]) for r in rows]
    if len(set(keys)) != 18 or len(keys) != 18:
        raise ValueError("Exactly one held-out centroid per each of 18 works required")
    rng = np.random.default_rng(SEED)
    groups = [np.array([i for i, r in enumerate(rows) if r["author_id"] == a]) for a in AUTHORS]
    if any(len(g) != 3 for g in groups):
        raise ValueError("Three works per fixed author required")
    return np.concatenate([rng.choice(g, size=(count, 3), replace=True) for g in groups], axis=1)


def _run_unlocked(model, study=OUT, extension_base=BASE):
    folder = extension_base / model
    if (folder / "RUNNING.lock").exists() or (study / f"generation/{model}/RUNNING.lock").exists():
        raise ValueError("Wait for completed immutable domain-transfer evidence")
    manifest = read_json(folder / "manifest.json")
    if manifest["inputs"] != fingerprints(model, study, extension_base):
        raise ValueError("Domain-transfer analysis is stale")
    for relative, expected in manifest["output_hashes"].items():
        if file_hash(folder / relative) != expected:
            raise ValueError("Domain-transfer evidence changed")
    destination = folder / "explanatory_model"
    paths = [ROOT / "research_v2/shift_contraction.py", extension_base / "EXPLANATORY_MODEL_PLAN.md", folder / "manifest.json"]
    inputs = {**manifest["inputs"], **{p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths}}
    originals = read_csv(study / "corpus/originals.csv")
    records, _ = align_records(originals, read_csv(study / f"generation/{model}/rewrites.csv"))
    works = {(r["author_id"], r["work_id"]) for r in originals}
    available = [p for p in SELECTED_PANELS if p in manifest["estimable_panels"]]
    parameters, predictions, components = [], [], []
    with threadpool_limits(limits=1):
        for panel in PANELS:
            if panel[0] not in available:
                continue
            selected, _ = panel_records(records, panel, works)
            for fold in range(3):
                train, test = split_rows(selected, fold)
                transform = FoldFeatures().fit([r["texts"]["original"] for r in train], [r["passage_id"] for r in train])
                train_matrices = {d: transform.transform([r["texts"][d] for r in train]) for d in DOMAINS}
                test_matrices = {d: transform.transform([r["texts"][d] for r in test]) for d in DOMAINS}
                for family in ("all_features", "function_words"):
                    mask = np.array([family == "all_features" or feature_family(n) == "function_word" for n in transform.feature_names_])
                    names = [n for n, keep in zip(transform.feature_names_, mask) if keep]
                    training_keys, x_train = work_centroids(train, train_matrices["original"][:, mask])
                    test_keys, x_test = work_centroids(test, test_matrices["original"][:, mask])
                    if set(training_keys) & set(test_keys) or len(training_keys) != 12 or len(test_keys) != 6:
                        raise ValueError("Work leakage in explanatory mapping")
                    for domain in DOMAINS[1:]:
                        _, y_train = work_centroids(train, train_matrices[domain][:, mask])
                        _, y_test = work_centroids(test, test_matrices[domain][:, mask])
                        common = {"panel": panel[0], "fold": fold, "family": family, "domain": domain}
                        for kind in MODELS:
                            alpha, intercept = fit_mapping(x_train, y_train, kind)
                            fit_id = digest_text(json.dumps({**common, "mapping": kind}, sort_keys=True))[:20]
                            predicted = alpha * x_test + intercept
                            parameters.append({**common, "fit_id": fit_id, "mapping": kind, "alpha": alpha,
                                               "intercept": intercept.tolist(), "feature_names": names,
                                               "training_works": training_keys, "test_works": test_keys,
                                               "training_centroids_original": x_train.tolist(),
                                               "training_centroids_rewrite": y_train.tolist(),
                                               "shared_transform_evidence": f"../transforms/{panel[0]}_fold{fold}_shared.json.gz"})
                            for i, (author, work) in enumerate(test_keys):
                                predictions.append({**common, "fit_id": fit_id, "mapping": kind,
                                                    "author_id": author, "work_id": work,
                                                    "mse": float(np.mean((y_test[i] - predicted[i]) ** 2)),
                                                    "original_centroid": x_test[i].tolist(),
                                                    "rewrite_centroid": y_test[i].tolist(),
                                                    "predicted_centroid": predicted[i].tolist()})
                            components.append({**common, "mapping": kind, "alpha_train": alpha,
                                               **dispersion_identity(x_test, y_test, alpha, intercept)})
            print(f"{model}: explanatory model {panel[0]}, held-out predictions completed", flush=True)
    summary, contrasts = [], []
    for panel in available:
        for family in ("all_features", "function_words"):
            for domain in DOMAINS[1:]:
                common = {"panel": panel, "family": family, "domain": domain}
                group = [r for r in predictions if all(r[k] == v for k, v in common.items())]
                vectors, samples = {}, {}
                for kind in MODELS:
                    rows = sorted([r for r in group if r["mapping"] == kind], key=lambda r: (r["author_id"], r["work_id"]))
                    indices = work_bootstrap(rows)
                    vectors[kind] = np.array([r["mse"] for r in rows])
                    samples[kind] = vectors[kind][indices].mean(axis=1)
                    low, high = np.quantile(samples[kind], [.025, .975])
                    summary.append({**common, "mapping": kind, "held_out_works": len(rows),
                                    "mse": float(vectors[kind].mean()), "ci_low": float(low), "ci_high": float(high)})
                for first, second, name in (("identity", "translation", "translation_improvement"),
                                            ("translation", "scalar_affine", "affine_improvement")):
                    low, high = np.quantile(samples[first] - samples[second], [.025, .975])
                    contrasts.append({**common, "contrast": name,
                                      "mse_reduction": float(np.mean(vectors[first] - vectors[second])),
                                      "ci_low": float(low), "ci_high": float(high), "bootstrap_replicates": 5000,
                                      "scope": "fixed_authors_work_centroids_conditional_fitted_mappings"})
    for relative, expected in inputs.items():
        if file_hash(ROOT / relative) != expected:
            raise ValueError("An input changed during explanatory analysis")
    write_jsonl(destination / "parameters.jsonl", parameters)
    write_jsonl(destination / "work_predictions.jsonl", predictions)
    write_csv(destination / "dispersion_components.csv", components)
    write_csv(destination / "summary.csv", summary)
    write_csv(destination / "contrasts.csv", contrasts)
    lookup = {(r["panel"], r["family"], r["domain"], r["mapping"]): r for r in summary}
    lines = [f"# Held-out shift/contraction explanation: {model}", "",
             "Exploratory model adequacy check, not proof of a linguistic law or human-verified semantics.", "",
             "| Panel | Features | Rewrite | Identity MSE | Translation MSE | Scalar-affine MSE | Training alpha by fold |",
             "|---|---|---|---:|---:|---:|---|"]
    for panel in available:
        for family in ("all_features", "function_words"):
            for domain in DOMAINS[1:]:
                vals = [lookup[panel, family, domain, kind]["mse"] for kind in MODELS]
                alphas = [r["alpha"] for r in parameters if r["panel"] == panel and r["family"] == family
                          and r["domain"] == domain and r["mapping"] == "scalar_affine"]
                lines.append(f"| {panel} | {family} | {domain} | " + " | ".join(f"{v:.4f}" for v in vals) +
                             " | " + ", ".join(f"{a:.3f}" for a in alphas) + " |")
    lines += ["", "Lower held-out MSE indicates better prediction of rewritten work centroids. "
              "A fitted alpha below one is not enough: the constrained explanation should improve unseen-work prediction, "
              "and residual/cross components must be considered. Paired marginal intervals are in contrasts.csv. "
              "The algebraic dispersion identity is checked numerically; a tiny closure error is arithmetic verification, not scientific validation.", "",
              "All work centroids are equally weighted. Scaling is original-training-fold-specific. "
              "Intervals condition on fitted mappings and observed centroids, omit training/passage uncertainty, "
              "and are not simultaneous across these overlapping comparisons. Topic/genre and availability effects remain.", ""]
    unavailable = [r for r in manifest["not_estimable_panels"] if r["panel"] in SELECTED_PANELS]
    if unavailable:
        lines += ["Planned controls not estimable (missing whole works): " + ", ".join(r["panel"] for r in unavailable) + ". See the parent panel_status.json.", ""]
    write_text(destination / "REPORT.md", "\n".join(lines))
    files = [destination / name for name in ("parameters.jsonl", "work_predictions.jsonl", "dispersion_components.csv",
                                             "summary.csv", "contrasts.csv", "REPORT.md")]
    result = {"completed_utc": datetime.now(timezone.utc).isoformat(), "model_key": model,
              "analysis_kind": "exploratory_restricted_mapping_held_out_work_validation",
              "inputs": inputs, "output_hashes": {p.name: file_hash(p) for p in files},
              "fits": len(parameters), "held_out_work_prediction_rows": len(predictions),
              "planned_panels": list(SELECTED_PANELS), "estimable_panels": available, "not_estimable_panels": unavailable,
              "max_absolute_dispersion_identity_error": max(abs(r["closure_error"]) for r in components),
              "submission_ready": False, "human_review_complete": False}
    write_json(destination / "manifest.json", result)
    return {k: v for k, v in result.items() if k not in {"inputs", "output_hashes"}}


def run(model, study=OUT, extension_base=BASE):
    if study == OUT:
        if extension_base != BASE or model not in {"azure_replication", "gem31lite"}:
            raise ValueError("Only the planned providers may enter this extension")
    else:
        from .expanded_study import BASE as expanded, effective_plan
        if study != expanded or extension_base != expanded / "extensions/jql_v1" or model not in effective_plan()["active_models"]:
            raise ValueError("Unrecognized expanded study/model")
    import os
    destination = extension_base / model / "explanatory_model"
    destination.mkdir(parents=True, exist_ok=True)
    lock = destination / "RUNNING.lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    try:
        return _run_unlocked(model, study, extension_base)
    finally:
        lock.unlink(missing_ok=True)


def replay_and_verify(model, study=OUT, extension_base=BASE):
    destination = extension_base / model / "explanatory_model"
    before = read_json(destination / "manifest.json")
    run(model, study, extension_base)
    after = read_json(destination / "manifest.json")
    if before["inputs"] != after["inputs"] or before["output_hashes"] != after["output_hashes"]:
        raise ValueError("Explanatory mapping rerun did not reproduce every result byte-for-byte")
    result = {"passed": True, "verified_utc": datetime.now(timezone.utc).isoformat(),
              "manifest_sha256": file_hash(destination / "manifest.json"),
              "unchanged_result_files": len(after["output_hashes"]),
              "fits_recomputed": after["fits"],
              "held_out_work_prediction_rows": after["held_out_work_prediction_rows"],
              "same_input_output_hashes": True, "not_human_scientific_validation": True}
    write_json(destination / "replay_verification.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=("azure_replication", "gem31lite"))
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    print(json.dumps(replay_and_verify(args.model) if args.replay else run(args.model), indent=2))
