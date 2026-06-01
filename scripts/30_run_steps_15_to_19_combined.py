"""
Combined runner for Steps 15-19.

This script runs the existing Step 15-19 pipeline scripts in order. It is an
orchestrator, not a rewrite of the scientific methods. The individual scripts
remain the source of truth for each step's internal calculations.

Run from repository root:

    python scripts/30_run_steps_15_to_19_combined.py

Optional:

    python scripts/30_run_steps_15_to_19_combined.py --stop-on-failure
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "metadata"
LOGS = ROOT / "logs"
REPORT = LOGS / "steps_15_to_19_combined_run_report.md"
MANIFEST = META / "steps_15_to_19_combined_manifest.csv"

STEPS = [
    {
        "step": "15",
        "name": "original author baseline",
        "script": "scripts/15_run_original_author_baseline.py",
        "checker": "scripts/check_step_14_original_baseline.py",
        "required_outputs": [
            "metadata/original_author_baseline_metrics.csv",
            "data/results/original_author_baseline_predictions.csv",
        ],
    },
    {
        "step": "16",
        "name": "original-to-rewritten degradation",
        "script": "scripts/16_run_original_to_rewritten_degradation.py",
        "checker": "scripts/check_step_15_rewrite_degradation.py",
        "required_outputs": [
            "metadata/original_to_rewritten_metrics.csv",
            "metadata/original_to_rewritten_degradation_summary.csv",
            "data/results/original_to_rewritten_predictions.csv",
        ],
    },
    {
        "step": "17",
        "name": "same-condition rewritten classification",
        "script": "scripts/17_run_rewritten_condition_classification.py",
        "checker": "scripts/check_step_16_rewritten_condition_classification.py",
        "required_outputs": [
            "metadata/rewritten_condition_author_metrics.csv",
            "metadata/rewritten_condition_author_survival_summary.csv",
            "data/results/rewritten_condition_author_predictions.csv",
        ],
    },
    {
        "step": "18",
        "name": "Burrows Delta distance and feature-family vulnerability",
        "script": "scripts/19_run_feature_family_vulnerability.py",
        "checker": "scripts/check_step_18_feature_family_vulnerability.py",
        "required_outputs": [
            "metadata/feature_family_vulnerability_summary.csv",
            "metadata/feature_family_distance_contraction.csv",
        ],
    },
    {
        "step": "19",
        "name": "paper tables, bootstrap tests, and figures",
        "script": "scripts/20_generate_statistical_tables_figures.py",
        "checker": "scripts/check_step_19_tables_figures.py",
        "required_outputs": [
            "metadata/paper_table_original_baseline.csv",
            "metadata/paper_table_transfer_degradation.csv",
            "metadata/paper_table_same_condition_survival.csv",
            "metadata/paper_table_distance_contraction.csv",
            "metadata/paper_table_feature_family_vulnerability.csv",
            "metadata/statistical_tests_bootstrap_macro_f1_loss.csv",
            "metadata/step19_tables_figures_manifest.csv",
        ],
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def run_command(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop-on-failure", action="store_true")
    parser.add_argument("--skip-checkers", action="store_true")
    args = parser.parse_args()

    LOGS.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)

    report_lines = [
        "# Combined Steps 15-19 Run Report",
        "",
        f"Generated UTC: {utc_now()}",
        "",
        "This orchestrator runs the existing Step 15-19 scripts in sequence. The individual step scripts remain the methodological source of truth.",
        "",
    ]
    manifest_rows = []
    overall_status = 0

    for item in STEPS:
        report_lines.append(f"## Step {item['step']}: {item['name']}")
        report_lines.append("")
        script_path = ROOT / item["script"]
        if not script_path.exists():
            report_lines.append(f"Missing script: `{item['script']}`")
            overall_status = 1
            if args.stop_on_failure:
                break
            continue

        code, output = run_command([sys.executable, item["script"]])
        report_lines.append(f"Script: `{item['script']}`")
        report_lines.append(f"Exit code: `{code}`")
        report_lines.append("")
        report_lines.append("```text")
        report_lines.append(output[-6000:])
        report_lines.append("```")
        report_lines.append("")
        if code != 0:
            overall_status = 1
            if args.stop_on_failure:
                break

        if not args.skip_checkers:
            checker_path = ROOT / item["checker"]
            if checker_path.exists():
                check_code, check_output = run_command([sys.executable, item["checker"]])
                report_lines.append(f"Checker: `{item['checker']}`")
                report_lines.append(f"Checker exit code: `{check_code}`")
                report_lines.append("")
                report_lines.append("```text")
                report_lines.append(check_output[-6000:])
                report_lines.append("```")
                report_lines.append("")
                if check_code != 0:
                    overall_status = 1
                    if args.stop_on_failure:
                        break
            else:
                report_lines.append(f"Checker missing: `{item['checker']}`")
                overall_status = 1

        for rel in item["required_outputs"]:
            path = ROOT / rel
            manifest_rows.append({
                "step": item["step"],
                "name": item["name"],
                "path": rel,
                "exists": int(path.exists()),
                "size_bytes": path.stat().st_size if path.exists() else 0,
                "sha256": sha_file(path),
            })

    write_csv(MANIFEST, manifest_rows, ["step", "name", "path", "exists", "size_bytes", "sha256"])
    report_lines.append("## Final status")
    report_lines.append("")
    report_lines.append(f"Overall exit status: `{overall_status}`")
    report_lines.append(f"Manifest: `{MANIFEST.relative_to(ROOT)}`")
    REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Combined Steps 15-19 runner finished with status {overall_status}.")
    print(f"Report: {REPORT.relative_to(ROOT)}")
    print(f"Manifest: {MANIFEST.relative_to(ROOT)}")
    return overall_status


if __name__ == "__main__":
    raise SystemExit(main())
