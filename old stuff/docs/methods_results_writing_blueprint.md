# Methods and Results Writing Blueprint for the DSH Manuscript

This document is a writing blueprint, not the manuscript itself. It fixes the biggest drafting risk: the paper must not read like a loose essay about AI and literature. It must read like a Digital Scholarship in the Humanities article with a clear humanities problem, a reproducible computational design, explicit validity checks, equations, tables, figures, and cautious interpretation.

## One-sentence writing rule

Every paragraph in Methods and Results must answer one of four questions:

1. What was measured?
2. How was it measured?
3. Why is that measurement valid for the research question?
4. What does the measurement show?

If a paragraph does not answer one of these, delete it or move it to Discussion.

## Core paper claim

The paper should not claim merely that classifiers lose accuracy after LLM rewriting. The stronger DSH claim is:

> LLM rewriting changes the evidentiary status of literary texts: passages can remain semantically usable while losing measurable authorial signal used by stylometric methods.

Everything in Methods and Results should support that claim.

## Recommended high-level manuscript structure

1. Introduction
2. Related Work
3. Materials and Methods
4. Results
5. Discussion
6. Limitations
7. Conclusion
8. Data availability, AI disclosure, ethics, funding, conflicts

The Methods and Results sections should carry the empirical weight of the paper. The Discussion should interpret, not introduce new measurements.

---

# 3. Materials and Methods blueprint

## 3.1 Corpus and source texts

### Purpose

Show that the corpus is legitimate, balanced, reproducible, and suitable for a stylometric experiment.

### Required content

- Six authors.
- Twelve works.
- Thirty selected passages per work.
- 360 unique passages.
- Four conditions per passage: original, paraphrase, modernize, simplify.
- 1,440 total modeling rows.
- Source texts from Project Gutenberg.
- Reuse/copyright caution: Project Gutenberg status is U.S.-focused and non-US copyright status is jurisdiction-dependent.

### Suggested wording pattern

Start with design, then provenance, then balance:

> The corpus was designed as a balanced authorship-attribution testbed rather than as a representative sample of all nineteenth-century prose. It contains six authors, two works per author, and thirty selected passages per work, producing 360 unique source passages. Each source passage appears in four conditions: the original passage and three LLM-mediated rewrites. This yields 1,440 modeling rows. Source texts were drawn from Project Gutenberg records documented in the project source register; because Project Gutenberg copyright status is U.S.-focused, non-US copyright status is jurisdiction-dependent and should not be generalized without local legal review.

### Table callout

Use **Table S1 or Appendix Table A1** for the source-text register. Do not overload the main paper with all twelve URLs unless the journal prefers this in the main article.

### Reviewer attack prevented

- “Where did the corpus come from?”
- “Is the corpus balanced?”
- “Are the source texts legally reusable?”
- “Is this reproducible?”

---

## 3.2 Rewrite conditions

### Purpose

Define the independent variable of the experiment.

### Required content

Define each condition operationally:

- `original`: unrewritten passage.
- `paraphrase`: semantically similar restatement without explicit modernization or simplification target.
- `modernize`: rewriting toward more contemporary wording while preserving content.
- `simplify`: rewriting toward easier language while preserving content.

### Good wording

> The three rewrite conditions were selected because they represent common forms of AI-mediated textual transformation: paraphrase, modernization, and simplification. These operations are not interchangeable. Paraphrase may preserve meaning while changing lexical and syntactic realization; modernization may replace historical diction with contemporary wording; simplification may reduce syntactic complexity and compress stylistic variation. Treating them as separate conditions allows the analysis to distinguish rewrite type from the general fact of AI mediation.

### Avoid

Do not write:

> We asked the AI to rewrite the texts and then checked accuracy.

That sounds casual and under-specified.

### Table/Figure callout

Use a small table defining the four text conditions if space allows:

| condition | operational meaning | reason for inclusion |
|---|---|---|
| original | source passage | baseline authorial signal |
| paraphrase | meaning-preserving restatement | general LLM rewriting |
| modernize | contemporary-language rewrite | historical-text mediation |
| simplify | easier-language rewrite | accessibility/pedagogical mediation |

