# Held-out shift/contraction explanation: astra_session

Exploratory model adequacy check, not proof of a linguistic law or human-verified semantics.

| Panel | Features | Rewrite | Identity MSE | Translation MSE | Scalar-affine MSE | Training alpha by fold |
|---|---|---|---:|---:|---:|---|
| valid_full | all_features | paraphrase | 0.2863 | 0.0707 | 0.0511 | 0.671, 0.708, 0.710 |
| valid_full | all_features | modernize | 0.2788 | 0.0820 | 0.0577 | 0.667, 0.672, 0.667 |
| valid_full | all_features | simplify | 0.2906 | 0.0926 | 0.0618 | 0.643, 0.632, 0.625 |
| valid_full | function_words | paraphrase | 0.1358 | 0.0575 | 0.0419 | 0.704, 0.709, 0.727 |
| valid_full | function_words | modernize | 0.1447 | 0.0646 | 0.0491 | 0.729, 0.706, 0.708 |
| valid_full | function_words | simplify | 0.1633 | 0.0692 | 0.0530 | 0.722, 0.704, 0.700 |
| w200_middle | all_features | paraphrase | 0.1821 | 0.0597 | 0.0433 | 0.652, 0.676, 0.684 |
| w200_middle | all_features | modernize | 0.1745 | 0.0655 | 0.0455 | 0.648, 0.638, 0.642 |
| w200_middle | all_features | simplify | 0.1862 | 0.0725 | 0.0475 | 0.618, 0.602, 0.601 |
| w200_middle | function_words | paraphrase | 0.0937 | 0.0493 | 0.0380 | 0.713, 0.690, 0.719 |
| w200_middle | function_words | modernize | 0.0985 | 0.0522 | 0.0403 | 0.723, 0.683, 0.689 |
| w200_middle | function_words | simplify | 0.1099 | 0.0545 | 0.0415 | 0.698, 0.683, 0.674 |
| w300_middle | all_features | paraphrase | 0.2144 | 0.0647 | 0.0465 | 0.647, 0.688, 0.700 |
| w300_middle | all_features | modernize | 0.2053 | 0.0733 | 0.0503 | 0.648, 0.642, 0.650 |
| w300_middle | all_features | simplify | 0.2188 | 0.0823 | 0.0539 | 0.622, 0.606, 0.617 |
| w300_middle | function_words | paraphrase | 0.1133 | 0.0550 | 0.0407 | 0.689, 0.684, 0.716 |
| w300_middle | function_words | modernize | 0.1217 | 0.0618 | 0.0465 | 0.704, 0.669, 0.691 |
| w300_middle | function_words | simplify | 0.1374 | 0.0648 | 0.0489 | 0.694, 0.672, 0.681 |

Lower held-out MSE indicates better prediction of rewritten work centroids. A fitted alpha below one is not enough: the constrained explanation should improve unseen-work prediction, and residual/cross components must be considered. Paired marginal intervals are in contrasts.csv. The algebraic dispersion identity is checked numerically; a tiny closure error is arithmetic verification, not scientific validation.

All work centroids are equally weighted. Scaling is original-training-fold-specific. Intervals condition on fitted mappings and observed centroids, omit training/passage uncertainty, and are not simultaneous across these overlapping comparisons. Topic/genre and availability effects remain.
