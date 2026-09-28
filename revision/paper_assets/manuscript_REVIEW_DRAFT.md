# Author attribution after LLM rewriting of fiction: a work-held-out study of six authors

> REVIEW DRAFT — NOT READY FOR SUBMISSION. Computational results, independent human review and archival status are distinguished below. This file is generated from `manuscript_v2_template.md`; edit that source, not the generated copy.

Author names, affiliations, corresponding author, contributions, funding and competing-interest declarations require investigator confirmation. No identity or declaration is inferred from the repository account.

## Abstract

Rewriting can change the textual signals used to identify an author, but a decline in attribution accuracy does not by itself demonstrate stylistic homogenization or preservation of meaning. We examine this distinction in a source-traceable corpus of 360 nonoverlapping fiction passages: six authors, three independently identified works per author, and twenty passages per work. Three rewrite instructions—light paraphrase, modernization and simplification—are applied through Gemini 3.1 Flash-Lite and Azure-hosted GPT-5.4 nano, yielding 2,160 assigned requests. Evaluation holds out entire works. Character-trigram selection, constant-feature removal and scaling use original training passages only. The primary outcome is the paired change in six-class macro-F1 for a fixed nearest-centroid classifier; Gaussian naive Bayes and shrinkage linear discriminant analysis assess classifier dependence. Work-aware uncertainty, output availability, length change and shared-scale centroid distances are reported separately. The full two-model analysis is pending. Appendix A reports the separately validated, interim Azure results. A planned two-person blinded audit assesses meaning and narrative preservation; its completion status is reported explicitly. The design supports a bounded account of attribution transfer under particular rewriting services, not a claim about all literary style or all language models.

Keywords: authorship attribution; literary stylometry; large language models; rewriting; grouped evaluation; research reproducibility.

## 1. Introduction

A rewritten passage remains connected to an earlier text while acquiring new wording, sentence organization and editorial choices. For literary scholarship, this raises a measurement question: which aspects of an author's textual distinctiveness remain detectable after automated rewriting? It also raises an interpretive question: what does failure to recognize the original author actually show? An attribution system may lose useful signals because the model substitutes a different vocabulary, compresses the passage, removes distinctive content, or changes a combination of these features. These possibilities should not be collapsed into a single claim that literary style has disappeared.

Authorship attribution supplies an operational test, not an exhaustive definition of style. Its feature representations and evaluation settings shape what can be recognized (Stamatatos, 2009). In this study, *author separability* means the ability of classifiers trained on original passages to distinguish six named authors in passages from their other works. The rewritten text is evaluated without retraining those classifiers. A decrease therefore measures diminished transfer of the original decision rule. It does not establish that a new classifier could not distinguish the rewrites, that readers would find them indistinguishable, or that a common model style caused the change.

We examine three questions. First, how does original-to-rewrite attribution change when the test work is absent from training? Second, how consistent is that change across two generation services, three instructions, and three fixed classifiers? Third, what constraints do output failures, length deviations and semantic preservation place on interpretation? The contribution is the combination of a traceable literary corpus, work-held-out evaluation, paired availability-aware comparisons and an auditable separation of computational outcomes from human judgments. The study does not claim to be the first demonstration that paraphrasing can disrupt attribution.

## 2. Related work

Stylometry offers a range of lexical and distributional representations rather than a single style variable. Stamatatos (2009) reviews attribution methods and their evaluation, while Eder, Rybicki and Kestemont (2016) provide an established computational toolkit for stylometric analysis. Our implementation uses interpretable text-local features and training-selected character trigrams. The distance analysis uses absolute differences in a shared standardized space, following the general Delta approach, but its feature inventory and reference sample are specified here rather than treated as interchangeable with every published Delta variant.

Evaluation must distinguish author-associated information from content and setting. Altakrori, Cheung and Fung (2021) introduce the topic-confusion task to expose topic dependence in attribution. Wang et al. (2023) investigate what learned authorship representations capture and emphasize that success at identifying authors alone does not guarantee a pure representation of style. Holding out works addresses direct work-level overlap in our study. It does not make topics, period, genre, character names or edition conventions independent of author identity.

Rewriting and authorship obfuscation are direct precedents. Altakrori et al. (2022) evaluate evasion, content preservation and misattribution as distinct concerns. Tripto et al. (2024) examine attribution under successive paraphrasing, making any broad claim that paraphrasing-related attribution loss is newly discovered untenable. We instead study a single application of three instructions to specified literary passages, retain service failures, and pair each usable rewrite with the identical original passage. The two-service comparison concerns these deployments and settings; it is not a controlled comparison of model architectures or training corpora.

