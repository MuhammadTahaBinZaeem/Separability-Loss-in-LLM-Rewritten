"""
Step 19: generate statistical summaries, paper-ready tables, and SVG figures.

Run from repository root after Step 18:

    python scripts/20_generate_statistical_tables_figures.py

Outputs are written to metadata/, figures/, and logs/.
"""

from __future__ import annotations

import csv
import hashlib
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "metadata"
RESULTS = ROOT / "data" / "results"
FIGURES = ROOT / "figures"
LOGS = ROOT / "logs"

BASELINE_METRICS = META / "original_author_baseline_metrics.csv"
TRANSFER_METRICS = META / "original_to_rewritten_metrics.csv"
TRANSFER_DEG = META / "original_to_rewritten_degradation_summary.csv"
TRANSFER_PREDS = RESULTS / "original_to_rewritten_predictions.csv"
SURVIVAL_METRICS = META / "rewritten_condition_author_metrics.csv"
SURVIVAL_SUMMARY = META / "rewritten_condition_author_survival_summary.csv"
DIST_SUMMARY = META / "inter_author_distance_summary.csv"
FAMILY_VULN = META / "feature_family_vulnerability_summary.csv"
FAMILY_DIST = META / "feature_family_distance_contraction.csv"

TABLE_BASELINE = META / "paper_table_original_baseline.csv"
TABLE_TRANSFER = META / "paper_table_transfer_degradation.csv"
TABLE_SURVIVAL = META / "paper_table_same_condition_survival.csv"
TABLE_DISTANCE = META / "paper_table_distance_contraction.csv"
TABLE_FAMILY = META / "paper_table_feature_family_vulnerability.csv"
BOOTSTRAP = META / "statistical_tests_bootstrap_macro_f1_loss.csv"
MANIFEST = META / "step19_tables_figures_manifest.csv"
REPORT = LOGS / "step_19_tables_figures_report.md"

FIG_MACRO = FIGURES / "fig_step19_macro_f1_degradation.svg"
FIG_DISTANCE = FIGURES / "fig_step19_distance_contraction.svg"
FIG_FAMILY = FIGURES / "fig_step19_feature_family_losses.svg"

AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
REWRITE_CONDITIONS = ["paraphrase", "modernize", "simplify"]
CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
MODELS = ["nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"]
BOOT_N = 2000
RNG_SEED = 20260601


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def fnum(x: str | float | int) -> float:
    return float(x)


def precision_recall_f1(y_true: list[str], y_pred: list[str], label: str) -> tuple[float, float, float, int]:
    tp = sum(1 for a, b in zip(y_true, y_pred) if a == label and b == label)
    fp = sum(1 for a, b in zip(y_true, y_pred) if a != label and b == label)
    fn = sum(1 for a, b in zip(y_true, y_pred) if a == label and b != label)
    support = sum(1 for a in y_true if a == label)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1, support


def macro_f1(y_true: list[str], y_pred: list[str]) -> float:
    return sum(precision_recall_f1(y_true, y_pred, label)[2] for label in AUTHORS) / len(AUTHORS)


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * p
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return values[int(k)]
    return values[lo] * (hi - k) + values[hi] * (k - lo)


