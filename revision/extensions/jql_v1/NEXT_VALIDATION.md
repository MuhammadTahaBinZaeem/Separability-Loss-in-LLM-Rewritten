# Prospective validation requirements — not collected or preregistered

This design brief is a next-step proposal, not a claim that a confirmation study
has been completed. It must be finalized and timestamped before collecting or
inspecting new validation outcomes. No new paid generation budget is authorized
by this file, and no existing spending cap is raised.

## Minimum useful independent test

Use at least two additional genuinely distinct fiction works per existing author
as untouched test works, with 20 nonoverlapping passages per work. That would
add 12 test works and 240 originals, with 1,440 planned rewrite assignments
under the same two providers and three instructions. This is a minimum design
for testing new works of these authors, not a sample-size/power guarantee or
evidence of generalization to new authors/languages. More independent works or
authors should be chosen on precision and target population, not significance.

Select eligible works and source boundaries before generating rewrites; exclude
editorial/mixed-authorship text using a genuine source review. Match prose type
where feasible and disclose unavoidable novel/story differences. Do not choose
works because a trial classifier or model rewrite performs favorably. Separate
titles in a collected volume can be distinct works; editions or chapters of an
already used work cannot become independent works merely by relabelling.

Train the already specified attribution and mapping pipelines on the discovery
works only. Keep every new work out of vocabulary selection, scaling, IDF,
parameter selection and any decision about which contrasts to emphasize.
Preserve original/rewrite pairing. Distinguish original-trained transfer,
rewrite-trained attribution and the restricted centroid-mapping prediction.

## Decisions required before execution

1. Final target population and a rights-checked, manually audited new-work list.
2. A precise primary validation estimand and a finite family of contrasts;
   smallest scientifically meaningful difference and desired precision.
3. Work-level design/precision simulation under an explicitly stated range of
   effects and heterogeneity, including null effects. Discovery estimates must
   not be treated as unbiased truths. Two test works per author may be too few.
4. A frozen failure/availability estimand and length/semantic handling rule.
   Substantial shortening is an observed provider behavior, not permission to
   keep trying new prompts until the quality check passes.
5. Native provider availability and an approved, separately capped additional
   API budget estimated from the frozen request sizes and verified pricing.
6. A documented institutional ethics/consent determination and qualified human
   source/semantic reviewers. Compensation must not depend on results.
7. A timestamped protocol, immutable test-set manifest and a rule to report all
   planned results even if the explanation fails. A local timestamp is not an
   independent registration; obtain the intended public/institutional record.

No new model, account, credential rotation, paid plan, external submission or
public dataset release is implicitly approved by this proposal. The existing
study can continue within its present authority while these choices are made.