Recent literary studies further narrow the novelty claim. O'Sullivan (2025) compares human- and model-written stories using frequent-word distances and clustering. Kirilloff et al. (2025) compare authentic nineteenth-century fiction with passages generated in named authors' styles. Those tasks concern new composition or explicit author imitation, rather than the same-source, metadata-withheld rewrite instructions used here. In a particularly close precedent, Icard et al. (2026) analyze French literary originals and model imitations under topic-controlled conditions, examining attribution transfer and the dispersion of multiple embedding representations. Our work therefore contributes an English, work-held-out and output-accounted transfer study, not the first literary examination of style after model rewriting. The differing tasks, representations and semantic constraints are important when comparing conclusions across these studies.

## 3. Corpus and research provenance

The corpus contains Jane Austen, Charles Dickens, Edgar Allan Poe, Mary Shelley, Mark Twain and Oscar Wilde. Each contributes three separately identified fiction works and twenty nonoverlapping passages per work. A volume containing several stories is not counted as several independent works unless story boundaries and work identities are separately recorded. All original passages contain 450–650 words under the archived tokenizer. Table 1 lists the works and their held-out folds.

Table 1. Frozen corpus; each work contributes twenty passages. Fold IDs are zero-based.

| Author | Work | Gutenberg ID | Held-out fold |
| --- | --- | --- | --- |
| Austen | Emma | 158 | 2 |
| Austen | Pride and Prejudice | 1342 | 0 |
| Austen | Persuasion | 105 | 1 |
| Dickens | Great Expectations | 1400 | 0 |
| Dickens | Oliver Twist | 730 | 2 |
| Dickens | A Tale of Two Cities | 98 | 1 |
| Poe | The Unparalleled Adventures of One Hans Pfaal | 2147 | 2 |
| Poe | The Gold-Bug | 2147 | 0 |
| Poe | The Murders in the Rue Morgue | 2147 | 1 |
| Shelley | Frankenstein | 84 | 2 |
| Shelley | The Last Man | 18247 | 0 |
| Shelley | Mathilda | 15238 | 1 |
| Twain | Adventures of Huckleberry Finn | 76 | 0 |
| Twain | The Adventures of Tom Sawyer | 74 | 1 |
| Twain | A Connecticut Yankee in King Arthur's Court | 86 | 2 |
| Wilde | The Picture of Dorian Gray | 174 | 0 |
| Wilde | Lord Arthur Savile’s Crime | 773 | 1 |
| Wilde | The Canterville Ghost | 773 | 2 |

Project Gutenberg source bytes, retrieval metadata and checksums are retained. Work specifications identify the start and end of the fictional body; passage records retain source character offsets and the precise cleaning transformation. Candidate selection excludes editorial interpolations, complete bracketed illustration/caption blocks, headings, note paragraphs and designated non-prose material. Numeric and letter note callouts are removed by a logged rule. Twenty eligible, nonoverlapping windows are spread deterministically through each work's candidate sequence. This is purposive, reproducible sampling, not a random sample of an author's oeuvre.

Source selection was revised after a structural audit of an earlier corpus. All 360 historical passages retain individual dispositions, and a superseded pre-generation draft is preserved. The source audit was AI-assisted; it is not represented as an independent human reading of every passage. Archived source correspondence establishes where the selected words came from, but does not alone certify the literary attribution of every embedded quotation or dialogue. The restricted authors, unequal work lengths, historical English and digitized editions constrain generalization.

A separate human source audit of all 360 passages has not yet passed the release gate. The issued packet requires a dated original verdict and note for every passage; no automated source match is substituted for this review.

The protocol was frozen before new provider generation. Provider-access failures required dated amendments selecting the available Gemini and Azure deployments. These amendments were recorded before rewritten-text attribution analysis, but this is an exploratory revision of an existing project, not a preregistered confirmatory study. Historical results, undocumented human-derived flags and a separate older-agent feasibility sample are excluded from the revised primary evidence. Repository retention of those artifacts documents their history; it does not validate their claims.

## 4. Methods

### 4.1. Rewrite generation and accounting

