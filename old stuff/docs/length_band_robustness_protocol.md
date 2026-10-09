# E7 Length-Band Robustness Protocol

## Status

Complete. The protocol, analysis script, checker, output CSV files, manifest, report, and workflow proof log are now present in the repository.

Run or rerun with:

```bash
python scripts/24_run_length_band_robustness.py
python scripts/check_e7_length_band_robustness.py
```

Generated output workflow proof:

```text
logs/e7_length_band_robustness_workflow_proof.md
```

Latest workflow-generated output commit:

```text
94c19220381aa8e4a00613024bf07c232b08a5c4
```

## Purpose

The main paper argues that controlled LLM rewriting reduces measurable authorial separability. A reviewer could object that the observed degradation is partly a passage-length artifact: rewritten passages may be shorter or longer than originals, and stylometric features can be length-sensitive.

E7 tests whether the transfer degradation pattern persists when evaluation rows are stratified by passage length.

## Band definitions

The planned length bands are:

| band_id | Word-count range |
|---|---:|
| `450_500` | 450-500 words |
| `501_575` | 501-575 words |
| `576_650` | 576-650 words |
| `outside_bands` | Any row outside the three planned bands |

## Two complementary grouping strategies

The selected original passages mostly fall in the 550-650 word region, while rewritten passages may shift downward or upward. Therefore E7 uses two length grouping strategies instead of pretending that every band contains comparable original rows.

### 1. Actual text length bands

Each evaluated text is assigned to a band using its own `word_count_feature`.

This directly tests whether performance changes among shorter or longer generated outputs. It is useful for detecting whether especially short rewrites are driving errors.

Limitation: some actual-length bands contain rewritten rows but no original rows, so within-band loss versus original is unavailable. This occurred in the `450_500` actual-length band because no original rows were that short.

### 2. Source-original length bands

Each evaluated text is assigned to a band using the word count of its corresponding original passage.

This preserves passage comparability across original/paraphrase/modernize/simplify versions. It is the main reviewer-facing length robustness test, because every version of the same passage is compared inside the same original-length stratum.

## Analysis design

For each grouping strategy, the script:

1. trains the transfer classifiers on all original-condition training rows;
2. evaluates original, paraphrase, modernize, and simplify rows in validation and test splits;
3. stratifies predictions by length band;
4. reports accuracy, macro-F1, weighted F1, row counts, and loss versus the same-band original baseline where available.

The three transfer classifiers are retained:

- `nearest_centroid`
- `diagonal_gaussian_nb`
- `linear_discriminant_shrinkage`

## Inputs

```text
data/modeling/modeling_metadata.csv
data/modeling/X_stylometric_raw.csv
data/modeling/y_author_labels.csv
metadata/modeling_feature_columns.csv
```

## Outputs

```text
data/results/length_band_transfer_predictions.csv
metadata/length_band_transfer_summary.csv
metadata/length_band_distribution_summary.csv
metadata/length_band_manifest.csv
logs/length_band_robustness_report.md
logs/e7_length_band_robustness_workflow_proof.md
```

## Completion result

E7 supports the paper, with one important nuance:

- In the main comparable source-original length grouping, nearest-centroid test losses remain positive in both populated original-length bands.
- Source-original band `501_575` has 42 test rows per condition and shows positive losses for paraphrase `0.365744`, modernize `0.228224`, and simplify `0.360043`.
- Source-original band `576_650` has only 12 test rows per condition, so it is smaller and less stable, but losses remain positive: paraphrase `0.422222`, modernize `0.160317`, and simplify `0.238889`.
- Actual-text-length grouping shows that many rewrites shift into shorter bands where no original baseline exists, especially `450_500`. This means length shift is a real descriptive feature of the rewrite process and should be acknowledged.

## Interpretation rules

The correct manuscript interpretation is:

> A source-original length-band robustness analysis shows that the rewrite-associated loss persists within the two populated original-length strata, suggesting that the main pattern is not only an artifact of original passage length. However, actual-text-length distributions reveal that rewriting often moves passages into shorter bands, so length shift should be treated as part of the rewriting intervention rather than ignored.

Do not claim that length has no role. E7 shows robustness across comparable source-original bands, not complete independence from generated length.

## Pass condition

The checker validates structural completeness and presence of the expected grouping strategies, models, splits, conditions, and populated bands. E7 passed structural validation through the workflow proof log.

## Manuscript use

E7 should be used as a robustness paragraph or supplementary table:

> A length-band robustness analysis stratified transfer predictions by both actual rewritten length and source-original passage length. The main transfer-loss pattern persisted in the two populated source-original length bands, while actual-length distributions showed that rewriting often shortened passages. We therefore treat length shift as a documented part of the rewrite intervention, not as an unexamined confound.