def bootstrap_loss_rows(pred_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    rng = random.Random(RNG_SEED)
    out = []
    by_key: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in pred_rows:
        by_key[(row["model"], row["split"], row["condition"])].append(row)

    for model in MODELS:
        for split in ["validation", "test"]:
            original_rows = by_key[(model, split, "original")]
            by_pid_original = {row["passage_id"]: row for row in original_rows}
            for condition in REWRITE_CONDITIONS:
                cond_rows = by_key[(model, split, condition)]
                by_pid_cond = {row["passage_id"]: row for row in cond_rows}
                common_pids = sorted(set(by_pid_original) & set(by_pid_cond))
                if len(common_pids) != 54:
                    raise ValueError(f"Expected 54 paired passage IDs for {model}/{split}/{condition}, found {len(common_pids)}")
                orig_true = [by_pid_original[pid]["true_author"] for pid in common_pids]
                orig_pred = [by_pid_original[pid]["predicted_author"] for pid in common_pids]
                cond_true = [by_pid_cond[pid]["true_author"] for pid in common_pids]
                cond_pred = [by_pid_cond[pid]["predicted_author"] for pid in common_pids]
                observed = macro_f1(orig_true, orig_pred) - macro_f1(cond_true, cond_pred)
                boot = []
                for _ in range(BOOT_N):
                    idxs = [rng.randrange(len(common_pids)) for _ in common_pids]
                    ot = [orig_true[i] for i in idxs]
                    op = [orig_pred[i] for i in idxs]
                    ct = [cond_true[i] for i in idxs]
                    cp = [cond_pred[i] for i in idxs]
                    boot.append(macro_f1(ot, op) - macro_f1(ct, cp))
                out.append({
                    "model": model,
                    "split": split,
                    "condition": condition,
                    "paired_passages": len(common_pids),
                    "observed_macro_f1_loss": round(observed, 9),
                    "ci_low_95": round(percentile(boot, 0.025), 9),
                    "ci_high_95": round(percentile(boot, 0.975), 9),
                    "p_loss_le_zero_bootstrap": round(sum(1 for x in boot if x <= 0) / len(boot), 9),
                    "bootstrap_iterations": BOOT_N,
                    "rng_seed": RNG_SEED,
                })
    return out


def svg_bar_chart(path: Path, title: str, labels: list[str], values: list[float], ylabel: str) -> None:
    width, height = 900, 520
    margin_left, margin_right, margin_top, margin_bottom = 90, 40, 70, 100
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    max_v = max(values + [0.001])
    if max_v < 0:
        max_v = 1.0
    bar_gap = 18
    bar_w = (plot_w - bar_gap * (len(values) - 1)) / len(values)
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    svg.append('<rect width="100%" height="100%" fill="white"/>')
    svg.append(f'<text x="{width/2}" y="35" text-anchor="middle" font-family="Arial" font-size="22" font-weight="bold">{title}</text>')
    svg.append(f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" stroke="black"/>')
    svg.append(f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" stroke="black"/>')
    for i in range(6):
        y = margin_top + plot_h - (plot_h * i / 5)
        val = max_v * i / 5
        svg.append(f'<line x1="{margin_left-5}" y1="{y}" x2="{margin_left}" y2="{y}" stroke="black"/>')
        svg.append(f'<text x="{margin_left-10}" y="{y+4}" text-anchor="end" font-family="Arial" font-size="12">{val:.2f}</text>')
    for i, (label, value) in enumerate(zip(labels, values)):
        x = margin_left + i * (bar_w + bar_gap)
        h = plot_h * value / max_v if max_v else 0
        y = margin_top + plot_h - h
        svg.append(f'<rect x="{x}" y="{y}" width="{bar_w}" height="{h}" fill="#7aa6c2" stroke="black"/>')
        svg.append(f'<text x="{x + bar_w/2}" y="{margin_top + plot_h + 22}" text-anchor="middle" font-family="Arial" font-size="12">{label}</text>')
        svg.append(f'<text x="{x + bar_w/2}" y="{y-6}" text-anchor="middle" font-family="Arial" font-size="12">{value:.3f}</text>')
    svg.append(f'<text x="25" y="{margin_top + plot_h/2}" text-anchor="middle" font-family="Arial" font-size="14" transform="rotate(-90 25 {margin_top + plot_h/2})">{ylabel}</text>')
    svg.append('</svg>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(svg), encoding="utf-8")


def main() -> int:
    inputs = [BASELINE_METRICS, TRANSFER_METRICS, TRANSFER_DEG, TRANSFER_PREDS, SURVIVAL_METRICS, SURVIVAL_SUMMARY, DIST_SUMMARY, FAMILY_VULN, FAMILY_DIST]
    missing = [p for p in inputs if not p.exists()]
    if missing:
        for p in missing:
            print(f"Missing input: {p.relative_to(ROOT)}")
        return 1

    baseline_rows = read_csv(BASELINE_METRICS)
    transfer_metrics = read_csv(TRANSFER_METRICS)
    transfer_deg = read_csv(TRANSFER_DEG)
    transfer_preds = read_csv(TRANSFER_PREDS)
    survival_metrics = read_csv(SURVIVAL_METRICS)
    survival_summary = read_csv(SURVIVAL_SUMMARY)
    distance_summary = read_csv(DIST_SUMMARY)
    family_vuln = read_csv(FAMILY_VULN)
    family_dist = read_csv(FAMILY_DIST)

    baseline_table = sorted(baseline_rows, key=lambda r: (r["model"], r["split"]))
    write_csv(TABLE_BASELINE, baseline_table, ["model", "split", "accuracy", "macro_f1", "weighted_f1", "rows"])

    transfer_table = sorted(transfer_deg, key=lambda r: (r["model"], r["split"], CONDITIONS.index(r["condition"])))
    write_csv(TABLE_TRANSFER, transfer_table, ["model", "split", "condition", "baseline_condition", "accuracy", "macro_f1", "weighted_f1", "accuracy_loss_vs_original", "macro_f1_loss_vs_original", "weighted_f1_loss_vs_original", "rows"])

    survival_table = sorted(survival_summary, key=lambda r: (r["model"], r["split"], CONDITIONS.index(r["condition"])))
    write_csv(TABLE_SURVIVAL, survival_table, ["model", "split", "condition", "baseline_condition", "accuracy", "macro_f1", "weighted_f1", "accuracy_difference_vs_original", "macro_f1_difference_vs_original", "weighted_f1_difference_vs_original", "macro_f1_survival_ratio", "rows"])

    distance_rows = []
    for row in distance_summary:
        if row["condition"] == "original":
            continue
        base = next(r for r in distance_summary if r["feature_set"] == row["feature_set"] and r["condition"] == "original")
        base_mean = fnum(base["mean_burrows_delta"])
        mean = fnum(row["mean_burrows_delta"])
        distance_rows.append({
            "feature_set": row["feature_set"],
            "condition": row["condition"],
            "original_mean_distance": round(base_mean, 9),
            "condition_mean_distance": round(mean, 9),
            "distance_contraction": round(base_mean - mean, 9),
            "distance_ratio": round(mean / base_mean, 9) if base_mean else 0.0,
            "pair_count": row["pair_count"],
        })
    write_csv(TABLE_DISTANCE, distance_rows, ["feature_set", "condition", "original_mean_distance", "condition_mean_distance", "distance_contraction", "distance_ratio", "pair_count"])

    family_rows = [r for r in family_vuln if r["split"] == "test" and r["condition"] != "original"]
    family_rows = sorted(family_rows, key=lambda r: float(r["macro_f1_loss_vs_original"]), reverse=True)
    write_csv(TABLE_FAMILY, family_rows, ["feature_family", "feature_count", "model", "split", "condition", "baseline_condition", "accuracy", "macro_f1", "weighted_f1", "accuracy_loss_vs_original", "macro_f1_loss_vs_original", "weighted_f1_loss_vs_original", "rows"])

    bootstrap_rows = bootstrap_loss_rows(transfer_preds)
    write_csv(BOOTSTRAP, bootstrap_rows, ["model", "split", "condition", "paired_passages", "observed_macro_f1_loss", "ci_low_95", "ci_high_95", "p_loss_le_zero_bootstrap", "bootstrap_iterations", "rng_seed"])

    best_model = "nearest_centroid"
    test_transfer = [r for r in transfer_metrics if r["split"] == "test" and r["model"] == best_model]
    svg_bar_chart(FIG_MACRO, "Step 15 Test Macro-F1 by Condition", [r["condition"] for r in test_transfer], [fnum(r["macro_f1"]) for r in test_transfer], "Macro-F1")

    fd = [r for r in distance_rows if r["feature_set"] == "function_word"]
    svg_bar_chart(FIG_DISTANCE, "Function-word Inter-author Distance Contraction", [r["condition"] for r in fd], [fnum(r["distance_contraction"]) for r in fd], "Contraction")

    family_top = family_rows[:10]
    svg_bar_chart(FIG_FAMILY, "Largest Feature-family Macro-F1 Losses", [f"{r['feature_family'][:8]}\n{r['condition'][:4]}" for r in family_top], [fnum(r["macro_f1_loss_vs_original"]) for r in family_top], "Macro-F1 loss")

    artifacts = [TABLE_BASELINE, TABLE_TRANSFER, TABLE_SURVIVAL, TABLE_DISTANCE, TABLE_FAMILY, BOOTSTRAP, FIG_MACRO, FIG_DISTANCE, FIG_FAMILY]
    manifest_rows = [{"artifact": p.stem, "path": p.relative_to(ROOT).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha_file(p)} for p in artifacts]
    write_csv(MANIFEST, manifest_rows, ["artifact", "path", "size_bytes", "sha256"])

    test_boot = [r for r in bootstrap_rows if r["split"] == "test" and r["model"] == best_model]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Step 19 Statistical Tables and Figures Report\n\n"
        "## Status\n\nComplete when generated locally and checker passes.\n\n"
        "## Outputs\n\n"
        f"- baseline table rows: {len(baseline_table)}\n"
        f"- transfer degradation table rows: {len(transfer_table)}\n"
        f"- same-condition survival table rows: {len(survival_table)}\n"
        f"- distance contraction table rows: {len(distance_rows)}\n"
        f"- feature-family vulnerability table rows: {len(family_rows)}\n"
        f"- bootstrap statistical rows: {len(bootstrap_rows)}\n"
        f"- figures: 3 SVG files\n\n"
        "## Test bootstrap macro-F1 loss intervals for nearest-centroid model\n\n" + "".join(
            f"- {r['condition']}: observed={r['observed_macro_f1_loss']}, 95% CI=[{r['ci_low_95']}, {r['ci_high_95']}], p_loss_le_zero={r['p_loss_le_zero_bootstrap']}\n" for r in test_boot
        ),
        encoding="utf-8",
    )
    print("Generated Step 19 paper-ready tables, bootstrap tests, and SVG figures.")
    print(f"Bootstrap rows: {len(bootstrap_rows)}")
    print("Figures: 3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
