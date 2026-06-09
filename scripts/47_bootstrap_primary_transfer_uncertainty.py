"""Bootstrap uncertainty for primary original-to-rewrite transfer losses.

This addresses a manuscript weakness: primary results previously reported point
estimates without interval estimates. The script uses the committed Step 15
prediction file and computes passage-level paired bootstrap intervals for
macro-F1 loss:

    loss_c = macroF1(original) - macroF1(condition c)

For each model, split, and rewrite condition, bootstrap resampling is done over
passage IDs shared by the original and rewrite condition in that split. This
keeps the original/rewrite comparison paired at the passage level.
"""
from __future__ import annotations

import csv
import hashlib
import random
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "data/results/original_to_rewritten_predictions.csv"
META = ROOT / "metadata"
LOGS = ROOT / "logs"
OUT = META / "primary_transfer_bootstrap_ci.csv"
MANIFEST = META / "primary_transfer_bootstrap_ci_manifest.csv"
REPORT = LOGS / "primary_transfer_bootstrap_ci_report.md"

AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
MODELS = ["nearest_centroid", "diagonal_gaussian_nb", "linear_discriminant_shrinkage"]
SPLITS = ["validation", "test"]
REWRITE_CONDITIONS = ["paraphrase", "modernize", "simplify"]
BOOTSTRAPS = 5000
SEED = 20260609


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


def prf(y_true: list[str], y_pred: list[str], label: str) -> tuple[float, float, float, int]:
    tp = sum(1 for a, b in zip(y_true, y_pred) if a == label and b == label)
    fp = sum(1 for a, b in zip(y_true, y_pred) if a != label and b == label)
    fn = sum(1 for a, b in zip(y_true, y_pred) if a == label and b != label)
    support = sum(1 for a in y_true if a == label)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1, support


def macro_f1(items: list[dict[str, str]]) -> float:
    y_true = [r["true_author"] for r in items]
    y_pred = [r["predicted_author"] for r in items]
    return sum(prf(y_true, y_pred, author)[2] for author in AUTHORS) / len(AUTHORS)


def percentile(values: list[float], p: float) -> float:
    if not values: return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def main() -> int:
    rows = read_csv(PRED)
    by_key: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for r in rows:
        by_key[(r["model"], r["split"], r["condition"], r["passage_id"])] = r

    rng = random.Random(SEED)
    out = []
    for model in MODELS:
        for split in SPLITS:
            original_ids = sorted(k[3] for k in by_key if k[0] == model and k[1] == split and k[2] == "original")
            for condition in REWRITE_CONDITIONS:
                rewrite_ids = sorted(k[3] for k in by_key if k[0] == model and k[1] == split and k[2] == condition)
                ids = sorted(set(original_ids) & set(rewrite_ids))
                if len(ids) != 54:
                    raise RuntimeError(f"Expected 54 paired ids for {model}/{split}/{condition}, found {len(ids)}")
                orig_items = [by_key[(model, split, "original", pid)] for pid in ids]
                rew_items = [by_key[(model, split, condition, pid)] for pid in ids]
                point_original = macro_f1(orig_items)
                point_rewrite = macro_f1(rew_items)
                point_loss = point_original - point_rewrite
                losses = []
                for _ in range(BOOTSTRAPS):
                    sample_ids = [ids[rng.randrange(len(ids))] for _ in ids]
                    boot_orig = [by_key[(model, split, "original", pid)] for pid in sample_ids]
                    boot_rew = [by_key[(model, split, condition, pid)] for pid in sample_ids]
                    losses.append(macro_f1(boot_orig) - macro_f1(boot_rew))
                out.append({
                    "model": model,
                    "split": split,
                    "condition": condition,
                    "paired_passages": len(ids),
                    "bootstrap_replicates": BOOTSTRAPS,
                    "original_macro_f1": round(point_original, 6),
                    "rewrite_macro_f1": round(point_rewrite, 6),
                    "macro_f1_loss": round(point_loss, 6),
                    "loss_ci_2_5": round(percentile(losses, 0.025), 6),
                    "loss_ci_50": round(percentile(losses, 0.50), 6),
                    "loss_ci_97_5": round(percentile(losses, 0.975), 6),
                    "bootstrap_nonpositive_rate": round(sum(1 for x in losses if x <= 0) / len(losses), 6),
                })
    fields = ["model", "split", "condition", "paired_passages", "bootstrap_replicates", "original_macro_f1", "rewrite_macro_f1", "macro_f1_loss", "loss_ci_2_5", "loss_ci_50", "loss_ci_97_5", "bootstrap_nonpositive_rate"]
    write_csv(OUT, out, fields)
    write_csv(MANIFEST, [{"artifact": OUT.stem, "path": OUT.relative_to(ROOT).as_posix(), "size_bytes": OUT.stat().st_size, "sha256": sha_file(OUT)}], ["artifact", "path", "size_bytes", "sha256"])

    test_rows = [r for r in out if r["split"] == "test"]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Primary Transfer Bootstrap CI Report\n\n"
        f"- bootstrap replicates per comparison: {BOOTSTRAPS}\n"
        f"- paired passages per comparison: 54\n"
        f"- seed: {SEED}\n\n"
        "## Test split focus\n\n" + "".join(
            f"- {r['model']} / {r['condition']}: loss={r['macro_f1_loss']}, 95% CI [{r['loss_ci_2_5']}, {r['loss_ci_97_5']}], nonpositive_rate={r['bootstrap_nonpositive_rate']}\n"
            for r in test_rows
        ),
        encoding="utf-8",
    )
    print(f"Wrote bootstrap CI table: {OUT.relative_to(ROOT)} ({len(out)} rows)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
