# Step 16 Rewritten-Condition Author Classification Protocol

## Purpose

Step 16 tests whether author-specific stylometric signals still survive **inside each rewritten condition**.

Step 15 asked:

```text
If a classifier learns from original passages, does that author signal transfer to rewritten passages?
```

Step 16 asks a different question:

```text
If a classifier learns from rewritten passages of the same rewrite condition, can it still distinguish authors?
```

This separates two effects:

1. **Transfer loss**: rewritten text moves away from original-author style space.
2. **Residual separability**: rewritten text may still retain internally learnable author-specific signals.

Both are important for the paper.

## Input files

```text
data/modeling/modeling_metadata.csv
data/modeling/X_stylometric_raw.csv
data/modeling/y_author_labels.csv
metadata/modeling_feature_columns.csv
```

## Experimental design

Run one same-condition author classification experiment per condition:

```text
original
paraphrase
modernize
simplify
```

For each condition:

```text
train on split=train and that condition only
evaluate on split=validation and that condition only
evaluate on split=test and that condition only
```

Expected rows per condition:

```text
train: 252
validation: 54
test: 54
```

Each training set has 42 rows per author. Each validation/test set has 9 rows per author.

## Leakage rule

For each condition-specific experiment, scaling must be fit only on that condition's training rows.

Do not use `X_stylometric_scaled_descriptive.csv` for classifier training.

## Models

Use the same three baseline classifiers used in Steps 14 and 15:

```text
nearest_centroid
diagonal_gaussian_nb
linear_discriminant_shrinkage
```

Keeping the classifiers stable makes the Step 14, Step 15, and Step 16 results comparable.

## Metrics

Required metrics:

```text
accuracy
macro_f1
weighted_f1
```

Also save:

```text
per-row predictions
confusion matrices
per-author classification report
same-condition separability summary
```

## Survival summary

For each model and split, compare each rewritten condition against the original same-condition baseline:

```text
macro_f1_difference_vs_original = condition_macro_f1 - original_macro_f1
macro_f1_survival_ratio = condition_macro_f1 / original_macro_f1
```

A ratio near 1.0 means rewritten texts remain almost as author-separable as original texts when trained and tested within the same condition.

A low ratio means rewriting strongly flattens author-specific separability even when the classifier is allowed to learn from rewritten examples.

## Expected outputs

```text
data/results/rewritten_condition_author_predictions.csv
metadata/rewritten_condition_author_metrics.csv
metadata/rewritten_condition_author_survival_summary.csv
metadata/rewritten_condition_author_confusion_matrices.csv
metadata/rewritten_condition_author_classification_report.csv
metadata/rewritten_condition_author_manifest.csv
logs/step_16_rewritten_condition_classification_report.md
```

## Completion criteria

Step 16 is complete only if:

- all four conditions are evaluated;
- all three models are evaluated;
- each condition has 252 train rows, 54 validation rows, and 54 test rows;
- scaling is fit separately inside each condition's training data;
- metrics exist for every model, split, and condition;
- survival summary exists for every model, split, and condition;
- no cross-condition training occurs;
- the Step 16 checker passes.
