# Deep Manuscript Readiness Audit

## Verdict

The repository is ready to move from dataset/analysis construction into manuscript writing.

This does not mean the manuscript text is finished. It means the empirical package is sufficiently complete, internally checked, traceable, and paper-facing enough that the next work should be writing and interpretation rather than more dataset engineering.

## Evidence checked

### Final reproducibility audit

The final audit report shows `PASS`.

All available checkers pass:

```text
Steps 1-7 source/candidate checker: pass
Step 8 selection checker: pass
Step 9 rewrite protocol checker: pass
Step 11 master dataset checker: pass
Step 12 feature checker: pass
Step 13 modeling matrix checker: pass
Step 14 original baseline checker: pass
Step 15 transfer degradation checker: pass
Step 16 same-condition classifier checker: pass
Step 17 Burrows Delta distance checker: pass
Step 18 feature-family vulnerability checker: pass
Step 19 tables/figures checker: pass
```

The audit checked 36 critical files and found 0 missing files.

### Step completion table

The final step-status table marks every major stage as complete:

```text
1-7 source/candidate construction
8 balanced passage selection
9 rewrite protocol
10 rewrite generation and QC
11 master text dataset
12 stylometric features
13 modeling matrices
14 original baseline
15 original-to-rewritten degradation
16 same-condition rewritten classification
17 Burrows Delta distance analysis
18 feature-family vulnerability
19 statistical tables and figures
20 final reproducibility audit
```

### Dataset and feature design

The locked empirical package contains:

```text
12 canonical Gutenberg works
6 authors
360 selected original passages
1080 controlled LLM rewrites
1440 master text rows
205 stylometric features
6 feature families
passage-level train/validation/test split
```

Feature-family counts are:

```text
char3: 120
function_word: 57
length_rhythm: 8
lexical_richness: 6
punctuation: 10
register_marker: 4
```

### Claim support matrix

The repository has a claim-support matrix covering seven main paper claims:

```text
C1 balanced canonical dataset
C2 205-feature stylometric representation
C3 original author separability
C4 degradation after rewriting
C5 residual separability inside rewritten conditions
C6 inter-author distance contraction
C7 feature-family vulnerability differences
```

All seven claims are marked supported by committed files.

## Main empirical story now supported

### 1. Original authorial separability exists

Original-condition classification gives non-trivial author separability before rewriting.

Best original test results include:

```text
nearest_centroid test macro F1: 0.776931
linear_discriminant_shrinkage test macro F1: 0.776931
diagonal_gaussian_nb test macro F1: 0.760859
```

This supports using author-classification performance as a proxy for measurable stylometric separability.

### 2. Train-on-original transfer degrades after rewriting

For nearest-centroid test results:

```text
original macro F1: 0.776931
paraphrase macro F1: 0.395797
modernize macro F1: 0.560720
simplify macro F1: 0.463636
```

Observed macro-F1 losses:

```text
paraphrase: 0.381133642
modernize: 0.216210995
simplify: 0.313294321
```

Bootstrap 95% confidence intervals are all positive on the test split for nearest-centroid:

```text
paraphrase: [0.264839149, 0.503284926]
modernize: [0.100501182, 0.343607038]
simplify: [0.194675605, 0.451590826]
```

### 3. Rewritten text still retains residual author signal

Same-condition classification shows rewritten texts are not stylistically anonymous.

Nearest-centroid test survival ratios:

```text
paraphrase: 0.803035
modernize: 0.878181
simplify: 0.878181
```

This supports a nuanced claim: rewriting disrupts original-style transfer, but does not erase author-specific structure completely.

### 4. Inter-author stylometric distances contract

Function-word distance ratios relative to original:

```text
paraphrase: 0.794204594
modernize: 0.874955255
simplify: 0.837402343
```

All-feature distance ratios relative to original:

```text
paraphrase: 0.819385059
modernize: 0.894129877
simplify: 0.868868214
```

This supports the phrase `style flattening` more directly than classification alone.

### 5. Feature families differ in vulnerability

The feature-family table shows the largest test losses are concentrated in character trigrams, lexical richness, and register markers for particular rewrite conditions.

The strongest table entries include:

```text
char3 / paraphrase / diagonal_gaussian_nb: loss 0.390815
char3 / paraphrase / nearest_centroid: loss 0.319179
lexical_richness / paraphrase / nearest_centroid: loss 0.268224
char3 / modernize / diagonal_gaussian_nb: loss 0.266201
```

This supports a feature-family discussion rather than only a global model-score discussion.

## Writing readiness judgment by section

### Abstract

Ready.

The abstract can state the dataset size, controlled rewrite conditions, 205-feature stylometric design, and main macro-F1 loss intervals.

### Introduction

Ready, but needs literature framing.

The empirical contribution is ready. The introduction still needs external literature citations around stylometry, authorship attribution, LLM rewriting/paraphrasing, and style transfer. This is manuscript work, not pipeline work.

### Related work

Not yet written.

Needs recent and classical citations. This should be handled during manuscript drafting with current web/literature searches.

### Methods

Ready.

The repository contains enough traceable material to write data sources, passage selection, rewrite protocol, feature extraction, modeling split, classification models, distance analysis, feature-family analysis, bootstrap testing, and reproducibility.

### Results

Ready.

The paper-facing tables and figures exist, and the key results are stable.

### Discussion

Ready for drafting, but interpretation must be careful.

The paper should avoid claiming that all LLMs erase authorial style. The supported claim is narrower:

```text
Under this controlled Gemini 3.1 Flash Lite rewriting setup, authorial separability learned from originals decreases across paraphrase, modernization, and simplification, while same-condition rewritten texts retain residual author-specific signal.
```

### Limitations

Ready.

Important limitations to include:

```text
single LLM model
six public-domain fiction authors
English literary prose only
rewrite conditions are prompt-defined
baseline stylometric classifiers rather than all possible authorship models
passage-level rather than full-book attribution
some rewrite warnings retained but documented
```

### Reproducibility statement

Ready.

The final manifest, step-status table, claim-support matrix, and checker reports are enough for a strong reproducibility paragraph.

## Gaps found

No blocking empirical or repository gaps remain.

The remaining gaps are manuscript-level, not pipeline-level:

1. literature citations still need to be selected and written into the paper;
2. final figures may need publication styling later;
3. results should avoid overclaiming beyond one model family and one source corpus;
4. journal formatting has not yet been applied;
5. exact title/abstract wording still needs final human approval.

## Update made by this audit

This audit file was added to preserve the manuscript-readiness decision and to distinguish completed empirical work from remaining writing work.

## Final decision

Proceed to manuscript writing.

The dataset and analysis pipeline should now be frozen unless a factual or reproducibility-breaking issue is found.
