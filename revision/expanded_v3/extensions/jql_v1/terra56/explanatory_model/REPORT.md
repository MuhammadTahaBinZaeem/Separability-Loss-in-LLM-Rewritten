# Held-out shift/contraction explanation: terra56

Exploratory model adequacy check, not proof of a linguistic law or human-verified semantics.

| Panel | Features | Rewrite | Identity MSE | Translation MSE | Scalar-affine MSE | Training alpha by fold |
|---|---|---|---:|---:|---:|---|
| valid_full | all_features | paraphrase | 0.1046 | 0.0472 | 0.0395 | 0.788, 0.823, 0.828 |
| valid_full | all_features | modernize | 0.1093 | 0.0538 | 0.0424 | 0.774, 0.787, 0.781 |
| valid_full | all_features | simplify | 0.1426 | 0.0640 | 0.0495 | 0.752, 0.760, 0.757 |
| valid_full | function_words | paraphrase | 0.0645 | 0.0400 | 0.0339 | 0.819, 0.819, 0.836 |
| valid_full | function_words | modernize | 0.0705 | 0.0397 | 0.0339 | 0.832, 0.830, 0.825 |
| valid_full | function_words | simplify | 0.0907 | 0.0456 | 0.0388 | 0.827, 0.811, 0.808 |
| w200_middle | all_features | paraphrase | 0.0749 | 0.0425 | 0.0358 | 0.784, 0.813, 0.802 |
| w200_middle | all_features | modernize | 0.0730 | 0.0470 | 0.0376 | 0.770, 0.769, 0.768 |
| w200_middle | all_features | simplify | 0.0912 | 0.0534 | 0.0419 | 0.744, 0.744, 0.745 |
| w200_middle | function_words | paraphrase | 0.0488 | 0.0365 | 0.0312 | 0.814, 0.806, 0.809 |
| w200_middle | function_words | modernize | 0.0535 | 0.0372 | 0.0323 | 0.825, 0.812, 0.805 |
| w200_middle | function_words | simplify | 0.0663 | 0.0423 | 0.0368 | 0.816, 0.797, 0.796 |
| w300_middle | all_features | paraphrase | 0.0842 | 0.0444 | 0.0374 | 0.784, 0.819, 0.815 |
| w300_middle | all_features | modernize | 0.0823 | 0.0492 | 0.0394 | 0.776, 0.782, 0.778 |
| w300_middle | all_features | simplify | 0.1054 | 0.0580 | 0.0452 | 0.741, 0.750, 0.755 |
| w300_middle | function_words | paraphrase | 0.0566 | 0.0393 | 0.0336 | 0.814, 0.815, 0.823 |
| w300_middle | function_words | modernize | 0.0616 | 0.0388 | 0.0336 | 0.831, 0.822, 0.816 |
| w300_middle | function_words | simplify | 0.0790 | 0.0459 | 0.0391 | 0.808, 0.798, 0.796 |

Lower held-out MSE indicates better prediction of rewritten work centroids. A fitted alpha below one is not enough: the constrained explanation should improve unseen-work prediction, and residual/cross components must be considered. Paired marginal intervals are in contrasts.csv. The algebraic dispersion identity is checked numerically; a tiny closure error is arithmetic verification, not scientific validation.

All work centroids are equally weighted. Scaling is original-training-fold-specific. Intervals condition on fitted mappings and observed centroids, omit training/passage uncertainty, and are not simultaneous across these overlapping comparisons. Topic/genre and availability effects remain.