Each passage is assigned to light paraphrase, modernization and simplification under each service. Every instruction asks for preservation of meaning, material facts, characters, relationships and event order; no summary; approximately the original length within 15%; and a strict JSON object with an opaque request identifier and rewritten prose. The prompt includes the source passage and word count but not its author, title or archive metadata. Recognizable names and wording remain, so metadata omission cannot guarantee that a model did not recognize a source.

Both services use temperature 0.2, top-p 1 and a 4,096-token output ceiling. Gemini uses its native generate-content endpoint with minimal thinking; Azure uses the Responses interface with reasoning effort none and response storage disabled. Native returned model identifiers, response identifiers, timestamps, usage, finish status, request hashes and response bodies are retained. A returned alias is not evidence that service weights were immutable. Identical nominal sampling values also do not establish identical behavior across APIs.

The first persisted provider response is retained for each frozen request, including malformed or incomplete outputs. No outcome-based reroll is permitted. Retriable transport errors and rate limits are logged, and supplied credentials are not rotated to circumvent quotas. An HTTP content-filter refusal is recorded separately from a model response, with no invented completion identifier or text; it is not resent. The audit trail explicitly records two early in-flight requests whose outcomes were not persisted when serial execution was replaced with bounded concurrent execution. Exact service regeneration is therefore distinct from reproducible analysis of the archived observations.

Technical QC fails empty, malformed, wrong-identifier, truncated, returned-model-mismatched and unchanged outputs. Length deviations above 15% and above 20% are retained as graded warnings, not automatically excluded. Quality labels are deterministically recomputed from preserved responses. Assignment, native-response receipt, terminal HTTP refusal, valid output and missing outcome are separate states. A finished accounting ledger does not mean every request produced a usable rewrite.

### 4.2. Estimand and missing outputs

Execution revealed content-filter failures before rewritten-text attribution analysis. The amended estimand is consequently *paired attribution loss conditional on valid output*. For each service and instruction, the original-side metric is calculated only on passages with a technically valid rewrite in that same comparison. Length-warning outputs remain included. Failed text is neither imputed nor treated as an unchanged original. We report failures by author, work and instruction because availability may depend on those variables.

This paired restriction avoids comparing different passage sets but does not remove selection bias. Results describe the delivered valid-output subset, not the hypothetical text a service might have produced without filtering. Cross-service comparisons can involve different surviving passage sets and are not estimates of a model-only causal effect. A quota-limited, unattempted or unresolved request remains missing and blocks final study accounting.

### 4.3. Held-out works and features

There are three outer folds. Each holds out one entire work from each author: 120 test passages and 240 original training passages. A fixed hash order with seed 20260915 determines each author's work allocation. A passage and all its rewrites share a fold. Pooled metrics use exactly one out-of-fold prediction per eligible passage and condition; folds are not treated as three independent experiments.

The representation combines 85 fixed text-local features with up to 120 character trigrams selected by frequency in original training text only. Feature families cover function words, length/rhythm proxies, punctuation, lexical richness, register markers and character trigrams. These proxies do not constitute parsed syntax, narrative interpretation or a complete literary theory of voice. Features constant in the training fold are removed. Means and standard deviations are estimated on original training passages and reused without refitting for all held-out originals and rewrites. Each fold's vocabulary, feature names, training passage IDs, source hashes and scaling parameters are retained.

### 4.4. Classifiers and reported performance

The primary classifier is Euclidean nearest centroid with uniform author priors. Fixed robustness classifiers are Gaussian naive Bayes, with variance smoothing 10^-9 and equal priors, and linear discriminant analysis with an lsqr solver, automatic shrinkage and equal priors. No test-set hyperparameter search or result-dependent classifier selection is performed. These are genuine distinct implementations; the discriminant model is not a relabeled centroid rule.

For each comparison, loss is original macro-F1 minus rewritten macro-F1 on the paired eligible passages. All six labels enter macro-F1, including labels with no predicted instances. Positive loss means lower rewritten-text attribution performance; zero or negative values are retained. Accuracy, confusion counts, per-author F1, work-level correct-attribution rates and fold-level results supplement the pooled outcome. Original baseline predictions shared across services are the same evidence, not independent replications.

Six leave-one-feature-family-out analyses refit the same training-only pipeline after omitting each family. These are descriptive robustness checks. The warning-free analysis uses matched pairs that meet technical QC without a length warning. If that subset lacks an author, the table reports the coverage shortfall rather than silently reducing the label set. Neither a selected length-compliant subset nor a favorable ablation becomes the primary analysis after inspection.

