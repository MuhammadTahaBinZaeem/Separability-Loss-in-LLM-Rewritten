# Step 20 Final Reproducibility Audit and Paper-Readiness Package

## Purpose

Step 20 is the final repository-level audit before manuscript writing.

It checks that the completed pipeline is internally reproducible from the committed artifacts and that the paper's main empirical claims are supported by traceable outputs.

This step does **not** regenerate source data, rewrite data, features, models, or figures. It audits them.

## Inputs

Step 20 depends on the committed outputs from Steps 1-19, especially:

```text
metadata/gutenberg_candidate_generation_summary.csv
metadata/selection_summary.csv
metadata/rewrite_request_summary.csv
metadata/rewrite_qc_report.csv
data/final/master_text_dataset.csv
data/features/stylometric_features.csv
data/modeling/modeling_metadata.csv
metadata/original_author_baseline_metrics.csv
metadata/original_to_rewritten_degradation_summary.csv
metadata/rewritten_condition_author_survival_summary.csv
metadata/inter_author_distance_summary.csv
metadata/feature_family_vulnerability_summary.csv
metadata/statistical_tests_bootstrap_macro_f1_loss.csv
```

## Audit checks

The audit verifies:

1. Required files for Steps 1-19 exist.
2. Existing step checkers pass where checkers are available.
3. Core row counts match the locked design.
4. Main result claims have direct evidence files.
5. All final paper-facing tables and figures exist.
6. A final manifest records hashes and sizes of critical files.

## Outputs

```text
metadata/final_reproducibility_manifest.csv
metadata/final_step_status.csv
metadata/paper_claim_support_matrix.csv
logs/final_reproducibility_audit_report.md
logs/final_paper_readiness_summary.md
```

## Completion criteria

Step 20 is complete only if:

- all required critical files exist;
- all available checkers pass;
- final manifest exists;
- final step-status table exists;
- paper claim-support matrix exists;
- final audit report exists;
- final paper-readiness summary exists;
- Step 20 checker passes.
