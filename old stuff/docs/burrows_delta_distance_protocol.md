# Step 17 Burrows' Delta and Inter-Author Distance Protocol

## Purpose

Step 17 adds a distance-based stylometric analysis layer after the classification experiments.

Classification answers whether author labels are recoverable. Distance analysis asks how far author profiles move and how separable author centroids remain after rewriting.

This step supports three paper claims:

1. LLM rewriting changes the position of author profiles in stylometric feature space.
2. Inter-author distances may contract after rewriting, indicating style flattening.
3. Burrows-style function-word distance provides a classical stylometric complement to classifier-based results.

## Inputs

```text
data/modeling/modeling_metadata.csv
data/modeling/X_stylometric_raw.csv
metadata/modeling_feature_columns.csv
```

## Feature sets

Step 17 uses two feature sets:

```text
function_word
all_features
```

### Function-word set

The function-word set contains all features whose names begin with:

```text
fw_
```

This is the primary Burrows' Delta feature set.

### All-feature set

The all-feature set contains all 205 stylometric features from Step 12/13.

This is used for broad inter-author centroid distance and author-profile shift analysis.

## Standardization policy

### Burrows' Delta

For Burrows' Delta, features are z-scored within each condition and feature set before distances are computed.

For each condition:

```text
z = (feature_value - condition_feature_mean) / condition_feature_std
```

Then Delta between two vectors is the mean absolute z-score difference:

```text
Delta(A, B) = mean(abs(z_A - z_B))
```

This is used for author-centroid distances and text-to-author-centroid distances.

### Inter-author distance

For inter-author distance matrices, author centroids are computed within each condition after condition-wise standardization.

The output includes:

```text
burrows_delta
mean_absolute_z_distance
euclidean_z_distance
```

For the function-word set, Burrows' Delta and mean absolute z-distance are equivalent by definition.

## Analyses produced

### 1. Author centroid distance matrices

For every condition and feature set, compute pairwise distances between the six author centroids.

Expected author pairs per condition/feature set:

```text
6 choose 2 = 15
```

Expected matrix rows:

```text
4 conditions × 2 feature sets × 15 pairs = 120 rows
```

### 2. Distance summary by condition

For each condition and feature set, summarize pairwise inter-author distances:

```text
mean distance
median distance
minimum distance
maximum distance
standard deviation
```

Expected summary rows:

```text
4 conditions × 2 feature sets = 8 rows
```

### 3. Original-to-rewritten centroid shift

For each author and rewritten condition, compute how far the author's rewritten-condition centroid is from their original-condition centroid.

Expected rows:

```text
6 authors × 3 rewritten conditions × 2 feature sets = 36 rows
```

### 4. Text-to-author Burrows' Delta

For function-word features, compute each text row's Burrows' Delta to every author centroid within the same condition.

Expected rows:

```text
1440 texts × 6 author centroids = 8640 rows
```

This supports later inspection of whether rewritten passages move closer to other author centroids.

## Outputs

```text
data/results/burrows_delta_text_to_author.csv
metadata/inter_author_distance_matrices.csv
metadata/inter_author_distance_summary.csv
metadata/author_centroid_shift_summary.csv
metadata/burrows_delta_distance_manifest.csv
logs/step_17_burrows_delta_distance_report.md
```

## Completion criteria

Step 17 is complete only if:

- function-word feature set exists and is non-empty;
- all-feature feature set has 205 features;
- 120 inter-author distance matrix rows are produced;
- 8 condition distance summary rows are produced;
- 36 author centroid shift rows are produced;
- 8640 text-to-author Delta rows are produced;
- no distance value is missing or non-numeric;
- manifest and report files exist;
- Step 17 checker passes.
