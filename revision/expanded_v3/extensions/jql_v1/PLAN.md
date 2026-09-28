# Version 3 transfer and length-control analysis

This applies the existing JQL exploratory analysis to the separately frozen
corrected corpus. The six requested arms are defined by generation_plan.json and
scope_amendment.json. Source replacements, previously seen results and reused
v2 observations are disclosed in ../../PROTOCOL.md. This is not a new confirmatory
preregistration. Session-generated Astra outputs are reported separately from API arms.

Use all three pre-existing pipelines, four training/testing domains and all seven
planned length panels in research_v2/transfer_extension.py. Preserve 18 works and
six authors in every estimable panel. Availability is determined from technical
QC and word counts only. Unavailable panels retain their planned thresholds and
explicit missing-work counts. Do not replace them with more favourable subsets.

Use 5,000 paired hierarchical bootstrap replicates; intervals remain conditional
on fitted learners and the fixed authors. No new confirmatory p-values or
significance-based model selection are introduced. Every transform fits only
training works; predictions, raw views and transforms are archived and replayed.
The frozen v2 results remain a separate analysis, not silently overwritten.

Run: `.venv/Scripts/python.exe -m research_v2.expanded_analysis run --models gem31lite`.
Verify: `.venv/Scripts/python.exe -m research_v2.expanded_analysis verify --models gem31lite`.
Replay: `.venv/Scripts/python.exe -m research_v2.expanded_analysis replay --models gem31lite`.

The complete review batch and review-dependent sensitivity/independence checks
must still be completed before manuscript claims or publication readiness.
