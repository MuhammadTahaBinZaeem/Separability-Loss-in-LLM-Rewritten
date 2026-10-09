# Separability Loss: research data and computational audit

This repository contains the recorded source passages, controlled rewrites, generation evidence, scientific code, result tables and computational checks for a study of author attribution after language-model rewriting. The current manuscript and its Word/PDF files are held locally and are not included here.

The current study uses **360 passages from six authors and eighteen works**, three rewrite instructions and six generation arms. There are **6,480 planned first outcomes: 6,118 valid rewrites and 362 failures**. Validity, mechanical warnings, failed attempts and sample coverage are retained separately. The primary analysis uses three held-out-work folds, training-only feature selection/scaling and a shared family of 54 tests.

## Start here

- [Audit guide](audit/README.md): the evidence chain, commands, verification scope and limitations.
- [Data dictionary](audit/DATA_DICTIONARY.md): identifiers, records, joins and result fields.
- [Access and exclusions](audit/ACCESS_AND_EXCLUSIONS.md): material intentionally withheld from this public tree and release permissions still to resolve.
- [Public file manifest](audit/PUBLIC_FILE_MANIFEST.json): SHA-256 and role of the files in this audit release.
- [Validation records](audit/validation/): completed checks and their exact scope.
- [Review allocation amendment](revision/expanded_v3/MARKDOWN_REVIEW_AMENDMENT.md): the change from the earlier two-account route to eight raters in four fixed dyads.

| Location | Role |
| --- | --- |
| `revision/expanded_v3/PROTOCOL.md` and plan/amendment files | Recorded design, scope, instructions and subsequent changes |
| `revision/sources/`, `revision/corpus/`, `revision/expanded_v3/corpus/` | Archived editions, earlier corpus freeze, corrected passages and lineage |
| `revision/expanded_v3/generation/` | Six active arms: requests, outcomes, rewrites, completion records and attempt evidence |
| `revision/expanded_v3/primary_analysis/` | Fold transforms, predictions, coverage and primary results |
| `revision/expanded_v3/extensions/jql_v1/` | Transfer, length controls and explanatory geometry results |
| `revision/expanded_v3/failures/` | Failure accounting; first outcomes distinguished from legacy/retry records |
| `research_v2/`, `tests/`, `requirements-v2.lock` | Frozen scientific implementation, tests and dependency hashes |
| `audit_tools/` | Additive offline audit/replay entry points |
| `research_assets/` | Fifteen exported CSV tables, five scientific figures, their builder and reference metadata |
| `old stuff/` | Prior public versions and legacy material, preserved for context rather than treated as the current release |

## Run an offline audit

Use Python **3.12.11** in an isolated environment, from the repository root:

```text
python -m pip install --require-hashes -r requirements-v2.lock
python audit_tools/replay.py --mode audit --output audit_runs/quick
python audit_tools/replay.py --mode primary --models all --output audit_runs/primary
python audit_tools/replay.py --mode transfer --models all --output audit_runs/transfer
python audit_tools/replay.py --mode explanatory --models all --output audit_runs/explanatory
```

Choose a fresh output directory for every invocation. Dependency installation may require internet access; replay uses stored text and outcomes, makes no model calls and requires no API keys. Read the [audit guide](audit/README.md) before interpreting a successful receipt: the modes verify different things.

## Interpret the evidence

The expanded study is exploratory. Confidence intervals condition on fitted models and the six selected authors. Only three of the 54 primary tests survive the shared Holm correction; all three are Gemini/shrinkage-LDA comparisons. The session arm records an orchestration workflow, whose exact backend checkpoint is not independently attested. The data do not establish a general provider ranking or loss of all recoverable author information.

Reviewer-level ratings, identifying records and raw returns remain withheld while written permission and the ethics basis are resolved. Aggregate semantic-review tables are provided, but their exclusions and agreement calculations cannot be independently reconstructed from this public tree alone. Numerical consistency does not establish participant identity, independent completion or absence of assistance.

No public DOI is claimed. License decisions for original contributions remain pending, and third-party source notices and rights continue to apply. Credentials, current manuscript files and the complete local author package are excluded. See [access and exclusions](audit/ACCESS_AND_EXCLUSIONS.md) for the precise boundary.
