# Semantic Fidelity Audit Protocol

## Status

Design locked; annotations not yet collected.

## Purpose

The rewrite protocol requires preservation of events, characters, narrative sequence, and core meaning. This audit tests whether that requirement is actually met in a human-checkable sample.

## Sampling design

Sample 10% of rewritten passages per condition from the frozen 1080 rewrite rows.

| Condition | Total rewrite rows | Sample size |
|---|---:|---:|
| paraphrase | 360 | 36 |
| modernize | 360 | 36 |
| simplify | 360 | 36 |
| **Total** | **1080** | **108** |

Sampling must be stratified by:

- condition;
- author;
- work where possible;
- QC status where possible, so warning rows are not accidentally hidden.

Use a fixed RNG seed and record it in the sample file.

## Annotation unit

Each annotation item contains:

- original passage text;
- rewritten passage text;
- condition;
- anonymised passage ID;
- no author name;
- no work title;
- no model/provider label.

## Annotators

Use two human annotators. They should annotate independently before resolving disagreements.

## Coding categories

Each annotator codes the following fields:

| Field | Values | Meaning |
|---|---|---|
| `added_facts` | 0/1 | Rewrite adds factual/narrative content not present in original. |
| `omitted_facts` | 0/1 | Rewrite removes important factual/narrative content. |
| `narrative_order_change` | 0/1 | Rewrite changes the order of events, reasoning, or dialogue sequence. |
| `tone_drift` | 0/1 | Rewrite substantially changes tone, affect, irony, formality, or narrative stance. |
| `meaning_preserved_score` | 1-5 | Overall semantic preservation rating. |
| `comment` | free text | Short explanation for any issue. |

## Rating guide

`meaning_preserved_score`:

| Score | Meaning |
|---:|---|
| 1 | Major semantic failure; rewrite is not faithful. |
| 2 | Several important changes or omissions. |
| 3 | Mostly faithful but with noticeable distortion. |
| 4 | Faithful with minor drift. |
| 5 | Faithful; no meaningful semantic distortion. |

## Agreement reporting

Report:

- raw percent agreement for each binary category;
- Cohen's kappa for each binary category if feasible;
- mean absolute difference for the 1-5 semantic preservation score;
- percentage of items where either annotator flags a problem;
- final adjudicated issue rate by condition.

## Planned repository outputs

```text
metadata/semantic_fidelity_sample.csv
metadata/semantic_fidelity_annotation_codebook.csv
metadata/semantic_fidelity_annotations_annotator1.csv
metadata/semantic_fidelity_annotations_annotator2.csv
metadata/semantic_fidelity_adjudicated_results.csv
metadata/semantic_fidelity_summary.csv
logs/semantic_fidelity_audit_report.md
```

## Manuscript use

The semantic fidelity audit should be used to defend the intervention as controlled rewriting rather than hidden summarisation, distortion, or free adaptation. If issue rates are high, the paper must report them honestly and use them as a limitation rather than burying them.