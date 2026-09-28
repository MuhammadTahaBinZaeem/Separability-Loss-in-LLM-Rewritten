# Exploratory domain-transfer extension: luna56

Not a confirmatory result, human validation or submission-readiness certificate.

Common valid cohort: 317/360 source passages. All panels retain 18 works and six authors.

All estimable 4 x 4 matrices from seven planned panels and three pipelines are in metrics.csv. No best pipeline is selected.

## Full common-cohort comparisons

| Pipeline | Rewrite | O -> O | O -> R | R -> R | Adaptation gain [marginal 95% CI] | Within-domain gap |
|---|---|---:|---:|---:|---|---:|
| shared_stylometry_nc | paraphrase | 0.660 | 0.502 | 0.577 | +0.075 [+0.022, +0.135] | +0.083 |
| shared_stylometry_nc | modernize | 0.660 | 0.523 | 0.544 | +0.022 [-0.031, +0.090] | +0.115 |
| shared_stylometry_nc | simplify | 0.660 | 0.449 | 0.542 | +0.093 [+0.041, +0.153] | +0.118 |
| shared_function_words_nc | paraphrase | 0.563 | 0.466 | 0.498 | +0.032 [-0.022, +0.095] | +0.065 |
| shared_function_words_nc | modernize | 0.563 | 0.452 | 0.480 | +0.027 [-0.025, +0.082] | +0.083 |
| shared_function_words_nc | simplify | 0.563 | 0.443 | 0.464 | +0.021 [-0.032, +0.072] | +0.099 |
| char3_5_tfidf_svm | paraphrase | 0.851 | 0.739 | 0.754 | +0.015 [-0.023, +0.057] | +0.097 |
| char3_5_tfidf_svm | modernize | 0.851 | 0.750 | 0.750 | -0.000 [-0.047, +0.042] | +0.101 |
| char3_5_tfidf_svm | simplify | 0.851 | 0.725 | 0.747 | +0.023 [-0.026, +0.076] | +0.103 |

## Length-control comparisons (same cohort for full and cropped text)

