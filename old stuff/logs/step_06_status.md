# Step 6 Status Report

## Step

**Step 6 — Passage Extraction Protocol**

## Status

Complete after verification fix.

## Files created or updated

- `docs/passage_extraction_protocol.md`
- `metadata/candidate_passage_schema.csv`
- `metadata/passage_extraction_config.json`
- `scripts/03_extract_candidate_passages.py`
- `docs/data_dictionary.md`
- `logs/step_06_status.md`
- `scripts/check_steps_01_06_consistency.py`

## What Step 6 did

Step 6 defines the formal protocol for extracting candidate passages from cleaned texts. It does not generate the candidate passage pool; candidate generation belongs to Step 7.

The protocol freezes:

- target final corpus size,
- candidate pool size target,
- passage word-count rules,
- source eligibility rules,
- genre exclusion rules,
- non-overlap rule,
- candidate metadata fields,
- candidate status values,
- complete-works/container handling rules,
- deterministic extraction configuration,
- extraction script scaffold.

## Locked target sizes

Final dataset target:

```text
6 authors × 60 passages = 360 original passages
```

Candidate pool target for Step 7:

```text
minimum 6 authors × 120 candidates = 720 candidate passages
```

## Passage length rules

Preferred range:

```text
450–650 words
```

Hard bounds:

```text
400–700 words
```

The extraction script aims for approximately 550 words per candidate passage.

## Non-overlap rule

Candidates from the same source must not overlap.

Minimum gap:

```text
150 words between candidates from the same source
```

## Sentence-boundary rule

The protocol says extraction should avoid mid-sentence cuts where possible. A verification pass found that the first script scaffold used simple word windows. This was corrected.

The committed extraction script now uses sentence-aware windows:

```text
scripts/03_extract_candidate_passages.py
```

The current scaffold accumulates full sentences until the preferred passage length is reached, applies hard word-count bounds, and advances by passage length plus the configured word gap to prevent overlap.

## Source eligibility rule

Allowed source statuses:

- `eligible_main`
- `eligible_backup`
- `eligible_container`
- `eligible_main_or_backup`

Excluded source status:

- `excluded`

## Important limitations carried into Step 7

- Complete-works/container sources still require internal work-boundary handling.
- Twain remains one-work limited unless another Twain source is added.
- Wilde has one usable prose source; the drama source and retelling remain excluded.
- Final passage balance is not done in Step 6; it belongs to Step 8.

## Script added and verified against protocol

The extraction script scaffold is:

```text
scripts/03_extract_candidate_passages.py
```

This script is intended to be run in Step 7 to create:

```text
data/interim/candidate_passages.csv
metadata/candidate_passage_metadata.csv
logs/candidate_generation_report.md
```

## Step 6 completion judgment

Step 6 is complete after the sentence-aware extraction fix. The passage extraction protocol and script scaffold are now specified well enough to proceed to Step 7 candidate passage pool generation.

## Next step

Step 7 should run the extraction script on the cleaned texts, create the candidate pool, generate candidate metadata, and report candidate counts by author/source.
