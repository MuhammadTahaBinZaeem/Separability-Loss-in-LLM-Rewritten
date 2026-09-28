# Held-out shift/contraction explanation: azure_replication

Exploratory model adequacy check, not proof of a linguistic law or human-verified semantics.

| Panel | Features | Rewrite | Identity MSE | Translation MSE | Scalar-affine MSE | Training alpha by fold |
|---|---|---|---:|---:|---:|---|
| valid_full | all_features | paraphrase | 0.0910 | 0.0519 | 0.0400 | 0.771, 0.782, 0.782 |
| valid_full | all_features | modernize | 0.0898 | 0.0456 | 0.0357 | 0.800, 0.798, 0.807 |
| valid_full | all_features | simplify | 0.1978 | 0.0882 | 0.0629 | 0.696, 0.656, 0.681 |
| valid_full | function_words | paraphrase | 0.0681 | 0.0397 | 0.0315 | 0.813, 0.791, 0.802 |
| valid_full | function_words | modernize | 0.0581 | 0.0342 | 0.0282 | 0.847, 0.814, 0.840 |
| valid_full | function_words | simplify | 0.1276 | 0.0646 | 0.0523 | 0.782, 0.720, 0.753 |
| w200_middle | all_features | paraphrase | 0.0676 | 0.0442 | 0.0345 | 0.757, 0.772, 0.769 |
| w200_middle | all_features | modernize | 0.0673 | 0.0390 | 0.0307 | 0.785, 0.789, 0.785 |
| w200_middle | all_features | simplify | 0.1389 | 0.0715 | 0.0521 | 0.672, 0.659, 0.681 |
| w200_middle | function_words | paraphrase | 0.0502 | 0.0371 | 0.0299 | 0.796, 0.778, 0.789 |
| w200_middle | function_words | modernize | 0.0430 | 0.0305 | 0.0250 | 0.824, 0.805, 0.823 |
| w200_middle | function_words | simplify | 0.0910 | 0.0564 | 0.0465 | 0.752, 0.727, 0.762 |
| w300_middle | all_features | paraphrase | 0.0777 | 0.0472 | 0.0365 | 0.764, 0.769, 0.776 |
| w300_middle | all_features | modernize | 0.0770 | 0.0412 | 0.0325 | 0.789, 0.789, 0.806 |
| w300_middle | all_features | simplify | 0.1630 | 0.0764 | 0.0547 | 0.675, 0.651, 0.688 |
| w300_middle | function_words | paraphrase | 0.0592 | 0.0382 | 0.0306 | 0.810, 0.781, 0.793 |
| w300_middle | function_words | modernize | 0.0512 | 0.0328 | 0.0270 | 0.831, 0.802, 0.832 |
| w300_middle | function_words | simplify | 0.1096 | 0.0594 | 0.0483 | 0.759, 0.719, 0.758 |

Lower held-out MSE indicates better prediction of rewritten work centroids. A fitted alpha below one is not enough: the constrained explanation should improve unseen-work prediction, and residual/cross components must be considered. Paired marginal intervals are in contrasts.csv. The algebraic dispersion identity is checked numerically; a tiny closure error is arithmetic verification, not scientific validation.

All work centroids are equally weighted. Scaling is original-training-fold-specific. Intervals condition on fitted mappings and observed centroids, omit training/passage uncertainty, and are not simultaneous across these overlapping comparisons. Topic/genre and availability effects remain.
