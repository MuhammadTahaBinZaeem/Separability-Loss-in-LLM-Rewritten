# E1 Groq Free-Model Generation Completion Report

This report validates the committed 360-scope Groq free-model generation outputs.

## Groq Llama 3.3 70B

- requests: 360
- successful raw rows: 394
- parsed rows: 360
- QC pass/warning/fail: 117 / 243 / 0
- condition counts: {'modernize': 120, 'paraphrase': 120, 'simplify': 120}
- author counts: {'austen': 60, 'dickens': 60, 'poe': 60, 'shelley': 60, 'twain': 60, 'wilde': 60}
- contamination scan counts: {'here_is': 3, 'i_cannot': 2}

Contamination examples needing manual review:
- groq_llama_3_3_70b_free|run_1|AUSTEN_EMMA_018|paraphrase: i_cannot
- groq_llama_3_3_70b_free|run_1|SHELLEY_FRANKENSTEIN_018|paraphrase: i_cannot
- groq_llama_3_3_70b_free|run_1|WILDE_DORIAN_GRAY_002|paraphrase: here_is
- groq_llama_3_3_70b_free|run_1|WILDE_DORIAN_GRAY_002|modernize: here_is
- groq_llama_3_3_70b_free|run_1|WILDE_DORIAN_GRAY_002|simplify: here_is

## Errors

- groq_llama_3_3_70b_free: duplicate successful request_id in raw_responses.jsonl
- groq_llama_3_3_70b_free: parsed request IDs do not match unique successful raw IDs