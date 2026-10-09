"""
Consistency checker for Step 17 Burrows' Delta and inter-author distance analysis.

Run from repository root after Step 17:

    python scripts/check_step_17_burrows_delta_distance.py

Exit code:
    0 = Step 17 outputs are internally consistent
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_TO_AUTHOR = ROOT / "data" / "results" / "burrows_delta_text_to_author.csv"
DIST_MATRICES = ROOT / "metadata" / "inter_author_distance_matrices.csv"
DIST_SUMMARY = ROOT / "metadata" / "inter_author_distance_summary.csv"
CENTROID_SHIFT = ROOT / "metadata" / "author_centroid_shift_summary.csv"
MANIFEST = ROOT / "metadata" / "burrows_delta_distance_manifest.csv"
REPORT = ROOT / "logs" / "step_17_burrows_delta_distance_report.md"
SCRIPT = ROOT / "scripts" / "18_run_burrows_delta_distance.py"
PROTOCOL = ROOT / "docs" / "burrows_delta_distance_protocol.md"

AUTHORS = {"austen", "dickens", "poe", "shelley", "twain", "wilde"}
CONDITIONS = {"original", "paraphrase", "modernize", "simplify"}
FEATURE_SETS = {"function_word", "all_features"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    required = [TEXT_TO_AUTHOR, DIST_MATRICES, DIST_SUMMARY, CENTROID_SHIFT, MANIFEST, REPORT, SCRIPT, PROTOCOL]
    for path in required:
        check(path.exists(), f"missing required Step 17 file: {path.relative_to(ROOT)}", failures)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    text_rows = read_csv(TEXT_TO_AUTHOR)
    dist_rows = read_csv(DIST_MATRICES)
    summary_rows = read_csv(DIST_SUMMARY)
    shift_rows = read_csv(CENTROID_SHIFT)

    check(len(text_rows) == 8640, f"expected 8640 text-to-author rows, found {len(text_rows)}", failures)
    check(len(dist_rows) == 120, f"expected 120 inter-author distance rows, found {len(dist_rows)}", failures)
    check(len(summary_rows) == 8, f"expected 8 distance summary rows, found {len(summary_rows)}", failures)
    check(len(shift_rows) == 36, f"expected 36 centroid shift rows, found {len(shift_rows)}", failures)

    dist_keys = Counter((row["feature_set"], row["condition"]) for row in dist_rows)
    for feature_set in FEATURE_SETS:
        for condition in CONDITIONS:
            check(dist_keys[(feature_set, condition)] == 15, f"distance pair count not 15 for {feature_set}/{condition}", failures)

    summary_keys = {(row["feature_set"], row["condition"]) for row in summary_rows}
    expected_summary_keys = {(f, c) for f in FEATURE_SETS for c in CONDITIONS}
    check(summary_keys == expected_summary_keys, "summary feature_set/condition grid mismatch", failures)

    shift_keys = Counter((row["feature_set"], row["to_condition"]) for row in shift_rows)
    for feature_set in FEATURE_SETS:
        for condition in {"paraphrase", "modernize", "simplify"}:
            check(shift_keys[(feature_set, condition)] == 6, f"shift rows not 6 for {feature_set}/{condition}", failures)

    text_keys = Counter((row["text_id"], row["condition"]) for row in text_rows)
    check(len(text_keys) == 1440, f"expected 1440 text-condition groups, found {len(text_keys)}", failures)
    for key, count in text_keys.items():
        check(count == 6, f"text-to-author centroid count not 6 for {key}", failures)

    condition_counts = Counter(row["condition"] for row in text_rows)
    for condition in CONDITIONS:
        check(condition_counts[condition] == 2160, f"text-to-author rows for {condition} not 2160", failures)

    for row in text_rows[:100] + text_rows[-100:]:
        check(row["true_author"] in AUTHORS, f"bad true author: {row}", failures)
        check(row["centroid_author"] in AUTHORS, f"bad centroid author: {row}", failures)
        check(row["condition"] in CONDITIONS, f"bad condition: {row}", failures)
        float(row["burrows_delta"])
        check(row["is_true_author_centroid"] in {"0", "1"}, f"bad true centroid flag: {row}", failures)
        check(row["is_nearest_centroid"] in {"0", "1"}, f"bad nearest centroid flag: {row}", failures)
        check(row["nearest_centroid_author"] in AUTHORS, f"bad nearest author: {row}", failures)
        check(row["nearest_centroid_correct"] in {"0", "1"}, f"bad nearest correct flag: {row}", failures)

    for row in dist_rows:
        check(row["feature_set"] in FEATURE_SETS, f"bad feature set: {row}", failures)
        check(row["condition"] in CONDITIONS, f"bad condition: {row}", failures)
        check(row["author_a"] in AUTHORS and row["author_b"] in AUTHORS, f"bad author pair: {row}", failures)
        check(row["author_a"] != row["author_b"], f"self distance row: {row}", failures)
        check(float(row["burrows_delta"]) >= 0, f"negative Delta: {row}", failures)
        check(float(row["euclidean_z_distance"]) >= 0, f"negative Euclidean: {row}", failures)

    for row in summary_rows:
        for col in ["mean_burrows_delta", "median_burrows_delta", "min_burrows_delta", "max_burrows_delta", "std_burrows_delta"]:
            check(float(row[col]) >= 0, f"negative summary distance: {row}", failures)
        check(row["pair_count"] == "15", f"summary pair count not 15: {row}", failures)

    for row in shift_rows:
        check(row["feature_set"] in FEATURE_SETS, f"bad shift feature set: {row}", failures)
        check(row["author_id"] in AUTHORS, f"bad shift author: {row}", failures)
        check(row["from_condition"] == "original", f"bad from condition: {row}", failures)
        check(row["to_condition"] in {"paraphrase", "modernize", "simplify"}, f"bad to condition: {row}", failures)
        check(float(row["burrows_delta_shift"]) >= 0, f"negative shift Delta: {row}", failures)
        check(float(row["euclidean_z_shift"]) >= 0, f"negative shift Euclidean: {row}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: Step 17 Burrows' Delta and inter-author distance analysis is complete and internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
