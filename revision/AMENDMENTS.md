# Prospective amendments and deviations

## 2026-09-25 staged reviewer issue and credential diagnosis

The user requested immediate review of completed Nano generation while Gemini
remains incomplete. The first fixed semantic batch therefore includes only
`azure_replication`: five technically valid outputs per author/work/condition
cell, or 270 pairs per reviewer. Both reviewers assess the same underlying pairs,
using the existing `human_audit_v2` selection, separate opaque IDs and separate
orders. No review judgments existed for this batch when this scope was set.
`annotations/review_scope.json` is hashed into the issue manifest. Further models
require separate immutable batches; they must not expand or replace these forms.
Completion of this batch alone cannot satisfy the full-study review gate.

This is a prospective workflow amendment, not a new preregistration or evidence
that the corpus is clean. The registered source review flagged four passages;
those findings and the frozen source records remain unchanged. Semantic ratings
do not resolve source attribution or authorize a publication-ready claim.

At the user's request, one non-study connectivity request was made using each of
eight distinct configured Gemini credentials. `gemchat` returned HTTP 503; the
other seven succeeded with `gemini-3.1-flash-lite`. Resume the missing frozen
requests with the single selected `gemtest` credential, recording its variable
name in new attempt/response records. This changes connection credentials only,
not model, instructions, sampling, first-response selection, or frozen payloads.
There is no automatic credential failover or quota rotation. The existing
cumulative $10 reservation cap still applies; provider throttling is respected.

The user also permitted GPT-5.1 Codex where useful, subject to fewer than
3,000,000 output tokens. A 128-token connectivity allowance succeeded with
11 actual output tokens. Its initial use is a bounded automated methods/code
audit (maximum 12,000 output tokens), separately recorded from experimental
rewrites and reviewer evidence. It does not add a third experimental condition
or produce reviewer responses. Further calls must reserve their maximum output
allowance, including reasoning, against the remaining user cap.

## 2026-09-20 provider availability

Recorded before any v2 study rewrite, after source review and original-only
baseline fitting. This remains an exploratory revision, not a preregistration.
The corpus and original protocol hash are unchanged. This document supplements,
and does not overwrite, the protocol captured in the corpus freeze.

The two Groq credentials returned HTTP 401 `expired_api_key`; no study output was
obtained. Their frozen requests, probe events, and original plan are retained in
`generation/gptoss120`, `generation/qwen27`, and `history/retired_groq_access`.

The user supplied new provider credentials locally, outside the repository.
Authenticated GET checks succeeded for Azure, Gemini, Featherless and Zenodo.
Featherless returned no models available on the current account plan; targeted
Qwen2.5-7B metadata also reported unavailable. No subscription upgrade was made.
Azure's model catalogue is not a list of deployed models; a tiny non-study
`gpt-4.1-mini` request returned DeploymentNotFound. The replication deployment is
therefore explicitly pending, not silently replaced with a second Gemini model.

A tiny non-study Gemini 2.5 Flash request returned 404. A subsequent Gemini 3.1
Flash-Lite connectivity/JSON-format check succeeded. The primary is now
`gemini-3.1-flash-lite`, using the native Google API, temperature 0.2, topP 1,
maxOutputTokens 4096, thinkingLevel=minimal and an explicit two-string JSON
schema. All source text, instructions, conditions, sampling, inference, and
human-review requirements remain unchanged. Model selection used accessibility
and feasibility only, not attribution or semantic outcomes. Smoke checks are
excluded from study data. All study responses, including failures, are retained.

Only `gemchat` is used; other Gemini credentials are not rotated to evade quotas.
Per-attempt conservative cost reservations use published standard text rates
($0.25/M input and $1.50/M output tokens) and a cumulative $10 reservation cap.
This estimate is not a provider billing statement. Transport retries are also
reserved. Stop if a provider limit, spending cap, or missing deployment prevents
completion; never fill missing experimental cells with agent-written text.

The planned inferential family remains 18 comparisons: two models, three
classifiers and three conditions. Until replication is complete, any primary
model results are explicitly provisional and incomplete for the overall study.
Annotation forms are issued only after both planned models are complete.

Documentation checked 2026-09-20:

- https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite
- https://ai.google.dev/gemini-api/docs/generate-content/thinking
- https://ai.google.dev/gemini-api/docs/pricing
- https://learn.microsoft.com/en-us/azure/ai-studio/ai-services/concepts/endpoints
- https://featherless.ai/docs/api-reference-models

This amendment does not assert a new human review, an ethics exemption, or a
published Zenodo record. A valid archive token is not evidence of publication.

## 2026-09-20 Azure deployment supplied by investigator

