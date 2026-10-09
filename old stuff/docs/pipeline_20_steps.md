# 20-Step Research Dataset Pipeline

This repository follows a strict 20-step process. Each step must leave durable files in the repository so that the final paper can trace every result back to source data and processing choices.

## Step 1 — Repository Audit and Project Skeleton

Establish repository structure, inventory current source state, document limitations, and prepare reproducibility files.

**Primary outputs:**

- `docs/repo_audit.md`
- `metadata/source_inventory.csv`
- `metadata/text_extraction_manifest.csv`
- `docs/raw_source_handling.md`
- `docs/pipeline_20_steps.md`
- directory skeleton

## Step 2 — Corpus Inventory and Author-Work Map

Convert the raw source inventory into a formal author/work table. Decide which works are eligible for the main corpus and which are excluded.

**Primary outputs:**

- `metadata/author_work_map.csv`
- `docs/corpus_selection_rationale.md`

## Step 3 — Raw Text Preservation and Checksum Logging

Freeze raw files and extracted text states through checksums, byte counts, and line/word counts.

**Primary outputs:**

- `metadata/raw_file_checksums.csv`
- `metadata/extracted_text_checksums.csv`
- `logs/raw_preservation_log.md`

## Step 4 — Text Cleaning Rules and Metadata Removal

Write and apply deterministic cleaning rules for removing non-literary metadata while preserving stylistic features.

**Primary outputs:**

- `scripts/01_clean_texts.py`
- `docs/cleaning_rules.md`
- `data/interim/cleaned_books/`
- `logs/cleaning_report.csv`

## Step 5 — Author-Specific Cleaning Validation

Validate that cleaning preserved punctuation, rhythm, dialogue, archaic spelling, and author-specific stylistic material.

**Primary outputs:**

- `logs/cleaning_validation_report.md`
- `metadata/cleaned_file_checksums.csv`

## Step 6 — Passage Extraction Protocol

Define exact passage selection rules before extracting final passages.

**Primary outputs:**

- `docs/passage_extraction_protocol.md`
- `scripts/02_extract_passages.py`

## Step 7 — Candidate Passage Pool

Generate more passages than needed, with metadata for balancing and quality filtering.

**Primary outputs:**

- `data/interim/candidate_passages.csv`
- `metadata/candidate_passage_metadata.csv`

## Step 8 — Final Passage Selection and Balance Check

Select the final 360 original passages and document balance across author, work, length, dialogue ratio, and section spread.

**Primary outputs:**

- `data/processed/original_passages.csv`
- `metadata/final_passage_metadata.csv`
- `logs/passage_balance_report.md`

## Step 9 — Baseline Stylometric Separability Check

Verify that the original authors are distinguishable before LLM rewriting.

**Primary outputs:**

- `results/tables/baseline_author_separability.csv`
- `results/figures/baseline_author_clusters.png`
- `logs/baseline_separability_report.md`

## Step 10 — Prompt Template Finalization

Freeze exact paraphrase, modernization, and simplification prompts.

**Primary outputs:**

- `metadata/rewrite_prompts.json`
- `docs/prompting_protocol.md`

## Step 11 — LLM Rewriting Batch 1: Paraphrase

Generate paraphrased versions of all selected passages and log all generation metadata.

**Primary outputs:**

- `data/interim/rewrites/paraphrase_raw.csv`
- `data/processed/rewrites/paraphrase_clean.csv`
- `logs/paraphrase_generation_log.csv`

## Step 12 — LLM Rewriting Batch 2: Modernize

Generate modernized versions of all selected passages and log all generation metadata.

**Primary outputs:**

- `data/interim/rewrites/modernize_raw.csv`
- `data/processed/rewrites/modernize_clean.csv`
- `logs/modernize_generation_log.csv`

## Step 13 — LLM Rewriting Batch 3: Simplify

Generate simplified versions of all selected passages and log all generation metadata.

**Primary outputs:**

- `data/interim/rewrites/simplify_raw.csv`
- `data/processed/rewrites/simplify_clean.csv`
- `logs/simplify_generation_log.csv`

## Step 14 — Rewrite Quality and Constraint Validation

Validate length, prose-only output, absence of model commentary, absence of accidental summarization, and output completeness.

**Primary outputs:**

- `logs/rewrite_quality_report.md`
- `metadata/rewrite_validation_flags.csv`
- `data/final/master_text_dataset.csv`

## Step 15 — Feature Extraction: Classical Stylometry

Extract all stylometric feature families.

**Primary outputs:**

- `scripts/03_extract_features.py`
- `data/processed/features/function_words.csv`
- `data/processed/features/sentence_lengths.csv`
- `data/processed/features/pos_distributions.csv`
- `data/processed/features/punctuation.csv`
- `data/processed/features/lexical_diversity.csv`
- `data/processed/features/burrows_delta_vectors.csv`
- `metadata/feature_dictionary.csv`

## Step 16 — Separability Metrics and ASSL Computation

Compute Authorial Style Separability Loss using classification, distance, and clustering-based separability scores.

**Primary outputs:**

- `scripts/04_compute_assl.py`
- `results/tables/assl_by_task.csv`
- `results/tables/assl_by_feature_family.csv`
- `results/tables/inter_author_distances.csv`
- `docs/assl_metric_definition.md`

## Step 17 — Classification Experiments

Run original-to-rewritten transfer and rewritten-to-rewritten internal separability tests.

**Primary outputs:**

- `scripts/05_classification_experiments.py`
- `results/tables/classification_original_to_rewritten.csv`
- `results/tables/classification_rewritten_internal.csv`
- `results/tables/confusion_matrices/`
- `logs/classification_report.md`

## Step 18 — Statistical Testing and Robustness Checks

Use confidence intervals, paired tests, permutation tests, and robustness checks.

**Primary outputs:**

- `scripts/06_statistical_tests.py`
- `results/tables/statistical_tests.csv`
- `results/tables/bootstrap_confidence_intervals.csv`
- `results/tables/robustness_checks.csv`
- `logs/statistical_validation_report.md`

## Step 19 — Figure and Table Generation

Generate paper-ready tables and figures.

**Primary outputs:**

- `scripts/07_generate_figures.py`
- `results/figures/`
- `results/tables/`
- `docs/figure_table_inventory.md`

## Step 20 — Final Reproducibility Package and Dataset Freeze

Freeze final datasets, scripts, schemas, outputs, and paper-method notes.

**Primary outputs:**

- `data/final/master_text_dataset.csv`
- `data/final/master_feature_dataset.csv`
- `data/final/master_results_dataset.csv`
- `metadata/final_dataset_schema.json`
- `docs/data_dictionary.md`
- `docs/reproducibility.md`
- `docs/final_protocol.md`
- `docs/paper_methods_draft.md`
- `REPRODUCIBILITY_LOCK.md`

## Rule

No step is considered complete unless it leaves clear repository artifacts and an audit trail.
