# Held-out shift/contraction explanation: codex51

Exploratory model adequacy check, not proof of a linguistic law or human-verified semantics.

| Panel | Features | Rewrite | Identity MSE | Translation MSE | Scalar-affine MSE | Training alpha by fold |
|---|---|---|---:|---:|---:|---|
| valid_full | all_features | paraphrase | 0.2114 | 0.0554 | 0.0446 | 0.755, 0.787, 0.791 |
| valid_full | all_features | modernize | 0.1954 | 0.0672 | 0.0521 | 0.736, 0.741, 0.747 |
| valid_full | all_features | simplify | 0.2195 | 0.0711 | 0.0572 | 0.752, 0.760, 0.754 |
| valid_full | function_words | paraphrase | 0.0939 | 0.0430 | 0.0326 | 0.761, 0.767, 0.778 |
| valid_full | function_words | modernize | 0.1027 | 0.0530 | 0.0416 | 0.770, 0.753, 0.768 |
| valid_full | function_words | simplify | 0.1120 | 0.0525 | 0.0440 | 0.802, 0.789, 0.780 |
| w200_middle | all_features | paraphrase | 0.1181 | 0.0496 | 0.0411 | 0.738, 0.775, 0.764 |
| w200_middle | all_features | modernize | 0.1156 | 0.0606 | 0.0448 | 0.707, 0.722, 0.721 |
| w200_middle | all_features | simplify | 0.1126 | 0.0633 | 0.0488 | 0.722, 0.748, 0.735 |
| w200_middle | function_words | paraphrase | 0.0645 | 0.0409 | 0.0328 | 0.763, 0.765, 0.759 |
| w200_middle | function_words | modernize | 0.0707 | 0.0460 | 0.0362 | 0.748, 0.733, 0.747 |
| w200_middle | function_words | simplify | 0.0789 | 0.0492 | 0.0408 | 0.777, 0.765, 0.757 |
| w300_middle | all_features | paraphrase | 0.1407 | 0.0514 | 0.0425 | 0.744, 0.785, 0.781 |
| w300_middle | all_features | modernize | 0.1290 | 0.0614 | 0.0467 | 0.708, 0.730, 0.735 |
| w300_middle | all_features | simplify | 0.1285 | 0.0649 | 0.0509 | 0.725, 0.746, 0.741 |
| w300_middle | function_words | paraphrase | 0.0767 | 0.0402 | 0.0318 | 0.761, 0.775, 0.775 |
| w300_middle | function_words | modernize | 0.0870 | 0.0504 | 0.0396 | 0.745, 0.741, 0.757 |
| w300_middle | function_words | simplify | 0.0972 | 0.0533 | 0.0439 | 0.773, 0.770, 0.750 |

Lower held-out MSE indicates better prediction of rewritten work centroids. A fitted alpha below one is not enough: the constrained explanation should improve unseen-work prediction, and residual/cross components must be considered. Paired marginal intervals are in contrasts.csv. The algebraic dispersion identity is checked numerically; a tiny closure error is arithmetic verification, not scientific validation.

All work centroids are equally weighted. Scaling is original-training-fold-specific. Intervals condition on fitted mappings and observed centroids, omit training/passage uncertainty, and are not simultaneous across these overlapping comparisons. Topic/genre and availability effects remain.
