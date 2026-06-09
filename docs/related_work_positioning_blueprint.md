# Related Work and Positioning Blueprint for a DSH Submission

Working title: **Rewriting the Author: Semantic Fidelity and Stylometric Degradation under Large Language Model Paraphrase, Modernization, and Simplification**

This document fixes a major manuscript weakness: the paper must not read like an isolated ML experiment. For *Digital Scholarship in the Humanities* (DSH), the Related Work section must show that the paper understands computational authorship studies, digital-humanities evidence standards, LLM-mediated textual transformation, and the interpretive risk of using rewritten texts as if they were originals.

---

## 1. The job of the Related Work section

The Related Work section should not be a chronological literature survey. It should build the exact gap that this paper fills.

The section must move through four layers:

1. **Stylometry as authorial evidence in digital humanities.**
   Establish that authorship attribution and stylometric analysis are established DH methods, especially when style is represented through repeated lexical, character, punctuation, function-word, or distributional patterns.

2. **Text transformation as a threat to authorial evidence.**
   Establish that paraphrase, obfuscation, translation, modernization, normalization, and similar interventions can preserve broad meaning while weakening stylistic features.

3. **LLMs as large-scale mediators of textual form.**
   Establish that LLMs make rewriting cheap, fluent, and culturally widespread. This changes the practical risk: rewritten texts can enter teaching, archives, summaries, editions, and downstream analysis pipelines.

4. **The missing validity layer: semantic fidelity plus sensitivity analysis.**
   Show that many studies either measure stylometric performance or evaluate generation quality, but fewer pair attribution degradation with explicit semantic-fidelity auditing and semantic-risk sensitivity checks.

The resulting gap should be worded as:

> Existing work shows that authorship signals can be measured, that stylistic obfuscation can weaken attribution, and that LLM-generated or LLM-mediated text has detectable stylistic regularities. What remains under-tested in a digital-humanities setting is whether common meaning-preserving LLM rewrite operations—paraphrase, modernization, and simplification—attenuate authorial signal in literary passages while preserving enough semantic fidelity for the rewrite to remain textually usable.

---

## 2. DSH-specific framing constraints

DSH is not the place for a pure model benchmark. The paper must be framed as a contribution to digital-humanities method.

### Required DSH-facing moves

- Treat the computational model as an instrument for studying textual mediation, not as the object of the paper.
- Use equations sparingly but clearly: macro-F1, loss vs original, semantic-risk filtered loss, and possibly distance ratio.
- Put the humanities concern before the technical pipeline: rewritten texts change evidentiary status.
- Keep claims cautious: the paper studies controlled English literary passages and three rewrite conditions, not all AI rewriting.
- Include Data Availability and AI Disclosure sections.
- Include alt text for all figures.

### Submission constraints to remember

DSH full papers should normally not exceed 9,000 words, excluding notes and references. The journal requests separate figure/artwork files and asks for at least 300 dpi artwork. DSH also requires a Data Availability statement and an AI Disclosure Statement when generative or other AI/ML tools were used in manuscript preparation or research work.

---

## 3. Recommended Related Work structure

Use four subsections. Do not use more than four unless the section becomes too dense.

### 2.1 Stylometry and authorship as computational evidence

Purpose: establish that authorial signal is a legitimate DH object.

Core points to make:

- Stylometry operationalizes style through measurable textual features.
- In authorship attribution, the key assumption is that some features vary more by author than by topic, edition, or random passage variation.
- Traditional stylometric work often emphasizes high-frequency, relatively topic-independent signals such as function words, character n-grams, punctuation, and distributional patterns.
- Authorship attribution is not only a forensic problem; in DH it is also a way to study textual transmission, collaboration, disputed attribution, and the computational status of authorial style.

Suggested wording:

> Stylometric authorship attribution treats style as a distributional pattern rather than as a set of isolated expressive choices. In digital-humanities work, this has made authorship attribution useful not only for disputed authorship but also for examining textual transmission, collaboration, and the statistical stability of authorial signatures. The present study adopts this evidentiary view of style: if an authorship model trained on original passages performs substantially worse on rewritten passages, the rewrite has altered the measurable relation between passage and author.

Sources to cite here:

- Burrows, John. 2002. “Delta: A Measure of Stylistic Difference and a Guide to Likely Authorship.” *Literary and Linguistic Computing*.
- Juola, Patrick. 2006/2008. Authorship attribution surveys/monograph.
- Stamatatos, Efstathios. 2009. “A Survey of Modern Authorship Attribution Methods.”
- Eder, Maciej; Rybicki, Jan; Kestemont, Mike. 2016. “Stylometry with R: A Package for Computational Text Analysis.”
- Segarra, Santiago; Eisen, Mark; Ribeiro, Alejandro. 2015/2017. Function-word adjacency networks.

