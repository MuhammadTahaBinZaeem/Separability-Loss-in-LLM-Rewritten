# Step 14 Original-Condition Author Classification Baseline

## Purpose

Step 14 tests whether the extracted stylometric feature set can separate the six authors **before rewriting**.

This is the baseline classification experiment. Later rewriting-degradation experiments should be compared against this original-condition baseline.

## Research role

The baseline answers:

```text
Can the stylometric feature table distinguish the six authors in original public-domain passages?
```

If this baseline is weak, then later claims about LLM rewriting reducing author separability would be unstable. A strong original baseline is therefore required before measuring post-rewrite degradation.

## Input files

```text
data/modeling/modeling_metadata.csv
data/modeling/X_stylometric_raw.csv
data/modeling/y_author_labels.csv
metadata/modeling_feature_columns.csv
```

## Data used

Use only:

```text
condition = original
```

Expected row counts:

```text
train: 252 original rows
validation: 54 original rows
test: 54 original rows
total original rows: 360
```

There are six authors. Each author contributes:

```text
42 train original rows
9 validation original rows
9 test original rows
```

## Leakage rule

Scaling must be fit on the training rows only.

Do **not** use `X_stylometric_scaled_descriptive.csv` for classifier training. That file was fit on the full dataset and is only for descriptive exploration.

The classifier pipeline must be:

```text
train raw features -> fit scaler on train only -> train classifier
validation/test raw features -> apply train-fitted scaler -> evaluate
```

## Models

Use simple, defensible baseline classifiers:

1. Logistic Regression
2. Linear SVM
3. Random Forest

The paper should not overclaim based on one model. These three provide a reasonable first baseline across linear and nonlinear decision rules.

## Metrics

Required metrics:

```text
accuracy
macro_f1
weighted_f1
```

Also save:

```text
confusion matrix
per-author precision/recall/F1
per-row predictions
```

## Expected outputs

```text
data/results/original_author_baseline_predictions.csv
metadata/original_author_baseline_metrics.csv
metadata/original_author_baseline_confusion_matrices.csv
metadata/original_author_baseline_classification_report.csv
metadata/original_author_baseline_manifest.csv
logs/step_14_original_author_baseline_report.md
```

## Completion criteria

Step 14 is complete only if:

- only original-condition rows are used;
- train/validation/test counts are 252/54/54;
- all six authors are present in each split;
- scaler fitting is train-only;
- predictions exist for validation and test rows;
- metrics exist for all configured models;
- confusion matrices exist for all configured models and evaluation splits;
- no rewritten rows enter this baseline;
- the Step 14 checker passes.
