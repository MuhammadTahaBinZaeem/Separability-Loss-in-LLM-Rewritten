# E4 Semantic Fidelity Audit Protocol

## Status

Package builder added; annotations not yet collected.

## Purpose

The semantic fidelity audit checks whether controlled LLM rewrites preserve the source passage's meaning closely enough for stylometric comparison.

The audit directly addresses the reviewer objection that observed author-signal degradation may be caused by content changes rather than style rewriting.

## Sample design

The audit uses a deterministic 10% sample of the frozen core rewrite dataset:

```text
6 authors × 2 works × 3 rewrite conditions × 3 passages = 108 rewritten passages
```

This equals:

| Condition | Total rewrite rows | Sample size |
|---|---:|---:|
| paraphrase | 360 | 36 |
| modernize | 360 | 36 |
| simplify | 360 | 36 |
| **Total** | **1080** | **108** |

The design is balanced by:

- condition;
- author;
- work;
- deterministic hash-based selection seed.

## Files

```text
data/audit/semantic_fidelity_sample.csv
data/audit/semantic_fidelity_annotation_sheet.csv
data/audit/semantic_fidelity_key.csv
metadata/semantic_fidelity_audit_manifest.csv
logs/semantic_fidelity_audit_build_report.md
```

The annotation sheet omits author and work names. The key file preserves provenance for analysis.

## Annotation unit

Each annotation item contains:

- audit ID;
- rewrite condition;
- original passage text;
- rewritten passage text;
- blank coding columns.

Use two human annotators. They should annotate independently before any disagreement discussion.

## Coding fields

### added_facts_0_1

Use `1` if the rewrite introduces a material fact, event, object, causal relation, character attribute, or setting detail that is not present in the original. Otherwise use `0`.

### omitted_facts_0_1

Use `1` if the rewrite removes a material fact, event, object, causal relation, character attribute, or setting detail that is present in the original. Minor wording compression is not automatically an omission unless meaning is lost.

### narrative_order_change_0_1

Use `1` if the rewrite changes the order of events, reasoning, dialogue, or presentation in a way that could affect interpretation.

### speaker_or_character_relation_change_0_1

Use `1` if the rewrite changes who is speaking, who is acting, or the relationship between characters/speakers.

### tone_drift_0_2

Use:

```text
0 = no meaningful tone drift
1 = mild tone drift, but passage remains comparable
2 = strong tone drift that changes the rhetorical or affective force
```

### meaning_preservation_1_5

Use:

```text
1 = meaning badly changed
2 = substantial semantic change
3 = partly preserved but with important drift
4 = mostly preserved with minor issues
5 = meaning preserved very closely
```

### overall_usable_yes_no

Use `yes` if the rewrite remains usable for the controlled style-transfer experiment. Use `no` if semantic drift is severe enough that the row should be excluded or separately analyzed.

## Disagreement handling

After both annotators complete the sheet:

1. compute raw agreement for each binary field;
2. compute mean and absolute difference for `tone_drift_0_2` and `meaning_preservation_1_5`;
3. flag rows where:
   - annotators disagree on `overall_usable_yes_no`;
   - either annotator marks added facts, omitted facts, narrative-order change, or character-relation change;
   - meaning preservation is below 4 from either annotator;
   - tone drift is 2 from either annotator.

## Reporting

The paper should report:

- number of audited rewrites;
- condition balance;
- author/work balance;
- added-fact rate;
- omitted-fact rate;
- narrative-order-change rate;
- speaker/character-relation-change rate;
- tone-drift distribution;
- mean meaning-preservation score;
- overall usable rate;
- inter-annotator agreement.

## Manuscript wording rule

If semantic fidelity is high, the paper may claim that the rewrite intervention was broadly meaning-preserving.

If semantic fidelity is mixed, the paper must phrase the result as conditional and include a sensitivity analysis excluding rows marked unusable or semantically drifted.