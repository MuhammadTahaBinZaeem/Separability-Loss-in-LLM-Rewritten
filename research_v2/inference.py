"""Paired, work-aware uncertainty with fixed author labels and explicit null tests."""
from __future__ import annotations

import numpy as np

from .corpus import AUTHORS


def f1_from_confusion(matrix: np.ndarray) -> np.ndarray:
    tp = np.diagonal(matrix, axis1=-2, axis2=-1)
    denominator = matrix.sum(axis=-1) + matrix.sum(axis=-2)
    scores = np.divide(2*tp, denominator, out=np.zeros_like(tp, dtype=float), where=denominator != 0)
    return scores.mean(axis=-1)


def confusion(y: np.ndarray, pred: np.ndarray, weights=None) -> np.ndarray:
    return np.bincount(y * len(AUTHORS) + pred, weights=weights,
                       minlength=len(AUTHORS)**2).reshape(len(AUTHORS), len(AUTHORS))


def paired_uncertainty(rows: list[dict], bootstraps: int = 5000, permutations: int = 9999,
                       seed: int = 20260915) -> dict:
    if not rows or len({r["passage_id"] for r in rows}) != len(rows):
        raise ValueError("One paired record per passage is required")
    labels = {a:i for i,a in enumerate(AUTHORS)}
    y = np.array([labels[r["author_id"]] for r in rows])
    original = np.array([labels[r["original_prediction"]] for r in rows])
    rewritten = np.array([labels[r["rewrite_prediction"]] for r in rows])
    works = sorted({(r["author_id"], r["work_id"]) for r in rows})
    groups = [np.array([i for i,r in enumerate(rows) if (r["author_id"],r["work_id"]) == work]) for work in works]
    author_groups = [[i for i,w in enumerate(works) if w[0] == author] for author in AUTHORS]
    if any(not g for g in author_groups):
        raise ValueError("All six authors must be present")
    co, cr = confusion(y,original), confusion(y,rewritten)
    observed = float(f1_from_confusion(co) - f1_from_confusion(cr))
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(bootstraps):
        sampled = []
        for ag in author_groups:
            for selected_group in rng.choice(ag, size=len(ag), replace=True):
                indices = groups[selected_group]
                sampled.extend(rng.choice(indices, size=len(indices), replace=True))
        idx = np.asarray(sampled)
        boot.append(float(f1_from_confusion(confusion(y[idx],original[idx])) - f1_from_confusion(confusion(y[idx],rewritten[idx]))))
    # Swap whole works; never treat the 20 passages of a work as 20 assignments.
    work_o = np.array([confusion(y[idx],original[idx]) for idx in groups])
    work_r = np.array([confusion(y[idx],rewritten[idx]) for idx in groups])
    null = []
    for offset in range(0, permutations, 1000):
        count = min(1000, permutations-offset)
        masks = rng.integers(0,2,size=(count,len(groups),1,1))
        swapped_o = (np.where(masks,work_r,work_o)).sum(axis=1)
        swapped_r = (np.where(masks,work_o,work_r)).sum(axis=1)
        null.extend((f1_from_confusion(swapped_o) - f1_from_confusion(swapped_r)).tolist())
    extreme = sum(abs(x) >= abs(observed)-1e-12 for x in null)
    return {"paired_passages": len(rows), "work_blocks": len(works),
            "original_macro_f1": float(f1_from_confusion(co)),
            "rewrite_macro_f1": float(f1_from_confusion(cr)), "macro_f1_loss": observed,
            "loss_ci_low": float(np.quantile(boot,.025)), "loss_ci_high": float(np.quantile(boot,.975)),
            "p_work_swap_two_sided": (extreme+1)/(permutations+1),
            "bootstrap_replicates": bootstraps, "permutation_replicates": permutations,
            "seed": seed, "inference_scope": "fixed_authors_conditional_on_fitted_models"}


def holm(p_values: list[float], family_size: int | None = None) -> list[float]:
    total = family_size if family_size is not None else len(p_values)
    if total < len(p_values):
        raise ValueError("Family cannot be smaller than observed tests")
    order = np.argsort(p_values)
    out, running = [0.0]*len(p_values), 0.0
    for rank,index in enumerate(order):
        running = max(running, (total-rank)*p_values[index])
        out[index] = min(1.0, running)
    return out