How to connect to our paper:

> Our classifiers are not presented as the newest authorship-attribution models. They are deliberately interpretable baselines used to test whether LLM rewriting changes the transferability of authorial signal from original texts to rewritten texts.

Avoid:

- Do not claim to improve authorship attribution.
- Do not claim stylometry perfectly captures style.
- Do not overuse “fingerprint”; use “signal,” “evidence,” or “distributional trace.”

---

### 2.2 Text transformation, obfuscation, and the fragility of style

Purpose: show that the paper is related to adversarial stylometry but different from it.

Core points:

- Authorship obfuscation/adversarial stylometry studies deliberately try to preserve meaning while reducing attribution accuracy.
- This literature is highly relevant because it proves the conceptual possibility that meaning and authorial style can diverge.
- Our paper differs because it does not study privacy attack success or deliberate anonymization. It studies common non-adversarial rewrite operations that may occur in DH, pedagogy, accessibility, or AI-mediated editing.

Suggested wording:

> Work on adversarial stylometry has already shown that stylistic evidence can be deliberately weakened while preserving enough content for a text to remain readable. The present study borrows the conceptual distinction between semantic preservation and stylistic masking, but shifts the setting from adversarial anonymity to ordinary LLM-mediated rewriting. Paraphrase, modernization, and simplification are not necessarily attacks, yet they may produce the same methodological consequence: a text that remains meaningful to a reader but becomes less reliable as evidence of authorial style.

Sources to cite here:

- Brennan, Michael; Afroz, Sadia; Greenstadt, Rachel. 2012. “Adversarial Stylometry: Circumventing Authorship Recognition to Preserve Privacy and Anonymity.”
- Potthast, Martin; Hagen, Matthias; Stein, Benno. 2016. “Author Obfuscation: Attacking the State of the Art in Authorship Verification.”
- Mahmood, Asad; Shafiq, Zubair; Srinivasan, Padmini. 2020. “A Girl Has A Name: Detecting Authorship Obfuscation.”
- Zhai, Wanyue et al. 2022. adversarial authorship attribution/deobfuscation.
- Gröndahl, Tommi; Asokan, N. 2020. adversarial settings survey.

Bridge sentence:

> The novelty here is not that style can be masked, but that routine LLM rewrite operations can create a comparable evidentiary problem in humanities workflows where no explicit adversary is present.

Avoid:

- Do not frame the paper as cybersecurity unless discussing obfuscation literature.
- Do not say LLM rewriting is “the same as” adversarial stylometry; say it is methodologically adjacent.

---

### 2.3 LLMs, generated text, and authorial style

Purpose: show that the paper belongs to the current AI-text moment without becoming a generic AI-detection paper.

Core points:

- LLMs generate fluent text and can rewrite existing text at scale.
- Prior work has asked whether generated text has detectable model-specific style, whether LLMs mimic human style, and whether stylometry can separate human from machine text.
- Our paper asks a different question: what happens to the source author’s signal after LLM rewriting?

Suggested wording:

> Recent work on neural and LLM authorship has often focused on detecting machine-generated text or attributing text to the model that produced it. That question is important, but it differs from the present one. In a rewrite setting, the output is neither simply human-authored nor simply machine-authored; it is a mediated text derived from a human source passage. The relevant question is therefore not only whether the LLM leaves its own signature, but whether the source author’s signature survives the transformation.

Sources to cite here:

- Manjavacas, Enrique; de Gussem, Jeroen; Daelemans, Walter; Kestemont, Mike. 2017. “Assessing the Stylistic Properties of Neurally Generated Text in Authorship Attribution.”
- Kumarage, Tharindu; Liu, Huan. 2023. “Neural Authorship Attribution: Stylometric Analysis on Large Language Models.”
- Przystalski, Karol et al. 2025. “Stylometry recognizes human and LLM-generated texts in short samples.”
- Huang, Weihang; Murakami, Akira; Grieve, Jack. 2024. “Authorial Language Models for Authorship Attribution.”
- Optional, if needed: recent LLM mimicry/stylometric papers, but use cautiously if only available as preprints.

Bridge sentence:

> Our work therefore treats LLM rewriting as a problem of authorial-signal transfer: the passage originates with a human author, but the surface form has been transformed by a model.

Avoid:

