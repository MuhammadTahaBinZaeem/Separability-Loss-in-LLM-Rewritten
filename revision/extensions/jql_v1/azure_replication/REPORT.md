# Exploratory domain-transfer extension: azure_replication

Not a confirmatory result, human validation or submission-readiness certificate.

Common valid cohort: 316/360 source passages. All panels retain 18 works and six authors.

All 4 x 4 matrices, seven panels and three pipelines are in metrics.csv. No best pipeline is selected.

## Full common-cohort comparisons

| Pipeline | Rewrite | O -> O | O -> R | R -> R | Adaptation gain [marginal 95% CI] | Within-domain gap |
|---|---|---:|---:|---:|---|---:|
| shared_stylometry_nc | paraphrase | 0.635 | 0.524 | 0.581 | +0.056 [-0.004, +0.126] | +0.054 |
| shared_stylometry_nc | modernize | 0.635 | 0.531 | 0.571 | +0.040 [-0.019, +0.106] | +0.063 |
| shared_stylometry_nc | simplify | 0.635 | 0.418 | 0.566 | +0.148 [+0.081, +0.223] | +0.069 |
| shared_function_words_nc | paraphrase | 0.545 | 0.483 | 0.551 | +0.068 [+0.013, +0.127] | -0.006 |
| shared_function_words_nc | modernize | 0.545 | 0.506 | 0.520 | +0.014 [-0.039, +0.071] | +0.025 |
| shared_function_words_nc | simplify | 0.545 | 0.448 | 0.494 | +0.047 [-0.004, +0.104] | +0.051 |
| char3_5_tfidf_svm | paraphrase | 0.857 | 0.718 | 0.765 | +0.047 [-0.015, +0.122] | +0.092 |
| char3_5_tfidf_svm | modernize | 0.857 | 0.746 | 0.774 | +0.028 [-0.021, +0.088] | +0.083 |
| char3_5_tfidf_svm | simplify | 0.857 | 0.641 | 0.703 | +0.062 [-0.001, +0.129] | +0.154 |

## Length-control comparisons (same cohort for full and cropped text)