---

## 3.3 Stylometric feature representation

### Purpose

Explain what the classifier sees without drowning the reader in implementation details.

### Required content

- Each text is represented as a stylometric feature vector.
- Features should be described by families if the full list is long.
- Mention normalization/scaling if used.
- Explain that features are style-sensitive proxies, not direct measurements of literary value.

### Equation 1: feature vector

Use this equation early in Methods:

\[
\mathbf{x}_{i,c} = (x_{i,c,1}, x_{i,c,2}, \ldots, x_{i,c,p})
\]

where \(i\) indexes passage, \(c\) indexes condition, and \(p\) is the number of stylometric features.

### Suggested wording

> Each text instance was represented as a stylometric vector \(\mathbf{x}_{i,c}\), where \(i\) denotes the source passage and \(c\) denotes the text condition. The feature vector encodes surface and distributional properties of the passage rather than semantic labels. This is important because the experiment asks whether rewriting changes the measurable stylistic evidence available to attribution models.

### Reviewer attack prevented

- “What exactly is being classified?”
- “Are you measuring meaning or style?”
- “Why is this a stylometry paper rather than a generic classification paper?”

---

## 3.4 Train/test design

### Purpose

Show that the design isolates transfer from original style to rewritten style.

### Required content

- Models train on original passages only.
- Evaluation occurs on held-out original and held-out rewritten passages.
- The training distribution is not contaminated by rewrites.
- Loss is measured relative to original-condition test performance.

### Key wording

> The central design is train-on-original, test-on-rewrite. This design asks whether a model trained on original authorial style transfers to AI-mediated versions of the same authors. It avoids training the model to recognize the rewrite style itself.

### Equation 2: training set

\[
\mathcal{D}_{train} = \{(\mathbf{x}_{i,original}, y_i): i \in I_{train}\}
\]

### Equation 3: evaluation set

\[
\mathcal{D}_{eval,c} = \{(\mathbf{x}_{i,c}, y_i): i \in I_{eval}\}, \quad c \in \{original, paraphrase, modernize, simplify\}
\]

### Figure callout

Use a schematic figure if possible:

**Figure 1. Experimental design.** Original passages are used for training; held-out originals and rewrites are used for evaluation. Arrows should show that the model never trains on rewritten passages in the primary analysis.

### Anti-essay rule

Do not spend more than one paragraph defending why authorship attribution matters. That belongs in Introduction/Related Work. Methods should be procedural and exact.

---

## 3.5 Authorship classifiers

### Purpose

Show that the result is not one-model fragility.

### Required content

Mention the three classifiers used:

- nearest centroid
- diagonal Gaussian naive Bayes
- shrinkage linear discriminant analysis

Explain why these are appropriate:

- transparent baselines
- low-complexity
- interpretable enough for humanities-methods work
- avoids relying on a black-box classifier as the only evidence

### Suggested wording

> The analysis uses three comparatively transparent attribution models rather than a single high-capacity classifier. This choice is deliberate: the study is concerned with the stability of stylometric evidence under rewriting, not with maximizing benchmark performance. Agreement across simple classifiers provides stronger methodological evidence than an isolated result from one complex model.

### Optional compact model descriptions

Nearest centroid:

\[
\hat{y}(\mathbf{x}) = \arg\min_k \lVert \mathbf{x} - \boldsymbol{\mu}_k \rVert_2^2
\]

where \(\boldsymbol{\mu}_k\) is the centroid for author \(k\).

Macro-F1 is enough for the main metric. Avoid turning the paper into a machine-learning textbook.

---

## 3.6 Primary outcome metric

### Purpose

Define the dependent variable clearly.

### Equation 4: macro-F1

\[
\mathrm{MacroF1}=\frac{1}{K}\sum_{k=1}^{K}F1_k
\]

### Equation 5: rewrite degradation

\[
\Delta \mathrm{F1}_{c} = \mathrm{MacroF1}_{original} - \mathrm{MacroF1}_{c}
\]

