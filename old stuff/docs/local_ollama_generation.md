# Step 10 Local Ollama Rewrite Generation Guide

## Purpose

This guide explains how to generate the 1080 controlled rewrite outputs locally with Ollama instead of using a paid API.

This is the recommended route when API credits are unavailable.

## Hardware target

Target machine:

- NVIDIA RTX 3060 Mobile
- Intel i7 10th generation
- 16 GB RAM

This hardware is suitable for 7B/8B-class quantized instruction models. It is not suitable for reliable 14B/32B generation unless heavily quantized and slow.

## Recommended model order

Try models in this order:

1. `qwen2.5:7b-instruct`
2. `llama3.1:8b-instruct`
3. `mistral:7b-instruct`
4. `gemma2:9b-instruct`

For the main paper dataset, use one model only.

Do not mix models across conditions unless the paper explicitly becomes a model-comparison study.

## Install and test Ollama

Install Ollama from the official website, then pull a model:

```bash
ollama pull qwen2.5:7b-instruct
```

Test that the local server responds:

```bash
curl http://localhost:11434/api/tags
```

Run a short prompt:

```bash
ollama run qwen2.5:7b-instruct
```

## Generate rewrites

From the repository root:

```bash
python scripts/10_run_rewrite_generation_ollama.py --model qwen2.5:7b-instruct
```

The script reads:

```text
data/interim/rewrite_requests.jsonl
```

and writes:

```text
data/interim/rewrite_responses_raw.jsonl
data/interim/rewrite_responses_parsed.csv
metadata/rewrite_run_manifest.csv
logs/step_10_rewrite_generation_report.md
```

## Resume behavior

The script is resumable.

If generation stops midway, rerun the same command. Already completed `request_id` values will be skipped.

## Speed expectation

A full run may take many hours on RTX 3060 Mobile hardware. This is normal.

Use a small test first:

```bash
python scripts/10_run_rewrite_generation_ollama.py --model qwen2.5:7b-instruct --limit 6
```

Then run QC:

```bash
python scripts/09_validate_rewrite_outputs.py
```

If the test works, run the full generation.

## Important reproducibility rule

Record the exact model name and keep the generated run manifest.

The paper should report:

- backend: Ollama local API;
- model name;
- model details from `ollama show` if available;
- prompt template hashes;
- request hashes;
- output hashes;
- QC results.

## Completion criteria

Step 10 generation is complete when these files exist and QC passes:

```text
data/interim/rewrite_responses_raw.jsonl
data/interim/rewrite_responses_parsed.csv
metadata/rewrite_run_manifest.csv
metadata/rewrite_qc_report.csv
logs/step_10_rewrite_generation_report.md
logs/rewrite_qc_summary.md
```
