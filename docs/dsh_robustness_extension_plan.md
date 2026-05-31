# DSH Robustness Extension Plan

## Purpose

This document tracks the post-freeze robustness extension for the `litpaper` project. The original 20-step empirical core remains frozen unless a factual or reproducibility-breaking issue is found. The extension exists to improve the odds of a serious submission to **Digital Scholarship in the Humanities** by directly addressing likely reviewer objections.

The extension is not a new paper direction. It strengthens the same core claim:

> Controlled LLM rewriting contracts measurable authorial style separability in a balanced public-domain fiction corpus, while leaving residual author-specific structure under same-condition analysis.

## Reviewer objections targeted

| Objection | Extension answer |
|---|---|
| The result may be a single-model Gemini effect. | Add multi-LLM replication across GPT-4o, Gemini 1.5 Pro, and Claude Sonnet 3.5, with repeated runs where deterministic seeding is unavailable. |
| The model may be measuring work/topic rather than author. | Add leave-one-work-out validation because each author contributes two works. |
| QC warning rows may drive the result. | **Completed E3:** Step 15-19-style metrics were recomputed on all rows, QC-pass-only rows, and rows excluding hard length warnings. The central transfer-loss and distance-contraction directions remained stable. |
| The rewrite protocol promises semantic fidelity but does not prove it. | Add a human semantic-fidelity annotation audit on a 10% sample of rewrites. |
| The paper lacks humanities-facing reader evidence. | Add a human reading study measuring readability, perceived style distinctiveness, AI/human judgement, and same-author similarity. |
| Prompt blinding is asserted but not empirically justified. | Add a smaller author-revealed prompt ablation. |
| Passage length may partly explain degradation. | Add length-band robustness analysis. |
| Feature-family results show vulnerability but not full-system dependence. | Add leave-one-feature-family-out ablation. |

## Experiment registry

| ID | Priority | Experiment | Current status | Can run from current repo only? | Main outputs |
|---|---|---|---|---|---|
| E1 | Essential | Multi-LLM replication | Protocol locked; data not collected | No | `docs/multillm_replication_protocol.md`, planned `data/interim/multillm_rewrite_requests/`, `data/interim/multillm_rewrite_outputs/`, `metadata/multillm_run_manifest.csv`, `metadata/multillm_replication_summary.csv` |
| E2 | Essential | Held-out-work validation | Ready to implement from existing features and metadata | Yes | `metadata/heldout_work_validation_summary.csv`, `data/results/heldout_work_validation_predictions.csv`, `logs/heldout_work_validation_report.md` |
| E3 | Essential | Warning-row sensitivity analysis | **Complete: outputs generated and committed** | Yes | `docs/warning_row_sensitivity_protocol.md`, `scripts/22_run_warning_row_sensitivity.py`, `scripts/check_e3_warning_row_sensitivity.py`, `data/results/warning_row_sensitivity_transfer_predictions.csv`, `metadata/warning_row_sensitivity_transfer_summary.csv`, `metadata/warning_row_sensitivity_same_condition_summary.csv`, `metadata/warning_row_sensitivity_distance_summary.csv`, `metadata/warning_row_sensitivity_feature_family_summary.csv`, `metadata/warning_row_sensitivity_bootstrap_macro_f1_loss.csv`, `metadata/warning_row_sensitivity_subset_counts.csv`, `metadata/warning_row_sensitivity_manifest.csv`, `logs/warning_row_sensitivity_report.md` |
| E4 | Essential | Semantic fidelity audit | Protocol locked; human annotation not collected | Partly | `docs/semantic_fidelity_audit_protocol.md`, planned `metadata/semantic_fidelity_sample.csv`, `metadata/semantic_fidelity_codebook.csv`, `metadata/semantic_fidelity_annotation_results.csv` |
| E5 | Strongly recommended | Human reading study | Protocol locked; participant data not collected | No | `docs/human_reading_study_protocol.md`, planned `metadata/human_reading_study_design.csv`, `metadata/human_reading_study_results.csv` |
| E6 | Strongly recommended | Prompt/protocol ablation | Protocol and smaller rewrite batch needed | Partly | `metadata/prompt_ablation_sample.csv`, `metadata/prompt_ablation_summary.csv` |
| E7 | Strongly recommended | Length-band robustness | Ready to implement from existing features and metadata | Yes | `metadata/length_band_robustness_summary.csv`, `logs/length_band_robustness_report.md` |
| E8 | Nice but valuable | Leave-one-feature-family-out ablation | Ready to implement from existing features and metadata | Yes | `metadata/leave_one_feature_family_out_summary.csv`, `logs/leave_one_feature_family_out_report.md` |

## E3 completion summary

E3 generated and committed the warning-row sensitivity package in commit `34c07109bcb01417b0ffdb0063c7126d55632908`.

Main result:

- nearest-centroid test macro-F1 loss stays positive for paraphrase, modernize, and simplify under all three subsets;
- paired-passage bootstrap intervals for nearest-centroid test losses stay positive under all three subsets;
- all-feature and function-word inter-author distance ratios remain below 1.0 for all rewrite conditions under all three subsets;
- QC-pass-only filtering reduces rows but keeps all six authors represented in every condition.

## Execution order

1. **E3 warning-row sensitivity is complete.** Use it as the first reviewer-facing robustness result.
2. **Next run E2 held-out-work validation.** This is now the most important methodological upgrade because it attacks the work/topic confound.
3. **Then run E7 and E8.** These are robustness additions that make the results section harder to dismiss.
4. **Prepare E1 request files.** Do not run model calls until provider access, cost limits, and model version logging are settled.
5. **Prepare E4/E5 human-study materials.** Do not present them as completed until annotations/participants are actually collected.
6. **Run E6 only after E1/E2/E3 are stable.** It is useful, but less central than multi-model replication and held-out-work validation.

## Status rule

No extension experiment may be marked complete unless it leaves:

1. a protocol or design note;
2. machine-readable output files;
3. a manifest or summary CSV;
4. a human-readable log report;
5. a checker script or audit note where practical.

## Manuscript use

These experiments should be framed in the eventual manuscript as reviewer-facing robustness evidence, not as a second main contribution. The paper should still remain focused on controlled rewriting and the measurability of literary authorial style.

E3 can now be cited in the manuscript as evidence that retained QC warning rows do not drive the main separability-loss result.