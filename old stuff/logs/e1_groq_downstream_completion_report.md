# E1 Groq Downstream Completion Report

## Validated artifacts

- `metadata/e1_groq_transfer_summary.csv`
- `metadata/e1_groq_same_condition_summary.csv`
- `metadata/e1_groq_distance_summary.csv`
- `data/interim/e1_free_model_replication/groq_downstream/e1_groq_stylometric_features.csv`
- `data/interim/e1_free_model_replication/groq_downstream/e1_groq_master_text_dataset.csv`
- `metadata/e1_groq_downstream_completion_summary.csv`

## Main manuscript summary table

- groq_llama_3_3_70b_free / paraphrase: transfer_loss=0.134524, same_survival=0.791817, all_distance_ratio=0.945427, function_word_ratio=0.877661
- groq_llama_3_3_70b_free / modernize: transfer_loss=-0.043254, same_survival=0.873645, all_distance_ratio=0.860345, function_word_ratio=0.852567
- groq_llama_3_3_70b_free / simplify: transfer_loss=0.326191, same_survival=0.713598, all_distance_ratio=0.938996, function_word_ratio=0.930514
- groq_qwen_32b_free / paraphrase: transfer_loss=0.178572, same_survival=0.873645, all_distance_ratio=0.953648, function_word_ratio=0.922589
- groq_qwen_32b_free / modernize: transfer_loss=0.069841, same_survival=0.991576, all_distance_ratio=0.90434, function_word_ratio=0.838536
- groq_qwen_32b_free / simplify: transfer_loss=0.156746, same_survival=0.895963, all_distance_ratio=0.927489, function_word_ratio=0.832842
- groq_gpt_oss_120b_free / paraphrase: transfer_loss=0.142593, same_survival=1.022316, all_distance_ratio=0.907039, function_word_ratio=0.834532
- groq_gpt_oss_120b_free / modernize: transfer_loss=0.133334, same_survival=0.80932, all_distance_ratio=1.002878, function_word_ratio=0.838817
- groq_gpt_oss_120b_free / simplify: transfer_loss=0.159524, same_survival=0.811728, all_distance_ratio=0.981119, function_word_ratio=0.841757

## Final verdict

PASS: E1 Groq downstream outputs are complete for the scoped free-model replication. Use as robustness evidence, not as a replacement for the frozen core experiment.
