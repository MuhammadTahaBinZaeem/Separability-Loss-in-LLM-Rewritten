"""Run semantic-risk sensitivity analysis for Step 15 transfer results.

Filters:
- all_rows: no semantic-fidelity exclusion;
- exclude_unusable: excludes audit rows marked overall_usable_yes_no == no;
- exclude_any_semantic_issue: excludes audit rows with any_semantic_issue_flag == 1.

Only annotated rewrite rows in the 108-item E4 sample can be excluded. Unsampled
rows remain in the analysis. Training remains original-only, matching Step 15.
"""
from __future__ import annotations

import csv, hashlib, importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MODEL_META = ROOT / "data/modeling/modeling_metadata.csv"
X_RAW = ROOT / "data/modeling/X_stylometric_raw.csv"
Y_LABELS = ROOT / "data/modeling/y_author_labels.csv"
FEATURES = ROOT / "metadata/modeling_feature_columns.csv"
AUDIT_KEY = ROOT / "data/audit/semantic_fidelity_key.csv"
AUDIT_FLAGS = ROOT / "data/audit/semantic_fidelity_annotation_flags.csv"
META = ROOT / "metadata"
LOGS = ROOT / "logs"
OUT = META / "semantic_risk_sensitivity_transfer_summary.csv"
DETAILS = META / "semantic_risk_sensitivity_excluded_rows.csv"
MANIFEST = META / "semantic_risk_sensitivity_manifest.csv"
REPORT = LOGS / "semantic_risk_sensitivity_report.md"

spec = importlib.util.spec_from_file_location("step15", ROOT / "scripts/16_run_original_to_rewritten_degradation.py")
step15 = importlib.util.module_from_spec(spec); spec.loader.exec_module(step15)  # type: ignore[union-attr]

