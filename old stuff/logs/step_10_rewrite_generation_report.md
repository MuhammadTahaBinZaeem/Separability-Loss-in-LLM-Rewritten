# Step 10 Rewrite Generation Report

- backend: google_gemini
- model: `gemini-3.1-flash-lite`
- total parsed rows: 1080
- total raw rows: 1080
- batch_A rows: 360
- batch_B rows: 360
- batch_C rows: 360
- disjoint request IDs across batches: True
- empty outputs: 0
- JSON parse failed: 1
- prompt/source leakage: 0
- hard length warnings: 44
- started UTC: 2026-05-29T10:25:03.252545+00:00
- finished UTC: 2026-05-29T12:18:37.250697+00:00

## QC Counts

- pass: 969
- warning: 111
- fail: 0

| batch | rows | pass | warning | fail | length warnings | hard length warnings | leakage | empty | JSON parse failed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| batch_A | 360 | 340 | 20 | 0 | 20 | 6 | 0 | 0 | 1 |
| batch_B | 360 | 299 | 61 | 0 | 61 | 30 | 0 | 0 | 0 |
| batch_C | 360 | 330 | 30 | 0 | 30 | 8 | 0 | 0 | 0 |

## Outputs

- per-batch responses: `data/interim/gemini_full`
- merged raw responses: `data/interim/rewrite_responses_raw.jsonl`
- merged parsed responses: `data/interim/rewrite_responses_parsed.csv`
- run manifest: `metadata/rewrite_run_manifest.csv`
- QC report: `metadata/rewrite_qc_report.csv`
- QC summary: `logs/rewrite_qc_summary.md`
- ZIP artifact: `artifacts/step10/gemini_full_rewrite_outputs.zip`