| Pipeline | Rewrite | Control | n | Full transfer loss | Cropped transfer loss | Full within-domain gap | Cropped within-domain gap |
|---|---|---|---:|---:|---:|---:|---:|
| shared_stylometry_nc | paraphrase | w200_prefix | 317 | +0.158 | +0.058 | +0.083 | +0.079 |
| shared_stylometry_nc | paraphrase | w200_middle | 317 | +0.158 | +0.119 | +0.083 | +0.099 |
| shared_stylometry_nc | paraphrase | w200_suffix | 317 | +0.158 | +0.099 | +0.083 | +0.073 |
| shared_stylometry_nc | paraphrase | w300_middle | 317 | +0.158 | +0.092 | +0.083 | +0.059 |
| shared_stylometry_nc | modernize | w200_prefix | 317 | +0.137 | +0.095 | +0.115 | +0.093 |
| shared_stylometry_nc | modernize | w200_middle | 317 | +0.137 | +0.123 | +0.115 | +0.098 |
| shared_stylometry_nc | modernize | w200_suffix | 317 | +0.137 | +0.110 | +0.115 | +0.105 |
| shared_stylometry_nc | modernize | w300_middle | 317 | +0.137 | +0.105 | +0.115 | +0.081 |
| shared_stylometry_nc | simplify | w200_prefix | 317 | +0.211 | +0.119 | +0.118 | +0.067 |
| shared_stylometry_nc | simplify | w200_middle | 317 | +0.211 | +0.150 | +0.118 | +0.076 |
| shared_stylometry_nc | simplify | w200_suffix | 317 | +0.211 | +0.133 | +0.118 | +0.107 |
| shared_stylometry_nc | simplify | w300_middle | 317 | +0.211 | +0.120 | +0.118 | +0.085 |
| shared_function_words_nc | paraphrase | w200_prefix | 317 | +0.097 | +0.086 | +0.065 | +0.048 |
| shared_function_words_nc | paraphrase | w200_middle | 317 | +0.097 | +0.051 | +0.065 | +0.052 |
| shared_function_words_nc | paraphrase | w200_suffix | 317 | +0.097 | +0.108 | +0.065 | +0.062 |
| shared_function_words_nc | paraphrase | w300_middle | 317 | +0.097 | +0.055 | +0.065 | +0.035 |
| shared_function_words_nc | modernize | w200_prefix | 317 | +0.110 | +0.076 | +0.083 | +0.065 |
| shared_function_words_nc | modernize | w200_middle | 317 | +0.110 | +0.051 | +0.083 | +0.070 |
| shared_function_words_nc | modernize | w200_suffix | 317 | +0.110 | +0.109 | +0.083 | +0.103 |
| shared_function_words_nc | modernize | w300_middle | 317 | +0.110 | +0.066 | +0.083 | +0.055 |
| shared_function_words_nc | simplify | w200_prefix | 317 | +0.119 | +0.103 | +0.099 | +0.086 |
| shared_function_words_nc | simplify | w200_middle | 317 | +0.119 | +0.054 | +0.099 | +0.029 |
| shared_function_words_nc | simplify | w200_suffix | 317 | +0.119 | +0.113 | +0.099 | +0.104 |
| shared_function_words_nc | simplify | w300_middle | 317 | +0.119 | +0.089 | +0.099 | +0.066 |
| char3_5_tfidf_svm | paraphrase | w200_prefix | 317 | +0.112 | +0.128 | +0.097 | +0.119 |
| char3_5_tfidf_svm | paraphrase | w200_middle | 317 | +0.112 | +0.141 | +0.097 | +0.101 |
| char3_5_tfidf_svm | paraphrase | w200_suffix | 317 | +0.112 | +0.139 | +0.097 | +0.100 |
| char3_5_tfidf_svm | paraphrase | w300_middle | 317 | +0.112 | +0.095 | +0.097 | +0.089 |
| char3_5_tfidf_svm | modernize | w200_prefix | 317 | +0.101 | +0.089 | +0.101 | +0.082 |
| char3_5_tfidf_svm | modernize | w200_middle | 317 | +0.101 | +0.082 | +0.101 | +0.096 |
| char3_5_tfidf_svm | modernize | w200_suffix | 317 | +0.101 | +0.105 | +0.101 | +0.098 |
| char3_5_tfidf_svm | modernize | w300_middle | 317 | +0.101 | +0.100 | +0.101 | +0.079 |
| char3_5_tfidf_svm | simplify | w200_prefix | 317 | +0.126 | +0.159 | +0.103 | +0.092 |
| char3_5_tfidf_svm | simplify | w200_middle | 317 | +0.126 | +0.124 | +0.103 | +0.097 |
| char3_5_tfidf_svm | simplify | w200_suffix | 317 | +0.126 | +0.118 | +0.103 | +0.088 |
| char3_5_tfidf_svm | simplify | w300_middle | 317 | +0.126 | +0.119 | +0.103 | +0.064 |

## Interpretation constraints

Positive adaptation gain means this learner recovers some predictive association when trained on rewrites. It does not prove preserved meaning, pure style or all recoverable information. Negative within-domain gaps do not establish that rewriting creates author information. Topic, genre, length and feature/learner choice still matter.

CIs resample the same held-out passage pairs within works and works within fixed authors; they do not refit the learners or cover new authors. Intervals across these many overlapping panels are not simultaneous. No new confirmatory p-values are reported. Equal-length cuts change which content is observed.

Planned but unavailable controls are listed in panel_status.json with zero-count works. Their thresholds and required work coverage are not changed, and no metrics are fabricated.

Reproduction: `.venv/Scripts/python.exe -m research_v2.transfer_extension --model luna56`. No API calls. See ../PLAN.md, manifest.json and the original generation ledgers for provenance.
