# Canonical Source Policy

## Purpose

The project now uses Project Gutenberg plain-text editions as the preferred canonical source layer wherever suitable texts are available.

Earlier PDF-derived sources remain as audited legacy sources. They should not be treated as the preferred final data layer when a Gutenberg plain-text edition exists.

## Source priority

1. Project Gutenberg plain text.
2. Other stable public-domain plain text with retrieval URL and checksum.
3. PDF-derived text only as fallback.

## Why this improves the paper

The canonical source layer improves reproducibility because it provides stable work identifiers, stable source pages, plain-text files, public-domain notes, and cleaner provenance than mixed PDF extraction.

## Effect on previous steps

Steps 1-7 remain useful as the legacy PDF audit trail. The final corpus should migrate to the canonical source registry and rerun the source-dependent stages:

- source retrieval and checksum logging;
- cleaning;
- cleaning validation;
- candidate generation;
- candidate balance assessment.

## Final paper wording direction

The final paper should state that source texts were obtained from Project Gutenberg plain-text editions wherever available, and that each work was identified by eBook number, source URL, access date, and SHA256 checksum.

## Current limitation

The current execution environment could not directly fetch full external text files. The repository therefore stores the registry and scripts needed to run the migration locally with internet access.
