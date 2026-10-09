# Exploratory domain-transfer extension: codex51

Not a confirmatory result, human validation or submission-readiness certificate.

Common valid cohort: 321/360 source passages. All panels retain 18 works and six authors.

All estimable 4 x 4 matrices from seven planned panels and three pipelines are in metrics.csv. No best pipeline is selected.

## Full common-cohort comparisons

| Pipeline | Rewrite | O -> O | O -> R | R -> R | Adaptation gain [marginal 95% CI] | Within-domain gap |
|---|---|---:|---:|---:|---|---:|
| shared_stylometry_nc | paraphrase | 0.639 | 0.514 | 0.574 | +0.060 [-0.008, +0.142] | +0.065 |
| shared_stylometry_nc | modernize | 0.639 | 0.494 | 0.550 | +0.056 [-0.011, +0.130] | +0.089 |
| shared_stylometry_nc | simplify | 0.639 | 0.480 | 0.571 | +0.092 [+0.040, +0.150] | +0.068 |
| shared_function_words_nc | paraphrase | 0.560 | 0.505 | 0.507 | +0.002 [-0.046, +0.050] | +0.053 |
| shared_function_words_nc | modernize | 0.560 | 0.473 | 0.507 | +0.034 [-0.027, +0.101] | +0.053 |
| shared_function_words_nc | simplify | 0.560 | 0.482 | 0.490 | +0.008 [-0.042, +0.061] | +0.070 |
| char3_5_tfidf_svm | paraphrase | 0.861 | 0.710 | 0.750 | +0.039 [-0.018, +0.095] | +0.112 |
| char3_5_tfidf_svm | modernize | 0.861 | 0.710 | 0.752 | +0.042 [-0.026, +0.110] | +0.110 |
| char3_5_tfidf_svm | simplify | 0.861 | 0.661 | 0.755 | +0.094 [+0.042, +0.150] | +0.106 |

## Length-control comparisons (same cohort for full and cropped text)

