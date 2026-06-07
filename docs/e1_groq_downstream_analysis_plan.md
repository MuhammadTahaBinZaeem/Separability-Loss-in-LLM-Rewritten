# E1 Groq Downstream Analysis Plan

## Status

E1 Groq generation is complete and validated for the 360-scope free-model replication set.

Validated models:

- `groq_llama_3_3_70b_free`
- `groq_qwen_32b_free`
- `groq_gpt_oss_120b_free`

Each model has:

- 360 scoped requests;
- 360 parsed rows;
- 0 QC-fail rows;
- balanced condition counts: 120 paraphrase, 120 modernize, 120 simplify;
- balanced author counts: 60 rewrite rows per author.

## Goal

Create separate E1 downstream outputs without touching the frozen core Gemini Flash analysis.

Required downstream outputs should use the `e1_groq_` prefix and live under:

```text
data/interim/e1_free_model_replication/groq_downstream/
metadata/e1_groq_*
logs/e1_groq_downstream_analysis_report.md
```

## Intended analysis

For each Groq model:

1. join 360 rewrites with their corresponding 120 original passages;
2. build a model-specific 480-row analysis dataset;
3. extract the same stylometric features used by the core pipeline;
4. split the 20 passages per author as:
   - 14 train;
   - 3 validation;
   - 3 test;
5. run original-to-rewritten transfer classification;
6. run same-condition classification;
7. compute distance contraction for all features and function words;
8. repeat for sensitivity subsets:
   - all rows;
   - QC pass only;
   - QC pass plus non-contaminated rows, where practical.

## Manuscript warning

This is a 360-rewrite scoped replication, not a replacement for the full frozen core experiment. The test split is small because it has only 3 passages per author. Results should be described as free-model replication evidence and not overclaimed.
