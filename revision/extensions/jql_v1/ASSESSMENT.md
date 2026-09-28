# Scientific assessment for Journal of Quantitative Linguistics

Checkpoint: 2026-09-22. Research first; manuscript polishing is paused.

## Judgment

The study now has a more defensible question than a classifier leaderboard:
**How much observed attribution loss reflects a shifted but recoverable signal,
and how much remains after within-rewrite training and length controls?**
The new exploratory evidence is promising for a narrower methodological paper.
It is not yet sufficient to call the manuscript submission-ready or guarantee
acceptance at JQL, much less a top-journal outcome.

JQL explicitly requires advancement in quantitative understanding of language;
an ad hoc computational application is not enough. The measurement distinction
and falsifiable shift/contraction explanation are candidate contributions, not
claims that established affine algebra is a new theorem.
[Official scope](https://www.tandfonline.com/journals/njql20/about-this-journal).

## What was actually extended

On Azure's 316 passages with usable outputs in all three instructions, covering
all 18 works and six authors, the extension computes all 16 train/test-domain
directions for three fixed pipelines and seven full/length-control panels.
It preserves 106,176 passage-level held-out predictions, 336 matrix cells and
189 descriptive paired contrasts. These are repeated analyses of the same
observations, **not 106,176 independently collected examples**.

Every result is connected to source/rewrite hashes, exact view offsets,
training/test work IDs, fitted vocabulary/scaling/IDF evidence and the code/
environment. `transfer_verify.py` re-derives cohorts, views, all scores and
paired intervals, and refits the transforms. A separate explanatory analysis
fits 162 restricted mappings and records 972 held-out work predictions.

The v2 frozen primary analysis is not replaced. Extensions were planned after
seeing v2 results and are labelled exploratory. Missing native responses,
refusals and output-quality failures are not generated away or hidden.

## What the Azure evidence says

With full stylometry and nearest centroids, simplification gives macro-F1
0.635 for original -> original, 0.418 for original -> simplify and 0.566 for
simplify -> simplify. The transfer loss of about 0.217 decomposes into roughly
0.148 adaptation gain and 0.069 remaining within-domain gap. The paired,
conditional marginal interval for adaptation gain is approximately 0.081–0.223.

The character 3–5-gram SVM is stronger on originals (0.857) and reaches 0.703
when trained and tested on simplifications, versus 0.641 in original-to-simplify
transfer. Thus recovery depends on the representation/learner, and a remaining
gap persists. It is not defensible to equate the original-trained loss with
wholesale destruction of author style. All three instructions, all pipelines
and every length sensitivity are reported, including smaller or uncertain
contrasts. Values refer to this common cohort, not the v2 per-condition samples.

Across the prespecified explanatory panels/families, a fitted common shift
plus scalar rescaling predicts held-out rewritten work centroids better in
mean squared error than a shift alone. Full-feature training slopes are around
0.77–0.78 for paraphrase, 0.80–0.81 for modernization and 0.66–0.70 for
simplification. This motivates testing a restricted convergence hypothesis;
it does not establish a general linguistic law. All paired intervals and
residual/cross-term components are retained in the explanatory output folder.

## Why more validation is still needed

- Only Azure currently has complete observation accounting. The second model
  remains incomplete and its substantial shortening makes cross-provider
  inference particularly sensitive to length and semantic preservation.
- Three works per author is a real improvement over passage-random validation,
  but still only 18 work units and six historically selected English authors.
  The exploratory discovery data are not an untouched confirmation set.
- Complete-case filtering excludes 44 originals from the extension. Failure
  patterns may select easier or otherwise unusual material. This is not a
  full intention-to-rewrite or causal estimand.
- Neither character features nor function words guarantee topic independence.
  Crops do not ensure matched semantic content. Centroid regression has noisy
  predictors/outcomes; an attenuated slope is not by itself proof of stylistic
  contraction. The fitted models are deliberately restricted approximations.
- Marginal bootstrap intervals are conditional on fitted models and fixed
  authors, not simultaneous, and do not account for training-set uncertainty.
- AI-assisted source checks do not replace the required independent human
  source review. The two independent semantic reviews are still unperformed.
- A final reproducible release needs actual author/affiliation information,
  rights/license decisions, real review records and a published archive DOI.
  A local ZIP, clean hashes or passing software tests cannot certify integrity
  of human provenance or confer scientific validity by themselves.

## Stop/go decision

Do not write a submission claiming universal separability loss now. Finish the
existing two-model evidence when the provider permits, apply these same locked
extension choices to the second model, and obtain the genuine reviews described
in `../../annotations/RECRUITMENT.md` and `../../source_review/INSTRUCTIONS.md`.
Then validate a narrowly stated hypothesis on untouched works under a separate
prospective protocol (see NEXT_VALIDATION.md). If that evidence fails to support
the explanation, narrow or reject the claim; do not keep changing analyses or
adding data until a desired significance threshold is crossed.

The separate supplied Dr. Rukaiza article is reserved as a later writing
reference. It has not been used as evidence, a dataset, or an instruction source
for these experiments. The user's report of its rejection is not independently
verified here. Its central practical lesson is addressed through the explicit
data -> code -> predictions -> results audit trail, not by borrowing results.
