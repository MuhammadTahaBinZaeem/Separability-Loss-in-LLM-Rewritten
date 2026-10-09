# Step 15 Original-to-Rewritten Author Separability Degradation Protocol

## Purpose

Step 15 is the first core Authorial Style Separability Loss experiment.

It asks:

```text
If a classifier learns authorial style from original passages only, how well does that learned author signal transfer to LLM-rewritten passages?
```

This directly tests whether rewriting moves texts away from their original author-specific stylometric signal.

## Input files

```text
data/modeling/modeling_metadata.csv
data/modeling/X_stylometric_raw.csv
data/modeling/y_author_labels.csv
metadata/modeling_feature_columns.csv
```

## Experimental design

### Training data

Use only:

```text
split = train
condition = original
```

Expected training rows:

```text
252
```

That means 42 original passages per author.

### Evaluation data

Evaluate separately on validation and test rows for all four conditions:

```text
original
paraphrase
modernize
simplify
```

Expected rows per evaluation split:

```text
original: 54
paraphrase: 54
modernize: 54
simplify: 54
```

Expected rows per evaluation split total:

```text
216
```

## Leakage rule

Scaling must be fit on the original-condition training rows only.

Do not use `X_stylometric_scaled_descriptive.csv` for classifier evaluation.

The pipeline must be:

```text
fit scaler on train/original raw features
train classifier on train/original scaled features
apply same scaler to validation/test rows from every condition
evaluate each condition separately
```

## Models

Use the same three baseline models from Step 14:

```text
nearest_centroid
diagonal_gaussian_nb
linear_discriminant_shrinkage
```

Keeping the model family stable allows Step 15 results to be compared directly with the Step 14 original-only baseline.

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
condition-wise degradation summary
```

## Degradation / ASSL-style summary

For each model and split, use the original-condition score as the baseline.

For each rewritten condition:

```text
macro_f1_loss = original_macro_f1 - rewritten_condition_macro_f1
accuracy_loss = original_accuracy - rewritten_condition_accuracy
weighted_f1_loss = original_weighted_f1 - rewritten_condition_weighted_f1
```

Positive loss means author separability decreased after rewriting.

## Expected outputs

```text
data/results/original_to_rewritten_predictions.csv
metadata/original_to_rewritten_metrics.csv
metadata/original_to_rewritten_degradation_summary.csv
metadata/original_to_rewritten_confusion_matrices.csv
metadata/original_to_rewritten_classification_report.csv
metadata/original_to_rewritten_manifest.csv
logs/step_15_original_to_rewritten_degradation_report.md
```

## Completion criteria

Step 15 is complete only if:

- training uses only original-condition train rows;
- training row count is exactly 252;
- validation and test evaluation each use 216 rows;
- each validation/test condition has 54 rows;
- all three models are evaluated;
- metrics exist for each model, split, and condition;
- degradation summary exists for each model, split, and condition;
- no train rows from rewritten conditions enter the training set;
- the Step 15 checker passes.
