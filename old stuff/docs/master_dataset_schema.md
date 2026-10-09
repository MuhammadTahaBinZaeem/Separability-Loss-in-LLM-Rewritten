# Step 11 Master Text Dataset Schema

## Purpose

Step 11 builds the canonical master text dataset used by all later feature extraction, modeling, distance analysis, statistical testing, and paper-facing tables.

The master dataset combines:

- the 360 selected original passages from Step 8;
- the 1080 controlled rewrite outputs from Step 10;
- provenance, condition, author, work, QC, parse, and checksum metadata.

## Main output

```text
data/final/master_text_dataset.csv
```

Expected row count:

```text
1440
```

Expected condition balance:

```text
original: 360
paraphrase: 360
modernize: 360
simplify: 360
```

## Required identifier and provenance columns

```text
text_id
passage_id
condition
text_group
author_id
author_name
work_id
work_title
original_word_count
text_word_count
text_sha256
source_text_sha256
qc_status
qc_flags
parse_status
text
```

## Condition rules

For original rows:

```text
condition = original
text_group = original
parse_status = not_applicable
```

For rewrite rows:

```text
condition in {paraphrase, modernize, simplify}
text_group = rewrite
rewrite_request_id = text_id
parse_status in {json_ok, json_parse_failed_used_raw_content}
```

## Balance rules

The final master dataset must contain:

```text
6 authors
12 works
360 unique passage IDs
4 condition rows per passage
60 rows per author per condition
30 rows per work per condition
```

## QC rules

No row may have:

```text
qc_status = fail
empty text
invalid text_sha256
```

Warnings are allowed only when preserved and documented from rewrite QC.

## Required Step 11 side outputs

```text
metadata/master_text_dataset_summary.csv
metadata/master_text_counts_by_condition.csv
metadata/master_text_counts_by_author_condition.csv
metadata/master_text_dataset_manifest.csv
logs/step_11_master_dataset_report.md
```

## Completion criteria

Step 11 is complete only if:

- master dataset has exactly 1440 rows;
- every text_id is unique;
- every passage_id has all four conditions;
- all condition, author, and work counts match the locked design;
- text hashes match stored text;
- no QC fail rows exist;
- the JSON fallback count is documented;
- manifest paths, sizes, and SHA256 values match committed files;
- the Step 11 checker passes.