where \(c\) is one of paraphrase, modernization, or simplification.

### Required interpretation sentence

> A positive \(\Delta \mathrm{F1}_{c}\) means that author attribution is weaker under rewrite condition \(c\) than under original-condition evaluation.

### Why macro-F1

Use this rationale:

> Macro-F1 weights authors equally and is therefore appropriate for a balanced authorship setting in which the unit of interest is not merely aggregate accuracy but author-level attribution stability.

---

## 3.7 Bootstrap uncertainty

### Purpose

Make the results publishable, not just descriptive.

### Required content

- Passage-level paired bootstrap.
- 5,000 replicates.
- Resampling over paired original/rewrite passage IDs.
- 95% percentile interval.
- Report nonpositive bootstrap rate.

### Equation 6: bootstrap loss

For bootstrap replicate \(b\):

\[
\Delta \mathrm{F1}_{c}^{(b)} = \mathrm{MacroF1}_{original}^{(b)} - \mathrm{MacroF1}_{c}^{(b)}
\]

The 95% interval is:

\[
\left[Q_{0.025}(\Delta \mathrm{F1}_{c}^{(b)}), Q_{0.975}(\Delta \mathrm{F1}_{c}^{(b)})\right]
\]

### Suggested wording

> To avoid reporting point estimates alone, uncertainty was estimated with a paired passage-level bootstrap. For each model, split, and rewrite condition, passage IDs shared by the original and rewritten condition were resampled with replacement. Macro-F1 loss was recomputed for 5,000 bootstrap replicates, and the 2.5th and 97.5th percentiles were reported as the confidence interval. The bootstrap is paired because the original and rewritten versions correspond to the same source passage.

### Results table callout

Table 1 must include:

- original macro-F1
- rewrite macro-F1
- absolute macro-F1 loss
- 95% CI
- nonpositive bootstrap rate

---

## 3.8 Semantic-fidelity audit

### Purpose

Prevent the reviewer from saying: “Your classifier dropped because the LLM changed the story, not the style.”

### Required content

- 108 audited rows.
- Balanced audit sample.
- Codes: added facts, omitted facts, narrative-order change, speaker/character-relation change, tone drift, meaning preservation, usability.
- 107/108 usable.
- Mean preservation 4.53/5.
- Explicit limitation: single-review audit, not independent double annotation.

### Equation 7: usability rate

\[
\mathrm{UsabilityRate}=\frac{N_{usable}}{N_{audit}}
\]

### Suggested wording

> Semantic fidelity was treated as a validity condition rather than as a secondary quality note. A rewrite that changes plot facts, character relations, or narrative order may produce attribution loss for reasons unrelated to stylistic mediation. The audit therefore records semantic-risk indicators and supports a sensitivity analysis that removes flagged rows.

### Must-have caution sentence

> Because the semantic-fidelity review is a structured single-review audit rather than independent double annotation, it is used as a validity screen and not as a definitive semantic gold standard.

Do not omit this. It makes the paper more honest and less vulnerable.

---

## 3.9 Semantic-risk sensitivity analysis

### Purpose

Show that the core result survives semantic-risk filtering.

### Required content

Three filters:

1. all rows
2. exclude the single unusable row
3. exclude all semantic-issue rows

### Equation 8: strict semantic-risk loss

\[
\Delta \mathrm{F1}_{c,strict} = \mathrm{MacroF1}_{original} - \mathrm{MacroF1}_{c \mid semantic\ pass}
\]

### Required interpretation

> If losses remain positive under the strict semantic-risk filter, the degradation pattern cannot be attributed solely to the audited semantically risky rewrites.

### Table callout

Use **Table 4** or a supplement table. The main text should report only the key values:

- strict-filter nonpositive losses = 0
- minimum strict test macro-F1 loss = 0.170812
- maximum rows excluded in a cell = 2

---

## 3.10 Cross-model/free-model replication

### Purpose

Show robustness without overclaiming universality.

### Required content

