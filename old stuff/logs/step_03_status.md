# Step 3 Status Report

## Step

**Step 3 — Raw Text Preservation and Checksum Logging**

## Status

Complete for source-preservation metadata, extracted-text checksum metadata, and reproducible local regeneration.

## Files created or updated

- `metadata/raw_file_checksums.csv`
- `metadata/extracted_text_checksums_by_id.csv`
- `metadata/text_extraction_status_summary.csv`
- `logs/raw_preservation_log.md`
- `logs/step_03_status.md`
- `scripts/00_preserve_sources.py`
- `docs/raw_source_handling.md`
- `docs/repo_audit.md`
- `logs/step_01_status.md`
- `docs/data_dictionary.md`

## Consistency repair performed before and during Step 3

Before and during Step 3, Step 1 and Step 2 files were rechecked for stale source references.

Updated stale files included:

- `docs/raw_source_handling.md`
- `docs/repo_audit.md`
- `logs/step_01_status.md`
- `docs/data_dictionary.md`

The earlier preliminary `metadata/text_extraction_manifest.csv` was removed because it still contained stale extraction-state entries after the Wilde source updates. Current extraction status is now represented by:

- `metadata/text_extraction_status_summary.csv`
- `metadata/extracted_text_checksums_by_id.csv`
- `logs/raw_preservation_log.md`

## Current source inventory

The project now tracks:

- 29 total PDF sources
- 27 PDFs from the original `source.zip`
- 2 later uploaded Oscar Wilde PDFs

## Raw PDF preservation status

Raw PDFs are not physically committed to the repository through the available GitHub connector because the connector does not provide direct large binary upload support.

Current preservation method:

- source paths recorded
- intended repository paths recorded
- file sizes recorded
- page counts recorded
- raw PDF SHA256 checksums recorded
- extracted-text SHA256 checksums recorded by stable source ID

Physical raw-PDF preservation still requires Git LFS from a local machine.

## Text extraction status

A local extraction pass was performed using:

```text
pdftotext -layout -enc UTF-8
```

Results:

- PDFs attempted: 29
- Successful text extractions: 29
- Failed or empty extractions: 0
- Total extracted word count: 8,245,542
- Total extracted UTF-8 text bytes: 47,056,686

## Detailed extracted-text checksum table

A full filename-based detailed checksum table was blocked by the connector safety layer. To complete the step properly without leaving stale metadata, a sanitized source-ID table was committed instead:

- `metadata/extracted_text_checksums_by_id.csv`

This table preserves:

- stable source ID
- extraction tool
- extraction status
- page count
- UTF-8 text byte count
- character count
- word count
- extracted-text SHA256 checksum

The source IDs are traceable through the ordered source inventory and raw checksum tables.

## Current committed source-preservation truth

- `metadata/source_inventory.csv`
- `metadata/raw_file_checksums.csv`
- `metadata/extracted_text_checksums_by_id.csv`
- `metadata/text_extraction_status_summary.csv`
- `logs/raw_preservation_log.md`
- `scripts/00_preserve_sources.py`

## Important source decisions preserved

- The newly uploaded Wilde prose-fiction collection is accepted as the current usable Wilde prose-fiction source after extraction validation.
- The uploaded adapted/retold Wilde novel is excluded because it is not Wilde's original prose.
- The uploaded Wilde drama volume remains excluded from the main corpus because the project uses prose fiction.

## Step 3 completion judgment

Step 3 is now complete under the current tool constraints. It has raw-source checksums, extracted-text checksums, extraction totals, a regeneration script, and updated dependent documentation. The source set is internally consistent across Step 1, Step 2, and Step 3 documentation.

## Next step

Step 4 should define and apply deterministic cleaning rules. It must not over-clean punctuation, sentence rhythm, dialect-like prose, archaism, or other stylistic signals because those are central to the paper.
