# Version 3 shift-versus-contraction replication

Apply the already specified v2 restricted mapping analysis to the corrected v3
corpus and all six active arms, keeping the session arm separate in interpretation.
This is exploratory, after v2 results were examined, not preregistered evidence.

Use valid_full, w200_middle and w300_middle, only where all eighteen works remain
estimable under the unchanged length rules. Report every unavailable planned panel.
Fit the original-training-only feature transform in each of the three work folds.
Evaluate all retained features and function words alone, for all three instructions.

Fit on twelve equally weighted training-work centroids and evaluate six held-out
work centroids per fold. Compare identity, common translation, and scalar affine
y = alpha*x + b. Estimate unrestricted alpha by centered least squares and b from
training means. No held-out work can determine alpha, intercept, vocabulary or scale.

Report all held-out errors, parameters, work IDs and training transform evidence.
Use 5,000 paired work-centroid bootstrap replicates within the six fixed authors,
conditional on the fitted mappings; intervals omit passage/training uncertainty
and are marginal, descriptive, not simultaneous confirmatory tests.

Check the exact centered-dispersion identity including residual and cross terms.
Alpha below one alone is not evidence of linguistic homogenization. Require the
restricted explanation to predict unseen-work centroids and report failures as
well as improvements. This is an empirical adequacy check, not a new theorem.
No additional transformations may be introduced to improve observed results.
