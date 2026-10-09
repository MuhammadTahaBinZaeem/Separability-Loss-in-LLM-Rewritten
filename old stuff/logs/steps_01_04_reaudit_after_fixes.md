# Steps 1–4 Re-Audit After Fixes

## Purpose

This file records the re-audit after the Taylor-and-Francis-level review found that Steps 1–4 were technically implemented but not yet sufficiently publication-grade.

## Fixes added after the audit

### 1. Formal source-ID map

Added:

```text
metadata/source_id_map.csv
```

Purpose:

- maps every stable source ID to author, source path, raw SHA256, Step 2 decision, and main-corpus status;
- makes `metadata/extracted_text_checksums_by_id.csv` and `metadata/cleaned_text_checksums_by_id.csv` fully traceable;
- removes the earlier weakness that source IDs were implicit rather than formally mapped.

### 2. Automated consistency checker

Added:

```text
scripts/check_steps_01_04_consistency.py
```

Purpose:

- checks required files exist;
- checks the 29-source count across source inventory, raw checksums, source-ID map, extracted checksums, cleaned checksums, and cleaning report;
- checks extraction totals;
- checks cleaning totals;
- checks stale forbidden strings;
- exits with nonzero status if inconsistencies are found.

## Current journal-readiness judgment

After these fixes, Steps 1–4 are strong enough to support Step 5.

They are **not yet final paper submission grade** because final publication readiness will still require:

1. stable source provenance improvement, preferably public-domain URLs or Git LFS source preservation;
2. pinned package versions after scripts stabilize;
3. final selected passages committed in later steps;
4. final feature/result datasets and figure-generation scripts.

These are not blockers for Step 5 because Step 5 is cleaning-validation work, and it can proceed from the current cleaned-output checksums and verified cleaning script.

## Step movement decision

Proceed to Step 5.

Reason:

- Step 1 has a consistent repo audit and skeleton.
- Step 2 has a formal author-work map and updated Wilde decisions.
- Step 3 has raw and extracted-text checksum layers plus regeneration script.
- Step 4 has a verified cleaning script, cleaning report, cleaned-output checksums, and exact reproduction proof.
- A source-ID map and automated consistency checker now close the main traceability weaknesses found in the strict audit.

## Remaining limitations to carry forward

These limitations must not be hidden:

- raw PDF binaries are not committed through the connector;
- full cleaned text files are not committed to the public repo;
- some current sources are packaged PDF editions rather than ideal stable public-domain source URLs;
- exact public-domain provenance should be strengthened before final paper submission.

## Final re-audit status

```text
Steps 1–4: strong enough to proceed to Step 5.
Final-paper submission readiness: not yet, but on track.
```
