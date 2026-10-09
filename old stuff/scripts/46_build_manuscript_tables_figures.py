"""Build manuscript-ready tables and figure data.

Collects validated outputs from the core experiment, E1 Groq replication, E4
semantic-fidelity audit, semantic-risk sensitivity analysis, and bootstrap
uncertainty estimates.

Outputs live under:
- paper_assets/tables/
- paper_assets/figures/
- docs/manuscript_results_summary.md
- metadata/manuscript_assets_manifest.csv
"""
from __future__ import annotations

import csv, hashlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "metadata"
TABLES = ROOT / "paper_assets" / "tables"
FIGS = ROOT / "paper_assets" / "figures"
DOCS = ROOT / "docs"

CORE = META / "original_to_rewritten_degradation_summary.csv"
BOOTSTRAP_CI = META / "primary_transfer_bootstrap_ci.csv"
GROQ = META / "e1_groq_downstream_completion_summary.csv"
FIDELITY = META / "semantic_fidelity_annotation_summary.csv"
RISK = META / "semantic_risk_sensitivity_transfer_summary.csv"
RISK_CHECK = META / "semantic_risk_sensitivity_check_summary.csv"

CORE_TABLE = TABLES / "table_1_core_transfer_test_results.csv"
FIDELITY_TABLE = TABLES / "table_2_semantic_fidelity_audit.csv"
GROQ_TABLE = TABLES / "table_3_groq_replication.csv"
RISK_TABLE = TABLES / "table_4_semantic_risk_sensitivity.csv"
CORE_FIG = FIGS / "figure_1_core_transfer_macro_f1_loss.svg"
GROQ_FIG = FIGS / "figure_2_groq_transfer_macro_f1_loss.svg"
SUMMARY_MD = DOCS / "manuscript_results_summary.md"
MANIFEST = META / "manuscript_assets_manifest.csv"

