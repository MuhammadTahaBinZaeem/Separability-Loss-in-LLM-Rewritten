# Rewriting the Author: Semantic Fidelity and Stylometric Degradation under Large Language Model Paraphrase, Modernization, and Simplification

> Manuscript skeleton for a Digital Scholarship in the Humanities-style full paper. This is a structural draft, not final prose. It fixes section order, equation placement, table/figure callouts, evidence placement, and safe wording before full writing begins.

## Target journal and article constraints

- Target: Digital Scholarship in the Humanities-style computational humanities article.
- Target length: approximately 8,000-9,000 words before references, unless journal-specific guidance changes.
- Style: empirical digital humanities, not generic NLP benchmarking and not essay-style reflection.
- Core claim: LLM rewriting can preserve broad semantic usability while weakening stylometric authorial evidence.
- Required caution: the semantic-fidelity annotation is a single-review audit, not independent double annotation.

---

## Abstract [200-250 words]

**Purpose.** State the problem: LLM-mediated paraphrase, modernization, and simplification are increasingly plausible forms of textual mediation, but style-sensitive DH methods may treat rewritten texts as analytically equivalent to originals.

**Method.** Balanced public-domain literary corpus; six authors, twelve works, 360 source passages, 1440 text-condition rows. Train classifiers on original passages; evaluate on original and rewritten passages. Add passage-level paired bootstrap confidence intervals, semantic-fidelity audit, semantic-risk sensitivity analysis, and Groq free-model replication.

**Results.** Give only the strongest numbers:

- Core test macro-F1 losses are positive across three classifiers and three rewrite conditions.
- Minimum lower 95% bootstrap CI bound is 0.050751.
- Semantic-fidelity audit: 107/108 usable, mean preservation 4.53/5.
- Strict semantic-risk filter: all test rewrite losses remain positive.
- Groq replication broadly supports the pattern but includes model/condition heterogeneity.

**Conclusion.** AI-mediated texts should not be treated as neutral substitutes for originals in style-sensitive literary computation.

---

## 1. Introduction [900-1100 words]

### Paragraph 1: Opening problem

Begin with textual mediation in DH: edited, normalized, modernized, simplified, translated, OCR-corrected, and now LLM-rewritten texts. Do not start with hype about ChatGPT. Start with evidentiary status.

**Safe opening claim:**

> Texts used in digital humanities research are often transformed before analysis. Such transformations may improve access, readability, or comparability, but they may also change the features that computational methods treat as evidence.

### Paragraph 2: Why LLM rewriting is a special case

Explain that LLM rewriting can be fluent and semantically plausible, making it more dangerous than obviously corrupt text. The problem is not just hallucination; it is style-preserving vs meaning-preserving distinction.

### Paragraph 3: Research gap

Current work around authorship/stylometry, AI text detection, and generated text often asks whether text is human or machine, or whether authorship can be detected. This paper asks a DH validity question: what happens when human-authored literary text is rewritten and then analyzed as if it still carried the same authorial evidence?

### Paragraph 4: Research questions

Use explicit RQs:

**RQ1.** How much does LLM rewriting reduce authorship-attribution performance when models are trained on original passages and evaluated on rewritten passages?

**RQ2.** Do paraphrase, modernization, and simplification differ in their degree of stylometric degradation?

**RQ3.** Does the degradation pattern survive semantic-fidelity auditing and semantic-risk sensitivity analysis?

**RQ4.** Does a free-model replication show the same general pattern, or does the effect vary by model and rewrite condition?

### Paragraph 5: Contribution statement

Three contributions:

1. Empirical estimate of rewrite-induced stylometric degradation across paraphrase, modernization, and simplification.
2. Semantic-fidelity audit as a validity layer for rewrite-based DH experiments.
3. Semantic-risk sensitivity analysis and free-model replication to avoid overclaiming from a single pipeline.

### Paragraph 6: Paper map

Give brief section overview. Keep it short.

---

## 2. Related work [1300-1600 words]

### 2.1 Stylometry and authorship as computational evidence

Goal: establish that stylometry is not just classification; it is a way of treating linguistic regularities as evidence for authorial attribution and style-sensitive literary inference.

Must include:

