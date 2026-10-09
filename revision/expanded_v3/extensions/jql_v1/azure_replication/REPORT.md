# Exploratory domain-transfer extension: azure_replication

Not a confirmatory result, human validation or submission-readiness certificate.

Common valid cohort: 315/360 source passages. All panels retain 18 works and six authors.

All estimable 4 x 4 matrices from seven planned panels and three pipelines are in metrics.csv. No best pipeline is selected.

## Full common-cohort comparisons

| Pipeline | Rewrite | O -> O | O -> R | R -> R | Adaptation gain [marginal 95% CI] | Within-domain gap |
|---|---|---:|---:|---:|---|---:|
| shared_stylometry_nc | paraphrase | 0.629 | 0.511 | 0.587 | +0.075 [+0.015, +0.139] | +0.042 |
| shared_stylometry_nc | modernize | 0.629 | 0.515 | 0.578 | +0.062 [+0.003, +0.130] | +0.051 |
| shared_stylometry_nc | simplify | 0.629 | 0.413 | 0.564 | +0.151 [+0.083, +0.222] | +0.065 |
| shared_function_words_nc | paraphrase | 0.546 | 0.477 | 0.558 | +0.082 [+0.022, +0.144] | -0.013 |
| shared_function_words_nc | modernize | 0.546 | 0.509 | 0.518 | +0.009 [-0.045, +0.064] | +0.028 |
| shared_function_words_nc | simplify | 0.546 | 0.455 | 0.498 | +0.042 [-0.008, +0.098] | +0.048 |
| char3_5_tfidf_svm | paraphrase | 0.863 | 0.713 | 0.770 | +0.058 [-0.008, +0.133] | +0.093 |
| char3_5_tfidf_svm | modernize | 0.863 | 0.755 | 0.771 | +0.016 [-0.046, +0.091] | +0.092 |
| char3_5_tfidf_svm | simplify | 0.863 | 0.647 | 0.708 | +0.061 [+0.001, +0.124] | +0.155 |

## Length-control comparisons (same cohort for full and cropped text)

