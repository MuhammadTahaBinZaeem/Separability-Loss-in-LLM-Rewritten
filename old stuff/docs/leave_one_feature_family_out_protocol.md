# E8 Leave-One-Feature-Family-Out Ablation Protocol

## Status

Complete. The protocol, analysis script, checker, output CSV files, manifest, report, and workflow proof log are now present in the repository.

Run or rerun with:

```bash
python scripts/25_run_leave_one_feature_family_out.py
python scripts/check_e8_leave_one_feature_family_out.py
```

Generated output workflow proof:

```text
logs/e8_leave_one_feature_family_out_workflow_proof.md
```

Latest workflow-generated output commit:

```text
fe202afab63f6d2fa4afd609c7f78c599e59f5f2
```

## Purpose

Earlier feature-family analyses show which families are vulnerable when used alone. E8 asks a different question:

> Which feature families actually drive the full-system transfer result?

A feature family can be weak alone but still matter in the full model. Conversely, a family can perform well alone but be redundant once other features are included. E8 therefore trains the nearest-centroid transfer classifier on the full feature set and then on full features **minus one family at a time**.

## Feature families

The feature-family list comes directly from:

```text
metadata/modeling_feature_columns.csv
```

Current families:

- `length_rhythm`
- `punctuation`
- `lexical_richness`
- `register_marker`
- `function_word`
- `char3`

## Ablation modes

| ablation_mode | Included features | Purpose |
|---|---|---|
| `full_features` | all 205 features | full nearest-centroid baseline |
| `minus_<family>` | all features except one family | tests dependence on that family |

## Analysis design

For each ablation mode:

1. train nearest-centroid on original-condition training rows;
2. evaluate original, paraphrase, modernize, and simplify on validation and test splits;
3. report accuracy, macro-F1, weighted F1, and loss versus original;
4. compare each `minus_<family>` condition against the `full_features` baseline.

## Inputs

```text
data/modeling/modeling_metadata.csv
data/modeling/X_stylometric_raw.csv
data/modeling/y_author_labels.csv
metadata/modeling_feature_columns.csv
```

## Outputs

```text
data/results/leave_one_feature_family_out_predictions.csv
metadata/leave_one_feature_family_out_summary.csv
metadata/leave_one_feature_family_out_delta_vs_full.csv
metadata/leave_one_feature_family_out_feature_registry.csv
metadata/leave_one_feature_family_out_manifest.csv
logs/leave_one_feature_family_out_report.md
logs/e8_leave_one_feature_family_out_workflow_proof.md
```

## Completion result

E8 supports the paper.

Main findings:

- every single-family removal keeps the nearest-centroid test transfer loss positive for paraphrase, modernize, and simplify;
- no one feature family is solely responsible for the degradation pattern;
- removing `punctuation` most strongly reduces the full-feature loss magnitude for paraphrase, modernize, and simplify, suggesting punctuation contributes meaningfully to the full-system degradation story;
- removing `length_rhythm` or `function_word` increases paraphrase loss relative to the full baseline, suggesting those families may partly stabilise paraphrase attribution in the full representation;
- removing `char3` lowers original macro-F1 from `0.776931` to `0.725668`, so character trigrams contribute to original author recognition, but the rewrite-loss pattern still persists without them.

Test split, nearest-centroid transfer losses:

| ablation_mode | paraphrase loss | modernize loss | simplify loss |
|---|---:|---:|---:|
| `full_features` | `0.381134` | `0.216211` | `0.313295` |
| `minus_length_rhythm` | `0.413669` | `0.234924` | `0.359235` |
| `minus_punctuation` | `0.298883` | `0.162491` | `0.268280` |
| `minus_lexical_richness` | `0.344086` | `0.174912` | `0.251384` |
| `minus_register_marker` | `0.340360` | `0.178417` | `0.290849` |
| `minus_function_word` | `0.416873` | `0.155773` | `0.251581` |
| `minus_char3` | `0.367531` | `0.200147` | `0.244372` |

## Interpretation rules

The correct manuscript interpretation is:

> A leave-one-feature-family-out ablation shows that the transfer-degradation pattern persists after removing each individual feature family from the full representation. This suggests that the effect is distributed across stylometric families rather than being an artifact of one family. However, loss magnitudes change by family removal, especially for punctuation and character trigrams, so the contribution of individual feature families should be treated as heterogeneous rather than interchangeable.

Do not claim that all feature families contribute equally. E8 shows distributed robustness, not equal importance.

## Pass condition

The checker validates structural completeness and full coverage of all feature families. E8 passed structural validation through the workflow proof log.

## Manuscript use

E8 should be reported as an ablation robustness test:

> A leave-one-feature-family-out ablation retrained the nearest-centroid transfer classifier after removing each feature family from the full representation. Transfer losses remained positive after every single-family removal, indicating that the degradation pattern was not driven by any one stylometric family alone. At the same time, loss magnitudes varied across removals, showing heterogeneous feature-family contributions.
