# Manuscript Results Summary


## Core transfer result


| model | condition | original_test_macro_f1 | rewrite_test_macro_f1 | macro_f1_loss_vs_original | macro_f1_loss_95ci | bootstrap_nonpositive_rate | rows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| nearest_centroid | paraphrase | 0.776931 | 0.395797 | 0.381134 | [0.261805, 0.502832] | 0.0 | 54 |
| nearest_centroid | modernize | 0.776931 | 0.56072 | 0.216211 | [0.099657, 0.346396] | 0.0 | 54 |
| nearest_centroid | simplify | 0.776931 | 0.463636 | 0.313295 | [0.193906, 0.448514] | 0.0 | 54 |
| diagonal_gaussian_nb | paraphrase | 0.760859 | 0.423931 | 0.336928 | [0.200441, 0.471742] | 0.0 | 54 |
| diagonal_gaussian_nb | modernize | 0.760859 | 0.590047 | 0.170812 | [0.050751, 0.304165] | 0.0018 | 54 |
| diagonal_gaussian_nb | simplify | 0.760859 | 0.449798 | 0.311061 | [0.172679, 0.45574] | 0.0 | 54 |
| linear_discriminant_shrinkage | paraphrase | 0.776931 | 0.390232 | 0.386699 | [0.265921, 0.504839] | 0.0 | 54 |
| linear_discriminant_shrinkage | modernize | 0.776931 | 0.598237 | 0.178694 | [0.071128, 0.301491] | 0.0002 | 54 |
| linear_discriminant_shrinkage | simplify | 0.776931 | 0.419634 | 0.357297 | [0.229058, 0.496117] | 0.0 | 54 |


## Semantic-fidelity audit


| condition | rows | meaning_preservation_mean_1_5 | usable_rate | semantic_issue_rate |
| --- | --- | --- | --- | --- |
| ALL | 108 | 4.527778 | 99.1% | 15.7% |
| modernize | 36 | 4.638889 | 100.0% | 8.3% |
| paraphrase | 36 | 4.305556 | 97.2% | 19.4% |
| simplify | 36 | 4.638889 | 100.0% | 19.4% |


## Semantic-risk sensitivity


| sensitivity_filter | condition | rows | excluded_rows | test_macro_f1 | macro_f1_loss_vs_original |
| --- | --- | --- | --- | --- | --- |
| all_rows | paraphrase | 54 | 0 | 0.395797 | 0.381134 |
| all_rows | modernize | 54 | 0 | 0.56072 | 0.216211 |
| all_rows | simplify | 54 | 0 | 0.463636 | 0.313295 |
| exclude_unusable | paraphrase | 54 | 0 | 0.395797 | 0.381134 |
| exclude_unusable | modernize | 54 | 0 | 0.56072 | 0.216211 |
| exclude_unusable | simplify | 54 | 0 | 0.463636 | 0.313295 |
| exclude_any_semantic_issue | paraphrase | 54 | 0 | 0.395797 | 0.381134 |
| exclude_any_semantic_issue | modernize | 54 | 0 | 0.56072 | 0.216211 |
| exclude_any_semantic_issue | simplify | 52 | 2 | 0.463749 | 0.313182 |


## Groq free-model replication


| analysis_model_id | condition | transfer_macro_f1_loss | same_condition_survival | all_feature_distance_ratio | function_word_distance_ratio |
| --- | --- | --- | --- | --- | --- |
| groq_llama_3_3_70b_free | paraphrase | 0.134524 | 0.791817 | 0.945427 | 0.877661 |
| groq_llama_3_3_70b_free | modernize | -0.043254 | 0.873645 | 0.860345 | 0.852567 |
| groq_llama_3_3_70b_free | simplify | 0.326191 | 0.713598 | 0.938996 | 0.930514 |
| groq_qwen_32b_free | paraphrase | 0.178572 | 0.873645 | 0.953648 | 0.922589 |
| groq_qwen_32b_free | modernize | 0.069841 | 0.991576 | 0.90434 | 0.838536 |
| groq_qwen_32b_free | simplify | 0.156746 | 0.895963 | 0.927489 | 0.832842 |
| groq_gpt_oss_120b_free | paraphrase | 0.142593 | 1.022316 | 0.907039 | 0.834532 |
| groq_gpt_oss_120b_free | modernize | 0.133334 | 0.80932 | 1.002878 | 0.838817 |
| groq_gpt_oss_120b_free | simplify | 0.159524 | 0.811728 | 0.981119 | 0.841757 |


## Manuscript-safe interpretation


- Core test macro-F1 losses are positive for all three rewrite conditions across all three classifiers.
- Passage-level paired bootstrap intervals support the primary test result: minimum lower 95% CI bound = 0.050751; maximum nonpositive bootstrap rate = 0.001800.
- Semantic-fidelity review: 107/108 rows usable; mean preservation score 4.53/5. Treat as single-review audit, not independent double annotation.
- Semantic-risk sensitivity passed: strict-filter non-positive losses = 0; minimum strict test loss = 0.170812.
- Groq replication broadly supports the degradation pattern, but Llama-modernize is a reversal and should be reported as heterogeneity.

