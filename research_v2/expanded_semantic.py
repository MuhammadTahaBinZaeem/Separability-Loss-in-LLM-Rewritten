"""Review-gated descriptive semantic sensitivity for expanded primary predictions."""
from __future__ import annotations

import json
from collections import defaultdict

from sklearn.metrics import f1_score

from .corpus import AUTHORS
from .expanded_primary import DESTINATION, inputs
from .expanded_review import semantic_validation
from .expanded_study import BASE, effective_plan, now
from .io import file_hash, read_csv, read_json, write_csv, write_json


def summarize(predictions, flags):
    lookup = {(r["model_key"], r["passage_id"], r["condition"]): r for r in flags}
    if len(lookup) != len(flags):
        raise ValueError("Duplicate semantic flags")
    original = {(r["model_key"], r["classifier"], r["passage_id"]): r for r in predictions
                if r["feature_set"] == "full" and r["condition"] == "original"}
    groups = defaultdict(list)
    for row in predictions:
        if row["feature_set"] == "full" and (row["model_key"], row["passage_id"], row["condition"]) in lookup:
            groups[row["model_key"], row["classifier"], row["condition"]].append(row)
    result = []
    for (model, name, condition), rows in sorted(groups.items()):
        for selection in ("all_audited_pairs", "audited_pairs_without_either_reviewer_risk"):
            chosen = rows if selection == "all_audited_pairs" else [r for r in rows if str(lookup[model, r["passage_id"], condition]["risk_union"]) == "0"]
            all_authors = {r["author_id"] for r in chosen} == set(AUTHORS)
            record = {"model_key": model, "classifier": name, "condition": condition, "selection": selection,
                      "audited_pairs": len(rows), "paired_rows": len(chosen), "excluded_risk_pairs": len(rows)-len(chosen),
                      "status": "estimable_descriptive" if all_authors else "not_estimable_missing_authors",
                      "original_macro_f1": "", "rewrite_macro_f1": "", "macro_f1_loss": ""}
            if all_authors:
                truth = [r["author_id"] for r in chosen]
                first = [original[model, name, r["passage_id"]]["predicted_author"] for r in chosen]
                second = [r["predicted_author"] for r in chosen]
                a = float(f1_score(truth, first, labels=AUTHORS, average="macro", zero_division=0))
                b = float(f1_score(truth, second, labels=AUTHORS, average="macro", zero_division=0))
                record.update(original_macro_f1=a, rewrite_macro_f1=b, macro_f1_loss=a-b)
            result.append(record)
    return result


def run():
    destination = BASE / "semantic_sensitivity"
    validation = semantic_validation()
    if not validation["complete"]:
        result = {"complete": False, "stage": "awaiting_validated_reviews", "review_stage": validation["stage"]}
        write_json(destination / "status.json", result)
        return result
    models = effective_plan()["active_models"]
    predictions, manifests = [], {}
    for model in models:
        folder = DESTINATION / model
        manifest = read_json(folder / "manifest.json")
        replay = read_json(folder / "replay_verification.json")
        if manifest["inputs"] != inputs(model) or not replay["passed"] or replay["manifest_sha256"] != file_hash(folder / "manifest.json"):
            raise ValueError("Current replay-verified primary evidence required")
        if file_hash(folder / "predictions.csv") != manifest["output_hashes"]["predictions.csv"]:
            raise ValueError("Primary predictions changed")
        manifests[model] = file_hash(folder / "manifest.json")
        predictions.extend(read_csv(folder / "predictions.csv"))
    path = BASE / "annotations/verified_flags.csv"
    flags = read_csv(path)
    results = summarize(predictions, flags)
    if len(results) != len(models) * 3 * 3 * 2:
        raise ValueError("Audited primary prediction coverage is incomplete")
    write_csv(destination / "comparisons.csv", results)
    result = {"complete": True, "completed_utc": now(), "comparison_rows": len(results),
              "flags_sha256": file_hash(path), "validation_sha256": file_hash(BASE / "annotations/validation.json"),
              "primary_manifest_sha256": manifests, "comparison_sha256": file_hash(destination / "comparisons.csv"),
              "scope": "Descriptive paired audited-subset sensitivity only; unreviewed pairs are not certified clean.",
              "submission_ready": False}
    write_json(destination / "status.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