MODELS = ["nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"]
CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
SPLITS = ["validation", "test"]
FILTERS = ["all_rows", "exclude_unusable", "exclude_any_semantic_issue"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def audit_sets() -> tuple[set[str], set[str], list[dict[str, Any]]]:
    key = {r["audit_id"]: r for r in read_csv(AUDIT_KEY)}
    flags = read_csv(AUDIT_FLAGS)
    unusable, issue = set(), set()
    detail_rows = []
    for r in flags:
        k = key[r["audit_id"]]
        text_id = k["text_id"]
        if r["overall_usable_yes_no"] == "no": unusable.add(text_id)
        if r["any_semantic_issue_flag"] == "1": issue.add(text_id)
        if r["overall_usable_yes_no"] == "no" or r["any_semantic_issue_flag"] == "1":
            detail_rows.append({
                "audit_id": r["audit_id"], "text_id": text_id, "condition": k["condition"],
                "author_id": k["author_id"], "work_id": k["work_id"],
                "overall_usable_yes_no": r["overall_usable_yes_no"],
                "any_semantic_issue_flag": r["any_semantic_issue_flag"],
                "semantic_issue_level": r["semantic_issue_level"],
                "added_facts_0_1": r["added_facts_0_1"],
                "omitted_facts_0_1": r["omitted_facts_0_1"],
                "tone_drift_0_2": r["tone_drift_0_2"],
                "meaning_preservation_1_5": r["meaning_preservation_1_5"],
            })
    return unusable, issue, detail_rows


def keep_eval(text_id: str, filter_name: str, unusable: set[str], issue: set[str]) -> bool:
    if filter_name == "all_rows": return True
    if filter_name == "exclude_unusable": return text_id not in unusable
    if filter_name == "exclude_any_semantic_issue": return text_id not in issue
    raise ValueError(filter_name)


def main() -> int:
    meta = read_csv(MODEL_META); x_rows = read_csv(X_RAW); y_rows = read_csv(Y_LABELS)
    feature_cols = [r["feature"] for r in read_csv(FEATURES)]
    by_x = {r["text_id"]: r for r in x_rows}; by_y = {r["text_id"]: r for r in y_rows}
    unusable, issue, detail_rows = audit_sets()

    dataset = []
    for m in meta:
        tid = m["text_id"]
        dataset.append({"meta": m, "x": [float(by_x[tid][c]) for c in feature_cols], "y": by_y[tid]["author_id"]})

    train = [r for r in dataset if r["meta"]["split"] == "train" and r["meta"]["condition"] == "original"]
    means, stds = step15.zscore_fit([r["x"] for r in train])
    xtrain = step15.zscore_apply([r["x"] for r in train], means, stds)
    ytrain = [r["y"] for r in train]
    fitted = {
        "nearest_centroid": step15.fit_nearest_centroid(xtrain, ytrain),
        "diagonal_gaussian_nb": step15.fit_gaussian_nb(xtrain, ytrain),
        "linear_discriminant_shrinkage": step15.fit_lda_shrinkage(xtrain, ytrain),
    }
    predictors = {
        "nearest_centroid": step15.predict_nearest_centroid,
        "diagonal_gaussian_nb": step15.predict_gaussian_nb,
        "linear_discriminant_shrinkage": step15.predict_lda_shrinkage,
    }

    metric_rows = []
    for filter_name in FILTERS:
        for model_name in MODELS:
            for split in SPLITS:
                base_metrics = None
                temp = []
                for condition in CONDITIONS:
                    subset = [r for r in dataset if r["meta"]["split"] == split and r["meta"]["condition"] == condition and keep_eval(r["meta"]["text_id"], filter_name, unusable, issue)]
                    xeval = step15.zscore_apply([r["x"] for r in subset], means, stds)
                    pred = predictors[model_name](fitted[model_name], xeval) if subset else []
                    metrics = step15.evaluate([r["y"] for r in subset], pred) if subset else {"accuracy": 0.0, "macro_f1": 0.0, "weighted_f1": 0.0}
                    if condition == "original": base_metrics = metrics
                    temp.append({
                        "sensitivity_filter": filter_name, "model": model_name, "split": split,
                        "condition": condition, "rows": len(subset),
                        "excluded_rows": 54 - len(subset) if condition != "original" else 0,
                        **metrics,
                    })
                assert base_metrics is not None
                for row in temp:
                    row["accuracy_loss_vs_original"] = round(float(base_metrics["accuracy"]) - float(row["accuracy"]), 6)
                    row["macro_f1_loss_vs_original"] = round(float(base_metrics["macro_f1"]) - float(row["macro_f1"]), 6)
                    row["weighted_f1_loss_vs_original"] = round(float(base_metrics["weighted_f1"]) - float(row["weighted_f1"]), 6)
                    metric_rows.append(row)

    write_csv(OUT, metric_rows, ["sensitivity_filter", "model", "split", "condition", "rows", "excluded_rows", "accuracy", "macro_f1", "weighted_f1", "accuracy_loss_vs_original", "macro_f1_loss_vs_original", "weighted_f1_loss_vs_original"])
    write_csv(DETAILS, detail_rows, ["audit_id", "text_id", "condition", "author_id", "work_id", "overall_usable_yes_no", "any_semantic_issue_flag", "semantic_issue_level", "added_facts_0_1", "omitted_facts_0_1", "tone_drift_0_2", "meaning_preservation_1_5"])
    artifacts = [OUT, DETAILS]
    write_csv(MANIFEST, [{"artifact": p.stem, "path": p.relative_to(ROOT).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha_file(p)} for p in artifacts], ["artifact", "path", "size_bytes", "sha256"])

    focus = [r for r in metric_rows if r["split"] == "test" and r["model"] == "nearest_centroid" and r["condition"] != "original"]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Semantic-Risk Sensitivity Report\n\n"
        f"- unusable audit text IDs excluded in exclude_unusable: {len(unusable)}\n"
        f"- semantic-issue audit text IDs excluded in exclude_any_semantic_issue: {len(issue)}\n\n"
        "## Nearest-centroid test focus\n\n" + "".join(
            f"- {r['sensitivity_filter']} / {r['condition']}: rows={r['rows']}, excluded={r['excluded_rows']}, macro_f1={r['macro_f1']}, loss={r['macro_f1_loss_vs_original']}\n"
            for r in focus
        ),
        encoding="utf-8",
    )
    print(f"Semantic-risk sensitivity complete: rows={len(metric_rows)}, excluded issue rows={len(issue)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
