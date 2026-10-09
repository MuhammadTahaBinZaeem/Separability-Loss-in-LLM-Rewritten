# Step 13 Modeling Matrix Protocol

## Purpose

Step 13 converts the Step 12 stylometric feature table into modeling-ready matrices and split metadata.

This step prepares the data for later experiments, but it does **not** run classifiers or calculate final paper results.

## Inputs

```text
data/features/stylometric_features.csv
metadata/stylometric_feature_summary.csv
metadata/stylometric_feature_family_counts.csv
```

## Main outputs

```text
data/modeling/modeling_metadata.csv
data/modeling/X_stylometric_raw.csv
data/modeling/X_stylometric_scaled_descriptive.csv
data/modeling/y_author_labels.csv
data/modeling/passage_level_split.csv
metadata/modeling_feature_columns.csv
metadata/modeling_split_summary.csv
metadata/modeling_matrix_manifest.csv
metadata/descriptive_scaling_parameters.csv
logs/step_13_modeling_matrix_report.md
```

## Key design choice: passage-level splitting

The project contains four text conditions per selected original passage:

```text
original
paraphrase
modernize
simplify
```

A split must keep all four versions of the same `passage_id` together.

Reason: if the original version of a passage appears in training and its rewritten version appears in test, the experiment may leak passage-specific content and inflate model performance.

Therefore Step 13 creates a deterministic passage-level split.

## Default split

Default split unit:

```text
passage_id
```

Default split ratio:

```text
70% train
15% validation
15% test
```

Because there are 360 passages total:

```text
252 train passages
54 validation passages
54 test passages
```

Since each passage has four condition rows, this corresponds to:

```text
1008 train text rows
216 validation text rows
216 test text rows
```

The split is stratified by `author_id` at the passage level.

Each author has 60 passages, so the default per-author split is:

```text
42 train passages
9 validation passages
9 test passages
```

## Scaling policy

### Raw matrix

The raw matrix is always preserved:

```text
data/modeling/X_stylometric_raw.csv
```

### Descriptive scaled matrix

Step 13 also creates:

```text
data/modeling/X_stylometric_scaled_descriptive.csv
```

This matrix is fit on the **full feature table** and is intended only for descriptive visualization and distance exploration where global standardization is explicitly documented.

It must not be used as the main classifier input for train/test experiments.

### Leakage-safe classifier scaling

For classifier experiments, scaling must be fit inside the experimental protocol on the training subset only.

That is intentionally deferred to later modeling steps.

## Labels

The primary classification label is:

```text
author_id
```

The `condition` column is not the target label. It is an experimental condition variable.

## Required validation checks

Step 13 is valid only if:

- 1440 metadata rows exist;
- 1440 raw matrix rows exist;
- 1440 descriptive scaled matrix rows exist;
- all matrices share the same `text_id` order;
- 205 numeric feature columns are present;
- no numeric feature column is entirely empty;
- all 360 passages are assigned to exactly one split;
- each passage's four condition rows share the same split;
- each split has all six authors;
- train/validation/test counts match 1008/216/216 rows;
- manifest and scaling parameter files exist.

## Downstream use

Step 13 feeds later steps:

- Step 14: original-author classification baselines;
- Step 15: train-on-original and test-on-rewritten degradation experiments;
- Step 16: rewritten-to-rewritten classification;
- Step 17: Burrows' Delta and inter-author distance analysis;
- Step 18: feature-family vulnerability analysis;
- Step 19: figures/tables;
- Step 20: final paper-ready dataset audit.