| Pipeline | Rewrite | Control | n | Full transfer loss | Cropped transfer loss | Full within-domain gap | Cropped within-domain gap |
|---|---|---|---:|---:|---:|---:|---:|
| shared_stylometry_nc | paraphrase | w200_prefix | 315 | +0.117 | +0.069 | +0.042 | +0.046 |
| shared_stylometry_nc | paraphrase | w200_middle | 315 | +0.117 | +0.032 | +0.042 | +0.051 |
| shared_stylometry_nc | paraphrase | w200_suffix | 315 | +0.117 | +0.029 | +0.042 | -0.005 |
| shared_stylometry_nc | paraphrase | w300_middle | 315 | +0.117 | +0.110 | +0.042 | +0.081 |
| shared_stylometry_nc | modernize | w200_prefix | 315 | +0.114 | +0.066 | +0.051 | +0.051 |
| shared_stylometry_nc | modernize | w200_middle | 315 | +0.114 | +0.075 | +0.051 | +0.039 |
| shared_stylometry_nc | modernize | w200_suffix | 315 | +0.114 | +0.041 | +0.051 | +0.017 |
| shared_stylometry_nc | modernize | w300_middle | 315 | +0.114 | +0.118 | +0.051 | +0.082 |
| shared_stylometry_nc | simplify | w200_prefix | 315 | +0.216 | +0.151 | +0.065 | +0.087 |
| shared_stylometry_nc | simplify | w200_middle | 315 | +0.216 | +0.150 | +0.065 | +0.050 |
| shared_stylometry_nc | simplify | w200_suffix | 315 | +0.216 | +0.117 | +0.065 | +0.013 |
| shared_stylometry_nc | simplify | w300_middle | 315 | +0.216 | +0.193 | +0.065 | +0.078 |
| shared_function_words_nc | paraphrase | w200_prefix | 315 | +0.069 | +0.022 | -0.013 | +0.052 |
| shared_function_words_nc | paraphrase | w200_middle | 315 | +0.069 | +0.025 | -0.013 | +0.006 |
| shared_function_words_nc | paraphrase | w200_suffix | 315 | +0.069 | +0.050 | -0.013 | +0.008 |
| shared_function_words_nc | paraphrase | w300_middle | 315 | +0.069 | +0.036 | -0.013 | -0.000 |
| shared_function_words_nc | modernize | w200_prefix | 315 | +0.036 | +0.007 | +0.028 | +0.041 |
| shared_function_words_nc | modernize | w200_middle | 315 | +0.036 | +0.033 | +0.028 | +0.033 |
| shared_function_words_nc | modernize | w200_suffix | 315 | +0.036 | +0.014 | +0.028 | +0.030 |
| shared_function_words_nc | modernize | w300_middle | 315 | +0.036 | +0.035 | +0.028 | +0.023 |
| shared_function_words_nc | simplify | w200_prefix | 315 | +0.090 | +0.075 | +0.048 | +0.048 |
| shared_function_words_nc | simplify | w200_middle | 315 | +0.090 | +0.067 | +0.048 | +0.023 |
| shared_function_words_nc | simplify | w200_suffix | 315 | +0.090 | +0.081 | +0.048 | +0.029 |
| shared_function_words_nc | simplify | w300_middle | 315 | +0.090 | +0.085 | +0.048 | +0.039 |
| char3_5_tfidf_svm | paraphrase | w200_prefix | 315 | +0.150 | +0.127 | +0.093 | +0.101 |
| char3_5_tfidf_svm | paraphrase | w200_middle | 315 | +0.150 | +0.119 | +0.093 | +0.105 |
| char3_5_tfidf_svm | paraphrase | w200_suffix | 315 | +0.150 | +0.117 | +0.093 | +0.096 |
| char3_5_tfidf_svm | paraphrase | w300_middle | 315 | +0.150 | +0.154 | +0.093 | +0.119 |
| char3_5_tfidf_svm | modernize | w200_prefix | 315 | +0.108 | +0.104 | +0.092 | +0.079 |
| char3_5_tfidf_svm | modernize | w200_middle | 315 | +0.108 | +0.134 | +0.092 | +0.122 |
| char3_5_tfidf_svm | modernize | w200_suffix | 315 | +0.108 | +0.108 | +0.092 | +0.090 |
| char3_5_tfidf_svm | modernize | w300_middle | 315 | +0.108 | +0.125 | +0.092 | +0.092 |
| char3_5_tfidf_svm | simplify | w200_prefix | 315 | +0.216 | +0.245 | +0.155 | +0.136 |
| char3_5_tfidf_svm | simplify | w200_middle | 315 | +0.216 | +0.205 | +0.155 | +0.136 |
| char3_5_tfidf_svm | simplify | w200_suffix | 315 | +0.216 | +0.215 | +0.155 | +0.136 |
| char3_5_tfidf_svm | simplify | w300_middle | 315 | +0.216 | +0.219 | +0.155 | +0.138 |

## Interpretation constraints

Positive adaptation gain means this learner recovers some predictive association when trained on rewrites. It does not prove preserved meaning, pure style or all recoverable information. Negative within-domain gaps do not establish that rewriting creates author information. Topic, genre, length and feature/learner choice still matter.

CIs resample the same held-out passage pairs within works and works within fixed authors; they do not refit the learners or cover new authors. Intervals across these many overlapping panels are not simultaneous. No new confirmatory p-values are reported. Equal-length cuts change which content is observed.

Planned but unavailable controls are listed in panel_status.json with zero-count works. Their thresholds and required work coverage are not changed, and no metrics are fabricated.

Reproduction: `.venv/Scripts/python.exe -m research_v2.transfer_extension --model azure_replication`. No API calls. See ../PLAN.md, manifest.json and the original generation ledgers for provenance.