- Groq-hosted Llama, Qwen, GPT-OSS.
- 360 rewrites per model.
- Qwen and GPT-OSS broadly support positive transfer loss.
- Llama-modernize reverses.
- Treat as heterogeneity, not failure.

### Suggested wording

> The free-model replication is interpreted as robustness evidence rather than as a replacement for the frozen core experiment. Its purpose is to test whether the primary degradation pattern is specific to one generation setting. The replication broadly supports the pattern but also shows model-condition heterogeneity, especially the Llama-modernize reversal.

### Avoid

Do not write:

> All models prove our hypothesis.

Correct wording:

> The replication broadly supports the degradation claim while showing that effect direction and magnitude vary by model and rewrite condition.

---

# 4. Results blueprint

## Results writing principle

Results should be written from strongest validated claim to weaker supporting evidence:

1. Primary test degradation with CIs.
2. Semantic-fidelity audit.
3. Semantic-risk sensitivity.
4. Groq replication.
5. Short transition to Discussion.

Do not start Results with corpus description. That belongs in Methods.

---

## 4.1 Primary original-to-rewritten degradation

### Paragraph 1: headline result

Must state:

- all three rewrite conditions reduce test macro-F1
- all three classifiers show positive losses
- Table 1 contains CIs

Suggested wording:

> The primary test results show consistent original-to-rewrite degradation across rewrite conditions and classifiers. For all three classifiers, paraphrase, modernization, and simplification produce lower macro-F1 than original-condition evaluation. Passage-level paired bootstrap intervals support the direction of the effect: all primary test-set 95% confidence intervals have positive lower bounds.

### Paragraph 2: nearest-centroid values

Report one classifier in detail:

- original = 0.776931
- paraphrase = 0.395797, loss = 0.381134, CI [0.261805, 0.502832]
- modernize = 0.560720, loss = 0.216211, CI [0.099657, 0.346396]
- simplify = 0.463636, loss = 0.313294, CI [0.193906, 0.448514]

### Paragraph 3: classifier robustness

Mention other classifiers compactly.

Do not repeat all table values in prose.

### Table callout

**Table 1. Original-to-rewritten attribution degradation on the test split.**

Columns:

- classifier
- condition
- original macro-F1
- rewrite macro-F1
- loss
- 95% CI
- nonpositive bootstrap rate

---

## 4.2 Semantic-fidelity audit

### Paragraph 1: audit headline

> The semantic-fidelity audit indicates that the rewrite sample is mostly usable but not semantically perfect.

Report:

- 108 audited rows
- 107 usable
- mean preservation = 4.527778/5
- 17 semantic-issue flags

### Paragraph 2: condition-level differences

- modernize has lowest semantic-issue rate: 8.3%
- paraphrase and simplify: 19.4% each
- paraphrase has lower mean preservation than modernize/simplify

### Table callout

**Table 2. Semantic-fidelity audit summary by rewrite condition.**

### Required caution

End the subsection with:

> Because the audit is a structured single-review check, these results are interpreted as a validity screen rather than as definitive semantic annotation.

---

## 4.3 Semantic-risk sensitivity

### Paragraph 1: why this matters

> The semantic-fidelity audit identifies a small set of semantically risky rows. The sensitivity analysis asks whether the primary attribution losses depend on those rows.

### Paragraph 2: key result

Report:

- excluding unusable row changes nothing in nearest-centroid test focus
- excluding all semantic-issue rows leaves losses positive
- strict-filter nonpositive losses = 0
- minimum strict test loss = 0.170812

### Table callout

**Table 4. Semantic-risk sensitivity for nearest-centroid test results.**

### Strong sentence

> The degradation pattern therefore survives the strongest semantic-risk exclusion used in this study.

---

## 4.4 Groq replication

### Paragraph 1: supportive but heterogeneous

Report:

- Qwen: all positive losses
- GPT-OSS: all positive losses
- Llama: paraphrase and simplify positive, modernize reversed

### Required caution

> The replication should be read as robustness evidence with heterogeneity, not as a universal model-independent law.

