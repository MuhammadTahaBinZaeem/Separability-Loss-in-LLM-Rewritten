# Step 4 Status Report

## Step

**Step 4 — Text Cleaning Rules and Metadata Removal**

## Status

Implemented, executed locally on the 29 extracted text sources, and reproduction-verified. Cleaning reports, checksum metadata, and script-verification proof are committed. The full cleaned text files were generated locally and packaged as an archive, but they are not committed into the public GitHub repository because the source files include packaged editions and connector upload constraints apply.

## Files created or updated

- `docs/cleaning_rules.md`
- `metadata/cleaning_config.json`
- `metadata/cleaning_report_schema.csv`
- `metadata/cleaning_summary.csv`
- `metadata/cleaned_text_checksums_by_id.csv`
- `scripts/01_clean_texts.py`
- `docs/data_dictionary.md`
- `logs/cleaning_report.csv`
- `logs/cleaning_output_summary.md`
- `logs/step_04_status.md`
- `logs/step_04_reproduction_verification.md`

## What Step 4 implemented

Step 4 added and ran a conservative cleaning protocol designed for stylometric research. The cleaner removes obvious PDF/source artifacts while preserving authorial style signals.

The cleaner is designed to preserve:

- punctuation
- quotation marks
- apostrophes
- em dashes / dash-like punctuation
- ellipses
- contractions
- archaic spelling
- dialect-like spelling
- paragraph breaks
- sentence rhythm
- long sentence structures

The cleaner explicitly avoids:

- lowercasing all text
- removing punctuation
- removing quotation marks
- standardizing dialect spelling
- modernizing spelling
- sentence-tokenizing and destructively rejoining prose
- removing semicolons/dashes/exclamation marks

## Cleaning run results

The cleaner was run locally against the Step 3 extracted text directory.

Summary:

- cleaned files: 29
- total raw words: 8,245,542
- total cleaned words: 8,235,425
- total raw characters: 46,746,751
- total cleaned characters: 46,089,342
- removed artifact lines: 6,954
- files with warning flags: 0
- maximum word-loss ratio: 0.01103
- maximum character-loss ratio: 0.313599

## Reproduction verification

The committed `scripts/01_clean_texts.py` and `metadata/cleaning_config.json` were run in a fresh local verification directory against the Step 3 extracted texts. The regenerated cleaned files were compared against the previously generated Step 4 cleaned outputs.

Verification result:

- cleaned files compared: 29
- exact SHA256 matches: 29
- mismatches: 0
- regenerated cleaning report matched previous cleaning report: yes

Full verification record:

```text
logs/step_04_reproduction_verification.md
```

## Why conservative cleaning matters

The paper studies authorial style separability. Over-cleaning would damage the exact signals needed for later experiments, especially:

- Austen's irony-bearing syntax
- Poe's punctuation intensity
- Twain's colloquial rhythm
- Wilde's aphoristic compression
- Dickens's descriptive accumulation
- Shelley's Gothic register

## Cleaning script

The verified cleaning script is:

```text
scripts/01_clean_texts.py
```

Expected input:

```text
data/raw/text_extracted/**/*.txt
```

Expected output:

```text
data/interim/cleaned_books/**/*.txt
```

Expected report:

```text
logs/cleaning_report.csv
```

## Current limitation

The cleaned text files were generated locally, but the full cleaned text corpus is not committed directly into this public GitHub repository. The committed reproducibility artifacts are:

- cleaning script
- cleaning rules
- cleaning configuration
- cleaning report
- cleaning summary
- cleaned-text SHA256 checksums by stable source ID
- reproduction verification log

This is sufficient to audit and regenerate the cleaned outputs when raw/extracted text files are available locally or through Git LFS.

## Step 4 completion judgment

Step 4 is complete at the reproducibility and metadata level. The actual cleaned text outputs were generated locally, checksummed, and reproduction-verified using the committed script and committed configuration; the public repo stores the audit trail and regeneration machinery rather than the full cleaned corpus.

## Next step

Step 5 should perform author-specific cleaning validation after the cleaner has been run on extracted texts. It should verify that cleaning did not damage punctuation, rhythm, dialogue, archaic spelling, dialect-like prose, or other style-bearing features.