- Do not make the paper about AI-generated text detection.
- Do not claim LLMs have a stable “style” unless supported by cited evidence.
- Do not over-cite generic AI papers that are not about text/style/provenance.

---

### 2.4 Semantic fidelity as a validity condition

Purpose: introduce the most important originality move.

Core points:

- A rewrite experiment is invalid if attribution loss is caused mainly by changed content.
- Semantic preservation cannot be assumed from fluency.
- Therefore, semantic-fidelity auditing is not a side note; it is necessary for interpreting stylometric degradation.
- Sensitivity analysis after excluding semantically risky rows converts a reviewer objection into a strength.

Suggested wording:

> A central difficulty in studying rewritten text is that style and meaning are not independently observable. If a rewrite changes narrative facts, speaker relations, or event structure, then attribution loss may reflect content distortion rather than stylistic attenuation. For that reason, the present study treats semantic fidelity as a validity condition. The semantic-fidelity audit does not prove perfect preservation, but it makes the interpretation falsifiable: if the degradation disappears after semantically risky rows are removed, the stylometric claim is weak; if it persists, the claim is strengthened.

This paragraph should appear near the end of Related Work and lead directly to the research questions.

Strong novelty sentence:

> The paper’s main methodological contribution is this pairing of stylometric degradation with semantic-fidelity auditing and semantic-risk sensitivity analysis.

Avoid:

- Do not pretend semantic fidelity was double-annotated.
- Do not say the audit proves meaning preservation absolutely.
- Do not hide the single-review limitation; name it and then show sensitivity analysis.

---

## 4. Final Related Work closing paragraph

Use something close to this:

> Taken together, these literatures establish three premises: stylometric methods can measure authorial signal; textual transformation can weaken that signal while preserving meaning; and LLMs now make fluent rewriting routine. What they do not yet fully establish is how common LLM rewrite operations affect authorial evidence in literary passages under a design that also checks semantic fidelity. This study addresses that gap by measuring original-to-rewrite attribution degradation, auditing the semantic usability of sampled rewrites, and testing whether the effect survives after semantically risky rows are excluded.

---

## 5. Research questions after Related Work

Use research questions immediately after the Related Work section or at the end of the Introduction.

Recommended wording:

**RQ1.** To what extent do LLM paraphrase, modernization, and simplification reduce authorship-attribution performance when models are trained on original literary passages and evaluated on rewritten passages?

**RQ2.** Are observed attribution losses robust across multiple transparent classifiers rather than dependent on a single model family?

**RQ3.** Do the observed losses persist after excluding rewrites marked as semantically unusable or semantically risky?

**RQ4.** Do free-model cross-provider replications reproduce the same degradation pattern, or do model and condition effects remain heterogeneous?

Do not add too many RQs. Four is the upper limit.

---

## 6. Where equations belong

Do not put equations in Related Work. Put them in Methods.

Recommended equations:

1. Macro-F1:

```text
MacroF1 = (1/K) * sum_{k=1}^{K} F1_k
```

2. Rewrite degradation:

```text
DeltaF1_c = MacroF1_original - MacroF1_c
```

3. Semantic-risk filtered degradation:

```text
DeltaF1_{c,S} = MacroF1_original - MacroF1_{c | S}
```

where `S` is the retained subset after semantic-risk filtering.

4. Optional distance-ratio equation:

```text
R_c = D_between,c / D_between,original
```

Use only if the final paper still includes distance-contraction analysis prominently.

---

## 7. Figure/table plan for Related Work alignment

The Related Work should prefigure the Results structure. Mention that the paper evaluates three evidentiary layers:

- **Attribution degradation:** Table 1 and Figure 1.
- **Semantic fidelity:** Table 2.
- **Sensitivity to semantic risk:** Table 4.
- **Model heterogeneity / replication:** Table 3 and Figure 2.

The Results should not bury the figures. Every table should be introduced by a one-sentence claim.

Examples:

- Table 1: “Across classifiers, all test-set rewrite conditions show positive macro-F1 loss, with bootstrap intervals above zero.”
- Table 2: “The semantic-fidelity audit indicates high usability but nonzero semantic risk.”
- Table 4: “The primary degradation pattern survives semantic-risk exclusions.”
- Table 3: “The Groq replication supports the main pattern while showing model-condition heterogeneity.”

---

## 8. Reviewer attack map and defensive wording

### Attack 1: “This is just NLP, not digital humanities.”

Defense:

> The paper is about the evidentiary status of AI-mediated literary text in DH workflows, not about improving an NLP classifier.

### Attack 2: “Authorship attribution is too narrow.”

Defense:

