# Final Gutenberg Steps 1-7 Audit

## Status

The canonical Project Gutenberg source layer is now the preferred source layer for the paper.

The old PDF-derived Step 7 candidate pool remains a legacy audit layer only. The final passage-selection path should use the Gutenberg layer.

## What was fixed

### 1. Missing Gutenberg outputs

The earlier code did not generate all Gutenberg-specific metadata and logs. The pipeline now has explicit Gutenberg outputs:

- `metadata/gutenberg_raw_text_checksums.csv`
- `metadata/gutenberg_cleaned_text_checksums.csv`
- `metadata/gutenberg_cleaning_summary.csv`
- `metadata/gutenberg_cleaning_validation_metrics.csv`
- `metadata/gutenberg_author_summary.csv`
- `metadata/gutenberg_candidate_generation_summary.csv`
- `metadata/gutenberg_candidate_counts_by_author.csv`
- `metadata/gutenberg_candidate_counts_by_source.csv`
- `logs/gutenberg_candidate_generation_report.md`
- `logs/step_07_gutenberg_status.md`

### 2. Long/fragile file names

A sanitized alias map was added:

```text
metadata/gutenberg_alias_map.csv
```

It maps short aliases such as `author1_work1` to exact author, title, Gutenberg ID, and URL metadata. This avoids fragile file names while preserving full traceability.

### 3. Fetch script paths

The Gutenberg fetch script now uses repository-relative paths and the alias map. It no longer depends on machine-specific absolute paths.

### 4. Canonical migration runner

The canonical migration runner now generates Gutenberg-specific cleaning, validation, and candidate-generation outputs. It no longer relies on the old PDF-era source map.

### 5. Consistency checker

A Gutenberg-specific checker was added:

```text
scripts/check_gutenberg_steps_01_07_consistency.py
```

This checker validates:

- 12 canonical sources,
- 6 authors,
- 12 raw checksum rows,
- 12 cleaned checksum rows,
- 12 validation rows,
- 6 author summaries,
- candidate counts,
- all authors meeting the 120-candidate target,
- zero validation flags.

## Gutenberg Step 7 result

| Author | Candidates | Status |
|---|---:|---|
| Austen | 395 | pass |
| Dickens | 471 | pass |
| Poe | 255 | pass |
| Shelley | 342 | pass |
| Twain | 252 | pass |
| Wilde | 164 | pass |

Total candidate rows:

```text
1879
```

All candidate rows pass the length/sentence checks.

## Final verdict

```text
Canonical Gutenberg Steps 1-7: complete and balance-ready for Step 8.
```

## Remaining limitation

The full candidate passage CSV contains passage text and is generated locally. The repository stores summaries, checksums, metadata, and scripts. Large text-bearing files should be handled through an archive, Git LFS, release artifact, or local reproducible run.
