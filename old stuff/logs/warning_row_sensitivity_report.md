# E3 Warning-Row Sensitivity Analysis Report

## Status

Complete when generated locally and checker passes.

## Subsets

- `all_rows`: All original and rewrite rows, including QC warning rows.
- `qc_pass_only`: Original rows plus rewrite rows with qc_status == pass.
- `pass_plus_non_hard_length_warning`: Original rows plus pass rows and warning rows that do not contain length_hard_warning.

## Output row counts

- transfer predictions: 3759
- transfer summary rows: 72
- same-condition summary rows: 72
- distance summary rows: 24
- feature-family summary rows: 432
- bootstrap rows: 54

## Nearest-centroid test transfer summary

- all_rows / original: macro_f1=0.776931, loss=0.0, rows=54
- all_rows / paraphrase: macro_f1=0.395797, loss=0.381134, rows=54
- all_rows / modernize: macro_f1=0.56072, loss=0.216211, rows=54
- all_rows / simplify: macro_f1=0.463636, loss=0.313295, rows=54
- qc_pass_only / original: macro_f1=0.776931, loss=0.0, rows=54
- qc_pass_only / paraphrase: macro_f1=0.398258, loss=0.378673, rows=47
- qc_pass_only / modernize: macro_f1=0.548754, loss=0.228177, rows=53
- qc_pass_only / simplify: macro_f1=0.468781, loss=0.30815, rows=51
- pass_plus_non_hard_length_warning / original: macro_f1=0.776931, loss=0.0, rows=54
- pass_plus_non_hard_length_warning / paraphrase: macro_f1=0.377314, loss=0.399617, rows=50
- pass_plus_non_hard_length_warning / modernize: macro_f1=0.56072, loss=0.216211, rows=54
- pass_plus_non_hard_length_warning / simplify: macro_f1=0.47518, loss=0.301751, rows=53
