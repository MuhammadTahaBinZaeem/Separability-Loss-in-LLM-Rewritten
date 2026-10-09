# Public data dictionary

Paths below are relative to the repository root unless a shorter path is explicitly named. Read CSV with a CSV parser: passage and rewrite fields contain commas, quotations and embedded newlines. JSONL contains one JSON object per line; line counts are useful for logs but not for multiline CSV records. Hashes are SHA-256 unless a field states otherwise.

## Identifiers and joins

| Field | Meaning and use |
| --- | --- |
| `passage_id` | Stable source-passage identifier. Its historical `V2_` prefix does not imply that a corrected passage still uses its earlier text; check lineage and hashes. |
| `author_id`, `work_id` | Fixed author label and literary work identifier. Works are the held-out groups. |
| `outer_fold` / `fold` | Assigned held-out-work fold, numbered 0–2. These are deterministic study groups, not independently sampled replications. |
| `condition` / domain | `original`, `paraphrase`, `modernize` or `simplify`, as appropriate to the table. |
| `model_key` | Stable arm key. Join it with `passage_id` and `condition` when comparing arms/outcomes. |
| `request_id` | Planned rewrite request identifier linking request, attempt and outcome evidence. Multiple attempts can share a request identifier; do not count them as separate planned observations. |
| `request_sha256` | Digest of the serialized request recorded by the generation code. |
| `source_sha256`, `text_sha256`, `rewrite_sha256`, `view_sha256` | Digests of the corresponding source, rewritten text or analysis view, under the frozen code's encoding/normalization rules. |
| `panel`, `pipeline`, `feature_set`, `classifier` | Analysis specification. Preserve these fields in joins; a passage may occur in many analyses. |

## Corpus

`revision/expanded_v3/corpus/originals.csv` has 360 rows. Its fields include `passage_id`, `outer_fold`, `author_id`, `work_id`, `work_title`, `gutenberg_id`, `source_start_char`, `source_end_char`, `word_count`, `text_sha256` and `text`. Source span boundaries refer to the archived edition and the frozen text-processing rules. They are not page numbers.

`lineage.csv` links each current passage with its earlier identifier/hash and records `disposition` and `reason`. It identifies 356 exact retained passages and four replacements. `freeze.json` records the corpus freeze. `audit_tools/work_registry_current.csv` lists the eighteen works/editions actually selected; `work_specs.json` preserves the frozen work-selection specification. Archived editions under `revision/sources/` retain their own notices.

## Generation and failure evidence

For each active arm under `revision/expanded_v3/generation/`:

- `requests.jsonl` and `request_manifest.json`: recorded prompts, options, source links and request hashes.
- `outcomes.jsonl`: stored outcome records, including response/error evidence and parsed type. An outcome need not contain usable prose.
- `rewrites.csv`: all 1,080 first-outcome records per arm, including failed rows, with source/rewrite hashes, requested/returned model fields, receipt time, finish reason, word counts, `length_ratio`, `qc_status`, `qc_flags`, outcome type and delivery information where applicable.
- `attempts.jsonl` / `all_native_attempts.csv`: attempt-level history, where present. Their granularity differs from the planned request denominator.
- `failed_visible_outputs.jsonl`: any visible failed output text retained by the frozen runner, where present. A refusal or HTTP failure can contain no rewrite text.
- `completion.json`: completion/coverage accounting. It should be read alongside attempt and outcome evidence rather than used as a substitute for it.

Mechanical QC warnings and semantic-review flags are different variables. A warning-free rewrite was not necessarily reviewed; a warning does not itself establish altered meaning. Failed first outcomes are excluded from valid-output comparisons but retained in availability accounting. The failure tables distinguish the 362 failed planned first outcomes from retries and older records.

## Primary analysis

Under `revision/expanded_v3/primary_analysis/<model_key>/`:

| File | Main contents |
| --- | --- |
| `folds/` | Per-training-fold feature and preprocessing evidence |
| `predictions.csv` | Model/classifier/feature-set/fold/passage/condition predictions and source labels |
| `outcome_coverage.csv` | Availability and cohort denominators |
| `metrics.csv`, `per_work.csv`, `confusions.csv` | Performance summaries, work-level results and confusion counts |
| `distances.csv` | Descriptive paired centroid-distance summaries |
| `primary_comparisons.csv` | Paired original/rewrite macro-F1, loss, CI, raw whole-work-swap p-value, resampling counts, seed and inference scope |
| `warning_sensitivity.csv` | Mechanically warning-filtered comparisons and non-estimable panels |
| `manifest.json`, replay/verification receipts | Input/output integrity and completed check records |

`macro_f1_loss` is original macro-F1 minus rewrite macro-F1 for the same paired cohort. Confidence bounds describe the saved conditional resampling procedure. The 54-test shared Holm adjustment is provided in the consolidated exported primary table; raw p-values in per-arm comparisons are not already adjusted. `status` and `missing_works` control whether a row is estimable. Empty or missing numeric values must not be interpreted as zero.

## Transfer and explanatory geometry

`revision/expanded_v3/extensions/jql_v1/<model_key>/` contains:

- `eligibility.csv`, `cohort_counts.csv`, `panel_status.json` and `views.csv`: coverage, exact views and length-panel eligibility.
- `transforms/`: saved training-domain preprocessing/vocabulary evidence.
- `predictions.csv`: `panel`, `pipeline`, `train_domain`, `test_domain`, `fold`, passage/work/author identifiers, prediction and view hash.
- `metrics.csv` and `contrasts.csv`: all transfer cells and derived differences/conditional intervals.
- `feature_changes.csv` and `geometry.csv`: descriptive feature and representation summaries.
- `explanatory_model/`: mapping parameters, held-out-work predictions, dispersion components, summaries and contrasts.

Within an arm, the full transfer cohort retains sources with valid outputs for all three instructions. Cropped panels can have smaller eligible cohorts. A train/test domain pair is an ordered pair; `original → paraphrase` and `paraphrase → original` answer different questions. Repeated cells and mapping contrasts are dependent analyses, not independent studies.

## Exported assets and withheld records

`research_assets/tables/` contains fifteen CSV exports; `facts.json` and `figure_manifest.json` record the builder's selected values and figure outputs. Keep these linked to the underlying frozen results rather than treating them as a second independent dataset. Semantic-review exports are aggregate summaries only: the 3,240 individual ratings, detailed risk decisions, adjudication/source-review returns and identifying records are not in this public tree. Their reconstruction requires separately authorized access.
