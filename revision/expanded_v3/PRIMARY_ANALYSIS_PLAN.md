# Expanded-corpus primary-method replication

This implements the existing v2 methods on the corrected v3 corpus, separately
for each of the six active arms. It is exploratory, not a new preregistration.
The model list follows the recorded scope amendment, not observed significance.

Use the original three held-out-work folds. Fit vocabulary, feature selection,
scaling, and classifiers only on original training works. Use all six fixed
author labels and the existing nearest-centroid, Gaussian NB, and shrinkage LDA
implementations. Report the full feature set and all six leave-one-family-out
ablations. No best-performing feature set or model is selected.

Each valid first output is paired to its own original. Failed outputs remain in
the denominator and availability tables, not in the valid-output estimand.
For all nine full-feature classifier/condition comparisons per arm, retain
5,000 hierarchical author-stratified work/passage bootstrap replicates and 9,999
whole-work swaps, seed 20260915. Intervals condition on fitted models and these
six authors; they do not include training uncertainty. Require all eighteen
works for inferential comparisons; otherwise explicitly report not estimable.
Holm correction spans all 54 planned tests, including unavailable tests. The
session arm is a workflow comparison and cannot establish API-model superiority.

Preserve paired centroid distances as descriptive dependent-pair summaries.
Report warning-free sensitivity without representing warnings as semantic errors.
Semantic sensitivity is a separate, review-gated step on the audited subset only.
It must use the union of independently supplied risk flags, preserve all original
ratings, and never infer that unreviewed pairs are semantically clean.

Hash the exact corpus, method code, requests, parsed outcomes, and completed
generation records. Save training-fold transform evidence, predictions, coverage,
metrics, confusion counts, per-work results, and inference tables. A replay must
reproduce all data and result files byte-for-byte; elapsed-time metadata is excluded.
