# Step 9 Controlled Rewriting Prompt Protocol Status

## Status

Complete.

## What Step 9 did

Step 9 defined the controlled rewriting protocol for the three experimental rewrite conditions:

- `paraphrase`
- `modernize`
- `simplify`

This step does not generate rewrites. It freezes the protocol required before rewrite generation.

## Files added

- `docs/rewrite_protocol.md`
- `metadata/rewrite_condition_registry.csv`
- `metadata/rewrite_generation_config.json`
- `metadata/rewrite_output_schema.csv`
- `prompts/rewrite_system_prompt.txt`
- `prompts/rewrite_paraphrase_prompt.txt`
- `prompts/rewrite_modernize_prompt.txt`
- `prompts/rewrite_simplify_prompt.txt`
- `scripts/08_prepare_rewrite_requests.py`
- `scripts/09_validate_rewrite_outputs.py`
- `logs/step_09_status.md`

## Locked conditions

| Condition | Severity | Purpose |
|---|---:|---|
| paraphrase | light | Change wording while preserving meaning and structure. |
| modernize | medium | Update older phrasing into contemporary English. |
| simplify | heavy | Make the passage easier to read without summarizing. |

## Prompt blinding

The rewriting prompts deliberately avoid revealing:

- author name;
- work title;
- Gutenberg ID;
- experimental purpose;
- feature statistics.

Reason: the rewriting model should not intentionally imitate or suppress known authorial style.

## Output format

The rewrite model must output JSON with exactly:

```json
{
  "passage_id": "...",
  "condition": "...",
  "rewritten_text": "..."
}
```

## Expected Step 10 request count

```text
360 selected passages × 3 rewrite conditions = 1080 rewrite requests
```

## Expected final text dataset after rewriting

```text
360 original + 1080 rewritten = 1440 total text rows
```

## Step 9 completion judgment

Step 9 is complete. The project is ready for Step 10 rewrite-request preparation and generation, provided Step 8 selected passage text is available in the working tree.
