# E1 Low-Budget Multi-Model Workflow

## Purpose

E1 tests whether the rewrite-associated style-separability loss is specific to the original Gemini Flash core dataset or appears across additional model families.

This workflow keeps E1 data separate from the frozen core dataset.

## Important boundary

Use only authorised API keys, collaborator keys, institutional access, free credits, student credits, or locally available models that you are allowed to use. Do not automate fake accounts, unauthorised account cycling, quota abuse, or billing evasion.

## Combined manager script

Use the single combined batch manager:

```bash
python scripts/26_e1_multillm_batch_manager.py prepare --chunk-size 100
python scripts/26_e1_multillm_batch_manager.py import
python scripts/26_e1_multillm_batch_manager.py status
```

The script does three jobs:

1. prepares all blinded rewrite requests;
2. splits them into manageable request batches;
3. imports and QC-checks provider responses after generation.

It does not call provider APIs directly.

## Separation from old data

E1 artifacts are stored under:

```text
data/interim/e1_multillm_replication/
metadata/e1_multillm_*
logs/e1_multillm_batch_manager_report.md
```

The original core Gemini Flash files remain untouched.

## Request preparation

Run:

```bash
python scripts/26_e1_multillm_batch_manager.py prepare --chunk-size 100
```

Main outputs:

```text
data/interim/e1_multillm_replication/requests/e1_rewrite_requests_all.jsonl
data/interim/e1_multillm_replication/request_batches/*.jsonl
metadata/e1_multillm_model_registry.csv
metadata/e1_multillm_batch_manifest.csv
logs/e1_multillm_batch_manager_report.md
```

Each request contains:

- request ID;
- provider/model label;
- run ID;
- passage ID;
- condition;
- system prompt;
- user prompt;
- source hash;
- output schema note.

## Incoming response format

After generating responses through authorised provider access, place JSONL files in:

```text
data/interim/e1_multillm_replication/incoming_raw_provider_responses/
```

Each JSONL line should contain at least:

```json
{
  "request_id": "...",
  "response_text": "{\"passage_id\": \"...\", \"condition\": \"paraphrase\", \"rewritten_text\": \"...\"}"
}
```

Optional fields:

```json
{
  "provider_model_version": "...",
  "seed_requested": "...",
  "seed_effective": "...",
  "created_utc": "..."
}
```

## Import and QC

Run:

```bash
python scripts/26_e1_multillm_batch_manager.py import
```

Main outputs:

```text
data/interim/e1_multillm_replication/parsed_outputs/e1_multillm_rewrite_outputs_parsed.csv
metadata/e1_multillm_import_manifest.csv
metadata/e1_multillm_qc_summary.csv
logs/e1_multillm_batch_manager_report.md
```

The importer checks:

- JSON parse status;
- passage ID match;
- condition match;
- empty output;
- prompt/source leakage;
- markdown/list formatting;
- length ratio;
- soft/hard length warnings.

## Status

Run:

```bash
python scripts/26_e1_multillm_batch_manager.py status
```

This prints planned request count and imported response counts by model.

## Low-budget execution strategy

Do not try to run everything at once. Use small batches:

1. Run `prepare` once.
2. Start with one provider and one small batch.
3. Import and QC that batch.
4. Fix any prompt/format issue before generating more.
5. Continue batch-by-batch.
6. Keep every provider's outputs separate through the request ID and model ID.

## Manuscript rule

Do not claim multi-LLM generalisation until enough completed E1 rows exist and downstream feature extraction/modeling has been run on the imported E1 outputs.

Until then, the manuscript must still describe the original core result as model-specific.