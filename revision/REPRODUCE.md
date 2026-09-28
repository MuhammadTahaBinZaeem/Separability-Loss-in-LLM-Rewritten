# Reproduce the revised study

## Research-first extensions (2026-09-22)

The current JQL research extension is separate from the frozen v2 endpoints.
Its choices are in `extensions/jql_v1/PLAN.md` and
`extensions/jql_v1/EXPLANATORY_MODEL_PLAN.md`; both are explicitly exploratory.
After the selected provider has complete accounting and no active writer:

```powershell
.\.venv\Scripts\python.exe -m research_v2.transfer_extension --model azure_replication
.\.venv\Scripts\python.exe -m research_v2.transfer_verify --model azure_replication --replay
.\.venv\Scripts\python.exe -m research_v2.shift_contraction --model azure_replication
.\.venv\Scripts\python.exe -m research_v2.shift_contraction --model azure_replication --replay
```

Use `gem31lite` only once that provider's accounting is complete. These commands
make no API calls, leave v2's primary results separate, and do not edit prose.
The full replay must reproduce the same data, transformed-view evidence,
predictions, scores, intervals and reports byte-for-byte. Wall-clock manifest
metadata is deliberately excluded from equality. Run explanatory-model steps
after the matrix replay, because their input includes its final manifest.

The scientific-only finisher can be started while generation is still active:
`python -m research_v2.science_finish --wait-minutes 100`. It performs no new
generation/retries and records an explicit incomplete state if a provider stops
short. Its status lives in `verification/research_watch_status.json`. The older
`reproduce`/`finish` commands below also build manuscript assets; do not use those
while manuscript writing is intentionally paused.

Counts, scientific assessment and the outstanding independent-work validation
proposal are in `extensions/jql_v1/ASSESSMENT.md` and `NEXT_VALIDATION.md`.

## Exact environment