- authorship attribution tradition;
- function words, character n-grams, punctuation, lexical features;
- distinction between interpretive evidence and black-box prediction;
- why macro-F1 is appropriate for balanced multi-author evaluation.

**Transition sentence:**

> If stylometric evidence depends on recurring distributions of surface and low-level linguistic features, then any systematic rewriting operation must be treated as an intervention on the evidence itself.

### 2.2 Text transformation, normalization, and the fragility of style

Goal: connect LLM rewriting to older DH concerns: normalization, modernization, translation, OCR correction, editing, and preprocessing.

Argue that transformation is common but not neutral.

Do not claim LLM rewriting is identical to normalization; claim it intensifies a known methodological problem.

### 2.3 LLM rewriting, generated text, and authorial signal

Goal: position the paper beside LLM-generated-text and AI authorship studies without becoming an AI-detection paper.

Key distinction:

- AI-detection asks: is this text machine-generated?
- This paper asks: after machine rewriting, how much authorial signal from the source remains usable?

### 2.4 Semantic fidelity as a validity condition

Goal: prepare the reader for the audit.

Argument:

A performance drop after rewriting is ambiguous unless semantic drift is checked. If meaning changes severely, attribution loss could reflect content corruption. If meaning remains broadly preserved and degradation persists, the stronger interpretation is that stylistic evidence has been attenuated.

End Related Work with the gap:

> What is missing is a validity-oriented DH experiment that combines stylometric degradation, semantic-fidelity auditing, and sensitivity analysis within a single controlled rewrite design.

---

## 3. Materials and methods [2200-2600 words]

### 3.1 Corpus and source texts

Use source-text documentation and copyright register.

Required facts:

- six authors;
- twelve works;
- 360 selected source passages;
- 1440 master rows after original + three rewrite conditions;
- 30 selected passages per work;
- Project Gutenberg source texts;
- non-US copyright status is jurisdiction-dependent.

**Table callout:**

> Table S1 reports the source-text register, including Project Gutenberg identifiers, URLs, selected passage counts, and reuse notes.

### 3.2 Rewrite conditions

Define:

- original;
- paraphrase;
- modernize;
- simplify.

Do not over-describe prompts unless final prompt text is available. State that the design treats rewrite condition as the experimental intervention.

### 3.3 Stylometric feature representation

Introduce feature vector notation.

Equation 1:

\[
\mathbf{x}_i = (x_{i1}, x_{i2}, \ldots, x_{ip})
\]

Where \(\mathbf{x}_i\) is the stylometric feature vector for text row \(i\), and \(p\) is the number of feature columns.

Explain feature families if available: lexical, function-word, character n-gram, punctuation, readability/surface features. Avoid claiming interpretability for every feature.

### 3.4 Train-on-original/test-on-rewrite design

State clearly:

- models trained only on original-condition training passages;
- scaler fit only on original training passages;
- evaluated on validation/test original and rewrite conditions;
- primary test split is the main inferential focus.

Equation 2:

\[
\mathcal{D}_{train}=\{(\mathbf{x}_i,y_i): c_i=\mathrm{original}, s_i=\mathrm{train}\}
\]

Equation 3:

\[
\mathcal{D}_{eval}(c,s)=\{(\mathbf{x}_i,y_i): c_i=c, s_i=s\}
\]

### 3.5 Authorship classifiers

Describe models without textbook overkill:

- nearest centroid;
- diagonal Gaussian naive Bayes;
- shrinkage linear discriminant analysis.

Reason for using three models:

> The aim is not to maximize leaderboard accuracy but to test whether degradation is stable across simple, inspectable attribution models.

### 3.6 Evaluation metric and degradation estimate

Equation 4: Macro-F1.

\[
\mathrm{MacroF1}=\frac{1}{K}\sum_{k=1}^{K}F1_k
\]

Equation 5: degradation.

\[
\Delta \mathrm{F1}_{m,c,s}=\mathrm{MacroF1}_{m,\mathrm{original},s}-\mathrm{MacroF1}_{m,c,s}
\]

Explain:

- \(m\) = classifier;
- \(c\) = rewrite condition;
- \(s\) = split;
- positive \(\Delta\) means degradation.

### 3.7 Bootstrap uncertainty