### 4.5. Conditional uncertainty and centroid distances

We calculate 5,000 stratified hierarchical bootstrap replicates. Within each fixed author, works are resampled with replacement, followed by paired passages within each selected work. Original and rewritten predictions always use the same sampled indices. Percentile 95% intervals describe uncertainty conditional on the fitted cross-validation models and the six selected authors; they do not include refitting uncertainty or justify population-wide author claims. Eighteen work blocks provide limited information, and resampling within only three works per author cannot create wider literary coverage.

A two-sided work-block swap test uses 9,999 sampled assignments. Each assignment swaps original and rewritten prediction labels for an entire work, preserving the dependence among its passages. The p-value is (extreme assignments + 1)/(9,999 + 1), never zero. This conditional test requires exchangeability under its null; the rewriting treatment was not randomized. Holm adjustment uses the full family of eighteen service-by-classifier-by-instruction comparisons. Bootstrap tail proportions are not reported as p-values.

For each held-out fold, author centroids are formed in the same original-training standardized feature space. Mean absolute feature differences are averaged over author pairs, separately for function words and all retained features. A rewrite condition is compared with the original centroids of its identical surviving passages. We report the distance ratio and original-to-rewrite centroid shift. Author pairs share authors and are dependent, so these distances are descriptive, without a test that treats fifteen pairs as independent. Centroid movement and reduced pairwise separation are different phenomena.

### 4.6. Independent semantic audit

The audit plan samples five technically valid original/rewrite pairs from every author-by-work-by-instruction-by-service cell using a fixed hash ranking: 540 pairs for each of two independent people. Each receives a separately randomized form with different opaque IDs and without model, author, instruction or other-reviewer labels. If any cell has fewer than five valid outputs, form issuance fails instead of substituting another cell. The prose itself may reveal identity or operation, so this is metadata blinding, not guaranteed perceptual blinding.

Reviewers assess additions and omissions of facts, changed narrative order, changed relationships, tone drift, meaning preservation and usability. Notes are required for flagged factual or substantial meaning changes. Untouched returned files, dated completion, pseudonymous reviewer identity and explicit independent-human attestation are retained. These records document provenance but do not cryptographically prove who performed a review. Agreement is reported as raw agreement and Cohen's kappa, with quadratic weighting for ordinal fields and explicit undefined values for constant ratings. Disagreements are preserved separately from any later adjudication.

The planned semantic sensitivity analysis excludes the union of either reviewer's factual, order/relationship, low-meaning-preservation or unusability flags. It compares original and rewritten predictions only within the audited paired subset. Unaudited passages are not certified clean. Human evaluation cannot be replaced by another language model while retaining a claim of independent human validation.

## 5. Results

### 5.1. Output availability and length

The full two-model analysis is pending. Appendix A reports the separately validated, interim Azure results.

### 5.2. Work-held-out attribution

The full two-model analysis is pending. Appendix A reports the separately validated, interim Azure results.

### 5.3. Classifier and feature robustness

The full two-model analysis is pending. Appendix A reports the separately validated, interim Azure results.

### 5.4. Shared-scale distances

The full two-model analysis is pending. Appendix A reports the separately validated, interim Azure results.

### 5.5. Semantic preservation

Two independent human reviews have not yet been verified. No agreement coefficient, preservation percentage or human-clean sensitivity result is asserted. The planned forms require 540 paired judgments from each reviewer. This unresolved validation limits interpretation and blocks submission readiness.

## 6. Discussion

The full two-model analysis is pending. Appendix A reports the separately validated, interim Azure results.

The central distinction is between an observed transfer failure and an explanation for that failure. The original-trained classifier has access to particular lexical and distributional signals; rewriting changes their relationship to the source-author labels. Even agreement across the three classifiers would leave open whether the operative change is primarily lexical substitution, shortening, omission, register shift or another correlated transformation. The feature ablations locate sensitivity within this representation; they do not identify a causal linguistic mechanism.

The same caution applies to homogenization. Lower original-to-rewrite F1 can occur while rewritten authors remain separable in a differently oriented representation. A reduced centroid-distance ratio supplies complementary evidence about the selected feature space, but is not equivalent to perceptual sameness or reduced literary value. Training a new classifier on rewrites would answer a different question and is not retrospectively substituted for the fixed transfer analysis.