Use Python 3.12.11. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-v2.lock
.\.venv\Scripts\python.exe -m pytest -q tests
.\.venv\Scripts\python.exe -m research_v2.reproduce
```

On Linux/macOS use `.venv/bin/python` in place of the Windows executable path.
The hash lock includes platform distributions; source bytes retain their original
line endings while generated text uses UTF-8/LF. The default reproduction command
rebuilds corpus selection from archived sources, recomputes historical QC,
consolidates native responses and terminal refusals, fits all three classifiers
in all three work-held-out folds, runs six family ablations, 5,000 bootstrap and
9,999 work-swap replicates, builds review forms, checks readiness and regenerates
the manuscript draft/figures. It makes no model API calls and incurs no generation
charges. A published-record validation, if configured, makes a public Zenodo GET.

After stopping generation, an optional local-only archive can be built with
`python -m research_v2.archive --env-file ../Paper-secrets/api.env`. It uses an
explicit file allowlist, excludes private reviewer administration, scans for the
supplied credential values without logging them, checks every zip member and
labels the package REVIEW_ONLY. It never contacts Zenodo or assigns a license.

Incomplete generation exits with status 2 and a machine-readable report. Missing
human reviews/DOI remain explicit blockers even after computational reproduction
finishes. Tests can pass while scientific readiness is false. An optional
`--allow-partial` diagnostic is not a final study. Never edit the original frozen
protocol to make a validator pass; changes belong in `AMENDMENTS.md`.

## Resume missing provider observations

Credentials are local-only, currently in the sibling secrets directory:
`C:\Users\Empty\Documents\Paper-secrets\api.env`. Do not paste credentials into
the repository, a command line, a manuscript, a workflow file or a chat message.

```powershell
.\.venv\Scripts\python.exe -m research_v2.parallel_generation --model gem31lite --env-file C:\Users\Empty\Documents\Paper-secrets\api.env --workers 4 --minutes 180
.\.venv\Scripts\python.exe -m research_v2.parallel_generation --model azure_replication --env-file C:\Users\Empty\Documents\Paper-secrets\api.env --workers 4 --minutes 180
```

The September 25 connection checks found eight distinct Gemini credentials.
Seven passed a tiny non-study generation check; `gemchat` returned HTTP 503.
For the selected working credential, a bounded resume is:

```powershell
.\.venv\Scripts\python.exe -m research_v2.parallel_generation --model gem31lite --env-file C:\Users\Empty\Documents\Paper-secrets\api.env --credential-variable gemtest --workers 2 --attempts 3 --minutes 20
```

The override selects one connection credential and records its variable name,
never its value. It does not modify the frozen model, request payloads or
spending cap, and does not automatically switch credentials. A tiny check is not
proof of sustained availability: full study requests have still returned some
503s. Read the latest `completion.json` and `runner_status.json` once the writer
has exited; do not use this historical connection check as a live health claim.

The first fixed review batch is Nano-only, with 270 pairs per reviewer under
`annotations/review_scope.json`. Re-running form preparation must preserve the
issued hashes. Gemini completion must not append items to these existing forms;
additional model review requires a separately recorded immutable batch and
full-study review accounting. Completing Nano review alone is not full-study
semantic validation.

These commands incur provider usage and have cumulative conservative reservation
caps configured in `generation_plan.json`. They reuse frozen requests and skip
persisted responses/refusals. Repeated quota failures stop the run; do not rotate
credentials, change models or censor prompts to fill gaps. The retired serial
generation command is disabled to prevent inconsistent accounting. The old Groq
workflow is historical and is not the active v2 generation path.

Each model folder has an exclusive `RUNNING.lock`. To stop gracefully, create its
`STOP_AFTER_CURRENT` marker and allow in-flight requests to persist. Do not remove
a lock while the PID it contains is active. A stale lock after a crash requires a
read-only PID check and explicit recovery; preserve transport evidence first.

## Human returns and archival publication

The audit is not completed by software. Issue only each reviewer's separate form
and `annotations/INSTRUCTIONS.md`. Keep private joins, other ratings and results
away from reviewers. The import command requires a distinct human pseudonym,
actual completion timestamp and an explicit independence attestation; only the
person/investigator can truthfully supply those. After both imports, rerun
`research_v2.reproduce` to calculate agreement and paired semantic sensitivity.
Private returns/registries are ignored by Git; backups and appropriate controlled
storage are the investigator's responsibility.

Archive packaging does not publish a DOI. Actual Zenodo publication requires
confirmed authors/affiliations, rights and license choices, reviewer-release
consent as applicable, complete verified inputs, and a checked final package.
The manuscript stays a review draft until those remaining decisions and records
are resolved. Hashes protect consistency, not proof of human identity, historical
truthfulness or journal acceptance.

## Current quota checkpoint and same-key resumption

On 2026-09-21 the provider identified Gemini's daily per-project/model quota of
500 requests. The checkpoint retains 962/1,080 native responses, not a complete
Gemini experiment. The next documented daily reset is 2026-09-22 07:00 UTC
(12:00 Asia/Karachi). Run this from the repository after quota becomes available:

```powershell
.\scripts\resume_and_finish_v2.ps1
```

It uses only the existing credential, removes only the workflow stop marker,
retains all saved responses, resumes missing requests, stops on a confirmed
daily limit, rebuilds offline evidence and makes a local review ZIP. It does not
hire reviewers, change billing, publish, push Git commits or submit the paper.
The script is provided, not scheduled: no background retry is currently active.

Read `annotations/RECRUITMENT.md` for the human-review route. The all-360 source
review is separately registered using `research_v2.source_review`; its private
return is excluded from Git and the public review-package allowlist.

## Word reading copy

Document generation is separate from the locked scientific environment. Use the
Codex bundled artifact Python with `scripts/build_manuscript_docx.py`, supplying
the generated Markdown and desired DOCX paths. In this Windows workspace,
LibreOffice is absent; `scripts/export_manuscript_pdf.ps1 -Docx ... -Pdf ...`
exports that same DOCX through installed Microsoft Word. Render the PDF with
bundled Poppler and inspect every page before claiming visual QA. Rebuild and
repeat QA after the numerical results change; a prior PDF is not an automatic
render of newly generated Markdown.