### Table callout

**Table 3. Free-model Groq replication summary.**

---

# Table and figure plan

## Main tables

### Table 1: Core transfer test results with bootstrap CIs

Must be in main paper.

### Table 2: Semantic-fidelity audit summary

Must be in main paper or near main paper because it protects validity.

### Table 3: Groq replication summary

Can be main paper if space allows; otherwise supplementary.

### Table 4: Semantic-risk sensitivity

Can be main paper if concise; otherwise supplementary with key values in prose.

## Main figures

### Figure 1: Experimental design schematic

Purpose: make Methods instantly understandable.

### Figure 2: Core macro-F1 loss bar chart

Purpose: show degradation across classifier × condition.

### Figure 3: Semantic-fidelity/sensitivity flow

Purpose: show 108 audited rows -> 107 usable -> 17 issue flags -> strict-filter losses remain positive.

### Figure 4: Groq replication heatmap/bar chart

Purpose: show robustness and heterogeneity.

Use figures for structure and effect patterns, not decoration.

---

# Equation placement plan

Do not dump all equations in one block. Place them exactly where the concept is introduced.

1. Feature vector equation: Methods 3.3.
2. Train/eval set equations: Methods 3.4.
3. Macro-F1 equation: Methods 3.6.
4. Degradation equation: Methods 3.6.
5. Bootstrap equation: Methods 3.7.
6. Usability rate equation: Methods 3.8.
7. Strict semantic-risk loss equation: Methods 3.9.

Equations should be used to clarify design, not to make the paper look technical artificially.

---

# Anti-weakness rules

## Do not overclaim

Bad:

> LLMs erase authorial style.

Better:

> LLM rewriting attenuates the stylometric evidence available to attribution models in this experimental setting.

## Do not pretend semantic annotation is stronger than it is

Bad:

> Human annotators confirmed semantic preservation.

Better:

> A structured single-review semantic-fidelity audit found high usability and meaning preservation; this is treated as a validity screen rather than independent double annotation.

## Do not hide heterogeneity

Bad:

> The Groq replication confirms the effect across all free models.

Better:

> The Groq replication broadly supports the effect while showing model-condition heterogeneity, including a Llama-modernize reversal.

## Do not write Results like Discussion

Bad:

> This shows that AI is changing literature forever.

Better:

> The result indicates that rewrite-mediated texts are not analytically interchangeable with originals for style-sensitive attribution tasks.

---

# Manuscript-ready Methods mini-outline

Use this order almost exactly:

1. Corpus and source texts
2. Rewrite conditions
3. Feature representation
4. Train-on-original evaluation design
5. Authorship classifiers
6. Primary degradation metric
7. Bootstrap uncertainty
8. Semantic-fidelity audit
9. Semantic-risk sensitivity analysis
10. Free-model replication
11. Reproducibility and implementation

---

# Manuscript-ready Results mini-outline

Use this order almost exactly:

1. Primary attribution degradation with CIs
2. Semantic-fidelity audit results
3. Semantic-risk sensitivity results
4. Groq replication results
5. Brief synthesis paragraph

---

# Final Results synthesis paragraph template

> Taken together, the results support the paper's central claim. LLM rewriting reduces authorship-attribution performance across paraphrase, modernization, and simplification. The effect is not removed by semantic-fidelity filtering: most audited rewrites remain usable, and strict semantic-risk exclusions leave all test rewrite losses positive. The free-model replication further supports the degradation pattern while showing that effect size varies by model and condition. These findings indicate that LLM-mediated texts may remain semantically usable while becoming stylometrically less interchangeable with their originals.

---

# What the final paper must prove

By the end of Results, a skeptical DSH reviewer should believe four things:

1. The corpus is balanced and reproducible.
2. The attribution degradation is real and statistically supported.
3. The degradation is not explained away by obvious semantic corruption.
4. The paper understands its limits and does not overclaim.

If the Methods and Results sections achieve these four things, the paper has a real chance of crossing the threshold from student project to publishable computational humanities article.