Length is especially important when an instruction asks for a faithful rewrite rather than a summary. A short response contains fewer observations for lexical estimates and may omit narrative information. Including length warnings preserves the operational consequences of the assigned prompt; excluding them may select unusually compliant passages. Both analyses therefore have a role, but neither by itself identifies an effect of style with meaning and length held constant. The human audit can clarify particular preservation failures, not transform the experiment into a randomized manipulation of style alone.

Provider filtering is likewise part of observed service behavior. Its failures must be visible rather than removed through retries, altered safety settings or unreported replacement text. Conditional comparisons are meaningful for the output actually supplied, with the stated selection limit. Claims about broader deployments require new evidence rather than an assumption that unavailable outputs resemble successful ones.

## 7. Limitations

The corpus is small in independent-work terms, restricted to six canonical historical English-language authors and selected works. Edition conventions, embedded quotations, genre, topic and period can remain associated with author labels. Famous public-domain passages may have appeared in model training; the study cannot establish model-training exclusion. Work holdout prevents direct reuse of the same work across classifier training and test, not all topic leakage or generator memorization.

One persisted output per request does not measure generation variability. Provider aliases, infrastructure, moderation and model-specific reasoning settings limit exact service replication and clean architectural comparisons. The generation amendments and prior exploratory work are disclosed, so findings should not be described as preregistered confirmation. Technical validity is not semantic validity, and heavy length warnings or differential refusal rates can materially limit interpretation.

Conditional intervals omit uncertainty from refitting models and from selecting authors, works and prompts. The work-swap test's exchangeability assumption is substantive. The human audit covers a stratified subset, with residual judgment uncertainty and possible recognition of sources despite metadata blinding. Software checks can detect inconsistencies and unsupported provenance claims; they cannot establish research intent or guarantee acceptance by a journal.

## 8. Conclusion

The full two-model analysis is pending. Appendix A reports the separately validated, interim Azure results.

The reusable contribution is a traceable way to distinguish assigned requests, delivered usable text, original-trained author attribution and independently assessed preservation. These layers should be reported together whenever literary rewriting is described as loss of authorial separability.

## Data, code and research-integrity statements

