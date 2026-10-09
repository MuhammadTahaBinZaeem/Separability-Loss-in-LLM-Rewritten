# Steps 1–4 Journal-Readiness Audit

## Audit purpose

This document evaluates Steps 1–4 at a stricter publication/reviewer level, not merely as a file-existence checklist.

Target publication identity:

- Applied AI / generative AI evaluation
- Quantitative linguistics / stylometry
- Reproducible computational literary dataset construction

## Overall verdict

**Steps 1–4 are technically implemented, but they are not yet fully journal-grade / Taylor-and-Francis-ready.**

They are suitable as a working research pipeline base, but several issues must be corrected before calling the data package publication-worthy.

## What is strong

### 1. Audit trail exists

The repository has step-level logs, source inventory, raw checksums, extracted-text checksums, cleaning reports, and reproduction verification.

### 2. Step 3 preservation is unusually strong for an early-stage student project

The project records:

- 29 tracked PDFs
- raw PDF SHA256 checksums
- extracted-text SHA256 checksums by source ID
- extraction totals
- extraction tool
- regeneration script

### 3. Step 4 cleaning is reproducible

The committed cleaner and config reproduce the cleaned outputs exactly:

- 29 files compared
- 29 exact SHA256 matches
- 0 mismatches

This is strong and should be preserved in the final methods section.

### 4. Conservative cleaning is methodologically appropriate

The cleaning rules explicitly protect punctuation, quotation, dashes, archaism, dialect-like spelling, and sentence rhythm. This is important because the paper measures authorial style separability.

## Main weaknesses preventing journal-grade status

### Weakness 1 — Raw PDFs are not physically stored in the repo

The repo contains checksums and metadata but not the raw PDFs themselves because the connector cannot upload large binary files.

This is acceptable for current tool constraints, but a reviewer-grade reproducibility package should either:

1. include raw sources through Git LFS, or
2. provide exact public-domain source URLs and retrieval scripts.

Current status: **not yet ideal.**

### Weakness 2 — Extracted and cleaned text files are not committed

Step 4 generated cleaned outputs locally and verifies them by checksum, but the cleaned text corpus is not committed to GitHub.

For a paper, this is only acceptable if:

- raw sources can be legally retrieved,
- extraction and cleaning scripts regenerate the same checksums,
- the final selected passages are committed later,
- the non-committed text-corpus decision is explained clearly.

Current status: **acceptable for now, but not final-publication-ready.**

### Weakness 3 — Source provenance is not yet journal-grade

Several sources appear to come from packaged PDF sites or complete-works compilations. For a quantitative linguistics / Applied AI paper, source provenance should be cleaner.

Before final paper submission, the preferred standard is:

- Project Gutenberg
- Standard Ebooks
- Internet Archive scans with stable identifiers
- author/title/publication metadata
- exact retrieval URL
- license/public-domain note

Current source metadata has filenames and checksums, but not enough stable bibliographic provenance.

Current status: **needs improvement before final paper.**

### Weakness 4 — Source ID mapping is implicit, not formal enough

`metadata/extracted_text_checksums_by_id.csv` and `metadata/cleaned_text_checksums_by_id.csv` use sanitized source IDs, but the repo should contain a direct `source_id_map.csv` mapping every `source_id` to source file, author, decision, and checksum.

Current status: **must be added before Step 5 or Step 6.**

### Weakness 5 — Dependency versions are not pinned

`requirements.txt` and `environment.yml` are useful stubs, but not journal-grade reproducibility files yet. Versions should be pinned once the scripts stabilize.

Current status: **acceptable now, but final reproducibility will need pinned versions.**

### Weakness 6 — No automated consistency checker yet

The project has many CSVs/logs/docs. Manual checking has caught stale metadata several times. A serious repo should include a script that checks:

- source counts match across files,
- source IDs are complete,
- checksum tables have 29 rows,
- no stale forbidden phrases exist,
- Step 1–4 status files agree on counts.

Current status: **needs automated guardrail.**

### Weakness 7 — Cleaning quality is not yet author-validated

Cleaning reports show no warning-flagged files, but Step 5 still must manually/algorithmically validate that cleaning preserved:

- Austen syntax
- Poe punctuation
- Twain colloquial rhythm
- Wilde aphoristic compression
- Dickens accumulation
- Shelley Gothic register

Current status: **expected; belongs to Step 5.**

## Decision

Do **not** move to Step 5 as if Steps 1–4 are fully publication-grade yet.

First, add two corrective artifacts:

1. `metadata/source_id_map.csv`
2. `scripts/check_steps_01_04_consistency.py`

Then rerun this journal-readiness audit.

## Current grade

| Area | Grade | Notes |
|---|---:|---|
| Step traceability | A- | Strong step logs and checksums |
| Raw source preservation | B | Checksums exist, binaries not stored |
| Extracted/cleaned text reproducibility | B+ | Generated and verified, not committed |
| Cleaning methodology | A- | Conservative and style-aware |
| Source provenance | C+ | Needs stable source URLs/license notes |
| Metadata consistency | B+ | Improved, but needs automated checker |
| Publication readiness | B | Good pipeline base, not final journal-grade |

## Required before Step 5

- Add formal source-ID mapping.
- Add consistency-check script.
- Add or plan stable public-domain source provenance improvement.

## Required before final paper submission

- Prefer stable public-domain source URLs over random PDF-packaged sources.
- Pin dependency versions.
- Commit final selected passages and feature datasets.
- Ensure every final table/figure can be regenerated from scripts.
- Document all exclusions and source limitations in Methods / Data Availability.
