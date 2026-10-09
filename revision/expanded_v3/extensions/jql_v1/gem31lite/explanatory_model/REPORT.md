# Held-out shift/contraction explanation: gem31lite

Exploratory model adequacy check, not proof of a linguistic law or human-verified semantics.

| Panel | Features | Rewrite | Identity MSE | Translation MSE | Scalar-affine MSE | Training alpha by fold |
|---|---|---|---:|---:|---:|---|
| valid_full | all_features | paraphrase | 1.0328 | 0.1632 | 0.1011 | 0.496, 0.469, 0.458 |
| valid_full | all_features | modernize | 0.9044 | 0.1490 | 0.1039 | 0.568, 0.549, 0.528 |
| valid_full | all_features | simplify | 0.9602 | 0.1571 | 0.1095 | 0.552, 0.535, 0.528 |
| valid_full | function_words | paraphrase | 0.2589 | 0.1209 | 0.0912 | 0.632, 0.585, 0.580 |
| valid_full | function_words | modernize | 0.2210 | 0.1103 | 0.0904 | 0.698, 0.663, 0.613 |
| valid_full | function_words | simplify | 0.2329 | 0.1168 | 0.0956 | 0.692, 0.649, 0.640 |
| w200_middle | all_features | paraphrase | 0.3106 | 0.1218 | 0.0690 | 0.438, 0.412, 0.421 |
| w200_middle | all_features | modernize | 0.2364 | 0.1122 | 0.0702 | 0.498, 0.478, 0.482 |
| w200_middle | all_features | simplify | 0.2360 | 0.1183 | 0.0738 | 0.478, 0.462, 0.476 |
| w200_middle | function_words | paraphrase | 0.1687 | 0.0946 | 0.0685 | 0.592, 0.538, 0.563 |
| w200_middle | function_words | modernize | 0.1514 | 0.0871 | 0.0673 | 0.641, 0.593, 0.588 |
| w200_middle | function_words | simplify | 0.1554 | 0.0890 | 0.0684 | 0.632, 0.587, 0.609 |

Lower held-out MSE indicates better prediction of rewritten work centroids. A fitted alpha below one is not enough: the constrained explanation should improve unseen-work prediction, and residual/cross components must be considered. Paired marginal intervals are in contrasts.csv. The algebraic dispersion identity is checked numerically; a tiny closure error is arithmetic verification, not scientific validation.

All work centroids are equally weighted. Scaling is original-training-fold-specific. Intervals condition on fitted mappings and observed centroids, omit training/passage uncertainty, and are not simultaneous across these overlapping comparisons. Topic/genre and availability effects remain.

Planned controls not estimable (missing whole works): w300_middle. See the parent panel_status.json.
