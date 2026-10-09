# Step 12 Stylometric Feature Schema

## Purpose

Step 12 extracts stylometric features from the 1440-row master text dataset.

The feature layer is the first analysis-ready numerical representation used for later:

- author classification;
- original-to-rewrite degradation tests;
- Burrows' Delta distance analysis;
- inter-author distance analysis;
- condition-wise style separability comparison;
- feature-family vulnerability analysis.

## Input

```text
data/final/master_text_dataset.csv
```

## Main output

```text
data/features/stylometric_features.csv
```

Expected rows:

```text
1440
```

There must be one feature row per `text_id` in the master dataset.

## Required metadata outputs

```text
metadata/stylometric_feature_summary.csv
metadata/stylometric_feature_manifest.csv
metadata/stylometric_feature_family_counts.csv
logs/step_12_feature_extraction_report.md
```

## Feature families

### 1. Length and rhythm features

These capture sentence and passage rhythm.

Examples:

```text
word_count
sentence_count
mean_sentence_words
median_sentence_words
std_sentence_words
short_sentence_ratio
long_sentence_ratio
paragraph_count
```

### 2. Punctuation features

These capture punctuation intensity and punctuation rhythm.

Examples:

```text
punctuation_per_1000w
comma_per_1000w
semicolon_per_1000w
colon_per_1000w
dash_per_1000w
question_per_1000w
exclamation_per_1000w
quote_mark_per_1000w
apostrophe_per_1000w
ellipsis_per_1000w
```

This family is especially important for Poe's punctuation intensity, Wilde's compression, and Dickens's accumulation patterns.

### 3. Lexical richness features

These capture vocabulary distribution.

Examples:

```text
type_token_ratio
root_type_token_ratio
hapax_ratio
avg_word_length
long_word_ratio
short_word_ratio
```

### 4. Function-word features

These support classic authorship/stylometry analysis and Burrows-style function-word comparison.

Examples:

```text
fw_the_per_1000w
fw_and_per_1000w
fw_of_per_1000w
fw_to_per_1000w
...
```

Function words are important because they are less topic-dependent than content words.

### 5. Register and marker features

These capture broad style/register markers.

Examples:

```text
contraction_per_1000w
archaic_marker_per_1000w
abstract_suffix_per_1000w
dialogue_marker_per_1000w
```

These are useful for modernization and simplification effects.

### 6. Character n-gram features

These capture surface rhythm, spelling habits, punctuation adjacency, and orthographic texture.

The extractor should produce a controlled set of high-frequency character 3-gram features selected from the original condition only, then applied to all conditions.

Example naming:

```text
char3_the
char3_and
char3_ing
```

## Feature extraction design rules

1. Extract features from every text row in the master dataset.
2. Preserve labels and metadata columns needed for modeling.
3. Do not use author labels to construct feature values.
4. Select character n-gram vocabulary from original-condition texts only to avoid rewrite leakage.
5. Use deterministic feature ordering.
6. Record feature family counts.
7. Record output hashes.
8. Do not overwrite the master text dataset.

## Required identifier columns

The feature table must preserve at least:

```text
text_id
passage_id
condition
author_id
author_name
work_id
work_title
qc_status
qc_flags
```

## Step 12 completion criteria

Step 12 is complete when:

- `stylometric_features.csv` exists;
- it has exactly 1440 rows;
- every `text_id` is unique;
- every master text row has one matching feature row;
- all four conditions have 360 feature rows;
- all six authors have 240 feature rows;
- no numeric feature columns are entirely null;
- summary, manifest, and report files exist;
- the Step 12 checker passes.