| Pipeline | Rewrite | Control | n | Full transfer loss | Cropped transfer loss | Full within-domain gap | Cropped within-domain gap |
|---|---|---|---:|---:|---:|---:|---:|
| shared_stylometry_nc | paraphrase | w200_prefix | 316 | +0.110 | +0.074 | +0.054 | +0.044 |
| shared_stylometry_nc | paraphrase | w200_middle | 316 | +0.110 | +0.035 | +0.054 | +0.055 |
| shared_stylometry_nc | paraphrase | w200_suffix | 316 | +0.110 | +0.046 | +0.054 | +0.024 |
| shared_stylometry_nc | paraphrase | w300_middle | 316 | +0.110 | +0.107 | +0.054 | +0.090 |
| shared_stylometry_nc | modernize | w200_prefix | 316 | +0.104 | +0.081 | +0.063 | +0.064 |
| shared_stylometry_nc | modernize | w200_middle | 316 | +0.104 | +0.066 | +0.063 | +0.054 |
| shared_stylometry_nc | modernize | w200_suffix | 316 | +0.104 | +0.049 | +0.063 | +0.028 |
| shared_stylometry_nc | modernize | w300_middle | 316 | +0.104 | +0.117 | +0.063 | +0.078 |
| shared_stylometry_nc | simplify | w200_prefix | 316 | +0.217 | +0.165 | +0.069 | +0.088 |
| shared_stylometry_nc | simplify | w200_middle | 316 | +0.217 | +0.170 | +0.069 | +0.056 |
| shared_stylometry_nc | simplify | w200_suffix | 316 | +0.217 | +0.126 | +0.069 | +0.021 |
| shared_stylometry_nc | simplify | w300_middle | 316 | +0.217 | +0.185 | +0.069 | +0.082 |
| shared_function_words_nc | paraphrase | w200_prefix | 316 | +0.062 | +0.029 | -0.006 | +0.050 |
| shared_function_words_nc | paraphrase | w200_middle | 316 | +0.062 | +0.031 | -0.006 | +0.016 |
| shared_function_words_nc | paraphrase | w200_suffix | 316 | +0.062 | +0.069 | -0.006 | +0.028 |
| shared_function_words_nc | paraphrase | w300_middle | 316 | +0.062 | +0.046 | -0.006 | +0.008 |
| shared_function_words_nc | modernize | w200_prefix | 316 | +0.039 | +0.007 | +0.025 | +0.039 |
| shared_function_words_nc | modernize | w200_middle | 316 | +0.039 | +0.046 | +0.025 | +0.037 |
| shared_function_words_nc | modernize | w200_suffix | 316 | +0.039 | +0.029 | +0.025 | +0.059 |
| shared_function_words_nc | modernize | w300_middle | 316 | +0.039 | +0.027 | +0.025 | +0.022 |
| shared_function_words_nc | simplify | w200_prefix | 316 | +0.098 | +0.097 | +0.051 | +0.053 |
| shared_function_words_nc | simplify | w200_middle | 316 | +0.098 | +0.086 | +0.051 | +0.034 |
| shared_function_words_nc | simplify | w200_suffix | 316 | +0.098 | +0.092 | +0.051 | +0.041 |
| shared_function_words_nc | simplify | w300_middle | 316 | +0.098 | +0.099 | +0.051 | +0.047 |
| char3_5_tfidf_svm | paraphrase | w200_prefix | 316 | +0.139 | +0.139 | +0.092 | +0.108 |
| char3_5_tfidf_svm | paraphrase | w200_middle | 316 | +0.139 | +0.128 | +0.092 | +0.101 |
| char3_5_tfidf_svm | paraphrase | w200_suffix | 316 | +0.139 | +0.125 | +0.092 | +0.105 |
| char3_5_tfidf_svm | paraphrase | w300_middle | 316 | +0.139 | +0.136 | +0.092 | +0.094 |
| char3_5_tfidf_svm | modernize | w200_prefix | 316 | +0.111 | +0.105 | +0.083 | +0.084 |
| char3_5_tfidf_svm | modernize | w200_middle | 316 | +0.111 | +0.133 | +0.083 | +0.120 |
| char3_5_tfidf_svm | modernize | w200_suffix | 316 | +0.111 | +0.115 | +0.083 | +0.107 |
| char3_5_tfidf_svm | modernize | w300_middle | 316 | +0.111 | +0.113 | +0.083 | +0.075 |
| char3_5_tfidf_svm | simplify | w200_prefix | 316 | +0.216 | +0.236 | +0.154 | +0.143 |
| char3_5_tfidf_svm | simplify | w200_middle | 316 | +0.216 | +0.207 | +0.154 | +0.145 |
| char3_5_tfidf_svm | simplify | w200_suffix | 316 | +0.216 | +0.225 | +0.154 | +0.148 |
| char3_5_tfidf_svm | simplify | w300_middle | 316 | +0.216 | +0.225 | +0.154 | +0.122 |

## Interpretation constraints

Positive adaptation gain means this learner recovers some predictive association when trained on rewrites. It does not prove preserved meaning, pure style or all recoverable information. Negative within-domain gaps do not establish that rewriting creates author information. Topic, genre, length and feature/learner choice still matter.

CIs resample the same held-out passage pairs within works and works within fixed authors; they do not refit the learners or cover new authors. Intervals across these many overlapping panels are not simultaneous. No new confirmatory p-values are reported. Equal-length cuts change which content is observed.

Reproduction: `.venv/Scripts/python.exe -m research_v2.transfer_extension --model azure_replication`. No API calls. See ../PLAN.md, manifest.json and the original generation ledgers for provenance.