After the first three Gemini study responses, the investigator named GPT-5.4
nano. A tiny non-study Azure `gpt-5.4-nano` connectivity test succeeded. The
previously unresolved Azure replication is now configured with that deployment,
reasoning effort none, temperature 0.2, top_p 1, max_output_tokens 4096,
store=false and the same strict two-string JSON schema. Accepted returned model
IDs are the tested alias and the documented 2026-03-17 snapshot. Actual provider
IDs are retained; an alias alone does not prove an immutable weight snapshot.
No original or rewrite attribution results were used to select the deployment.

The Azure cost guard uses deliberately conservative planning assumptions
($0.50/M input, $2.50/M output) and a $20 cumulative per-attempt reservation cap,
not a verified Azure account tariff or a guarantee about the actual bill.
The same fixed inference family and human sampling design apply. The first three
Gemini outputs had length warnings; they remain study observations, not deleted
pilots or quality-selected replacements. The system prompt is unchanged.

## 2026-09-20 failed-output estimand and execution

During generation, before any rewritten-text attribution analysis, Azure
returned incomplete responses with native reason `content_filter`. No filter
was weakened, source text censored, refusal bypassed, or failed generation
replaced. This is a substantive limitation, especially because failure can
depend on author/work/content.

The original all-360-output contrast cannot be computed for a condition with a
missing valid rewrite. Therefore report generation success/failure for all
assigned requests, then explicitly label stylometric comparisons as
**paired loss conditional on valid output**. Use the identical surviving passage
IDs on both original and rewritten sides; retain all length warnings. Describe
this as an amendment prompted by execution failures, not a prespecified
intention-to-treat/causal effect. Never impute missing text or imply filtered
outputs were unchanged. The old strict `complete` flag still requires zero
failures; `responses_complete` means all 1,080 native responses are archived.
Final analysis readiness requires complete response accounting, all 18
comparisons, explicit failure tables, and disclosure of this selection limit.
Distances likewise use paired surviving original passages as the denominator.
The study does not estimate the style of outputs the service did not deliver.

The human audit samples five technically valid pairs per original sampling
cell. It is conditional on availability, not an audit of failed/refused text.
If any cell has fewer than five valid pairs, stop and flag the sampling shortfall
rather than silently sampling replacements from other cells. The warning-free
and human-verified subsets remain sensitivity analyses, not result-selected
primary samples. All six author labels remain in every reported macro-F1.

For speed, serial workers were interrupted and replaced with at most four
concurrent requests per provider, shared rate-limit backoff, and one fixed key
per provider. `access/parallel_restart.json` records two in-flight attempts whose
outcomes were not persisted; only those unresolved transport attempts can be
retried. All previously persisted outputs are retained. The concurrency change
does not change requests, sampling parameters, or the first-persisted-response
rule. Native response bodies, IDs and timestamps remain the provenance source.

## 2026-09-21 HTTP refusal accounting

Before rewritten-text attribution analysis, the Azure run stopped after 107
native responses on an HTTP 400 `content_filter` event. This is a terminal
service refusal, not a transport error to retry and not a model completion.
The existing dated event is preserved and linked by hash to a separate
terminal-outcome ledger. Its original error body was not retained; no body,
provider completion ID, returned model or text is reconstructed. Subsequent
HTTP filter events retain safe headers and an error-body hash, not private
account-bearing error messages. No blocked request is resent.

The runner now continues other independent frozen requests after recording a
filter refusal. `accounting_complete` requires every assigned request to have
either an archived native response or an evidenced terminal HTTP refusal.
`responses_complete` still means all assigned requests have native responses;
`complete` additionally requires zero technical failures. Analysis and human
form preparation use complete accounting and the previously disclosed
valid-output estimand. Failures remain in availability tables and never enter
stylometric or human-review samples. Missing quota-limited requests are not
classified as refusals. This operational repair does not change prompts,
models, safety settings, sampling or statistical hypotheses.

## 2026-09-21 interim reporting and human source-review administration

After the first Azure-only diagnostic analysis, Gemini remained incomplete.
Only complete-accounting model ledgers may appear in a separately labeled
interim companion; the main two-model results and release gate remain blocked.
Interim multiplicity correction still reserves all eighteen planned tests.
No prompts, feature sets, hypotheses, exclusion rules or inferential settings
were changed after observing these interim results.

The original request for manual review of all 360 sources is now represented by
a separate human-attestation and immutable-return release gate. This is an
administrative provenance check, not a claim that the AI-assisted structural
audit was already a human review. A source reviewer must not unblind semantic
reviewers before their original independent ratings have been sealed. Findings
requiring source corrections must trigger transparent versioning and reassessment,
not post-hoc removal because a passage produces an unfavorable attribution effect.