> Authorship attribution is used here as a probe for authorial signal. The broader claim concerns style-sensitive computational analysis of rewritten text.

### Attack 3: “Maybe the LLM changed meaning.”

Defense:

> The paper directly tests this through semantic-fidelity auditing and semantic-risk sensitivity analysis.

### Attack 4: “Only one annotation source.”

Defense:

> The audit is explicitly reported as a structured single-review audit; claims are limited accordingly, and the central result is supported by sensitivity analysis rather than by claiming perfect semantic truth.

### Attack 5: “Model results are heterogeneous.”

Defense:

> Heterogeneity is not hidden. It is part of the contribution: rewrite condition and model identity affect the magnitude of degradation.

---

## 9. Reference priority list

### Must cite

1. Burrows 2002 — Delta / foundational stylometry.
2. Stamatatos 2009 — authorship attribution survey.
3. Eder, Rybicki, Kestemont 2016 — stylo / computational text analysis in DH.
4. Brennan, Afroz, Greenstadt 2012 — adversarial stylometry.
5. Potthast, Hagen, Stein 2016 — author obfuscation / attacking authorship verification.
6. Manjavacas et al. 2017 — neural generation and authorial style.
7. A recent LLM stylometry / neural authorship attribution paper, e.g. Kumarage and Liu 2023.
8. DSH author guidelines — for format, data availability, AI disclosure, and figure accessibility compliance.

### Good supporting citations

- Segarra et al. on function-word adjacency networks.
- Mahmood et al. 2020 on detecting authorship obfuscation.
- Zhai et al. 2022 on adversarial deobfuscation.
- Przystalski et al. 2025 on stylometry detecting human vs LLM-generated texts.
- Huang, Murakami, Grieve 2024 on Authorial Language Models.

### Avoid or use sparingly

- Generic “LLMs are changing everything” papers unless tied directly to textual provenance, authorship, or DH.
- Pure AI-detection papers with no stylistic interpretation.
- Unverified blog posts.
- Wikipedia as a manuscript citation. It is fine for orientation, not for final references.

---

## 10. How to write this section at 8/10 publishability level

A weak Related Work section says:

> Many people have studied stylometry. Many people have studied AI. We study LLM rewriting.

A strong DSH section says:

> Stylometry depends on the assumption that authorial style remains measurable in the textual artifact under analysis. LLM rewriting challenges that assumption because it can preserve reader-facing meaning while altering the feature distributions used as authorial evidence. Prior work has studied authorship attribution, adversarial obfuscation, and machine-generated text, but these literatures have not fully tested routine LLM rewriting as a validity problem for style-sensitive DH analysis. This paper fills that gap by pairing original-to-rewrite attribution degradation with semantic-fidelity auditing and semantic-risk sensitivity analysis.

That is the core argument.

---

## 11. Prompts for LLM reviewers

### Prompt A: DSH fit judge

> You are a strict reviewer for *Digital Scholarship in the Humanities*. Evaluate this manuscript only for journal fit. Does it read as a digital-humanities methods paper rather than a generic NLP benchmark? Check whether the paper connects computational results to humanities questions about textual mediation, authorial evidence, editions, rewriting, and interpretive validity. Score DSH fit from 1–10 and give concrete revision instructions.

### Prompt B: Related Work critic

> You are a computational literary studies scholar. Brutally critique the Related Work section. Identify missing foundational citations in stylometry, authorship attribution, adversarial stylometry, LLM-generated text, and semantic fidelity. Tell me where the gap claim is weak, overclaimed, or not novel. Score related-work strength from 1–10.

### Prompt C: Methods validity critic

> You are a quantitative reviewer. Evaluate whether the methodology supports the claims. Focus on train/test split, leakage, feature selection, macro-F1, bootstrap confidence intervals, semantic-fidelity audit, and semantic-risk sensitivity analysis. Identify threats to validity and whether the paper overclaims. Score methodological credibility from 1–10.

### Prompt D: Humanities framing critic

> You are a humanities reviewer skeptical of computational methods. Read the paper and identify where the argument becomes too technical, where it fails to explain why the findings matter for literary or digital-humanities scholarship, and where it treats literature as mere data. Suggest wording changes that preserve technical rigor while improving humanities relevance.

### Prompt E: Acceptance simulation

> You are simulating three anonymous reviewers for *Digital Scholarship in the Humanities*: one supportive computational DH reviewer, one skeptical literary scholar, and one strict methods reviewer. For each reviewer, write a full review with major strengths, major weaknesses, required revisions, and likely recommendation. Then give a final editor-style decision and a publishability score out of 10.
