# Exploratory domain-transfer extension: gem31lite

Not a confirmatory result, human validation or submission-readiness certificate.

Common valid cohort: 359/360 source passages. All panels retain 18 works and six authors.

All estimable 4 x 4 matrices from seven planned panels and three pipelines are in metrics.csv. No best pipeline is selected.

## Full common-cohort comparisons

| Pipeline | Rewrite | O -> O | O -> R | R -> R | Adaptation gain [marginal 95% CI] | Within-domain gap |
|---|---|---:|---:|---:|---|---:|
| shared_stylometry_nc | paraphrase | 0.636 | 0.310 | 0.454 | +0.144 [+0.069, +0.228] | +0.182 |
| shared_stylometry_nc | modernize | 0.636 | 0.364 | 0.456 | +0.092 [+0.018, +0.175] | +0.180 |
| shared_stylometry_nc | simplify | 0.636 | 0.307 | 0.399 | +0.091 [+0.026, +0.162] | +0.237 |
| shared_function_words_nc | paraphrase | 0.557 | 0.334 | 0.384 | +0.050 [-0.012, +0.118] | +0.173 |
| shared_function_words_nc | modernize | 0.557 | 0.366 | 0.393 | +0.028 [-0.037, +0.088] | +0.164 |
| shared_function_words_nc | simplify | 0.557 | 0.380 | 0.357 | -0.023 [-0.080, +0.034] | +0.200 |
| char3_5_tfidf_svm | paraphrase | 0.862 | 0.479 | 0.648 | +0.169 [+0.084, +0.261] | +0.214 |
| char3_5_tfidf_svm | modernize | 0.862 | 0.581 | 0.699 | +0.118 [+0.043, +0.195] | +0.163 |
| char3_5_tfidf_svm | simplify | 0.862 | 0.557 | 0.645 | +0.088 [+0.020, +0.158] | +0.217 |

## Length-control comparisons (same cohort for full and cropped text)

| Pipeline | Rewrite | Control | n | Full transfer loss | Cropped transfer loss | Full within-domain gap | Cropped within-domain gap |
|---|---|---|---:|---:|---:|---:|---:|
| shared_stylometry_nc | paraphrase | w200_prefix | 339 | +0.304 | +0.230 | +0.163 | +0.158 |
| shared_stylometry_nc | paraphrase | w200_middle | 339 | +0.304 | +0.219 | +0.163 | +0.110 |
| shared_stylometry_nc | paraphrase | w200_suffix | 339 | +0.304 | +0.237 | +0.163 | +0.145 |
| shared_stylometry_nc | paraphrase | w300_middle | — | Not estimable | Not estimable | Not estimable | Not estimable |
| shared_stylometry_nc | modernize | w200_prefix | 339 | +0.235 | +0.235 | +0.164 | +0.121 |
| shared_stylometry_nc | modernize | w200_middle | 339 | +0.235 | +0.198 | +0.164 | +0.130 |
| shared_stylometry_nc | modernize | w200_suffix | 339 | +0.235 | +0.179 | +0.164 | +0.134 |
| shared_stylometry_nc | modernize | w300_middle | — | Not estimable | Not estimable | Not estimable | Not estimable |
| shared_stylometry_nc | simplify | w200_prefix | 339 | +0.281 | +0.213 | +0.196 | +0.133 |
| shared_stylometry_nc | simplify | w200_middle | 339 | +0.281 | +0.210 | +0.196 | +0.155 |
| shared_stylometry_nc | simplify | w200_suffix | 339 | +0.281 | +0.203 | +0.196 | +0.136 |
| shared_stylometry_nc | simplify | w300_middle | — | Not estimable | Not estimable | Not estimable | Not estimable |
| shared_function_words_nc | paraphrase | w200_prefix | 339 | +0.214 | +0.158 | +0.175 | +0.116 |
| shared_function_words_nc | paraphrase | w200_middle | 339 | +0.214 | +0.098 | +0.175 | +0.043 |
| shared_function_words_nc | paraphrase | w200_suffix | 339 | +0.214 | +0.185 | +0.175 | +0.160 |
| shared_function_words_nc | paraphrase | w300_middle | — | Not estimable | Not estimable | Not estimable | Not estimable |
| shared_function_words_nc | modernize | w200_prefix | 339 | +0.187 | +0.149 | +0.167 | +0.128 |
| shared_function_words_nc | modernize | w200_middle | 339 | +0.187 | +0.103 | +0.167 | +0.067 |
| shared_function_words_nc | modernize | w200_suffix | 339 | +0.187 | +0.139 | +0.167 | +0.149 |
| shared_function_words_nc | modernize | w300_middle | — | Not estimable | Not estimable | Not estimable | Not estimable |
| shared_function_words_nc | simplify | w200_prefix | 339 | +0.192 | +0.141 | +0.200 | +0.140 |
| shared_function_words_nc | simplify | w200_middle | 339 | +0.192 | +0.093 | +0.200 | +0.098 |
| shared_function_words_nc | simplify | w200_suffix | 339 | +0.192 | +0.156 | +0.200 | +0.148 |
| shared_function_words_nc | simplify | w300_middle | — | Not estimable | Not estimable | Not estimable | Not estimable |
| char3_5_tfidf_svm | paraphrase | w200_prefix | 339 | +0.396 | +0.323 | +0.241 | +0.197 |
| char3_5_tfidf_svm | paraphrase | w200_middle | 339 | +0.396 | +0.276 | +0.241 | +0.129 |
| char3_5_tfidf_svm | paraphrase | w200_suffix | 339 | +0.396 | +0.270 | +0.241 | +0.174 |
| char3_5_tfidf_svm | paraphrase | w300_middle | — | Not estimable | Not estimable | Not estimable | Not estimable |
| char3_5_tfidf_svm | modernize | w200_prefix | 339 | +0.300 | +0.232 | +0.183 | +0.147 |
| char3_5_tfidf_svm | modernize | w200_middle | 339 | +0.300 | +0.230 | +0.183 | +0.084 |
| char3_5_tfidf_svm | modernize | w200_suffix | 339 | +0.300 | +0.249 | +0.183 | +0.099 |
| char3_5_tfidf_svm | modernize | w300_middle | — | Not estimable | Not estimable | Not estimable | Not estimable |
| char3_5_tfidf_svm | simplify | w200_prefix | 339 | +0.310 | +0.279 | +0.230 | +0.196 |
| char3_5_tfidf_svm | simplify | w200_middle | 339 | +0.310 | +0.253 | +0.230 | +0.156 |
| char3_5_tfidf_svm | simplify | w200_suffix | 339 | +0.310 | +0.238 | +0.230 | +0.202 |
| char3_5_tfidf_svm | simplify | w300_middle | — | Not estimable | Not estimable | Not estimable | Not estimable |

## Interpretation constraints

Positive adaptation gain means this learner recovers some predictive association when trained on rewrites. It does not prove preserved meaning, pure style or all recoverable information. Negative within-domain gaps do not establish that rewriting creates author information. Topic, genre, length and feature/learner choice still matter.

CIs resample the same held-out passage pairs within works and works within fixed authors; they do not refit the learners or cover new authors. Intervals across these many overlapping panels are not simultaneous. No new confirmatory p-values are reported. Equal-length cuts change which content is observed.

Planned but unavailable controls are listed in panel_status.json with zero-count works. Their thresholds and required work coverage are not changed, and no metrics are fabricated.

Reproduction: `.venv/Scripts/python.exe -m research_v2.transfer_extension --model gem31lite`. No API calls. See ../PLAN.md, manifest.json and the original generation ledgers for provenance.
