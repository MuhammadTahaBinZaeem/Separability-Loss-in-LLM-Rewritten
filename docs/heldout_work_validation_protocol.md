# E2 Held-Out-Work Validation Protocol

## Status

Complete. The protocol, analysis script, checker, output CSV files, manifest, report, and workflow proof log are now present in the repository.

Run or rerun with:

```bash
python scripts/23_run_heldout_work_validation.py
python scripts/check_e2_heldout_work_validation.py
```

Generated output workflow proof:

```text
logs/e2_heldout_work_validation_workflow_proof.md
```

Latest workflow-generated output commit:

```text
572cbc9a73d2caca1b7f1b2bdb034a78ba2c4ec3
```

## Purpose

The main frozen pipeline uses passage-level train/validation/test splits while keeping all versions of each passage in the same split. That prevents passage leakage, but it does not fully answer the sharper reviewer objection:

> The model may be learning work/topic differences rather than authorial style.

Because every author contributes two works, E2 performs leave-one-work-out validation. The classifier must learn author signal from one work per author and predict author labels on the other work by the same author.

## Fold design

Each author has exactly two selected works. E2 creates two folds:

| fold_id | Train set | Test set |
|---|---|---|
| `work_fold_1` | first listed work for each author | second listed work for each author |
| `work_fold_2` | second listed work for each author | first listed work for each author |

The work order is taken from:

```text
metadata/selected_counts_by_work.csv
```

This produces, for every fold:

```text
6 authors × 1 train work × 30 passages = 180 base passages for training
6 authors × 1 test work × 30 passages = 180 base passages for evaluation
```

For transfer analysis, training uses **original-condition** rows only from the train works, then evaluates on original, paraphrase, modernize, and simplify conditions from the held-out test works.

## Metrics recomputed

1. **Held-out-work original-to-rewritten transfer**
   - train on original rows from train works;
   - evaluate original and rewritten rows from held-out works;
   - report accuracy, macro-F1, weighted F1, and loss versus held-out original.

2. **Held-out-work same-condition classification**
   - for each condition, train on that condition in train works;
   - test on that same condition in held-out works;
   - report residual cross-work author separability.

3. **Held-out-work distance contraction**
   - compute inter-author distances using held-out test works only;
   - compute both function-word and all-feature distance ratios relative to the held-out original condition.

## Inputs

```text
data/modeling/modeling_metadata.csv
data/modeling/X_stylometric_raw.csv
data/modeling/y_author_labels.csv
metadata/modeling_feature_columns.csv
metadata/selected_counts_by_work.csv
```

## Outputs

```text
data/results/heldout_work_transfer_predictions.csv
metadata/heldout_work_fold_registry.csv
metadata/heldout_work_transfer_summary.csv
metadata/heldout_work_same_condition_summary.csv
metadata/heldout_work_distance_summary.csv
metadata/heldout_work_manifest.csv
logs/heldout_work_validation_report.md
logs/e2_heldout_work_validation_workflow_proof.md
```

## Completion result

E2 is a mixed but useful robustness result:

- held-out-work original nearest-centroid macro-F1 falls to `0.601154`, so cross-work authorship signal is only moderate;
- original-to-rewritten transfer losses remain positive under the stricter held-out-work setting:
  - paraphrase loss: `0.179796`;
  - modernize loss: `0.101997`;
  - simplify loss: `0.125387`;
- same-condition rewritten classification retains residual author signal, but weaker than the frozen passage-level split;
- distance contraction remains directionally stable:
  - function-word ratios: paraphrase `0.824602584`, modernize `0.892516328`, simplify `0.863369023`;
  - all-feature ratios: paraphrase `0.840368543`, modernize `0.900911819`, simplify `0.878210609`.

## Interpretation rules

E2 is intentionally stricter than the frozen passage-level split. It should not be treated as a clean triumph.

The correct manuscript interpretation is:

> In a stricter held-out-work validation, original author classification remains above chance but drops substantially, indicating that the passage-level model contains some work-sensitive signal. However, the direction of rewrite-associated separability loss and inter-author distance contraction persists across folds. This supports the main claim cautiously, while narrowing it: the result is not purely a passage-split artifact, but cross-work generalisation is moderate rather than strong.

## Pass condition

The checker validates structural completeness, not whether the outcome is flattering. E2 passed structural validation through the workflow proof log.

## Manuscript use

E2 should appear as a robustness/validation section rather than as a replacement for the main frozen experiment. It directly addresses the work/topic confound and should be reported honestly as a stricter, mixed validation.