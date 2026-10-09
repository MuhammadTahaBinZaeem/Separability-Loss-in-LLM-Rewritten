# Human source-integrity review

Run `python -m research_v2.source_review prepare` to issue the frozen 360-item
packet. This is separate from semantic review. Do not reveal author/work/source
metadata to semantic reviewers before both blinded returns are sealed.

For each item in `blank_review.jsonl`, inspect the complete passage and its
surrounding archived source context. `revision/corpus/work_registry.csv` and
`revision/work_specs.json` identify the chosen works; source text is archived in
`revision/sources/`. Offsets refer to the builder's decoded source, not raw bytes.
Review for introductions, editorial narration, footnotes, heading fragments,
mixed/uncertain literary attribution and deviations from the specified fictional
body. Distinguish dialogue within the work from editorial or outside-authored
material. Do not certify an uncertain item just to complete the dataset.

Keep all issued fields unchanged. In your own copy, set `verdict` to `pass` or
`needs_correction` and write a substantive `notes` explanation for every item.
An administrator can provide a more usable editor without changing fields or
text; the canonical return must retain one valid JSON object per item. Record
your real/pseudonymous identity and actual completion time with timezone and
explicitly attest that you personally performed this review.

Register a genuine completed file using `python -m research_v2.source_review
ingest --help`. The importer preserves its exact bytes and hash in the ignored
`private/` directory. Do not manufacture signatures, dates or notes. The release
gate fails for absent evidence or any item needing correction. A correction must
be investigated and versioned; it must not overwrite the corpus or existing
generation records silently. Reading all 360 passages takes real human time.
