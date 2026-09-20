# Revised analysis protocol (v2)

Status: specified before new generation and revised model fitting. This is a dated
revision of an exploratory study, not a retrospective claim of preregistration.

## Corpus and scope

Six fixed authors; three independently authored fiction works per author; twenty
nonoverlapping 450–650 word passages per work (360 originals). A collection is a
source volume, not a work. Poe and Wilde stories receive individual work IDs.
The archive retains the bytes of each Gutenberg source, retrieval metadata,
explicit body boundaries, and source character offsets for each passage. Source
selection and exclusions depend on provenance and textual boundaries, never on
attribution outcomes. Each of the historical 360 passages receives a traceable
audit disposition; that audit is AI-assisted structural review, not independent
human semantic annotation. Original experimental artifacts remain historical.

## Generation

Version 2 is a new experiment. The existing Gemini corpus is not silently
augmented with another provider. The planned current models are Groq-hosted
`openai/gpt-oss-120b` (primary) and `qwen/qwen3.6-27b` (replication). Selection is
based on current availability and existing repository credentials, before results.
The previous free-tier Llama 3.3 and Qwen 3 32B endpoints have been retired
(https://console.groq.com/docs/deprecations, checked 2026-09-15).

Three conditions: paraphrase, modernize, simplify. Temperature 0.2, top_p 1.0;
one generation per passage/condition/model. Fixed model-specific reasoning
settings are logged in the request. The request contains an opaque ID and text,
but no author, title, or source metadata. Natural character names are retained.
Record request/response bytes, prompt hash, source hash, provider response ID,
model returned by provider, timestamp, usage and finish reason. Checkpoints allow
resume without regenerating a successful request. Do not choose from multiple
responses using stylistic or semantic outcome scores. Retry transport errors and
rate limits only. Preserve malformed/truncated responses as failures; never
replace them silently. No quota circumvention or credential rotation.

Length deviation >15% is a warning; >20% is a severe warning. Empty, malformed,
wrong-ID, truncated and identical-to-original outputs are failures. All nonfailed
outputs enter intention-to-rewrite analysis, with warning-free sensitivity shown
separately. An incomplete model/condition cannot produce a final primary table.

## Evaluation and preprocessing

Three outer folds: one entire work per author held out each time, with the other
two works per author used for training. Work order is reproducibly hashed using
seed 20260915, not assigned by passage order. Each passage and its three rewrites
stay in the same fold. All predictions in the pooled primary metric are out of
fold. The authors are fixed; do not infer population-wide author effects.

Primary classifier: Euclidean nearest centroid. Confirmatory robustness models:
GaussianNB(var_smoothing=1e-9) and actual sklearn LinearDiscriminantAnalysis with
solver='lsqr', shrinkage='auto', equal author priors. Models and settings are fixed;
there is no test-set model selection or hyperparameter search. If tuning is later
introduced it must use inner work-grouped folds and be recorded as a revision.

For every fold fit the character-trigram vocabulary on original training text
only. Extract 85 fixed features plus up to 120 training-selected character
trigrams, drop training-constant features and fit StandardScaler on originals in
the training fold only. Preserve the fitted vocabulary, feature names, training
IDs and scaling statistics. Transform all held-out conditions using that same
fit. Character trigrams are lexical/orthographic features; this protocol makes no
claim to measure parsed syntax.

The primary outcome is paired macro-F1 loss: original minus rewritten, evaluated
on identical source passages with all six labels always included. Also report
accuracy, per-author performance, work-level correct-attribution rates, confusion
counts, each outer fold and pooled out-of-fold predictions. Feature-family
ablations and the warning-free analysis are secondary. No result-dependent
choice of primary feature set.

## Distance and uncertainty

Burrows-style Delta is mean absolute standardized feature difference. Original
training data supply the reference mean/SD, used unchanged for originals and
rewrites. Compute held-out author centroids in this shared space, pairwise
distances, and original-to-rewrite centroid shifts within each outer fold. The
author pairs share authors and are not independent sample units.

For macro-F1 loss report 5,000 stratified hierarchical bootstrap replicates:
within each of the six fixed authors resample its three works, then resample
paired passages within each selected work. The same indices apply to originals
and rewrites. These intervals are conditional on fitted cross-validation models;
they do not include model-refitting uncertainty or establish a causal population
effect. Eighteen works provide limited precision; report that limitation.

Use a two-sided paired work-block randomization test: swap original/rewrite
prediction labels for whole works under a sharp exchangeability null. Use the
same assignment for every passage in a work, 9,999 sampled assignments, and
(extreme+1)/(B+1). This is an explicitly conditional test, requiring exchangeable
labels under the null, not a claim that rewrites were randomly assigned.
Apply Holm correction jointly across the predeclared 2 models x 3 classifiers x
3 conditions (18 comparisons). Report no p=0. Bootstrap nonpositive proportions
are not p-values. Distances are descriptive; do not test 15 author pairs as if
they were independent observations.

## Independent semantic annotation

The historical filled PDFs are absent and the CSV template is blank. Their
derived flags are unverified legacy evidence and are excluded from v2 claims.

Draw five passages per author/work/condition/model cell after generation, using
a fixed hash sample (270 pairs per model). Give two people separate randomized
forms with different opaque IDs, no author/model/condition labels or existing
ratings. Each person must complete the form independently before discussion.
Record pseudonymous identity, completion date, independence and human-review
attestation, and the SHA-256 of the untouched returned file. Keep original returns
and immutable provenance; public release may use pseudonyms. AI review is not a
substitute for these people. Obtain any institutionally required review/consent
before recruiting; do not invent an exemption.

Fields: added facts, omitted facts, changed narrative order, changed speaker or
character relations (binary); tone drift (0–2); meaning preservation (1–5);
usable (yes/no), notes. Require notes for unusable/meaning<=3 and factual changes.
Report raw agreement and Cohen's kappa for binary outcomes, weighted kappa for
ordinal ratings, including undefined values when all ratings are constant.
Preserve disagreements and adjudication separately; never duplicate one review
to impersonate two. Identical complete forms require an explicit provenance
check, not an automatic accusation of misconduct.

Prespecified sensitivity exclusion uses the union of the two reviewers' factual,
order/relationship, meaning<=3, or unusable flags. Disagreements and any subsequent
human adjudication remain separate; the conservative sensitivity rule does not
depend on reaching consensus. Critical-edition editorial interpolations, quoted
verse blocks and complete bracketed illustrations/captions are excluded during
source selection. Numeric/letter note callouts are removed with a logged rule.

Only after verification rerun sensitivity on paired audited rows and disclose
its sample size. Unaudited passages are unknown, not certified clean.

## Reproducibility and release

Python 3.12, a dependency lock with distribution hashes, UTF-8/LF generated text,
source files preserved byte-for-byte. One command rebuilds corpus, comparisons,
tables, figures and manifest from archived inputs. Validators recompute
invariants and metrics, never require a predetermined effect size or direction.
Final readiness requires complete model outputs, independent human annotations,
all computational tests passing, and an actual published archival record/DOI.
Pending inputs must remain visible. A reserved DOI alone is not publication.

The empirical claims in historical readiness reports and writing blueprints are
superseded. A final manuscript must use revision/results and revision/paper_assets
only after revision/readiness.json reports ready_for_writing=true.