Explain passage-level paired bootstrap:

- resample paired original/rewrite passage IDs within model/split/condition;
- recompute macro-F1 loss;
- 5000 replicates;
- report 2.5th and 97.5th percentiles.

Equation 6:

\[
CI_{95\%}(\Delta \mathrm{F1}) = [Q_{0.025}(\Delta^*), Q_{0.975}(\Delta^*)]
\]

Where \(\Delta^*\) is the bootstrap loss distribution.

### 3.8 Semantic-fidelity audit

State:

- 108-item audit sample;
- balanced by author/work/condition;
- fields: added facts, omitted facts, narrative order, speaker/character relation, tone drift, meaning preservation, usable yes/no;
- single-review audit, not independent double annotation.

**Safe limitation sentence in Methods:**

> Because the completed packets contain identical selected choices, the audit is treated as a structured single-review semantic check rather than an independent double-annotation study.

### 3.9 Semantic-risk sensitivity analysis

Use exact phrase: semantic-risk sensitivity.

Define filters:

- all rows;
- exclude_unusable;
- exclude_any_semantic_issue.

Equation 7:

\[
\Delta \mathrm{F1}_{m,c,s}^{strict}=\mathrm{MacroF1}_{m,\mathrm{original},s}-\mathrm{MacroF1}_{m,c,s\mid semantic\ pass}
\]

### 3.10 Groq free-model replication

State scope:

- Llama 3.3 70B;
- Qwen 32B;
- GPT-OSS 120B;
- 360 rewrites per model;
- 1080 total free-model rewrites;
- robustness evidence, not replacement for frozen core experiment.

Caution:

> The replication is interpreted as model-heterogeneity evidence rather than as a claim of universal effect size.

### 3.11 Reproducibility and availability

Point to GitHub repository, manifests, scripts, generated tables, and source register.

Mention Data Availability and AI Disclosure will appear at end.

---

## 4. Results [1800-2200 words]

### 4.1 Primary original-to-rewrite degradation

Open with the main finding in one sentence.

> Across all three attribution models and all three rewrite conditions, test-set macro-F1 was lower for rewritten passages than for original passages.

**Table callout:**

> Table 1 reports test-set macro-F1 losses with passage-level paired bootstrap confidence intervals.

Use exact numbers from Table 1.

Important: mention CIs, not just losses.

> The smallest lower bound across primary test comparisons is 0.050751, and the largest nonpositive bootstrap rate is 0.001800.

**Figure callout:**

> Figure 1 visualizes the macro-F1 loss for each classifier-condition pair.

### 4.2 Semantic-fidelity audit

**Table callout:**

> Table 2 summarizes the semantic-fidelity audit.

Report:

- 107/108 usable;
- mean preservation 4.527778/5;
- 17 semantic issue flags;
- no narrative-order or speaker/character relation changes.

Interpret carefully:

> The audit supports the usability of the rewrite set but should not be treated as a definitive semantic gold standard.

### 4.3 Semantic-risk sensitivity

**Table callout:**

> Table 4 reports nearest-centroid test results under semantic-risk filters.

Key result:

- exclude_unusable unchanged;
- exclude_any_semantic_issue still positive;
- strict-filter non-positive losses = 0;
- minimum strict test loss = 0.170812.

This is the validity bridge.

### 4.4 Groq free-model replication

**Table callout:**

> Table 3 reports free-model replication results.

Report support and heterogeneity:

- Qwen positive across all conditions;
- GPT-OSS positive across all conditions;
- Llama positive for paraphrase/simplify, reversal for modernize;
- therefore supportive but not universal.

**Figure callout:**

> Figure 2 shows Groq transfer losses by model and rewrite condition.

### 4.5 Interim result summary

End Results with a synthesis paragraph:

> The primary, uncertainty, semantic-fidelity, semantic-risk, and replication analyses converge on a cautious conclusion: LLM rewriting tends to attenuate authorship signal, and this attenuation is not eliminated by semantic-risk filtering. However, the size and direction of the effect vary by rewrite condition and model.

---

## 5. Discussion [1300-1600 words]

### 5.1 Main interpretation

The paper’s key interpretive claim:

> LLM rewriting can preserve broad semantic usability while weakening the stylometric evidence used for authorial attribution.

