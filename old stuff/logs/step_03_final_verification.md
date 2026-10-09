# Step 3 Final Verification

## Verification result

**Step 3 is complete under the current tool constraints.**

## Verified files

The following files now form the committed Step 3 preservation package:

- `metadata/source_inventory.csv`
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

## Verified counts

- Tracked PDF sources: 29
- Original source archive PDFs: 27
- Later uploaded Wilde PDFs: 2
- PDFs attempted for text extraction: 29
- Successful extractions: 29
- Failed or empty extractions: 0
- Total extracted words: 8,245,542
- Total extracted UTF-8 text bytes: 47,056,686

## Verified checksum layers

Step 3 now preserves two checksum layers:

1. Raw PDF checksums in `metadata/raw_file_checksums.csv`.
2. Extracted-text checksums in `metadata/extracted_text_checksums_by_id.csv`.

The extracted-text checksum table uses sanitized source IDs because the connector repeatedly blocked a full filename-based checksum table. This does not remove traceability: source IDs are ordered consistently with the source inventory and raw checksum tables.

## Verified stale metadata removal

The old preliminary `metadata/text_extraction_manifest.csv` was deleted because it contained stale extraction-state rows. The current extraction truth is represented by:

- `metadata/text_extraction_status_summary.csv`
- `metadata/extracted_text_checksums_by_id.csv`
- `logs/raw_preservation_log.md`

## Known limitation

Raw PDFs are not physically committed through the connector because direct large binary upload is unsupported. The repo contains checksums and regeneration scripts. Full binary preservation still requires Git LFS from a local machine.

## Step 3 closure

Step 3 may be considered closed. Step 4 can begin from this preservation state.
