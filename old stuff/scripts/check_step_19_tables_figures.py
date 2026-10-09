"""
Consistency checker for Step 19 statistical tables and figures.

Run from repository root after Step 19:

    python scripts/check_step_19_tables_figures.py

Exit code:
    0 = Step 19 outputs are internally consistent
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "metadata"
FIGURES = ROOT / "figures"
LOGS = ROOT / "logs"
SCRIPT = ROOT / "scripts" / "20_generate_statistical_tables_figures.py"
PROTOCOL = ROOT / "docs" / "statistical_tables_figures_protocol.md"

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

MODELS = {"nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"}
SPLITS = {"validation", "test"}
CONDITIONS = {"original", "paraphrase", "modernize", "simplify"}
REWRITE_CONDITIONS = {"paraphrase", "modernize", "simplify"}
FEATURE_SETS = {"function_word", "all_features"}
FAMILIES = {"char3", "function_word", "length_rhythm", "lexical_richness", "punctuation", "register_marker"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    required = [
        TABLE_BASELINE, TABLE_TRANSFER, TABLE_SURVIVAL, TABLE_DISTANCE, TABLE_FAMILY,
        BOOTSTRAP, MANIFEST, REPORT, FIG_MACRO, FIG_DISTANCE, FIG_FAMILY, SCRIPT, PROTOCOL,
    ]
    for path in required:
        check(path.exists(), f"missing required Step 19 file: {path.relative_to(ROOT)}", failures)
        if path.exists():
            check(path.stat().st_size > 0, f"empty Step 19 file: {path.relative_to(ROOT)}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    baseline = read_csv(TABLE_BASELINE)
    transfer = read_csv(TABLE_TRANSFER)
    survival = read_csv(TABLE_SURVIVAL)
    distance = read_csv(TABLE_DISTANCE)
    family = read_csv(TABLE_FAMILY)
    bootstrap = read_csv(BOOTSTRAP)
    manifest = read_csv(MANIFEST)

    check(len(baseline) == 6, f"baseline table expected 6 rows, found {len(baseline)}", failures)
    check(len(transfer) == 24, f"transfer table expected 24 rows, found {len(transfer)}", failures)
    check(len(survival) == 24, f"survival table expected 24 rows, found {len(survival)}", failures)
    check(len(distance) == 6, f"distance table expected 6 rows, found {len(distance)}", failures)
    check(len(family) == 54, f"feature-family table expected 54 rows, found {len(family)}", failures)
    check(len(bootstrap) == 18, f"bootstrap table expected 18 rows, found {len(bootstrap)}", failures)
    check(len(manifest) == 9, f"manifest expected 9 rows, found {len(manifest)}", failures)

    for row in baseline:
        check(row["model"] in MODELS, f"bad baseline model: {row}", failures)
        check(row["split"] in SPLITS, f"bad baseline split: {row}", failures)
        check(row["rows"] == "54", f"baseline rows not 54: {row}", failures)
        for col in ["accuracy", "macro_f1", "weighted_f1"]:
            v = float(row[col])
            check(0 <= v <= 1, f"baseline metric outside range: {row}", failures)

    transfer_keys = {(r["model"], r["split"], r["condition"]) for r in transfer}
    expected_transfer = {(m, s, c) for m in MODELS for s in SPLITS for c in CONDITIONS}
    check(transfer_keys == expected_transfer, "transfer table grid mismatch", failures)
    for row in transfer:
        check(row["rows"] == "54", f"transfer rows not 54: {row}", failures)
        check(row["baseline_condition"] == "original", f"transfer baseline not original: {row}", failures)
        for col in ["accuracy", "macro_f1", "weighted_f1"]:
            v = float(row[col])
            check(0 <= v <= 1, f"transfer metric outside range: {row}", failures)
        for col in ["accuracy_loss_vs_original", "macro_f1_loss_vs_original", "weighted_f1_loss_vs_original"]:
            float(row[col])

    survival_keys = {(r["model"], r["split"], r["condition"]) for r in survival}
    check(survival_keys == expected_transfer, "survival table grid mismatch", failures)
    for row in survival:
        check(row["rows"] == "54", f"survival rows not 54: {row}", failures)
        check(row["baseline_condition"] == "original", f"survival baseline not original: {row}", failures)
        float(row["macro_f1_survival_ratio"])

    distance_keys = {(r["feature_set"], r["condition"]) for r in distance}
    expected_distance = {(fs, c) for fs in FEATURE_SETS for c in REWRITE_CONDITIONS}
    check(distance_keys == expected_distance, "distance contraction table grid mismatch", failures)
    for row in distance:
        check(row["pair_count"] == "15", f"distance pair_count not 15: {row}", failures)
        for col in ["original_mean_distance", "condition_mean_distance", "distance_contraction", "distance_ratio"]:
            float(row[col])

    for row in family:
        check(row["feature_family"] in FAMILIES, f"bad feature family: {row}", failures)
        check(row["model"] in MODELS, f"bad model in family row: {row}", failures)
        check(row["split"] == "test", f"family table should be test only: {row}", failures)
        check(row["condition"] in REWRITE_CONDITIONS, f"family table should be rewrite condition only: {row}", failures)
        check(row["rows"] == "54", f"family rows not 54: {row}", failures)
        for col in ["macro_f1", "macro_f1_loss_vs_original"]:
            float(row[col])

    boot_keys = {(r["model"], r["split"], r["condition"]) for r in bootstrap}
    expected_boot = {(m, s, c) for m in MODELS for s in SPLITS for c in REWRITE_CONDITIONS}
    check(boot_keys == expected_boot, "bootstrap table grid mismatch", failures)
    for row in bootstrap:
        check(row["paired_passages"] == "54", f"bootstrap paired passages not 54: {row}", failures)
        check(row["bootstrap_iterations"] == "2000", f"bootstrap iterations not 2000: {row}", failures)
        for col in ["observed_macro_f1_loss", "ci_low_95", "ci_high_95", "p_loss_le_zero_bootstrap"]:
            float(row[col])
        p = float(row["p_loss_le_zero_bootstrap"])
        check(0 <= p <= 1, f"bootstrap p outside range: {row}", failures)

    for fig in [FIG_MACRO, FIG_DISTANCE, FIG_FAMILY]:
        text = fig.read_text(encoding="utf-8")
        check(text.strip().startswith("<svg"), f"figure is not SVG: {fig.relative_to(ROOT)}", failures)
        check("</svg>" in text, f"figure missing SVG close tag: {fig.relative_to(ROOT)}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: Step 19 statistical tables and figures are complete and internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
