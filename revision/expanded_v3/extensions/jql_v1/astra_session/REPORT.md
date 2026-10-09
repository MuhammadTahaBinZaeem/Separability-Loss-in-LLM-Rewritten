# Exploratory domain-transfer extension: astra_session

Not a confirmatory result, human validation or submission-readiness certificate.

Common valid cohort: 360/360 source passages. All panels retain 18 works and six authors.

All estimable 4 x 4 matrices from seven planned panels and three pipelines are in metrics.csv. No best pipeline is selected.

## Full common-cohort comparisons

| Pipeline | Rewrite | O -> O | O -> R | R -> R | Adaptation gain [marginal 95% CI] | Within-domain gap |
|---|---|---:|---:|---:|---|---:|
| shared_stylometry_nc | paraphrase | 0.635 | 0.489 | 0.579 | +0.089 [+0.030, +0.161] | +0.056 |
| shared_stylometry_nc | modernize | 0.635 | 0.456 | 0.569 | +0.113 [+0.053, +0.187] | +0.066 |
| shared_stylometry_nc | simplify | 0.635 | 0.414 | 0.546 | +0.131 [+0.057, +0.219] | +0.089 |
| shared_function_words_nc | paraphrase | 0.556 | 0.467 | 0.466 | -0.001 [-0.052, +0.059] | +0.090 |
| shared_function_words_nc | modernize | 0.556 | 0.455 | 0.492 | +0.038 [-0.017, +0.095] | +0.064 |
| shared_function_words_nc | simplify | 0.556 | 0.420 | 0.492 | +0.072 [+0.015, +0.136] | +0.064 |
| char3_5_tfidf_svm | paraphrase | 0.866 | 0.679 | 0.778 | +0.099 [+0.048, +0.164] | +0.088 |
| char3_5_tfidf_svm | modernize | 0.866 | 0.676 | 0.737 | +0.062 [+0.014, +0.115] | +0.128 |
| char3_5_tfidf_svm | simplify | 0.866 | 0.649 | 0.737 | +0.088 [+0.023, +0.157] | +0.129 |

## Length-control comparisons (same cohort for full and cropped text)

