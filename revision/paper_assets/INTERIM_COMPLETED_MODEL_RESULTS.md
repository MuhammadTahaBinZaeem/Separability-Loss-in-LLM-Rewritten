# Interim completed-model results — not the final two-model study

This companion reports only completed generation ledgers and validated current-code analysis. The main manuscript remains pending. Missing requests are not imputed or replaced. Human semantic and source reviews remain outstanding.

Models included: Azure GPT-5.4 nano.

Table 1. Paired attribution loss conditional on technically valid outputs, with all length warnings retained. Intervals use 5,000 paired hierarchical bootstrap replicates and condition on the fitted classifiers. Work-swap p-values use 9,999 draws. Interim Holm adjustment retains the full planned family of eighteen tests, with unavailable tests effectively assigned p=1; adjusted values must be recomputed when all eighteen are available.

| Classifier | Instruction | Pairs | Original F1 | Rewrite F1 | Loss [95% CI] | Interim Holm p |
| --- | --- | --- | --- | --- | --- | --- |
| Nearest centroid | paraphrase | 328 | 0.633 | 0.518 | 0.115 [0.055, 0.181] | 0.1974 |
| Nearest centroid | modernize | 332 | 0.639 | 0.547 | 0.092 [0.029, 0.164] | 0.5379 |
| Nearest centroid | simplify | 326 | 0.636 | 0.406 | 0.230 [0.159, 0.304] | 0.1424 |
| Gaussian NB | paraphrase | 328 | 0.567 | 0.485 | 0.082 [0.021, 0.148] | 0.1974 |
| Gaussian NB | modernize | 332 | 0.578 | 0.462 | 0.117 [0.046, 0.200] | 0.1710 |
| Gaussian NB | simplify | 326 | 0.571 | 0.446 | 0.125 [0.048, 0.202] | 0.7650 |
| Shrinkage LDA | paraphrase | 328 | 0.722 | 0.615 | 0.107 [0.041, 0.182] | 0.3468 |
| Shrinkage LDA | modernize | 332 | 0.722 | 0.593 | 0.129 [0.062, 0.206] | 0.1037 |
| Shrinkage LDA | simplify | 326 | 0.721 | 0.459 | 0.261 [0.191, 0.338] | 0.0090 |

A positive loss indicates poorer transfer of an original-trained classifier. Bootstrap intervals and the work-swap test answer different conditional questions; an interval excluding zero is not a multiplicity-corrected significance claim. No pure-style, causal, or population-wide effect is identified.

Nearest-centroid loss is positive in 3 of 3 available comparisons; 0 cross .05 under the interim eighteen-test Holm adjustment. These are interim outcomes, not a completed two-model study.

Azure GPT-5.4 nano has 1,080 accounted requests: 1,054 native responses and 26 evidenced HTTP refusals; 986 outputs are technically valid and 94 fail technical QC or are refusals. Failed outcomes are excluded only under the disclosed valid-output estimand. No failed output is rerolled.
