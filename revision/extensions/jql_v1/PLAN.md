# JQL research extension 1: loss versus displacement of author-associated signal

Recorded 2026-09-22, before running the extension's classification experiments.
This is an **exploratory, post-v2-results extension**, not a preregistration.
The Azure v2 results and both providers' QC/length patterns were already known.
An availability-only check found 316 Azure passages valid in all three rewrite
conditions; all 316 have at least 300 words in every version. No extension
classification scores were inspected to choose this plan. Gemini collection
is still running. The frozen v2 protocol, primary endpoints and results are
not replaced by this extension.

## Scientific question and contribution

An original-trained classifier's failure on rewrites does not distinguish
information loss from a changed representation of still-predictive information.
Estimate all 16 directions of a four-domain train/test matrix: original,
paraphrase, modernize and simplify. Train and test always use different works;
all versions of a passage remain on the same side of a split. The six authors
and 18 works are fixed. These are author-associated signals, not certified
topic-free style, identity proof or a causal measurement of information loss.

For each rewrite domain R, on exactly the same held-out passage IDs, report:

- transfer loss = F1(O -> O) - F1(O -> R);
- adaptation gain = F1(R -> R) - F1(O -> R);
- within-domain gap = F1(O -> O) - F1(R -> R).

The first quantity equals the sum of the other two. Adaptation gain measures
recoverability under the specified learner and sample size, not a bound on all
recoverable author information. All reverse and cross-instruction cells are
reported, even if they weaken the proposed interpretation.

## Observations, exclusions and length controls

Use each provider's intersection of technically valid outputs across all three
instructions. Retain length warnings; never reroll failed outputs. Publish an
eligibility record for every original passage, including excluded conditions,
lengths and per-author/work counts. This complete-case estimand is conditional
on output availability, and differs from the v2 per-condition paired estimand.

Seven fixed panels, without choosing the best-performing one:

1. Full texts on the valid common cohort.
2. Full texts on the subset with >=200 words in every version.
3. First 200 words on that same subset.
4. Middle 200 words on that same subset.
5. Last 200 words on that same subset.
6. Full texts on the subset with >=300 words in every version.
7. Middle 300 words on that same subset.

Use the frozen corpus word regex. Crop at word boundaries, retaining intervening
punctuation and whitespace, without padding or combining disjoint fragments.
Record zero-based source character offsets and text hashes for every view.
Comparisons with each length-matched full-text panel separate changes in sample
membership from cropping. Cropping changes content and may cut sentences;
equal word count neither aligns meaning nor removes topic effects. Overlapping
panels are sensitivity analyses, not independent replications.

## Three fixed, non-tuned pipelines

- Shared-original-coordinate stylometry plus Euclidean nearest centroid, uniform
  class priors. Fit vocabulary, constant-feature filtering and scaling only on
  original texts in the training works of that panel/fold. Reuse this coordinate
  system for all four training domains; refit only the classifier's centroids.
- Function-word subset of that same original-fitted coordinate system plus the
  same nearest-centroid classifier. This reduces reliance on content words but
  does not certify topic independence.
- Character 3-5-gram TF-IDF and linear SVM: lowercase, min_df=2, maximum 30,000
  features, sublinear term frequency, smoothed IDF and L2 row normalization;
  LinearSVC C=1, class_weight=balanced, tol=1e-4, max_iter=10000,
  dual=auto, seed=20260922. Fit vocabulary and IDF separately on each training
  domain's training works only. Here adaptation includes the representation.

Use the original three work-held-out folds; no tuning on held-out works and no
passage-random split. Missing an author or a whole work fails the panel rather
than silently reducing the label set. Report all six labels in macro-F1.

## Descriptive uncertainty and linguistic geometry

Use 5,000 paired bootstrap replicates, fixed six authors, resampling works
within each author and passages within each selected work. All matrix cells
share the same resampled observations. Intervals are marginal 95% descriptive
intervals, conditional on the fitted models and these authors; training-set
uncertainty, correlated cross-validation fits and new-author generalization
are not covered. No new confirmatory p-values or significance-based stopping.
The v2 Holm family of 18 tests remains separate and unchanged.

In the shared original-training coordinates, report held-out between-author
centroid dispersion, within-author passage dispersion, their ratio, common
centroid shift and differential author-centroid shift. Weight authors equally.
Each test fold contains only one work per author, so geometry is also sensitive
to work/topic. Publish all per-work feature changes, not only largest effects.
These are descriptive dependent quantities, not independent pairwise tests.

## Evidence and stopping rule

Run both planned providers once their accounting is complete, within existing
generation budgets. Preserve request manifests, native responses/refusals,
QC records, exact source texts, fold/view IDs, fitted-transform evidence,
predictions, metric derivations, code/environment hashes and output hashes.
The extension is offline and makes no model calls. Rerunning it must reproduce
the deterministic evidence artifacts; wall-clock metadata is not a result.

Stop this extension after the specified analyses, irrespective of their sign.
Do not rewrite the paper as submission-ready based on these exploratory data.
Before strong general claims, the investigators still need genuine independent
source/semantic review and a prospective, untouched-work validation study.
That new study needs a separately fixed corpus/design and approved budget,
not repeated additions until a desired result appears. Publication cannot be
guaranteed; the empirical outcome may warrant a narrower methodological paper.

## Literature and journal fit

Journal of Quantitative Linguistics includes quantitative stylistics and
statistical explanations of language phenomena; the proposed focus is the
measurement distinction above, not merely a new model leaderboard.
Official scope: https://www.tandfonline.com/journals/njql20

Icard et al. (2026), *Measuring Embedding Sensitivity to Authorial Style in
French*, studies literary style imitations and embedding sensitivity, including
a character-n-gram attribution validator. Our proposed comparison uses neutral
rewrite instructions, held-out works and a full training/test-domain matrix.
This is a specific methodological distinction, not a claim of being the first
study of style preservation or LLM rewriting.
Source: https://arxiv.org/html/2605.10606v1

Topic confounding remains an established concern in attribution:
Altakrori et al. (2021), https://aclanthology.org/2021.findings-emnlp.359/
