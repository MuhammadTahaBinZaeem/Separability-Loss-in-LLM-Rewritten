# Raw source handling note

The original uploaded source archive contained 27 PDF files. Two additional Oscar Wilde PDFs were uploaded later, bringing the current tracked source inventory to **29 PDF files**.

The GitHub connector available in this chat can create/update UTF-8 text files, but it does not expose a direct local binary-file streaming upload action for large PDFs.

For traceability, this repository stores:

1. `metadata/source_inventory.csv` — source paths, planned repository paths, byte sizes, modification notes, and SHA256 checksums for all tracked PDFs.
2. `metadata/raw_file_checksums.csv` — Step 3 raw-file preservation checksum table with page counts and preservation status.
3. `metadata/text_extraction_status_summary.csv` — compact current extraction-status summary for all tracked PDFs.
4. `metadata/extracted_text_checksums_by_id.csv` — sanitized Step 3 extracted-text checksum table using stable source IDs.
5. `logs/raw_preservation_log.md` — human-readable Step 3 preservation summary.
6. `scripts/00_preserve_sources.py` — local regeneration script for raw checksum and extraction summary metadata.

Recommended raw-PDF preservation route outside this connector:

```bash
mkdir -p data/raw/pdf
unzip source.zip -d /tmp/litpaper_source
rsync -av /tmp/litpaper_source/source/ data/raw/pdf/
# manually copy later uploaded Wilde PDFs into data/raw/pdf/Oscarwilde/
git lfs install
git lfs track "*.pdf"
git add .gitattributes data/raw/pdf metadata/source_inventory.csv metadata/raw_file_checksums.csv
git commit -m "Add raw PDF sources via Git LFS"
git push
```

For the actual research pipeline, text extracted from the PDFs should be used as the computational source, while the raw PDFs remain auditable by checksum.

## Current source status after Step 3

- Current tracked PDFs: 29
- Original source-archive PDFs: 27
- Later uploaded Wilde PDFs: 2
- Raw PDFs physically uploaded to GitHub through connector: no, binary upload unsupported by connector
- Raw PDF traceability status: inventoried by path, size, page count, and SHA256 checksum
- Text extraction tool used in Step 3: `pdftotext -layout -enc UTF-8`
- Text extraction status after Step 3: 29/29 extracted locally and checksummed
- Total extracted word count: 8,245,542
- Total extracted UTF-8 text bytes: 47,056,686

## Removed stale metadata

The preliminary `metadata/text_extraction_manifest.csv` was removed because it contained stale extraction-state rows after the source set changed. Current extraction metadata is represented by:

- `metadata/text_extraction_status_summary.csv`
- `metadata/extracted_text_checksums_by_id.csv`

## Important source decisions

- The newly uploaded Wilde prose-fiction collection is accepted as the current usable Wilde prose source after extraction validation.
- The uploaded adapted/retold Wilde novel is excluded because it is not Wilde's original prose.
- The uploaded Wilde drama volume remains excluded because the main corpus is prose fiction.
