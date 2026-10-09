# Held-out shift/contraction explanation: luna56

Exploratory model adequacy check, not proof of a linguistic law or human-verified semantics.

| Panel | Features | Rewrite | Identity MSE | Translation MSE | Scalar-affine MSE | Training alpha by fold |
|---|---|---|---:|---:|---:|---|
| valid_full | all_features | paraphrase | 0.1280 | 0.0496 | 0.0393 | 0.776, 0.787, 0.789 |
| valid_full | all_features | modernize | 0.1141 | 0.0525 | 0.0409 | 0.779, 0.779, 0.774 |
| valid_full | all_features | simplify | 0.1753 | 0.0699 | 0.0529 | 0.740, 0.725, 0.730 |
| valid_full | function_words | paraphrase | 0.0737 | 0.0402 | 0.0324 | 0.806, 0.799, 0.799 |
| valid_full | function_words | modernize | 0.0720 | 0.0401 | 0.0334 | 0.828, 0.812, 0.809 |
| valid_full | function_words | simplify | 0.1083 | 0.0537 | 0.0446 | 0.810, 0.774, 0.769 |
| w200_middle | all_features | paraphrase | 0.0839 | 0.0404 | 0.0326 | 0.773, 0.790, 0.780 |
| w200_middle | all_features | modernize | 0.0791 | 0.0480 | 0.0368 | 0.766, 0.771, 0.764 |
| w200_middle | all_features | simplify | 0.1102 | 0.0599 | 0.0445 | 0.726, 0.720, 0.716 |
| w200_middle | function_words | paraphrase | 0.0525 | 0.0345 | 0.0283 | 0.803, 0.788, 0.794 |
| w200_middle | function_words | modernize | 0.0530 | 0.0357 | 0.0305 | 0.823, 0.804, 0.802 |
| w200_middle | function_words | simplify | 0.0753 | 0.0456 | 0.0385 | 0.802, 0.771, 0.750 |
| w300_middle | all_features | paraphrase | 0.0963 | 0.0439 | 0.0351 | 0.769, 0.789, 0.787 |
| w300_middle | all_features | modernize | 0.0857 | 0.0482 | 0.0377 | 0.771, 0.777, 0.768 |
| w300_middle | all_features | simplify | 0.1260 | 0.0635 | 0.0479 | 0.722, 0.715, 0.725 |
| w300_middle | function_words | paraphrase | 0.0619 | 0.0378 | 0.0310 | 0.797, 0.798, 0.804 |
| w300_middle | function_words | modernize | 0.0622 | 0.0394 | 0.0333 | 0.814, 0.807, 0.802 |
| w300_middle | function_words | simplify | 0.0921 | 0.0517 | 0.0429 | 0.788, 0.763, 0.761 |

Lower held-out MSE indicates better prediction of rewritten work centroids. A fitted alpha below one is not enough: the constrained explanation should improve unseen-work prediction, and residual/cross components must be considered. Paired marginal intervals are in contrasts.csv. The algebraic dispersion identity is checked numerically; a tiny closure error is arithmetic verification, not scientific validation.

All work centroids are equally weighted. Scaling is original-training-fold-specific. Intervals condition on fitted mappings and observed centroids, omit training/passage uncertainty, and are not simultaneous across these overlapping comparisons. Topic/genre and availability effects remain.
