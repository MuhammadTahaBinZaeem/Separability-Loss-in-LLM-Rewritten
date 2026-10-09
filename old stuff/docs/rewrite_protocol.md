# Step 9 Controlled Rewriting Protocol

## Purpose

Step 9 defines the controlled rewriting protocol for transforming the 360 selected original passages into three LLM-rewritten conditions:

- `paraphrase`
- `modernize`
- `simplify`

This step does **not** generate the rewritten dataset. It freezes the experimental prompt design, metadata schema, quality-control rules, and reproducibility requirements before rewriting begins.

## Why this step matters

The paper studies loss of computationally detectable author-specific style separability after LLM rewriting. The rewrite protocol must therefore avoid uncontrolled transformations that would make the result scientifically weak.

The rewriting tasks must be strong enough to change expression but controlled enough that the passage still represents the same narrative/semantic content.

## Locked rewriting conditions

### `original`

The source passage selected in Step 8. This condition is not rewritten.

### `paraphrase`

Light rewrite.

Goal: preserve meaning, plot content, characters, sequence, and approximate passage length while changing wording and local phrasing.

Expected effect: mild style movement away from the original author.

### `modernize`

Medium rewrite.

Goal: update archaic or nineteenth-century phrasing into contemporary English while preserving content, tone category, and narrative sequence.

Expected effect: moderate style movement, especially in diction, punctuation, syntax, and register.

### `simplify`

Heavy rewrite.

Goal: make the passage easier to read for a general modern reader while preserving the same events and core meaning.

Expected effect: strong style movement, especially in sentence length, lexical diversity, syntax, punctuation, and author-specific rhythm.

## Explicitly excluded conditions

The following are excluded from the main experiment:

- summarization;
- translation;
- creative continuation;
- adaptation into another genre;
- dialogue-only rewriting;
- free literary imitation;
- author-style imitation.

Summarization is excluded because shortening and restructuring would create a confound: style separability would decrease partly because the passage length and narrative structure changed.

## General rewriting constraints

Every rewrite must obey these rules:

1. Preserve the same events, objects, characters, speaker relationships, and narrative sequence.
2. Do not add new plot information.
3. Do not remove material facts.
4. Do not summarize.
5. Do not explain the passage.
6. Do not mention the author, title, Project Gutenberg, dataset, prompt, or experiment.
7. Do not add headings, bullet points, stage directions, notes, or commentary.
8. Preserve paragraph structure where reasonably possible.
9. Keep the output in prose.
10. Keep the output within the configured length tolerance.

## Length tolerance

Target length rule:

```text
rewritten_word_count should be within ±15% of original_word_count
```

Hard warning threshold:

```text
rewritten_word_count outside ±20% receives a QC warning
```

This allows linguistic transformation while preventing hidden summarization or expansion.

## Prompt isolation rule

The prompt must not reveal the author name or title to the rewriting model.

Reason: if the model sees `Jane Austen`, `Poe`, `Twain`, etc., it may intentionally imitate or suppress a known style. The experiment is about style separability loss under generic rewriting, not author-aware rewriting.

The rewriting model may receive:

- `passage_id`
- `condition`
- the original passage text
- condition-specific instructions

The rewriting model must not receive:

- author name
- work title
- Gutenberg ID
- candidate ID
- feature statistics
- expected analysis goals

## Output format

Each model response must be captured as a JSON object with exactly these fields:

```json
{
  "passage_id": "...",
  "condition": "paraphrase|modernize|simplify",
  "rewritten_text": "..."
}
```

If a model provider returns extra metadata, store that separately in the run log, not inside the rewritten text field.

## Rewrite reproducibility metadata

Each rewrite row must eventually store:

- `passage_id`
- `condition`
- `model_provider`
- `model_name`
- `model_version_or_snapshot`
- `temperature`
- `top_p`
- `seed_if_available`
- `prompt_template_id`
- `prompt_template_sha256`
- `source_text_sha256`
- `rewritten_text_sha256`
- `original_word_count`
- `rewritten_word_count`
- `length_ratio`
- `qc_status`
- `qc_flags`
- `created_utc`

## Recommended generation settings

Default setting for the main experiment:

```text
temperature: 0.2
top_p: 1.0
presence_penalty: 0
frequency_penalty: 0
```

Reason: lower stochasticity improves reproducibility and prevents the rewrite task from becoming creative adaptation.

If the chosen LLM supports a seed, set and record it.

## Main prompt design

Use one system instruction shared across all conditions and one condition-specific user instruction.

The system instruction should establish that the model must perform a controlled rewrite and output only valid JSON.

The user instruction should define the specific rewriting condition.

## Quality-control rules

Each rewrite must be checked for:

- valid JSON parse;
- expected `passage_id`;
- expected `condition`;
- non-empty `rewritten_text`;
- no prompt leakage;
- no author/title/source leakage;
- no markdown headings or bullet lists;
- word-count ratio within acceptable bounds;
- minimum sentence count;
- high textual overlap warning for paraphrase if almost unchanged;
- excessive shortening warning;
- excessive expansion warning.

## QC status values

Allowed values:

- `pass`
- `warning`
- `fail`

A warning row may remain in the dataset if documented. A fail row must be regenerated or manually reviewed.

## Main generated datasets for later steps

Step 10 should eventually create:

```text
data/interim/rewrite_requests.jsonl
data/interim/rewrite_responses_raw.jsonl
data/interim/rewrite_responses_parsed.csv
metadata/rewrite_run_manifest.csv
metadata/rewrite_qc_report.csv
logs/step_10_rewrite_generation_report.md
```

Step 11 should eventually create the final master text dataset:

```text
data/final/master_text_dataset.csv
```

Expected final text rows after rewriting:

```text
360 original + 360 paraphrase + 360 modernize + 360 simplify = 1440 text rows
```

## Step 9 completion criteria

Step 9 is complete when the repository contains:

- this protocol document;
- a condition registry;
- prompt templates;
- prompt/output schema;
- generation configuration;
- rewrite batch-preparation script;
- rewrite QC/checker script;
- Step 9 status report;
- README update.

## Step 9 verdict

After this protocol is committed, the project is ready for Step 10 rewrite generation once the selected original-passage text artifact is confirmed available.
