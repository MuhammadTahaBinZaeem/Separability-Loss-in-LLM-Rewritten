# Audit guide

This guide describes the current public evidence package. Begin at the repository root; earlier material under `old stuff/` is historical context. Check `PUBLIC_FILE_MANIFEST.json` and the corresponding validation records before relying on a result. A file's presence or a documented command is not itself evidence that a particular replay completed successfully.

## Evidence chain

1. **Design and amendments.** Read `revision/expanded_v3/PROTOCOL.md`, `PRIMARY_ANALYSIS_PLAN.md`, `generation_plan.json`, `scope_amendment.json` and `astra_delegation_amendment.json`. The expanded analysis was developed after the earlier study; it is exploratory, not a retrospective preregistration. Amendments and dated generation records preserve changes to scope and workflow.
2. **Source selection.** Join the corrected `corpus/originals.csv` to `lineage.csv`, the earlier corpus freeze, the work register and archived text editions. Each of the eighteen works contributes twenty passages. Of the 360 passages, 356 retain the earlier text and four are replacements. Exact text spans, hashes, length bounds, overlap and fixed work folds are computationally checkable. The withheld source-review returns cannot be independently inspected in this release.
3. **Generation.** Inspect each active arm's request manifest, requests, stored outcomes, rewrite table, completion record and attempt logs. Link records by `request_id`; check source/request/rewrite hashes. Separate the first planned outcome from subsequent attempts and legacy records. A valid parsed output can still carry mechanical QC warnings. Such warnings are not proof of semantic error.
4. **Primary analysis.** Inspect per-fold feature selection/scaling evidence, predictions, coverage, per-work summaries, confusion counts and comparisons. Vocabulary selection and preprocessing must use only training works. Each valid rewrite is paired with its own original. Failed first outcomes remain in availability accounting and are excluded from the valid-output estimand.
5. **Transfer and controls.** Inspect common-cohort membership, view hashes, crop eligibility, training-domain transforms and all transfer cells. Cohorts are common across the three rewrite conditions within each arm; they are not a single common cohort shared by all arms. Retain panels marked not estimable and adverse or near-zero results.
6. **Explanatory geometry.** Inspect training-work mapping parameters, held-out-work predictions, dispersion components and contrasts. These describe the fitted representation; contraction does not by itself establish irreversible destruction of author information.
7. **Exported assets.** Join the fifteen CSV tables and five figures in `research_assets/` back to their recorded analysis files. `build_figures.py` rebuilds the assets from the archived results. References are source metadata, not a copy of the current manuscript.

## Active generation keys

| Key | Recorded arm |
| --- | --- |
| `gem31lite` | Gemini 3.1 Flash-Lite API deployment |
| `azure_replication` | GPT-5.4 Nano API deployment |
| `codex51` | GPT-5.1 Codex API deployment |
| `luna56` | GPT-5.6 Luna API deployment |
| `terra56` | GPT-5.6 Terra API deployment |
| `astra_session` | Recorded GPT-6 Astra-designated session/orchestration workflow |

The designation in the session records is workflow provenance, not independent verification of its underlying model checkpoint. The API arms also describe the deployments and responses actually recorded; they are not claims that all settings or orchestration contexts are equivalent. The superseded `sol56` material, where retained historically, is not a seventh active arm.

## Replay commands and scope

Use Python 3.12.11 with `requirements-v2.lock`, installing with hash verification:

```text
python -m pip install --require-hashes -r requirements-v2.lock
```

Then run from the repository root, choosing a new output directory each time:

```text
python audit_tools/replay.py --mode audit --output audit_runs/quick
python audit_tools/replay.py --mode primary --models all --output audit_runs/primary
python audit_tools/replay.py --mode transfer --models all --output audit_runs/transfer
python audit_tools/replay.py --mode explanatory --models all --output audit_runs/explanatory
```

Replace `all` with one or more active keys to reduce computation. Replay needs no credentials or generated text requests. Do not use a historical live-generation command as a substitute for this offline replay; regeneration entails separate model access and costs and cannot recreate the same stochastic outputs.

| Mode | What it establishes | What it does not establish |
| --- | --- | --- |
| `audit` | Public file integrity, exact source evidence and reconstruction of primary point estimates/Holm adjustment from archived predictions and raw p-values | Classifier refits, fresh bootstrap/swap inference, or reconstruction of withheld reviewer ratings |
| `primary` | Refit of three classifiers, seven feature panels and three held-out-work folds for selected arms; recomputation of 5,000 bootstrap and 9,999 work-swap replicates; comparison with frozen empirical outputs | Independent replication on new authors/works or inclusion of training uncertainty |
| `transfer` | Refit of training-only transforms; cohort/view alignment; reconstruction of scores and paired intervals from archived transfer predictions | Refit of the classifiers that originally produced those transfer predictions |
| `explanatory` | Refit of shift/contraction mappings and comparison of parameters, held-out-work predictions, dispersion, summaries and contrasts | Refit of the parent transfer classifiers or proof of a causal mechanism |

Primary and explanatory replay compare empirical files byte-for-byte; timing metadata is outside that comparison. Transfer verification requires exact hashes, cohort identifiers, vocabulary order and non-IDF transform metadata. Its additive portability verifier allows finite, equally shaped IDF arrays to differ by at most **eight floating-point units in the last place**, using the spacing at `max(1, abs(archived IDF))`. Score and interval tolerance is `1e-12`.

This narrowly documented exception follows an actual failed exact comparison: six of 30,000 original-domain Codex IDF values in full-text fold 2 differed by one ULP, with maximum absolute difference `2.220446049250313e-16`. Vocabulary and the other metadata matched. The portable verifier records affected values and differences. The unchanged historical exact verifier and the failed attempt remain distinguishable from the portable successful route. Archived predictions and empirical results were not replaced to obtain a pass.

Successful runs write receipts in their output directories; failures exit nonzero and may leave diagnostic files. Consult `validation/` for completed release checks and their dates, selected arms, tolerances and output comparisons. Saved receipts can contain local execution paths; these paths describe that run and are not dependencies needed by a new clone.

The scientific unit tests run with `python -m pytest -q tests -k 'not test_pending_manuscript_has_no_invented_results'`. One historical manuscript-builder test is explicitly deselected because its manuscript template is intentionally held locally. The unchanged test file remains available for inspection. The same command is used by the offline GitHub workflow; no live generation workflow is active in the current layout.

## Statistical and evidential limits

- There are 6,480 planned first outcomes, 6,118 valid rewrites and 362 failures. The broader failure index also includes legacy/retry records; its row count is not the primary failure denominator.
- The 54-test family covers six arms, three classifiers and three rewrite conditions. Only three adjusted results are significant, all Gemini/shrinkage-LDA comparisons. Positive point estimates are not synonymous with statistically established effects.
- Primary uncertainty is conditional on fitted classifiers and these six authors. Results do not estimate performance across all literature, authors, model versions or future generations.
- Full-text, length-control, warning-filtered, semantic-filtered and transfer cohorts have different denominators. Compare the coverage files before comparing numbers.
- Some semantic and source review evidence is withheld. Aggregate tables preserve reported results but do not provide a complete public reconstruction of participant-level decisions.
- Mechanical hashes and numerical replay cannot prove participant identity, independence, absence of assistance, informed consent or institutional ethics approval. No such certification is supplied by this repository.

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for record joins and [ACCESS_AND_EXCLUSIONS.md](ACCESS_AND_EXCLUSIONS.md) for publication boundaries.