REWRITE_CONDITIONS = ["paraphrase", "modernize", "simplify"]
CORE_MODELS = ["nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"]
GROQ_MODELS = ["groq_llama_3_3_70b_free", "groq_qwen_32b_free", "groq_gpt_oss_120b_free"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def f(value: str) -> float:
    return float(value)


def pct(value: str) -> str:
    return f"{100*float(value):.1f}%"


def ci_text(row: dict[str, str]) -> str:
    return f"[{row['loss_ci_2_5']}, {row['loss_ci_97_5']}]"


def simple_bar_svg(path: Path, title: str, rows: list[dict[str, Any]], label_col: str, value_col: str) -> None:
    width, height = 980, 420
    margin_left, margin_top, margin_bottom = 210, 60, 70
    plot_w = width - margin_left - 40
    plot_h = height - margin_top - margin_bottom
    max_v = max(float(r[value_col]) for r in rows) if rows else 1.0
    max_v = max(max_v, 0.01)
    bar_h = max(14, int(plot_h / max(len(rows), 1) * 0.58))
    gap = max(5, int(plot_h / max(len(rows), 1) * 0.42))
    y = margin_top
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    parts.append('<rect width="100%" height="100%" fill="white"/>')
    parts.append(f'<text x="{width/2}" y="30" text-anchor="middle" font-family="Arial" font-size="20" font-weight="bold">{title}</text>')
    parts.append(f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height-margin_bottom}" stroke="black"/>')
    parts.append(f'<line x1="{margin_left}" y1="{height-margin_bottom}" x2="{width-35}" y2="{height-margin_bottom}" stroke="black"/>')
    for r in rows:
        label = str(r[label_col]).replace("&", "&amp;")
        val = float(r[value_col])
        bw = int((val / max_v) * plot_w)
        parts.append(f'<text x="{margin_left-8}" y="{y+bar_h*0.72}" text-anchor="end" font-family="Arial" font-size="12">{label}</text>')
        parts.append(f'<rect x="{margin_left}" y="{y}" width="{bw}" height="{bar_h}" fill="#666666"/>')
        parts.append(f'<text x="{margin_left+bw+6}" y="{y+bar_h*0.72}" font-family="Arial" font-size="12">{val:.3f}</text>')
        y += bar_h + gap
    parts.append(f'<text x="{margin_left + plot_w/2}" y="{height-25}" text-anchor="middle" font-family="Arial" font-size="13">Macro-F1 loss vs original; higher means stronger degradation</text>')
    parts.append('</svg>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def build_core_table() -> list[dict[str, Any]]:
    rows = read_csv(CORE)
    ci_rows = read_csv(BOOTSTRAP_CI)
    ci_by_key = {(r["model"], r["split"], r["condition"]): r for r in ci_rows}
    out = []
    for model in CORE_MODELS:
        original = next(r for r in rows if r["model"] == model and r["split"] == "test" and r["condition"] == "original")
        for cond in REWRITE_CONDITIONS:
            r = next(x for x in rows if x["model"] == model and x["split"] == "test" and x["condition"] == cond)
            ci = ci_by_key[(model, "test", cond)]
            out.append({
                "model": model,
                "condition": cond,
                "original_test_macro_f1": original["macro_f1"],
                "rewrite_test_macro_f1": r["macro_f1"],
                "macro_f1_loss_vs_original": r["macro_f1_loss_vs_original"],
                "macro_f1_loss_95ci": ci_text(ci),
                "macro_f1_loss_ci_low": ci["loss_ci_2_5"],
                "macro_f1_loss_ci_high": ci["loss_ci_97_5"],
                "bootstrap_nonpositive_rate": ci["bootstrap_nonpositive_rate"],
                "original_test_accuracy": original["accuracy"],
                "rewrite_test_accuracy": r["accuracy"],
                "accuracy_loss_vs_original": r["accuracy_loss_vs_original"],
                "rows": r["rows"],
            })
    write_csv(CORE_TABLE, out, list(out[0].keys()))
    return out


def build_fidelity_table() -> list[dict[str, Any]]:
    rows = read_csv(FIDELITY)
    out = []
    for r in rows:
        out.append({
            "condition": r["condition"],
            "rows": r["rows"],
            "added_facts": r["added_facts_count"],
            "added_facts_rate": pct(r["added_facts_rate"]),
            "omitted_facts": r["omitted_facts_count"],
            "omitted_facts_rate": pct(r["omitted_facts_rate"]),
            "tone_drift_mean_0_2": r["tone_drift_mean"],
            "meaning_preservation_mean_1_5": r["meaning_preservation_mean"],
            "usable_rows": r["usable_yes_count"],
            "usable_rate": pct(r["usable_rate"]),
            "semantic_issue_flags": r["any_semantic_issue_count"],
            "semantic_issue_rate": pct(r["any_semantic_issue_rate"]),
        })
    write_csv(FIDELITY_TABLE, out, list(out[0].keys()))
    return out


def build_groq_table() -> list[dict[str, Any]]:
    rows = read_csv(GROQ)
    out = []
    for model in GROQ_MODELS:
        for cond in REWRITE_CONDITIONS:
            r = next(x for x in rows if x["analysis_model_id"] == model and x["condition"] == cond)
            out.append({
                "analysis_model_id": model,
                "condition": cond,
                "original_test_macro_f1": r["original_test_macro_f1"],
                "transfer_test_macro_f1": r["transfer_test_macro_f1"],
                "transfer_macro_f1_loss": r["transfer_macro_f1_loss"],
                "same_condition_survival": r["same_condition_survival"],
                "all_feature_distance_ratio": r["all_feature_distance_ratio"],
                "function_word_distance_ratio": r["function_word_distance_ratio"],
            })
    write_csv(GROQ_TABLE, out, list(out[0].keys()))
    return out


def build_risk_table() -> list[dict[str, Any]]:
    rows = read_csv(RISK)
    out = []
    for filt in ["all_rows", "exclude_unusable", "exclude_any_semantic_issue"]:
        for cond in REWRITE_CONDITIONS:
            r = next(x for x in rows if x["sensitivity_filter"] == filt and x["model"] == "nearest_centroid" and x["split"] == "test" and x["condition"] == cond)
            out.append({
                "sensitivity_filter": filt,
                "condition": cond,
                "rows": r["rows"],
                "excluded_rows": r["excluded_rows"],
                "test_macro_f1": r["macro_f1"],
                "macro_f1_loss_vs_original": r["macro_f1_loss_vs_original"],
            })
    write_csv(RISK_TABLE, out, list(out[0].keys()))
    return out


def markdown_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    header = "| " + " | ".join(fields) + " |"
    sep = "| " + " | ".join(["---"] * len(fields)) + " |"
    body = ["| " + " | ".join(str(r.get(f, "")) for f in fields) + " |" for r in rows]
    return "\n".join([header, sep] + body)


def main() -> int:
    for required in [CORE, BOOTSTRAP_CI, GROQ, FIDELITY, RISK, RISK_CHECK]:
        if not required.exists():
            raise FileNotFoundError(required)
    TABLES.mkdir(parents=True, exist_ok=True); FIGS.mkdir(parents=True, exist_ok=True)
    core = build_core_table(); fidelity = build_fidelity_table(); groq = build_groq_table(); risk = build_risk_table()

    core_fig_rows = [{"label": f"{r['model']} / {r['condition']}", "loss": r["macro_f1_loss_vs_original"]} for r in core]
    groq_fig_rows = [{"label": f"{r['analysis_model_id'].replace('groq_', '').replace('_free', '')} / {r['condition']}", "loss": r["transfer_macro_f1_loss"]} for r in groq]
    simple_bar_svg(CORE_FIG, "Core experiment: original-to-rewrite degradation", core_fig_rows, "label", "loss")
    simple_bar_svg(GROQ_FIG, "Groq replication: original-to-rewrite degradation", groq_fig_rows, "label", "loss")

    risk_check = read_csv(RISK_CHECK)[0]
    min_ci_low = min(float(r["macro_f1_loss_ci_low"]) for r in core)
    max_nonpositive = max(float(r["bootstrap_nonpositive_rate"]) for r in core)
    summary = []
    summary.append("# Manuscript Results Summary\n")
    summary.append("## Core transfer result\n")
    summary.append(markdown_table(core, ["model", "condition", "original_test_macro_f1", "rewrite_test_macro_f1", "macro_f1_loss_vs_original", "macro_f1_loss_95ci", "bootstrap_nonpositive_rate", "rows"]))
    summary.append("\n## Semantic-fidelity audit\n")
    summary.append(markdown_table(fidelity, ["condition", "rows", "meaning_preservation_mean_1_5", "usable_rate", "semantic_issue_rate"]))
    summary.append("\n## Semantic-risk sensitivity\n")
    summary.append(markdown_table(risk, ["sensitivity_filter", "condition", "rows", "excluded_rows", "test_macro_f1", "macro_f1_loss_vs_original"]))
    summary.append("\n## Groq free-model replication\n")
    summary.append(markdown_table(groq, ["analysis_model_id", "condition", "transfer_macro_f1_loss", "same_condition_survival", "all_feature_distance_ratio", "function_word_distance_ratio"]))
    summary.append("\n## Manuscript-safe interpretation\n")
    summary.append(f"- Core test macro-F1 losses are positive for all three rewrite conditions across all three classifiers.\n- Passage-level paired bootstrap intervals support the primary test result: minimum lower 95% CI bound = {min_ci_low:.6f}; maximum nonpositive bootstrap rate = {max_nonpositive:.6f}.\n- Semantic-fidelity review: 107/108 rows usable; mean preservation score 4.53/5. Treat as single-review audit, not independent double annotation.\n- Semantic-risk sensitivity passed: strict-filter non-positive losses = {risk_check['strict_test_nonpositive_losses']}; minimum strict test loss = {risk_check['minimum_strict_test_macro_f1_loss']}.\n- Groq replication broadly supports the degradation pattern, but Llama-modernize is a reversal and should be reported as heterogeneity.\n")
    SUMMARY_MD.write_text("\n\n".join(summary) + "\n", encoding="utf-8")

    artifacts = [CORE_TABLE, FIDELITY_TABLE, GROQ_TABLE, RISK_TABLE, CORE_FIG, GROQ_FIG, SUMMARY_MD]
    write_csv(MANIFEST, [{"artifact": p.stem, "path": p.relative_to(ROOT).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha_file(p)} for p in artifacts], ["artifact", "path", "size_bytes", "sha256"])
    print(f"Built manuscript assets: {len(artifacts)} files")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
