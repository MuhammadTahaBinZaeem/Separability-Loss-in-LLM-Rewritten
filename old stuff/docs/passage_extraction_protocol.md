# Step 6 Passage Extraction Protocol

## Step

**Step 6 — Passage Extraction Protocol**

## Purpose

Step 6 defines the exact rules for extracting candidate passages from cleaned literary texts. It does not finalize the 360-passage corpus yet. That happens in Step 8 after a larger candidate pool is generated in Step 7 and balanced.

The goal is to make passage extraction deterministic, traceable, and defensible for a paper on authorial style separability loss.

## Target final corpus

The planned original-passage corpus remains:

```text
6 authors × 60 passages = 360 original passages
```

The candidate pool generated in Step 7 should be larger than the final dataset:

```text
minimum target candidate pool: 6 authors × 120 candidates = 720 candidate passages
```

This allows Step 8 to select a balanced final set.

## Passage length rule

Preferred passage length:

```text
450–650 words
```

Hard minimum:

```text
400 words
```

Hard maximum:

```text
700 words
```

The extraction script should aim for approximately 550 words per candidate passage, extending to sentence/paragraph boundaries where possible.

## Unit of extraction

Preferred unit:

1. paragraph-aware passage,
2. sentence-boundary safe,
3. non-overlapping.

The extractor should avoid cutting mid-sentence if possible. If paragraph boundaries produce passages that are too short or too long, sentence-boundary segmentation may be used.

## Non-overlap rule

Candidate passages from the same work/source must not overlap.

Minimum gap between candidates from the same source:

```text
at least 150 words
```

This prevents near-duplicate neighboring passages from inflating author separability.

## Source eligibility rule

Use only sources marked as eligible in `metadata/source_id_map.csv`.

Allowed statuses:

- `eligible_main`
- `eligible_backup`
- `eligible_container`
- `eligible_main_or_backup`

Excluded statuses:

- `excluded`

Excluded sources may remain in metadata for audit purposes, but they must not enter candidate passage generation.

## Genre rule

Main corpus should use prose fiction only.

Exclude from main passage generation:

- drama
- poetry
- essays
- reviews
- travel writing
- biography
- editorial introductions
- advertisements
- tables of contents
- indexes
- retellings/adaptations by another author
- collaborative texts unless explicitly justified as backup

## Complete-works/container handling

Some sources are complete-works PDFs rather than single-work files. These require special handling in later extraction:

- Austen complete works: extract only selected novels or clearly separated novel sections.
- Poe complete works: extract selected prose fiction tales; exclude poems, essays, reviews.
- Shelley complete works: extract novels/fiction; exclude travel writing, essays, biographies, poems, adaptations.

The candidate extractor must preserve `source_id`, and later Step 7/8 must assign `work_id` once boundaries are identified.

## Author target strategy

### Austen

Main candidates:

- *Pride and Prejudice*
- *Emma*

Backups:

- *Sense and Sensibility*
- *Mansfield Park*
- *Persuasion*
- *Northanger Abbey*

Validation focus: preserve syntax, punctuation, semicolons, quotation, and social-narrative rhythm.

### Dickens

Main candidates:

- *Great Expectations*
- *Oliver Twist*

Backups:

- other eligible Dickens novels and short fiction listed in `metadata/source_id_map.csv`.

Validation focus: preserve descriptive accumulation, long sentence structure, comma density, quotation material.

### Poe

Main candidates:

- selected prose fiction tales.

Backup:

- *The Narrative of Arthur Gordon Pym of Nantucket* if short-story segmentation is insufficient.

Validation focus: preserve punctuation intensity, dash/semicolon material, sentence-rhythm variation.

### Twain

Main candidate:

- *Adventures of Huckleberry Finn*.

Current limitation:

- Twain remains one-work limited unless another Twain prose source is added.

Validation focus: preserve colloquial rhythm, apostrophes, contractions, quotation density.

### Shelley

Main candidates:

- *Frankenstein* 1818
- *The Last Man*

Backups:

- *Valperga*
- *Lodore*
- *Falkner*
- selected short fiction if needed.

Validation focus: preserve Gothic register, long sentences, elevated diction, abstract lexical markers.

### Wilde

Current usable source:

- *Lord Arthur Savile's Crime and Other Stories*.

Excluded:

- Wilde drama volume.
- adapted/retold *Dorian Gray* upload.

Desired but not currently available:

- original public-domain *The Picture of Dorian Gray*.

Validation focus: preserve aphoristic compression, quotation, polished sentence balance.

## Required candidate passage metadata

Every candidate passage in Step 7 must include:

- `candidate_id`
- `source_id`
- `author_id`
- `author_name`
- `work_id`
- `work_title`
- `source_path`
- `candidate_index_within_source`
- `start_word_index`
- `end_word_index`
- `word_count`
- `sentence_count`
- `paragraph_count`
- `start_char`
- `end_char`
- `dialogue_marker_count`
- `dialogue_marker_per_1000w`
- `punctuation_per_1000w`
- `semicolon_per_1000w`
- `dash_per_1000w`
- `apostrophe_per_1000w`
- `mean_sentence_words`
- `long_sentence_ratio`
- `extraction_rule_version`
- `candidate_status`
- `exclusion_reason`
- `text`

## Candidate status values

Allowed values:

- `candidate_unreviewed`
- `candidate_pass_length`
- `candidate_fail_length`
- `candidate_fail_source_excluded`
- `candidate_fail_metadata_boundary`
- `candidate_fail_low_sentence_count`
- `candidate_fail_excessive_artifact_signal`
- `selected_final`
- `excluded_balance`
- `excluded_manual_review`

## Balance constraints for Step 8

Step 7 only creates candidate passages. Step 8 must select final passages while balancing:

- author count,
- work distribution,
- passage length,
- dialogue-marker density,
- sentence count,
- punctuation density,
- section spread,
- source/work diversity where possible.

## Randomness rule

If random sampling is used, it must use a fixed seed:

```text
seed = 20260526
```

However, deterministic sequential extraction is preferred for the candidate pool, with final balancing handled later.

## Output expectations for Step 7

Step 7 should generate:

```text
data/interim/candidate_passages.csv
metadata/candidate_passage_metadata.csv
logs/candidate_generation_report.md
```

## Step 6 completion standard

Step 6 is complete when the repository contains:

- this protocol document,
- a candidate passage schema,
- an extraction configuration,
- a deterministic extraction script scaffold,
- a Step 6 status report,
- updated data dictionary entries.

Actual candidate generation is Step 7, not Step 6.
