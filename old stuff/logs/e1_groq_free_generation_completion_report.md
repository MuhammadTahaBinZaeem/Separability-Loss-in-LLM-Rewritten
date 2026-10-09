# E1 Groq Free-Model Generation Completion Report

This report validates the committed 360-scope Groq free-model generation outputs.

Historical duplicate successful raw rows from resumed runs are reported as diagnostics, not treated as fatal, as long as the de-duplicated scoped successful raw IDs match `requests_used.jsonl` and `parsed_outputs.csv`.

## Groq Llama 3.3 70B

- requests: 360
- raw OK rows total: 394
- unique successful scoped raw rows: 360
- duplicate successful scoped raw rows: 0
- successful raw rows outside current scope: 34
- parsed rows: 360
- QC pass/warning/fail: 117 / 243 / 0
- condition counts: {'modernize': 120, 'paraphrase': 120, 'simplify': 120}
- author counts: {'austen': 60, 'dickens': 60, 'poe': 60, 'shelley': 60, 'twain': 60, 'wilde': 60}
- contamination scan counts: {'here_is': 3, 'i_cannot': 2}

Resume diagnostics:
- duplicate successful raw rows are historical resume artifacts: 0
- successful raw rows outside current 360-scope are ignored for validation: 34

Contamination examples needing manual review:
- groq_llama_3_3_70b_free|run_1|AUSTEN_EMMA_018|paraphrase: i_cannot
- groq_llama_3_3_70b_free|run_1|SHELLEY_FRANKENSTEIN_018|paraphrase: i_cannot
- groq_llama_3_3_70b_free|run_1|WILDE_DORIAN_GRAY_002|paraphrase: here_is
- groq_llama_3_3_70b_free|run_1|WILDE_DORIAN_GRAY_002|modernize: here_is
- groq_llama_3_3_70b_free|run_1|WILDE_DORIAN_GRAY_002|simplify: here_is

## Groq Qwen 32B

- requests: 360
- raw OK rows total: 360
- unique successful scoped raw rows: 360
- duplicate successful scoped raw rows: 0
- successful raw rows outside current scope: 0
- parsed rows: 360
- QC pass/warning/fail: 259 / 101 / 0
- condition counts: {'modernize': 120, 'paraphrase': 120, 'simplify': 120}
- author counts: {'austen': 60, 'dickens': 60, 'poe': 60, 'shelley': 60, 'twain': 60, 'wilde': 60}
- contamination scan counts: {'here_is': 10, 'i_cannot': 19}

Contamination examples needing manual review:
- groq_qwen_32b_free|run_1|AUSTEN_EMMA_005|paraphrase: i_cannot,here_is
- groq_qwen_32b_free|run_1|AUSTEN_EMMA_005|simplify: i_cannot,here_is
- groq_qwen_32b_free|run_1|AUSTEN_EMMA_006|paraphrase: i_cannot
- groq_qwen_32b_free|run_1|AUSTEN_EMMA_012|paraphrase: i_cannot
- groq_qwen_32b_free|run_1|AUSTEN_EMMA_013|paraphrase: i_cannot
- groq_qwen_32b_free|run_1|AUSTEN_EMMA_015|paraphrase: i_cannot
- groq_qwen_32b_free|run_1|AUSTEN_EMMA_018|paraphrase: i_cannot
- groq_qwen_32b_free|run_1|DICKENS_GREAT_EXPECTATIONS_010|paraphrase: i_cannot
- groq_qwen_32b_free|run_1|DICKENS_GREAT_EXPECTATIONS_010|simplify: i_cannot
- groq_qwen_32b_free|run_1|DICKENS_GREAT_EXPECTATIONS_014|paraphrase: i_cannot

## Groq GPT-OSS 120B

- requests: 360
- raw OK rows total: 425
- unique successful scoped raw rows: 360
- duplicate successful scoped raw rows: 0
- successful raw rows outside current scope: 65
- parsed rows: 360
- QC pass/warning/fail: 258 / 102 / 0
- condition counts: {'modernize': 120, 'paraphrase': 120, 'simplify': 120}
- author counts: {'austen': 60, 'dickens': 60, 'poe': 60, 'shelley': 60, 'twain': 60, 'wilde': 60}
- contamination scan counts: {'below_is': 2, 'here_is': 6, 'i_cannot': 28}

Resume diagnostics:
- duplicate successful raw rows are historical resume artifacts: 0
- successful raw rows outside current 360-scope are ignored for validation: 65

Contamination examples needing manual review:
- groq_gpt_oss_120b_free|run_1|AUSTEN_EMMA_002|paraphrase: i_cannot
- groq_gpt_oss_120b_free|run_1|AUSTEN_EMMA_005|paraphrase: i_cannot,here_is
- groq_gpt_oss_120b_free|run_1|AUSTEN_EMMA_005|simplify: here_is
- groq_gpt_oss_120b_free|run_1|AUSTEN_EMMA_006|paraphrase: i_cannot
- groq_gpt_oss_120b_free|run_1|AUSTEN_EMMA_006|simplify: i_cannot
- groq_gpt_oss_120b_free|run_1|AUSTEN_EMMA_012|paraphrase: i_cannot
- groq_gpt_oss_120b_free|run_1|AUSTEN_EMMA_013|paraphrase: i_cannot
- groq_gpt_oss_120b_free|run_1|AUSTEN_EMMA_015|paraphrase: i_cannot
- groq_gpt_oss_120b_free|run_1|AUSTEN_EMMA_018|paraphrase: i_cannot
- groq_gpt_oss_120b_free|run_1|AUSTEN_EMMA_018|simplify: i_cannot

## Final verdict

PASS: all three 360-scope Groq free-model generation outputs are structurally complete and safe for downstream E1 feature extraction/modeling, subject to manual review of warning-heavy rows.

Machine-readable summaries written to `metadata/e1_groq_free_generation_completion_summary.csv` and related `metadata/e1_groq_free_generation_*` files.