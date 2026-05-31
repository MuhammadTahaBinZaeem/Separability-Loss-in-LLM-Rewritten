# Multi-LLM Replication Protocol

## Status

Design locked; data not yet collected.

## Purpose

The original empirical core uses one rewriting model. This replication tests whether the observed authorial-style separability loss is specific to that model or appears across multiple contemporary LLM rewriting systems.

## Models

The planned replication models are:

| model_id | Provider label | Role in design |
|---|---|---|
| `gpt_4o` | GPT-4o | OpenAI replication model |
| `gemini_1_5_pro` | Gemini 1.5 Pro | Google higher-capacity replication model |
| `claude_sonnet_3_5` | Claude Sonnet 3.5 | Anthropic replication model |

The existing Gemini 3.1 Flash Lite outputs remain the original core condition, not the replication baseline.

## Source passages

Use the frozen 360 selected original passages already present in the repository. Do not reselect passages.

## Rewrite conditions

For every model, generate all three rewrite conditions:

- `paraphrase`
- `modernize`
- `simplify`

Total target requests per model:

```text
360 passages × 3 conditions = 1080 rewrite requests
```

Total target requests across the three replication models:

```text
1080 × 3 = 3240 rewrite requests
```

If a model lacks deterministic seeding, perform three complete runs for that model:

```text
1080 requests × 3 runs = 3240 requests/model
```

## Prompting rules

Use the same blinded prompts and condition definitions as the frozen Step 9 protocol.

The prompt must not reveal:

- author name;
- work title;
- Gutenberg ID;
- feature statistics;
- experimental purpose;
- expected direction of results.

## Generation settings

| Setting | Value |
|---|---|
| temperature | `0.2` |
| top_p | `1.0` |
| presence penalty | `0` where supported |
| frequency penalty | `0` where supported |
| seed | logged where supported |

If a provider does not support one of these settings, record `unsupported` in the run manifest.

## Required output schema

Each rewrite output must be normalised into:

| Column | Meaning |
|---|---|
| `replication_model_id` | One of the locked model IDs |
| `provider_model_name` | Exact provider-facing model name used at call time |
| `provider_model_version` | Version/snapshot if available |
| `run_id` | `run_1`, `run_2`, or `run_3` |
| `passage_id` | Frozen selected passage ID |
| `condition` | Rewrite condition |
| `rewritten_text` | Clean rewritten prose text |
| `temperature` | Requested temperature |
| `top_p` | Requested top_p |
| `seed_requested` | Requested seed, if supported |
| `seed_effective` | Effective seed returned by provider, if available |
| `prompt_template_sha256` | Hash of prompt template |
| `source_text_sha256` | Hash of source passage |
| `rewritten_text_sha256` | Hash of rewrite |
| `created_utc` | Generation timestamp |
| `qc_status` | `pass`, `warning`, or `fail` |
| `qc_flags` | Semicolon-separated warning/fail flags |

## Planned repository outputs

```text
data/interim/multillm_rewrite_requests/
data/interim/multillm_rewrite_outputs/
metadata/multillm_model_registry.csv
metadata/multillm_run_manifest.csv
metadata/multillm_rewrite_qc_summary.csv
metadata/multillm_replication_summary.csv
logs/multillm_replication_report.md
```

## Analysis plan

For each replication model and condition:

1. build a master text dataset using the same selected original passage IDs;
2. extract the same stylometric feature set;
3. run the same original-to-rewritten transfer analysis;
4. run same-condition rewritten classification;
5. run inter-author distance contraction analysis;
6. compare macro-F1 losses and distance contraction against the original Gemini-core result;
7. for multi-run models, report mean, standard deviation, minimum, and maximum of each key metric.

## Manuscript claim allowed only after completion

Do not claim that the result generalises across LLMs until this experiment is complete. Before completion, the manuscript must say the original result is model-specific.