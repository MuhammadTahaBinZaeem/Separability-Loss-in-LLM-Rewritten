# E3 Warning-Row Sensitivity Analysis Protocol

## Status

Complete. The protocol, analysis script, checker, output CSV files, manifest, and report are now present in the repository.

Run or rerun with:

```bash
python scripts/22_run_warning_row_sensitivity.py
python scripts/check_e3_warning_row_sensitivity.py
```

Generated output commit:

```text
34c07109bcb01417b0ffdb0063c7126d55632908
```

## Purpose

The frozen main dataset contains QC warning rows. The main paper should not merely state that warnings were documented; it should show that the central result does not depend on those rows.

This experiment recomputes the main Step 15-19 empirical metrics under three QC subsets.

## Subsets

| subset_id | Definition | Reviewer objection answered |
|---|---|---|
| `all_rows` | Original frozen analysis set: original rows plus all rewrite rows, including warnings. | Preserves the original reported result. |
| `qc_pass_only` | Original rows plus only rewrite rows with `qc_status == pass`. | Tests whether warning rows are driving the effect. |
| `pass_plus_non_hard_length_warning` | Original rows plus pass rows and warning rows whose `qc_flags` do **not** include `length_hard_warning`. | Tests whether hard length deviations are driving the effect while retaining softer non-fatal warnings. |

Original-condition rows are always retained because they are not LLM rewrite outputs.

## Metrics recomputed

The script recomputes reviewer-facing analogues of Steps 15-19:

1. **Original-to-rewritten transfer degradation**
   - train on original-condition training rows;
   - evaluate original, paraphrase, modernize, and simplify rows separately;
   - report macro-F1, accuracy, weighted F1, and loss versus original.

2. **Same-condition author classification**
   - train and evaluate within each condition;
   - report residual author separability under rewritten conditions.

3. **Burrows Delta / inter-author distance contraction**
   - recompute mean inter-author distances for function-word and all-feature spaces;
   - report distance ratios against the original condition.

4. **Feature-family sensitivity**
   - recompute transfer degradation by feature family;
   - tests whether the warning-row decision changes the feature-family vulnerability story.

5. **Bootstrap macro-F1 loss intervals**
   - recompute paired-passage bootstrap intervals for original-to-rewritten macro-F1 losses;
   - uses the same fixed RNG seed as the frozen Step 19 package where practical.

## Inputs

```text
data/modeling/modeling_metadata.csv
data/modeling/X_stylometric_raw.csv
data/modeling/y_author_labels.csv
metadata/modeling_feature_columns.csv
metadata/rewrite_qc_report.csv
```

## Outputs

```text
data/results/warning_row_sensitivity_transfer_predictions.csv
metadata/warning_row_sensitivity_transfer_summary.csv
metadata/warning_row_sensitivity_same_condition_summary.csv
metadata/warning_row_sensitivity_distance_summary.csv
metadata/warning_row_sensitivity_feature_family_summary.csv
metadata/warning_row_sensitivity_bootstrap_macro_f1_loss.csv
metadata/warning_row_sensitivity_subset_counts.csv
metadata/warning_row_sensitivity_manifest.csv
logs/warning_row_sensitivity_report.md
```

## Completion result

E3 passed the directional robustness test:

- rewritten conditions still show lower original-to-rewritten macro-F1 than original;
- nearest-centroid test macro-F1 loss remains positive for paraphrase, modernize, and simplify under all three subsets;
- paired-passage bootstrap 95% confidence intervals remain positive for nearest-centroid test losses under all three subsets;
- distance contraction remains directionally similar in both function-word and all-feature spaces;
- QC-pass-only filtering keeps all six authors represented in every condition.

## Manuscript use

The results can appear in the paper as a robustness paragraph and/or supplementary table:

> A warning-row sensitivity analysis repeated the main classification and distance analyses under all rows, QC-pass-only rows, and pass-plus-non-hard-length-warning rows. The main degradation pattern remained stable, showing that the reported style-separability loss is not an artifact of retained QC warning rows.

Use this wording only with the actual E3 result tables and the limitation that QC-pass-only filtering reduces the number of test rows in rewritten conditions.