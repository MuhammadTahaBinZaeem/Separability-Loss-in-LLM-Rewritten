# Held-out shift/contraction explanation: azure_replication

Exploratory model adequacy check, not proof of a linguistic law or human-verified semantics.

| Panel | Features | Rewrite | Identity MSE | Translation MSE | Scalar-affine MSE | Training alpha by fold |
|---|---|---|---:|---:|---:|---|
| valid_full | all_features | paraphrase | 0.0913 | 0.0519 | 0.0400 | 0.768, 0.780, 0.783 |
| valid_full | all_features | modernize | 0.0897 | 0.0457 | 0.0357 | 0.797, 0.797, 0.807 |
| valid_full | all_features | simplify | 0.1980 | 0.0886 | 0.0632 | 0.693, 0.656, 0.682 |
| valid_full | function_words | paraphrase | 0.0679 | 0.0397 | 0.0314 | 0.809, 0.789, 0.804 |
| valid_full | function_words | modernize | 0.0580 | 0.0342 | 0.0282 | 0.844, 0.812, 0.841 |
| valid_full | function_words | simplify | 0.1276 | 0.0647 | 0.0525 | 0.778, 0.719, 0.754 |
| w200_middle | all_features | paraphrase | 0.0678 | 0.0442 | 0.0345 | 0.759, 0.771, 0.769 |
| w200_middle | all_features | modernize | 0.0675 | 0.0393 | 0.0308 | 0.785, 0.786, 0.784 |
| w200_middle | all_features | simplify | 0.1381 | 0.0714 | 0.0521 | 0.675, 0.659, 0.682 |
| w200_middle | function_words | paraphrase | 0.0499 | 0.0365 | 0.0295 | 0.797, 0.778, 0.791 |
| w200_middle | function_words | modernize | 0.0428 | 0.0302 | 0.0248 | 0.824, 0.804, 0.823 |
| w200_middle | function_words | simplify | 0.0906 | 0.0562 | 0.0468 | 0.755, 0.729, 0.764 |
| w300_middle | all_features | paraphrase | 0.0780 | 0.0471 | 0.0364 | 0.766, 0.770, 0.778 |
| w300_middle | all_features | modernize | 0.0771 | 0.0412 | 0.0324 | 0.790, 0.789, 0.806 |
| w300_middle | all_features | simplify | 0.1631 | 0.0766 | 0.0550 | 0.676, 0.653, 0.688 |
| w300_middle | function_words | paraphrase | 0.0589 | 0.0378 | 0.0304 | 0.810, 0.780, 0.796 |
| w300_middle | function_words | modernize | 0.0510 | 0.0326 | 0.0268 | 0.832, 0.802, 0.831 |
| w300_middle | function_words | simplify | 0.1097 | 0.0594 | 0.0486 | 0.760, 0.721, 0.758 |

Lower held-out MSE indicates better prediction of rewritten work centroids. A fitted alpha below one is not enough: the constrained explanation should improve unseen-work prediction, and residual/cross components must be considered. Paired marginal intervals are in contrasts.csv. The algebraic dispersion identity is checked numerically; a tiny closure error is arithmetic verification, not scientific validation.

All work centroids are equally weighted. Scaling is original-training-fold-specific. Intervals condition on fitted mappings and observed centroids, omit training/passage uncertainty, and are not simultaneous across these overlapping comparisons. Topic/genre and availability effects remain.