| Pipeline | Rewrite | Control | n | Full transfer loss | Cropped transfer loss | Full within-domain gap | Cropped within-domain gap |
|---|---|---|---:|---:|---:|---:|---:|
| shared_stylometry_nc | paraphrase | w200_prefix | 321 | +0.125 | +0.105 | +0.065 | +0.091 |
| shared_stylometry_nc | paraphrase | w200_middle | 321 | +0.125 | +0.085 | +0.065 | +0.064 |
| shared_stylometry_nc | paraphrase | w200_suffix | 321 | +0.125 | +0.101 | +0.065 | +0.070 |
| shared_stylometry_nc | paraphrase | w300_middle | 321 | +0.125 | +0.076 | +0.065 | +0.043 |
| shared_stylometry_nc | modernize | w200_prefix | 321 | +0.145 | +0.123 | +0.089 | +0.094 |
| shared_stylometry_nc | modernize | w200_middle | 321 | +0.145 | +0.114 | +0.089 | +0.079 |
| shared_stylometry_nc | modernize | w200_suffix | 321 | +0.145 | +0.096 | +0.089 | +0.041 |
| shared_stylometry_nc | modernize | w300_middle | 321 | +0.145 | +0.116 | +0.089 | +0.047 |
| shared_stylometry_nc | simplify | w200_prefix | 321 | +0.159 | +0.145 | +0.068 | +0.085 |
| shared_stylometry_nc | simplify | w200_middle | 321 | +0.159 | +0.110 | +0.068 | +0.074 |
| shared_stylometry_nc | simplify | w200_suffix | 321 | +0.159 | +0.089 | +0.068 | +0.038 |
| shared_stylometry_nc | simplify | w300_middle | 321 | +0.159 | +0.101 | +0.068 | +0.030 |
| shared_function_words_nc | paraphrase | w200_prefix | 321 | +0.055 | +0.058 | +0.053 | +0.051 |
| shared_function_words_nc | paraphrase | w200_middle | 321 | +0.055 | +0.033 | +0.053 | +0.027 |
| shared_function_words_nc | paraphrase | w200_suffix | 321 | +0.055 | +0.067 | +0.053 | +0.051 |
| shared_function_words_nc | paraphrase | w300_middle | 321 | +0.055 | +0.033 | +0.053 | +0.024 |
| shared_function_words_nc | modernize | w200_prefix | 321 | +0.087 | +0.056 | +0.053 | +0.057 |
| shared_function_words_nc | modernize | w200_middle | 321 | +0.087 | +0.013 | +0.053 | +0.025 |
| shared_function_words_nc | modernize | w200_suffix | 321 | +0.087 | +0.065 | +0.053 | +0.031 |
| shared_function_words_nc | modernize | w300_middle | 321 | +0.087 | +0.042 | +0.053 | +0.034 |
| shared_function_words_nc | simplify | w200_prefix | 321 | +0.078 | +0.076 | +0.070 | +0.058 |
| shared_function_words_nc | simplify | w200_middle | 321 | +0.078 | +0.054 | +0.070 | +0.010 |
| shared_function_words_nc | simplify | w200_suffix | 321 | +0.078 | +0.066 | +0.070 | +0.074 |
| shared_function_words_nc | simplify | w300_middle | 321 | +0.078 | +0.048 | +0.070 | +0.031 |
| char3_5_tfidf_svm | paraphrase | w200_prefix | 321 | +0.151 | +0.123 | +0.112 | +0.130 |
| char3_5_tfidf_svm | paraphrase | w200_middle | 321 | +0.151 | +0.107 | +0.112 | +0.093 |
| char3_5_tfidf_svm | paraphrase | w200_suffix | 321 | +0.151 | +0.133 | +0.112 | +0.126 |
| char3_5_tfidf_svm | paraphrase | w300_middle | 321 | +0.151 | +0.125 | +0.112 | +0.097 |
| char3_5_tfidf_svm | modernize | w200_prefix | 321 | +0.151 | +0.146 | +0.110 | +0.089 |
| char3_5_tfidf_svm | modernize | w200_middle | 321 | +0.151 | +0.139 | +0.110 | +0.083 |
| char3_5_tfidf_svm | modernize | w200_suffix | 321 | +0.151 | +0.134 | +0.110 | +0.119 |
| char3_5_tfidf_svm | modernize | w300_middle | 321 | +0.151 | +0.146 | +0.110 | +0.073 |
| char3_5_tfidf_svm | simplify | w200_prefix | 321 | +0.200 | +0.190 | +0.106 | +0.103 |
| char3_5_tfidf_svm | simplify | w200_middle | 321 | +0.200 | +0.159 | +0.106 | +0.085 |
| char3_5_tfidf_svm | simplify | w200_suffix | 321 | +0.200 | +0.164 | +0.106 | +0.111 |
| char3_5_tfidf_svm | simplify | w300_middle | 321 | +0.200 | +0.171 | +0.106 | +0.070 |

## Interpretation constraints

Positive adaptation gain means this learner recovers some predictive association when trained on rewrites. It does not prove preserved meaning, pure style or all recoverable information. Negative within-domain gaps do not establish that rewriting creates author information. Topic, genre, length and feature/learner choice still matter.

CIs resample the same held-out passage pairs within works and works within fixed authors; they do not refit the learners or cover new authors. Intervals across these many overlapping panels are not simultaneous. No new confirmatory p-values are reported. Equal-length cuts change which content is observed.

Planned but unavailable controls are listed in panel_status.json with zero-count works. Their thresholds and required work coverage are not changed, and no metrics are fabricated.

Reproduction: `.venv/Scripts/python.exe -m research_v2.transfer_extension --model codex51`. No API calls. See ../PLAN.md, manifest.json and the original generation ledgers for provenance.