Explain why this matters for DH.

### 5.2 Why semantic preservation is not stylistic preservation

Develop the central conceptual distinction:

- semantic fidelity = broad meaning preserved;
- stylistic fidelity = distributions of features remain author-linked;
- the paper shows these can diverge.

### 5.3 Implications for DH workflows

Discuss:

- AI-assisted simplification;
- modernization;
- pedagogical rewriting;
- corpus normalization;
- style-sensitive computational analysis;
- warning against treating rewritten texts as originals.

### 5.4 Implications for reporting standards

Argue future studies should report:

- rewrite prompts/model details;
- semantic-fidelity checks;
- sensitivity exclusions;
- uncertainty intervals;
- source-text provenance.

### 5.5 Model and condition heterogeneity

Use Groq result to avoid overclaiming.

Safe wording:

> The replication suggests that rewrite-induced degradation is a recurring but not uniform phenomenon.

---

## 6. Limitations [700-900 words]

Required limitations:

1. Single-review semantic-fidelity audit, not independent double annotation.
2. Six authors and twelve works; not all genres/languages/time periods.
3. Rewrite conditions limited to paraphrase, modernization, simplification.
4. Groq replication heterogeneous; Llama-modernize reversal.
5. Public-domain English-language literary texts only.
6. Macro-F1 attribution is one operationalization of authorial signal, not the whole of literary style.
7. Non-US copyright status is jurisdiction-dependent.

Do not hide limitations; make them sound like careful design boundaries.

---

## 7. Conclusion [350-500 words]

Do not introduce new numbers. Synthesize:

- LLM rewriting changes evidentiary status;
- authorship signal weakens under controlled rewriting;
- semantic usability does not guarantee stylometric equivalence;
- DH studies using AI-mediated texts need fidelity audits and sensitivity tests.

Final sentence candidate:

> For style-sensitive digital humanities, the relevant question is therefore not only whether an AI rewrite is readable or semantically adequate, but whether it remains evidentially equivalent to the text it replaces.

---

## Declarations and end matter

### Data availability

Use `docs/dsh_submission_endmatter_package.md`.

### Code availability

Point to GitHub repository and reproducibility manifests.

### AI Disclosure Statement

Disclose AI assistance in code drafting, documentation, and manuscript support; state that outputs, analyses, and interpretations were checked by the author.

### Ethics statement

No human-subjects research unless the semantic-fidelity reviewer is treated as human-subject data. Since only annotation of public-domain text was performed, state this cautiously.

### Funding

No funding unless changed.

### Conflict of interest

No conflict unless changed.

### Author contributions

Single-author CRediT-style statement unless co-authors are added.

---

## Tables and figures

### Main text tables

- **Table 1.** Core test-set original-to-rewrite macro-F1 loss with 95% paired bootstrap CIs.
- **Table 2.** Semantic-fidelity audit summary.
- **Table 3.** Groq free-model replication summary.
- **Table 4.** Semantic-risk sensitivity summary.

### Main text figures

- **Figure 1.** Core experiment macro-F1 loss by classifier and rewrite condition.
- **Figure 2.** Groq replication macro-F1 loss by model and rewrite condition.

### Supplementary tables

- **Table S1.** Source-text register.
- **Table S2.** Feature registry.
- **Table S3.** Full validation and test metrics.
- **Table S4.** Semantic-fidelity item-level flags.
- **Table S5.** Reproducibility manifest.

---

## Anti-overclaim rules for final drafting

Use:

- “attenuates authorial signal”
- “weakens stylometric evidence”
- “broadly supports”
- “semantic usability”
- “single-review audit”
- “model/condition heterogeneity”

Avoid:

- “destroys authorial style”
- “proves LLMs erase authorship”
- “human annotation study”
- “semantic fidelity was guaranteed”
- “all models show the same effect”
- “universal effect of LLM rewriting”

---

## Paper-writing order

1. Results section first, using Tables 1-4 and Figures 1-2.
2. Methods section second, matching every Results claim to a script/output.
3. Introduction third, after exact claims are known.
4. Related Work fourth, to position the already-fixed claim.
5. Discussion and Limitations fifth.
6. Abstract last.

