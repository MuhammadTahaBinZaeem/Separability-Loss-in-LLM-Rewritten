# Step 19 Statistical Testing and Paper-Ready Tables/Figures Protocol

## Purpose

Step 19 converts the completed empirical outputs from Steps 14-18 into paper-ready result tables, statistical summaries, and figures.

This step does not change the dataset, rewrite outputs, feature table, split, or modeling outputs. It is a reporting and statistical-synthesis layer.

## Inputs

```text
metadata/original_author_baseline_metrics.csv
metadata/original_to_rewritten_metrics.csv
metadata/original_to_rewritten_degradation_summary.csv
data/results/original_to_rewritten_predictions.csv
metadata/rewritten_condition_author_metrics.csv
metadata/rewritten_condition_author_survival_summary.csv
metadata/inter_author_distance_summary.csv
metadata/feature_family_vulnerability_summary.csv
metadata/feature_family_distance_contraction.csv
```

## Main analyses

### 1. Classification summary tables

Prepare paper-ready tables for:

- original-condition baseline classification;
- train-on-original to rewritten-condition transfer degradation;
- same-condition rewritten author classification survival.

### 2. Bootstrap confidence intervals

For Step 15 transfer degradation, compute paired bootstrap confidence intervals over evaluation rows for macro-F1 loss:

```text
loss = macro_f1(original condition) - macro_f1(rewritten condition)
```

The bootstrap is computed separately for:

```text
model × split × rewritten condition
```

Default bootstrap iterations:

```text
2000
```

The output includes:

```text
observed_loss
ci_low_95
ci_high_95
p_loss_le_zero_bootstrap
```

The p-value is an empirical one-sided bootstrap estimate for whether the observed loss could be non-positive.

### 3. Distance contraction summary

Summarize Step 17 distance results:

- function-word Burrows' Delta contraction;
- all-feature inter-author distance contraction;
- condition ranking by distance contraction.

### 4. Feature-family vulnerability summary

Summarize Step 18 feature-family vulnerability results:

- largest macro-F1 losses by feature family;
- distance contraction by feature family;
- centroid shift summaries by feature family.

### 5. Figures

Generate compact SVG figures that can be inspected in the repository and later recreated for publication styling.

Expected figures:

```text
figures/fig_step19_macro_f1_degradation.svg
figures/fig_step19_distance_contraction.svg
figures/fig_step19_feature_family_losses.svg
```

## Outputs

```text
metadata/paper_table_original_baseline.csv
metadata/paper_table_transfer_degradation.csv
metadata/paper_table_same_condition_survival.csv
metadata/paper_table_distance_contraction.csv
metadata/paper_table_feature_family_vulnerability.csv
metadata/statistical_tests_bootstrap_macro_f1_loss.csv
metadata/step19_tables_figures_manifest.csv
figures/fig_step19_macro_f1_degradation.svg
figures/fig_step19_distance_contraction.svg
figures/fig_step19_feature_family_losses.svg
logs/step_19_tables_figures_report.md
```

## Completion criteria

Step 19 is complete only if:

- all required input files exist;
- all paper table CSV files exist;
- bootstrap statistical summary exists;
- all three SVG figures exist;
- manifest exists and records all output hashes;
- report exists;
- no source dataset or modeling output is modified;
- Step 19 checker passes.
