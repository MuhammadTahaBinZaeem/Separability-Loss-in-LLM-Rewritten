# Human Reading Study Protocol

## Status

Design draft locked; participant data not yet collected.

## Purpose

The computational pipeline measures stylometric separability loss. The human reading study tests whether those computational shifts have a reader-facing correlate: do readers perceive rewritten passages as less stylistically distinctive, more readable, more machine-like, or less similar to the original author's style?

## Participants

Target sample:

```text
72 participants
```

Participant requirements:

- adult readers;
- fluent English reading ability;
- no requirement that participants be literary specialists;
- record basic self-reported literature familiarity.

## Reading load

Each participant reads:

```text
24 passages
```

Use a Latin-square design so that passages are balanced across:

- author;
- condition;
- work;
- participant order;
- original versus rewritten exposure.

No participant should see the same base passage in multiple conditions.

## Conditions

- `original`
- `paraphrase`
- `modernize`
- `simplify`

## Measures

For each passage, collect:

| Measure | Scale | Purpose |
|---|---|---|
| readability | 1-7 Likert | Reader-facing ease of reading. |
| perceived_stylistic_distinctiveness | 1-7 Likert | Whether the passage feels stylistically marked or distinctive. |
| perceived_literary_voice_strength | 1-7 Likert | Whether the passage feels like it has a strong authorial voice. |
| human_or_ai_guess | human / AI / unsure | Whether participants perceive AI mediation. |
| confidence | 1-7 Likert | Confidence in the AI/human judgement. |
| same_author_similarity | 1-7 Likert | In paired items, whether two passages feel like they could be by the same author. |

## Design note

The study should avoid telling participants that the goal is to detect AI rewriting. A neutral framing is better:

> You will read short literary passages and answer questions about style, readability, and similarity.

## Analysis plan

Use mixed-effects models where feasible:

- fixed effects: condition, author, passage length, condition × author;
- random effects: participant and passage ID;
- outcomes: readability, distinctiveness, voice strength, AI/human judgement, similarity rating.

If mixed-effects modeling is not feasible, use clearly marked fallback analyses:

- condition-wise means and confidence intervals;
- ordinal/logistic models for AI/human guesses;
- participant-level aggregation to avoid treating all readings as independent.

## Planned repository outputs

```text
metadata/human_reading_study_design.csv
metadata/human_reading_study_item_bank.csv
metadata/human_reading_study_latin_square.csv
metadata/human_reading_study_results.csv
metadata/human_reading_study_summary.csv
logs/human_reading_study_report.md
```

## Manuscript use

This study should not replace the computational result. It should add a humanities-facing layer: whether measured stylometric contraction corresponds to reader perceptions of style, readability, and AI mediation.

If human readers do not perceive the same pattern as the computational model, that is still valuable. It would support a more nuanced claim: computationally measurable style loss may not map directly onto reader perception.