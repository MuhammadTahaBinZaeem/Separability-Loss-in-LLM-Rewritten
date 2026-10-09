# Corrected corpus and model expansion, version 3

Recorded prospectively before new expansion study outputs. This is an exploratory
extension after examination of v2 results, not a retrospectively preregistered
confirmatory study. The frozen v2 protocol, corpus, responses and returns remain intact.

## Corpus and lineage

Keep the six authors, eighteen works, three held-out-work folds, twenty passages
per work, and 450–650-word source windows. Replace four independently flagged
passages using exact archived spans from the same works. Candidate selection uses
nearest eligible nonoverlapping windows outside the affected chapters (and outside
literal edition-formatting markers), without consulting rewrite or classifier
performance. The exact spans and reasons are in research_v2/expanded_study.py.
Preserve the other 356 texts byte-for-byte. Replacement IDs begin V3; unchanged
V2 IDs intentionally retain lineage. The four replacements require a dated source
follow-up. Automated correspondence and the assistant's reading do not pass that review.

## Model arms and scope

Gemini 3.1 Flash Lite and GPT-5.4 Nano reuse only exact, unchanged v2 observations,
with original request IDs, model metadata and response hashes. Twelve new requests
per existing model cover the four replacements in three conditions. New arms are
GPT-5.1 Codex, GPT-5.6 Sol and GPT-5.6 Terra. Sol replaces previously proposed Luna
under the user's latest naming, not as a result-driven model choice.

GPT-6 Astra via Codex, Extra High is a separate session arm. A user screenshot
supports the selected interface label, not backend checkpoint identity. Session
outputs must retain their exact prompt, source, output and available session link.
They do not have fabricated provider response IDs, token usage or API settings.
Persistent context includes prior study work, so this is an interface/workflow
comparison and must not be pooled as an equivalent controlled API condition.

All arms target 1,080 assignments: 360 sources by paraphrase, modernize, simplify.
The existing fidelity instructions are unchanged. Nano/Gemini retain v2 sampling
parameters. Sol/Terra use no reasoning; Codex uses low reasoning, without unsupported
temperature/top-p overrides. API output ceiling remains 4,096 tokens, including
reasoning where applicable. Supported parameter differences are reported, not hidden.

## Attempts, failures, and budget

First received study outcome is primary. Existing v2 outcomes are never replaced
or relabelled. Up to two additional attempts are permitted for technical failures
in a separately labelled retry-assisted sensitivity dataset; do not reroll mere
length warnings, semantic ratings, or scientifically inconvenient results.
Refusals are counted; do not rephrase material to bypass provider safeguards.
Transport retries use the same request and credential, honor provider backoff,
and stop on account/day limits. Retain attempts, timestamps and all available
native failed/partial output. Historical HTTP text that was not archived is marked
unavailable, never invented. New HTTP bodies are stored privately for secret review.

All new paid calls share the user's $35 ceiling, including diagnostics and retries.
Reserve an upper estimate before each request; unknown usage retains its full
reservation. Reported token usage may settle a reservation using recorded reference
rates. Rates are published OpenAI planning references, not a verified Azure bill;
account-specific billing remains unverified. Do not claim a billing guarantee.
GPT-5.1 Codex remains below three million output tokens, with prior reservations
counted. If completion exceeds the cap, report the incomplete scope; do not lower
text-length targets, silently drop models, or fabricate completion.

## Analysis and review gates

Retain train-fold-only feature selection/scaling, work-grouped validation, fixed
six-author labels, paired work-aware inference, and failure/warning sensitivity.
Use explicit not-estimable status when a planned length panel loses an entire
work; never pad texts, change the threshold or silently drop that work.
Expanded model comparisons are exploratory. Larger model count alone is not
evidence of scientific merit. Review-dependent exclusions and agreement analyses
are run only after independent returns are sealed.

Review samples use fixed, balanced source/work/condition strata, opaque item IDs,
hidden model labels, two independent ratings per sampled pair and preserved original
returns. More reviewers may partition the workload, not reduce double-rating.
Previously issued Nano-only forms remain immutable and cannot certify other arms.
Final expanded packets must not be called complete before all intended assignments
are accounted for and the sampling manifest is frozen. Neutral interface wording
does not remove provenance or permit assisted ratings to become independent evidence.
