# Exploratory domain-transfer extension: terra56

Not a confirmatory result, human validation or submission-readiness certificate.

Common valid cohort: 318/360 source passages. All panels retain 18 works and six authors.

All estimable 4 x 4 matrices from seven planned panels and three pipelines are in metrics.csv. No best pipeline is selected.

## Full common-cohort comparisons

| Pipeline | Rewrite | O -> O | O -> R | R -> R | Adaptation gain [marginal 95% CI] | Within-domain gap |
|---|---|---:|---:|---:|---|---:|
| shared_stylometry_nc | paraphrase | 0.643 | 0.562 | 0.608 | +0.046 [-0.014, +0.113] | +0.035 |
| shared_stylometry_nc | modernize | 0.643 | 0.527 | 0.553 | +0.026 [-0.028, +0.095] | +0.090 |
| shared_stylometry_nc | simplify | 0.643 | 0.485 | 0.558 | +0.073 [+0.018, +0.144] | +0.085 |
| shared_function_words_nc | paraphrase | 0.552 | 0.515 | 0.521 | +0.007 [-0.033, +0.049] | +0.031 |
| shared_function_words_nc | modernize | 0.552 | 0.478 | 0.503 | +0.025 [-0.017, +0.072] | +0.049 |
| shared_function_words_nc | simplify | 0.552 | 0.452 | 0.473 | +0.020 [-0.033, +0.078] | +0.080 |
| char3_5_tfidf_svm | paraphrase | 0.876 | 0.757 | 0.791 | +0.034 [-0.011, +0.086] | +0.084 |
| char3_5_tfidf_svm | modernize | 0.876 | 0.774 | 0.812 | +0.038 [+0.002, +0.078] | +0.064 |
| char3_5_tfidf_svm | simplify | 0.876 | 0.736 | 0.760 | +0.024 [-0.037, +0.088] | +0.116 |

## Length-control comparisons (same cohort for full and cropped text)

| Pipeline | Rewrite | Control | n | Full transfer loss | Cropped transfer loss | Full within-domain gap | Cropped within-domain gap |
|---|---|---|---:|---:|---:|---:|---:|
| shared_stylometry_nc | paraphrase | w200_prefix | 318 | +0.080 | +0.063 | +0.035 | +0.058 |
| shared_stylometry_nc | paraphrase | w200_middle | 318 | +0.080 | +0.081 | +0.035 | +0.089 |
| shared_stylometry_nc | paraphrase | w200_suffix | 318 | +0.080 | +0.025 | +0.035 | +0.033 |
| shared_stylometry_nc | paraphrase | w300_middle | 318 | +0.080 | +0.075 | +0.035 | +0.047 |
| shared_stylometry_nc | modernize | w200_prefix | 318 | +0.116 | +0.083 | +0.090 | +0.077 |
| shared_stylometry_nc | modernize | w200_middle | 318 | +0.116 | +0.121 | +0.090 | +0.105 |
| shared_stylometry_nc | modernize | w200_suffix | 318 | +0.116 | +0.069 | +0.090 | +0.046 |
| shared_stylometry_nc | modernize | w300_middle | 318 | +0.116 | +0.076 | +0.090 | +0.056 |
| shared_stylometry_nc | simplify | w200_prefix | 318 | +0.158 | +0.101 | +0.085 | +0.060 |
| shared_stylometry_nc | simplify | w200_middle | 318 | +0.158 | +0.130 | +0.085 | +0.129 |
| shared_stylometry_nc | simplify | w200_suffix | 318 | +0.158 | +0.082 | +0.085 | +0.082 |
| shared_stylometry_nc | simplify | w300_middle | 318 | +0.158 | +0.101 | +0.085 | +0.064 |
| shared_function_words_nc | paraphrase | w200_prefix | 318 | +0.038 | +0.050 | +0.031 | +0.050 |
| shared_function_words_nc | paraphrase | w200_middle | 318 | +0.038 | +0.010 | +0.031 | +0.009 |
| shared_function_words_nc | paraphrase | w200_suffix | 318 | +0.038 | +0.048 | +0.031 | +0.040 |
| shared_function_words_nc | paraphrase | w300_middle | 318 | +0.038 | +0.034 | +0.031 | +0.032 |
| shared_function_words_nc | modernize | w200_prefix | 318 | +0.074 | +0.068 | +0.049 | +0.072 |
| shared_function_words_nc | modernize | w200_middle | 318 | +0.074 | +0.026 | +0.049 | +0.042 |
| shared_function_words_nc | modernize | w200_suffix | 318 | +0.074 | +0.069 | +0.049 | +0.061 |
| shared_function_words_nc | modernize | w300_middle | 318 | +0.074 | +0.044 | +0.049 | +0.047 |
| shared_function_words_nc | simplify | w200_prefix | 318 | +0.100 | +0.079 | +0.080 | +0.064 |
| shared_function_words_nc | simplify | w200_middle | 318 | +0.100 | +0.048 | +0.080 | +0.054 |
| shared_function_words_nc | simplify | w200_suffix | 318 | +0.100 | +0.089 | +0.080 | +0.103 |
| shared_function_words_nc | simplify | w300_middle | 318 | +0.100 | +0.068 | +0.080 | +0.060 |
| char3_5_tfidf_svm | paraphrase | w200_prefix | 318 | +0.118 | +0.097 | +0.084 | +0.062 |
| char3_5_tfidf_svm | paraphrase | w200_middle | 318 | +0.118 | +0.093 | +0.084 | +0.086 |
| char3_5_tfidf_svm | paraphrase | w200_suffix | 318 | +0.118 | +0.100 | +0.084 | +0.103 |
| char3_5_tfidf_svm | paraphrase | w300_middle | 318 | +0.118 | +0.085 | +0.084 | +0.096 |
| char3_5_tfidf_svm | modernize | w200_prefix | 318 | +0.102 | +0.066 | +0.064 | +0.051 |
| char3_5_tfidf_svm | modernize | w200_middle | 318 | +0.102 | +0.084 | +0.064 | +0.061 |
| char3_5_tfidf_svm | modernize | w200_suffix | 318 | +0.102 | +0.072 | +0.064 | +0.101 |
| char3_5_tfidf_svm | modernize | w300_middle | 318 | +0.102 | +0.077 | +0.064 | +0.057 |
| char3_5_tfidf_svm | simplify | w200_prefix | 318 | +0.140 | +0.130 | +0.116 | +0.068 |
| char3_5_tfidf_svm | simplify | w200_middle | 318 | +0.140 | +0.112 | +0.116 | +0.106 |
| char3_5_tfidf_svm | simplify | w200_suffix | 318 | +0.140 | +0.138 | +0.116 | +0.122 |
| char3_5_tfidf_svm | simplify | w300_middle | 318 | +0.140 | +0.108 | +0.116 | +0.093 |

## Interpretation constraints

Positive adaptation gain means this learner recovers some predictive association when trained on rewrites. It does not prove preserved meaning, pure style or all recoverable information. Negative within-domain gaps do not establish that rewriting creates author information. Topic, genre, length and feature/learner choice still matter.

CIs resample the same held-out passage pairs within works and works within fixed authors; they do not refit the learners or cover new authors. Intervals across these many overlapping panels are not simultaneous. No new confirmatory p-values are reported. Equal-length cuts change which content is observed.

Planned but unavailable controls are listed in panel_status.json with zero-count works. Their thresholds and required work coverage are not changed, and no metrics are fabricated.

Reproduction: `.venv/Scripts/python.exe -m research_v2.transfer_extension --model terra56`. No API calls. See ../PLAN.md, manifest.json and the original generation ledgers for provenance.
