# Pipeline Steps 1-15 Paper-Readiness Audit

## Audit status

Steps 1-15 are implemented, committed, and internally consistent enough to support the next paper-building stages.

This audit does not claim the full paper is finished. It confirms that the source layer, passage layer, rewrite layer, feature layer, modeling matrix layer, original-author baseline, and original-to-rewritten degradation experiment are complete enough to be treated as stable inputs for later statistical testing, feature-family analysis, tables, figures, and manuscript writing.

## Step coverage verdict

| Stage | Verdict |
|---|---|
| Steps 1-7 source and candidate construction | Complete |
| Step 8 selected original passages | Complete |
| Step 9 rewrite protocol | Complete |
| Step 10 rewrite generation and QC | Complete |
| Step 11 master text dataset | Complete |
| Step 12 stylometric feature extraction | Complete |
| Step 13 modeling matrix preparation | Complete |
| Step 14 original author baseline | Complete |
| Step 15 original-to-rewritten degradation | Complete |

## Evidence summary

### Source and candidate layer

The canonical Gutenberg source layer contains 12 cleaned works, 1,373,324 cleaned words, and zero warning-flagged files. The candidate layer contains 1,879 candidate passages, all passing length and sentence-count checks, with all six authors above the target minimum candidate count.

### Selected original passage layer

Step 8 selected 360 original passages across six authors and twelve works, with 60 passages per author and 30 per work. The selection status is complete.

### Rewrite request and rewrite generation layer

Step 9 prepared 1,080 rewrite requests from 360 selected original passages and three rewrite conditions.

Step 10 generated 1,080 raw and parsed rewrite rows using Gemini 3.1 Flash Lite. Final QC accepted 969 pass rows and 111 warning rows with zero fail rows, zero empty outputs, and zero prompt/source leakage.

### Master text layer

Step 11 produced the 1,440-row master text dataset:

```text
360 original
360 paraphrase
360 modernize
360 simplify
```

The master dataset has six authors, twelve works, 360 unique passages, zero master QC failures, and zero empty text rows.

### Feature layer

Step 12 produced 1,440 feature rows with 205 numeric stylometric features and 9 identifier columns. The feature families are:

```text
char3: 120
function_word: 57
length_rhythm: 8
lexical_richness: 6
punctuation: 10
register_marker: 4
```

This gives a strong enough stylometric representation for authorship classification, distance analysis, and feature-family vulnerability testing.

### Modeling matrix layer

Step 13 produced modeling matrices with 1,440 rows and 205 feature columns. The passage-level split is:

```text
train: 1008 rows / 252 passages
validation: 216 rows / 54 passages
test: 216 rows / 54 passages
```

All four versions of each passage stay in the same split. This is necessary to avoid content leakage between original and rewritten versions of the same passage.

The descriptive scaled matrix is explicitly labeled as full-dataset descriptive scaling only, not for classifier training.

### Original author baseline

Step 14 uses only original-condition rows. It trains on 252 original rows and evaluates on 54 validation and 54 test original rows.

Best validation model:

```text
diagonal_gaussian_nb
validation macro F1: 0.683694
test macro F1: 0.760859
test accuracy: 0.759259
```

This confirms that authorial style separability is measurable before rewriting.

### Original-to-rewritten degradation experiment

Step 15 trains only on original-condition training rows. The scaler is fit only on train/original rows. It evaluates original, paraphrase, modernize, and simplify conditions separately.

Best original-test model:

```text
nearest_centroid
original test macro F1: 0.776931
original test accuracy: 0.777778
```

For that model, test macro-F1 degradation is:

```text
original: 0.776931, loss 0.000000
paraphrase: 0.395797, loss 0.381134
modernize: 0.560720, loss 0.216211
simplify: 0.463636, loss 0.313295
```

The degradation effect is directionally clear: all three rewrite conditions reduce train-on-original author separability on the test split.

## Paper-readiness judgment

The pipeline up to Step 15 is strong enough to support a serious paper's empirical core, but it is not yet the final paper-ready result package.

The current state is suitable for:

- methods section drafting;
- dataset construction description;
- rewrite protocol description;
- baseline classification result discussion;
- first core degradation result discussion.

The remaining work for a top-level paper should include:

1. rewritten-to-rewritten classification to test whether author signals survive within rewritten conditions;
2. Burrows' Delta and inter-author distance analysis;
3. feature-family vulnerability analysis;
4. statistical testing and confidence intervals;
5. final tables and figures;
6. limitations and reproducibility notes;
7. final consistency audit.

## Limitations to state honestly later

- The rewriting model is a single Gemini model, so model-specific rewrite behavior is not separated from general LLM rewriting behavior.
- The dataset uses public-domain English fiction from six authors and twelve works, so the findings should not be generalized to all literature.
- Some rewrite outputs have length warnings; they are retained because QC fail count is zero and warnings are documented.
- Step 15 uses baseline classifiers, not deep learning models. This is acceptable because the research question concerns stylometric separability, not maximum possible classifier performance.
- The current results establish a strong degradation signal, but later statistical tests are still needed before final paper claims.

## Final audit verdict

Steps 1-15 are complete enough to lock as the first major paper-ready milestone.

The project should now proceed to Step 16 without changing prior data unless a later audit discovers a reproducibility-breaking issue.