Archived inputs and executable analysis are maintained in the [research repository](https://github.com/MuhammadTahaBinZaeem/Separability-Loss-in-LLM-Rewritten), with the revised experiment isolated under `revision/` and `research_v2/`. The dependency environment is hash locked. Offline reproduction does not require API credentials or a second generation run. Source and generation hashes, request/response records, fold evidence, predictions and machine-checked result tables are retained. Provider safety failures and unresolved transport attempts are disclosed, not reconstructed. No published, checksum-verified archival DOI is available yet. A token or reserved DOI is not represented as publication.

Generative AI was used for experimental rewriting and also assisted source auditing, software development, analysis implementation and manuscript drafting. The separate older-agent feasibility sample is explicitly excluded from primary data and from human annotation. The investigator must verify all submitted claims and supply a journal-appropriate AI-use declaration. An AI system is not listed as a human author or independent reviewer.

No completed independent semantic review, ethics approval/exemption, participant consent, funding arrangement, authorship contribution or conflict-of-interest statement is asserted without supporting records. The investigator must obtain the applicable institutional determination and reviewer consent before recruitment and confirm what pseudonymized material may be released. Named sources and their edition notices remain separately identifiable; no blanket data/code reuse license is invented.

The historical audit identified methodological and provenance concerns, not evidence establishing intent to fabricate. Historical QC discrepancies are reconciled with their rule versions. Historical bootstrap output and unsupported semantic flags are not used for revised claims. No text-only AI detector is treated as proof of misconduct.

## References

Altakrori, M., Cheung, J. C. K., & Fung, B. C. M. (2021). The Topic Confusion Task: A Novel Evaluation Scenario for Authorship Attribution. *Findings of EMNLP*, 4242–4256. https://aclanthology.org/2021.findings-emnlp.359/

Altakrori, M., Scialom, T., Fung, B. C. M., & Cheung, J. C. K. (2022). A Multifaceted Framework to Evaluate Evasion, Content Preservation, and Misattribution in Authorship Obfuscation Techniques. *Proceedings of EMNLP*, 2391–2406. https://aclanthology.org/2022.emnlp-main.153/

Eder, M., Rybicki, J., & Kestemont, M. (2016). Stylometry with R: A Package for Computational Text Analysis. *The R Journal*, 8(1), 107–121. https://journal.r-project.org/articles/RJ-2016-007/

Icard, B., Sainero, L., Breton, A., Zve, E., & Ganascia, J.-G. (2026). Measuring Embedding Sensitivity to Authorial Style in French: Comparing Literary Texts with Language Model Rewritings. *arXiv*, 2605.10606, version 1. https://arxiv.org/abs/2605.10606

Kirilloff, G., Carroll, C., Daboul, Z., Frank, A., Khan, R., Hinrichs-Morrow, M., & Weingart, R. (2025). 'Written in the Style of': ChatGPT and the Literary Canon. *Harvard Data Science Review*, 7(4). https://doi.org/10.1162/99608f92.6d5fb5ef

O'Sullivan, J. (2025). Stylometric comparisons of human versus AI-generated creative writing. *Humanities and Social Sciences Communications*, 12, 1708. https://doi.org/10.1057/s41599-025-05986-3

Stamatatos, E. (2009). A survey of modern authorship attribution methods. *Journal of the American Society for Information Science and Technology*, 60(3), 538–556. https://doi.org/10.1002/asi.21001

Tripto, N. I., Venkatraman, S., Macko, D., Moro, R., Srba, I., Uchendu, A., Le, T., & Lee, D. (2024). A Ship of Theseus: Curious Cases of Paraphrasing in LLM-Generated Texts. *Proceedings of ACL*, 6608–6625. https://aclanthology.org/2024.acl-long.357/

Wang, A., Aggazzotti, C., Kotula, R., Rivera Soto, R., Bishop, M., & Andrews, N. (2023). Can Authorship Representation Learning Capture Stylistic Features? *Transactions of the Association for Computational Linguistics*, 11, 1416–1431. https://aclanthology.org/2023.tacl-1.80/


## Appendix A. Interim completed-model results

This companion reports only completed generation ledgers and validated current-code analysis. The main manuscript remains pending. Missing requests are not imputed or replaced. Human semantic and source reviews remain outstanding.

Models included: Azure GPT-5.4 nano.

Table A1. Paired attribution loss conditional on technically valid outputs, with all length warnings retained. Intervals use 5,000 paired hierarchical bootstrap replicates and condition on the fitted classifiers. Work-swap p-values use 9,999 draws. Interim Holm adjustment retains the full planned family of eighteen tests, with unavailable tests effectively assigned p=1; adjusted values must be recomputed when all eighteen are available.

| Classifier | Instruction | Pairs | Original F1 | Rewrite F1 | Loss [95% CI] | Interim Holm p |
| --- | --- | --- | --- | --- | --- | --- |
| Nearest centroid | paraphrase | 328 | 0.633 | 0.518 | 0.115 [0.055, 0.181] | 0.1974 |
| Nearest centroid | modernize | 332 | 0.639 | 0.547 | 0.092 [0.029, 0.164] | 0.5379 |
| Nearest centroid | simplify | 326 | 0.636 | 0.406 | 0.230 [0.159, 0.304] | 0.1424 |
| Gaussian NB | paraphrase | 328 | 0.567 | 0.485 | 0.082 [0.021, 0.148] | 0.1974 |
| Gaussian NB | modernize | 332 | 0.578 | 0.462 | 0.117 [0.046, 0.200] | 0.1710 |
| Gaussian NB | simplify | 326 | 0.571 | 0.446 | 0.125 [0.048, 0.202] | 0.7650 |
| Shrinkage LDA | paraphrase | 328 | 0.722 | 0.615 | 0.107 [0.041, 0.182] | 0.3468 |
| Shrinkage LDA | modernize | 332 | 0.722 | 0.593 | 0.129 [0.062, 0.206] | 0.1037 |
| Shrinkage LDA | simplify | 326 | 0.721 | 0.459 | 0.261 [0.191, 0.338] | 0.0090 |

A positive loss indicates poorer transfer of an original-trained classifier. Bootstrap intervals and the work-swap test answer different conditional questions; an interval excluding zero is not a multiplicity-corrected significance claim. No pure-style, causal, or population-wide effect is identified.

Nearest-centroid loss is positive in 3 of 3 available comparisons; 0 cross .05 under the interim eighteen-test Holm adjustment. These are interim outcomes, not a completed two-model study.

Azure GPT-5.4 nano has 1,080 accounted requests: 1,054 native responses and 26 evidenced HTTP refusals; 986 outputs are technically valid and 94 fail technical QC or are refusals. Failed outcomes are excluded only under the disclosed valid-output estimand. No failed output is rerolled.