| Pipeline | Rewrite | Control | n | Full transfer loss | Cropped transfer loss | Full within-domain gap | Cropped within-domain gap |
|---|---|---|---:|---:|---:|---:|---:|
| shared_stylometry_nc | paraphrase | w200_prefix | 360 | +0.146 | +0.069 | +0.056 | +0.044 |
| shared_stylometry_nc | paraphrase | w200_middle | 360 | +0.146 | +0.097 | +0.056 | +0.063 |
| shared_stylometry_nc | paraphrase | w200_suffix | 360 | +0.146 | +0.086 | +0.056 | +0.053 |
| shared_stylometry_nc | paraphrase | w300_middle | 360 | +0.146 | +0.069 | +0.056 | +0.039 |
| shared_stylometry_nc | modernize | w200_prefix | 360 | +0.179 | +0.114 | +0.066 | +0.058 |
| shared_stylometry_nc | modernize | w200_middle | 360 | +0.179 | +0.142 | +0.066 | +0.045 |
| shared_stylometry_nc | modernize | w200_suffix | 360 | +0.179 | +0.117 | +0.066 | +0.087 |
| shared_stylometry_nc | modernize | w300_middle | 360 | +0.179 | +0.113 | +0.066 | +0.015 |
| shared_stylometry_nc | simplify | w200_prefix | 360 | +0.220 | +0.147 | +0.089 | +0.066 |
| shared_stylometry_nc | simplify | w200_middle | 360 | +0.220 | +0.188 | +0.089 | +0.053 |
| shared_stylometry_nc | simplify | w200_suffix | 360 | +0.220 | +0.125 | +0.089 | +0.066 |
| shared_stylometry_nc | simplify | w300_middle | 360 | +0.220 | +0.132 | +0.089 | +0.021 |
| shared_function_words_nc | paraphrase | w200_prefix | 360 | +0.089 | +0.033 | +0.090 | +0.041 |
| shared_function_words_nc | paraphrase | w200_middle | 360 | +0.089 | +0.046 | +0.090 | +0.026 |
| shared_function_words_nc | paraphrase | w200_suffix | 360 | +0.089 | +0.087 | +0.090 | +0.057 |
| shared_function_words_nc | paraphrase | w300_middle | 360 | +0.089 | +0.079 | +0.090 | +0.044 |
| shared_function_words_nc | modernize | w200_prefix | 360 | +0.101 | +0.065 | +0.064 | +0.051 |
| shared_function_words_nc | modernize | w200_middle | 360 | +0.101 | +0.051 | +0.064 | +0.036 |
| shared_function_words_nc | modernize | w200_suffix | 360 | +0.101 | +0.095 | +0.064 | +0.079 |
| shared_function_words_nc | modernize | w300_middle | 360 | +0.101 | +0.069 | +0.064 | +0.036 |
| shared_function_words_nc | simplify | w200_prefix | 360 | +0.136 | +0.044 | +0.064 | +0.048 |
| shared_function_words_nc | simplify | w200_middle | 360 | +0.136 | +0.106 | +0.064 | +0.025 |
| shared_function_words_nc | simplify | w200_suffix | 360 | +0.136 | +0.118 | +0.064 | +0.119 |
| shared_function_words_nc | simplify | w300_middle | 360 | +0.136 | +0.116 | +0.064 | +0.045 |
| char3_5_tfidf_svm | paraphrase | w200_prefix | 360 | +0.187 | +0.144 | +0.088 | +0.074 |
| char3_5_tfidf_svm | paraphrase | w200_middle | 360 | +0.187 | +0.109 | +0.088 | +0.084 |
| char3_5_tfidf_svm | paraphrase | w200_suffix | 360 | +0.187 | +0.179 | +0.088 | +0.092 |
| char3_5_tfidf_svm | paraphrase | w300_middle | 360 | +0.187 | +0.164 | +0.088 | +0.095 |
| char3_5_tfidf_svm | modernize | w200_prefix | 360 | +0.190 | +0.116 | +0.128 | +0.114 |
| char3_5_tfidf_svm | modernize | w200_middle | 360 | +0.190 | +0.086 | +0.128 | +0.053 |
| char3_5_tfidf_svm | modernize | w200_suffix | 360 | +0.190 | +0.155 | +0.128 | +0.124 |
| char3_5_tfidf_svm | modernize | w300_middle | 360 | +0.190 | +0.127 | +0.128 | +0.070 |
| char3_5_tfidf_svm | simplify | w200_prefix | 360 | +0.217 | +0.188 | +0.129 | +0.114 |
| char3_5_tfidf_svm | simplify | w200_middle | 360 | +0.217 | +0.146 | +0.129 | +0.072 |
| char3_5_tfidf_svm | simplify | w200_suffix | 360 | +0.217 | +0.184 | +0.129 | +0.124 |
| char3_5_tfidf_svm | simplify | w300_middle | 360 | +0.217 | +0.161 | +0.129 | +0.098 |

## Interpretation constraints

Positive adaptation gain means this learner recovers some predictive association when trained on rewrites. It does not prove preserved meaning, pure style or all recoverable information. Negative within-domain gaps do not establish that rewriting creates author information. Topic, genre, length and feature/learner choice still matter.

CIs resample the same held-out passage pairs within works and works within fixed authors; they do not refit the learners or cover new authors. Intervals across these many overlapping panels are not simultaneous. No new confirmatory p-values are reported. Equal-length cuts change which content is observed.

Planned but unavailable controls are listed in panel_status.json with zero-count works. Their thresholds and required work coverage are not changed, and no metrics are fabricated.

Reproduction: `.venv/Scripts/python.exe -m research_v2.transfer_extension --model astra_session`. No API calls. See ../PLAN.md, manifest.json and the original generation ledgers for provenance.
