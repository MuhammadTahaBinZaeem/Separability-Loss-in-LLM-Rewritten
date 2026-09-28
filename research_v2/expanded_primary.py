"""Explicit corrected-corpus replication of the frozen primary methods."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from threadpoolctl import threadpool_limits

from .analysis import CLASSIFIERS, FAMILIES, PRED_FIELDS, classifier, distance_rows, split_rows
from .corpus import AUTHORS
from .expanded_study import BASE, effective_plan, now, verify
from .features import FoldFeatures
from .inference import holm, paired_uncertainty
from .io import ROOT, file_hash, read_csv, read_json, write_csv, write_json
from .transfer_extension import fingerprints

DESTINATION = BASE / "primary_analysis"


def inputs(model):
    paths = [ROOT / "research_v2/expanded_primary.py", BASE / "PRIMARY_ANALYSIS_PLAN.md"]
    return {**fingerprints(model, BASE, BASE / "extensions/jql_v1"),
            **{p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths}}


def outcome_coverage(originals, rows, conditions):
    index = {r["passage_id"]: r for r in originals}
    cells = defaultdict(list)
    for row in rows:
        source = index[row["passage_id"]]
        cells[source["author_id"], source["work_id"], row["condition"]].append(row)
    result = []
    for author, work in sorted({(r["author_id"], r["work_id"]) for r in originals}):
        for condition in conditions:
            subset = cells[author, work, condition]
            result.append({"author_id": author, "work_id": work, "condition": condition,
                           "expected": sum(r["work_id"] == work and r["author_id"] == author for r in originals),
                           "accounted": len(subset), "pass": sum(r["qc_status"] == "pass" for r in subset),
                           "warning": sum(r["qc_status"] == "warning" for r in subset),
                           "failed": sum(r["qc_status"] == "fail" for r in subset)})
    return result


def check_output_hash(row):
    from .io import digest_text
    # An HTTP block has no generated text/hash; this is an absence, not a rewrite.
    if row["outcome_type"] == "http_content_filter":
        if row["qc_status"] != "fail" or row["rewritten_text"] or row["rewrite_sha256"]:
            raise ValueError("HTTP filtering cannot contain a fabricated rewrite")
    elif row["rewrite_sha256"] != digest_text(row["rewritten_text"]):
        raise ValueError("A primary output hash differs")


def infer(predictions, originals, model, conditions, bootstraps, permutations):
    groups = defaultdict(list)
    for row in predictions:
        groups[row["classifier"], row["feature_set"], row["condition"]].append(row)
    comparisons, sensitivity = [], []
    expected_works = {(r["author_id"], r["work_id"]) for r in originals}
    for name in CLASSIFIERS:
        baseline = {r["passage_id"]: r for r in groups[name, "full", "original"]}
        for condition in conditions:
            paired = [{"passage_id": r["passage_id"], "author_id": r["author_id"], "work_id": r["work_id"],
                       "original_prediction": baseline[r["passage_id"]]["predicted_author"],
                       "rewrite_prediction": r["predicted_author"], "qc_status": r["qc_status"]}
                      for r in groups[name, "full", condition]]
            works = {(r["author_id"], r["work_id"]) for r in paired}
            row = {"model_key": model, "classifier": name, "condition": condition,
                   "estimand": "paired_loss_conditional_on_valid_first_output",
                   "excluded_failed_outputs": len(originals) - len(paired),
                   "status": "estimable" if works == expected_works else "not_estimable_missing_works",
                   "missing_works": json.dumps(sorted(expected_works - works))}
            if works == expected_works:
                row.update(paired_uncertainty(paired, bootstraps, permutations))
            comparisons.append(row)
            selected = [r for r in paired if r["qc_status"] == "pass"]
            all_authors = {r["author_id"] for r in selected} == set(AUTHORS)
            s = {"model_key": model, "classifier": name, "condition": condition,
                 "selection": "warning_free_paired", "paired_rows": len(selected),
                 "excluded_warning_rows": len(paired) - len(selected), "all_authors_present": all_authors,
                 "original_macro_f1": "", "rewrite_macro_f1": "", "macro_f1_loss": ""}
            if all_authors:
                y = [r["author_id"] for r in selected]
                first = float(f1_score(y, [r["original_prediction"] for r in selected], labels=AUTHORS, average="macro", zero_division=0))
                second = float(f1_score(y, [r["rewrite_prediction"] for r in selected], labels=AUTHORS, average="macro", zero_division=0))
                s.update(original_macro_f1=first, rewrite_macro_f1=second, macro_f1_loss=first-second)
            sensitivity.append(s)
    return comparisons, sensitivity


def run(model, bootstraps=5000, permutations=9999):
    plan = effective_plan()
    if model not in plan["active_models"]:
        raise ValueError("Only an active model may enter the expanded analysis")
    if bootstraps != 5000 or permutations != 9999:
        raise ValueError("Production analysis must use the frozen replication counts")
    verify()
    generation = BASE / f"generation/{model}"
    if (generation / "RUNNING.lock").exists() or not read_json(generation / "completion.json")["accounting_complete"]:
        raise ValueError("Wait for complete generation accounting")
    destination = DESTINATION / model
    destination.mkdir(parents=True, exist_ok=True)
    lock = destination / "RUNNING.lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    try:
        return _run(model, plan, destination, bootstraps, permutations)
    finally:
        lock.unlink(missing_ok=True)


def _run(model, plan, destination, bootstraps, permutations):
    original_inputs = inputs(model)
    originals = read_csv(BASE / "corpus/originals.csv")
    source_index = {r["passage_id"]: r for r in originals}
    all_outputs = read_csv(BASE / f"generation/{model}/rewrites.csv")
    mapping = {(r["passage_id"], r["condition"]): r for r in all_outputs}
    expected = {(r["passage_id"], c) for r in originals for c in plan["conditions"]}
    if set(mapping) != expected or len(mapping) != len(all_outputs):
        raise ValueError("Every assignment must have exactly one primary outcome")
    for row in all_outputs:
        if row["source_sha256"] != source_index[row["passage_id"]]["text_sha256"]:
            raise ValueError("A primary source hash differs")
        check_output_hash(row)
    mapping = {k: r for k, r in mapping.items() if r["qc_status"] in {"pass", "warning"}}
    predictions, distances = [], []
    with threadpool_limits(limits=1):
        for omitted in [None, *FAMILIES]:
            feature_set = "full" if omitted is None else f"without_{omitted}"
            for fold in range(3):
                train, test = split_rows(originals, fold)
                features = FoldFeatures(omit_family=omitted).fit([r["text"] for r in train], [r["passage_id"] for r in train])
                write_json(destination / f"folds/{feature_set}_{fold}.json", features.evidence())
                matrix = features.transform([r["text"] for r in train])
                domains = {"original": (features.transform([r["text"] for r in test]), test)}
                for condition in plan["conditions"]:
                    rows = [{**s, **mapping[s["passage_id"], condition]} for s in test if (s["passage_id"], condition) in mapping]
                    if rows:
                        domains[condition] = (features.transform([r["rewritten_text"] for r in rows]), rows)
                for name in CLASSIFIERS:
                    fitted = classifier(name).fit(matrix, [r["author_id"] for r in train])
                    for condition, (test_matrix, rows) in domains.items():
                        for row, label in zip(rows, fitted.predict(test_matrix)):
                            predictions.append({"model_key": model, "classifier": name, "feature_set": feature_set,
                                                "fold": fold, "passage_id": row["passage_id"], "author_id": row["author_id"],
                                                "work_id": row["work_id"], "condition": condition, "predicted_author": str(label),
                                                "qc_status": row.get("qc_status", "source_followup_pending")})
                if omitted is None:
                    distances.extend(distance_rows(fold, model, features, domains))
            print(f"{model}: primary {feature_set}, three held-out-work folds complete", flush=True)
    groups = defaultdict(list)
    for row in predictions:
        groups[row["classifier"], row["feature_set"], row["condition"]].append(row)
    metrics, confusions, per_work = [], [], []
    for (name, feature_set, condition), rows in sorted(groups.items()):
        common = {"model_key": model, "classifier": name, "feature_set": feature_set, "condition": condition}
        for fold in ["pooled", 0, 1, 2]:
            selected = rows if fold == "pooled" else [r for r in rows if r["fold"] == fold]
            if not selected:
                continue
            y, p = [r["author_id"] for r in selected], [r["predicted_author"] for r in selected]
            metrics.append({**common, "fold": fold, "rows": len(selected), "macro_f1": float(f1_score(y, p, labels=AUTHORS, average="macro", zero_division=0)), "accuracy": float(accuracy_score(y, p))})
        if feature_set != "full":
            continue
        matrix = confusion_matrix([r["author_id"] for r in rows], [r["predicted_author"] for r in rows], labels=AUTHORS)
        for i, author in enumerate(AUTHORS):
            for j, predicted in enumerate(AUTHORS):
                confusions.append({**common, "true_author": author, "predicted_author": predicted, "count": int(matrix[i, j])})
        for author, work in sorted({(r["author_id"], r["work_id"]) for r in rows}):
            subset = [r for r in rows if (r["author_id"], r["work_id"]) == (author, work)]
            per_work.append({**common, "author_id": author, "work_id": work, "rows": len(subset),
                             "correct_attribution_rate": sum(r["predicted_author"] == author for r in subset) / len(subset)})
    comparisons, sensitivity = infer(predictions, originals, model, plan["conditions"], bootstraps, permutations)
    tables = {"predictions.csv": predictions, "distances.csv": distances, "metrics.csv": metrics,
              "confusions.csv": confusions, "per_work.csv": per_work,
              "primary_comparisons.csv": comparisons, "warning_sensitivity.csv": sensitivity,
              "outcome_coverage.csv": outcome_coverage(originals, all_outputs, plan["conditions"])}
    for name, rows in tables.items():
        fields = list(dict.fromkeys(k for row in rows for k in row))
        write_csv(destination / name, rows, fields)
    if inputs(model) != original_inputs:
        raise ValueError("Inputs changed during the primary-method analysis")
    hashes = {p.relative_to(destination).as_posix(): file_hash(p) for p in sorted(destination.rglob("*"))
              if p.is_file() and (p.suffix == ".csv" or p.parent.name == "folds")}
    result = {"completed_utc": now(), "model_key": model, "inputs": original_inputs, "output_hashes": hashes,
              "prediction_rows": len(predictions), "comparison_count": len(comparisons), "bootstraps": bootstraps,
              "permutations": permutations, "all_six_ablations_included": True,
              "multiplicity_adjustment": "pending across all six arms in finalize",
              "review_complete": False, "submission_ready": False}
    write_json(destination / "manifest.json", result)
    return result


def replay(model):
    destination = DESTINATION / model
    before = read_json(destination / "manifest.json")
    if before["inputs"] != inputs(model):
        raise ValueError("Primary inputs changed; rerun before replay")
    after = run(model)
    if before["inputs"] != after["inputs"] or before["output_hashes"] != after["output_hashes"]:
        raise ValueError("Primary replay differed")
    result = {"passed": True, "verified_utc": now(), "manifest_sha256": file_hash(destination / "manifest.json"),
              "unchanged_result_files": len(after["output_hashes"]), "review_complete": False}
    write_json(destination / "replay_verification.json", result)
    return result


def finalize():
    models = effective_plan()["active_models"]
    missing = [m for m in models if not (DESTINATION / m / "manifest.json").exists()]
    if missing:
        return {"complete": False, "missing_models": missing}
    rows, hashes = [], {}
    for model in models:
        folder = DESTINATION / model
        manifest = read_json(folder / "manifest.json")
        if manifest["inputs"] != inputs(model):
            raise ValueError(f"Stale primary analysis: {model}")
        for path, expected in manifest["output_hashes"].items():
            if file_hash(folder / path) != expected:
                raise ValueError("Primary result changed")
        receipt = read_json(folder / "replay_verification.json")
        if not receipt["passed"] or receipt["manifest_sha256"] != file_hash(folder / "manifest.json"):
            raise ValueError("A current successful replay is required")
        hashes[model] = file_hash(folder / "manifest.json")
        rows.extend(read_csv(folder / "primary_comparisons.csv"))
    valid = [r for r in rows if r["status"] == "estimable"]
    family = len(models) * len(CLASSIFIERS) * len(effective_plan()["conditions"])
    if len(rows) != family:
        raise ValueError("Missing planned comparisons")
    for row, corrected in zip(valid, holm([float(r["p_work_swap_two_sided"]) for r in valid], family_size=family)):
        row["p_holm"] = corrected
    fields = list(dict.fromkeys(k for row in rows for k in row))
    write_csv(DESTINATION / "all_models_comparisons.csv", rows, fields)
    result = {"complete": True, "planned_family_size": family, "estimable_tests": len(valid),
              "source_manifests": hashes, "table_sha256": file_hash(DESTINATION / "all_models_comparisons.csv"),
              "analysis_scope": "exploratory; session/API workflow differences prevent a model-only causal interpretation",
              "review_complete": False, "submission_ready": False}
    write_json(DESTINATION / "status.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "replay", "finalize"))
    parser.add_argument("--models", nargs="+", default=[])
    args = parser.parse_args()
    if args.action == "finalize":
        results = [finalize()]
    else:
        if not args.models:
            parser.error("Provide models")
        results = [(run if args.action == "run" else replay)(m) for m in args.models]
    print(json.dumps([{k: v for k, v in r.items() if k not in {"inputs", "output_hashes"}} for r in results], indent=2))


if __name__ == "__main__":
    main()
