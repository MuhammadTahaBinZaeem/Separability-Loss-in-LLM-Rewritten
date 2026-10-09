# DSH Submission End-Matter Package

This document locks the end-matter and ethics/disclosure language needed for a Digital Scholarship in the Humanities-style submission. It is a drafting guide, not the final manuscript text.

## Why this matters

DSH/OUP requires a Data availability section and an AI Disclosure Statement when AI tools are used. The journal also strongly encourages making data and software available where ethically feasible, and requires authors to remain accountable for accuracy, integrity, and originality when AI tools assist manuscript preparation.

The paper must therefore not only present strong results; it must also show transparent reproducibility, responsible AI disclosure, and copyright awareness.

---

## 1. Data availability statement

### Recommended manuscript heading

`Data availability`

### Recommended statement

> The data and code underlying this article are available in the project repository at [repository URL / DOI to be inserted after archival deposit]. The repository contains the corpus metadata, rewrite metadata, stylometric feature tables, model predictions, bootstrap confidence-interval outputs, semantic-fidelity audit materials, semantic-risk sensitivity outputs, manuscript tables, figure source files, and reproducibility scripts. Where source literary texts are derived from public-domain sources, the repository records source metadata and passage identifiers. Any third-party material subject to reuse restrictions should be cited and documented according to its original licence.

### Stronger version after Zenodo/OSF archival deposit

> The data and code underlying this article are available in Zenodo at [DOI]. The archived repository contains the corpus metadata, rewrite metadata, stylometric feature tables, model predictions, bootstrap confidence-interval outputs, semantic-fidelity audit materials, semantic-risk sensitivity outputs, manuscript tables, figure source files, and reproducibility scripts. The GitHub development repository is available at [GitHub URL]. Public-domain literary sources are identified in the corpus metadata; any third-party sources are cited according to their original licences.

### Notes for final submission

- Use a permanent DOI if possible, ideally Zenodo or OSF.
- GitHub alone is good for development, but a citable archive is stronger.
- Do not claim full raw-text redistribution unless the source-text licences actually allow it.
- If any passages are not redistributable, state that derived features and identifiers are available while restricted raw text is not redistributed.

---

## 2. Software/code availability statement

This can be integrated into Data availability or stated separately.

> All analysis scripts used to generate the reported tables and figures are available in the project repository. The repository includes scripted stages for feature extraction, original-to-rewritten transfer evaluation, semantic-fidelity audit processing, semantic-risk sensitivity analysis, bootstrap confidence intervals, Groq free-model replication, and manuscript-asset generation. Each output table is accompanied by a manifest or validation report where applicable.

---

## 3. AI Disclosure Statement

### Recommended manuscript heading

`AI Disclosure Statement`

### Honest statement for this project

> This manuscript and the associated research workflow were prepared with assistance from ChatGPT (OpenAI, GPT-5.5 Thinking) and GitHub/Codex-style code assistance. These tools were used to support drafting, editing, code generation, code review, workflow construction, tabular summarization, and preliminary critique of manuscript wording. The authors retained responsibility for the research design, source selection, interpretation, verification of generated code, checking of reported numerical results, and final manuscript content. All AI-assisted text, code, tables, figures, and references were reviewed and approved by the authors before use.

### If the final paper uses fewer AI tools

> This manuscript was prepared with assistance from [tool names and versions]. The tools were used for [language editing / code assistance / table summarization / preliminary critique]. All AI-generated or AI-assisted content was checked and approved by the authors, who remain responsible for the accuracy, integrity, originality, and interpretation of the work.

### What not to do

- Do not hide AI use.
- Do not list AI tools as authors.
- Do not claim that AI tools independently verified results.
- Do not cite fake references suggested by an AI system.
- Do not say “no AI was used” if AI helped with drafting, code, critique, or analysis.

---

## 4. Ethics statement

### Recommended manuscript heading

`Ethics statement`

### Recommended statement

> This study analyzes public-domain or otherwise lawfully accessible literary texts and generated rewrites of those texts. It does not involve human-subject experiments, private personal data, medical data, or intervention with human participants. The semantic-fidelity review reported in the article is treated as a structured single-review validity audit rather than as a human-subject study or independent multi-annotator experiment.

### If a supervisor wants simpler wording

> This research used literary texts and generated textual transformations only. No human participants, private personal data, or sensitive personal data were involved.

---

## 5. Funding statement

### If no funding

> This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.

### If funded later

> This work was supported by [official funder name] [grant number xxxx].

---

## 6. Conflict of interest statement

> The authors declare no competing interests.

If there is any actual conflict, replace this with a specific disclosure.

---

## 7. Author contributions / CRediT-style draft

Use only what is true for the final author list.

> Conceptualization: [names]. Methodology: [names]. Software: [names]. Validation: [names]. Formal analysis: [names]. Investigation: [names]. Data curation: [names]. Writing—original draft: [names]. Writing—review and editing: [names]. Visualization: [names]. Supervision: [names]. Project administration: [names].

For a student-led manuscript, this should make the student contribution visible without overstating any supervisor role.

---

## 8. Copyright and source-text note

> The literary passages used in this study were selected from public-domain or lawfully accessible sources. Corpus metadata records author, work, passage identifier, and source information. The manuscript quotes only limited excerpts where necessary for scholarly explanation; longer source passages and generated rewrites are handled through the project repository subject to applicable source licences and permissions.

If the repository includes full passages, verify that every source is public domain or legally redistributable before final submission.

---

## 9. Reproducibility statement

> The computational workflow is organized as a scripted, stage-based pipeline. The repository includes validation scripts for generation completeness, downstream analysis, semantic-fidelity annotations, semantic-risk sensitivity, bootstrap confidence intervals, and manuscript assets. Reported numerical results are generated from committed CSV outputs and are accompanied by manifests or check reports.

---

## 10. Figure accessibility and alt text plan

Every manuscript figure should include alt text under the figure legend.

### Figure 1 alt text draft

> Alt text: Bar chart showing macro-F1 loss in authorship attribution after LLM rewriting. Losses are positive for paraphrase, modernization, and simplification across all three classifiers, indicating reduced attribution performance on rewritten passages compared with original passages.

### Figure 2 alt text draft

> Alt text: Bar chart showing macro-F1 loss in the Groq free-model replication. Most model-condition combinations show positive loss, while the Llama modernization condition shows a small reversal, indicating heterogeneous replication across models and rewrite conditions.

---

## 11. Submission checklist

Before submission, confirm:

- Full paper length is within the target word limit.
- Main manuscript is prepared as a Word file or accepted format.
- Figures are supplied separately and at suitable resolution.
- Each figure has alt text.
- Data availability statement is included under `Data availability`.
- AI disclosure is included under `AI Disclosure Statement`.
- Funding statement is included.
- Conflict of interest statement is included.
- Public-domain/copyright status of literary passages is checked.
- References are real and verified.
- Repository is archived with DOI if possible.
- No claim of independent double annotation is made for the semantic-fidelity audit.
- Results text cites bootstrap confidence intervals, not only point estimates.
- Groq replication is described as heterogeneous, not uniform.

---

## 12. Manuscript-safe end-matter block

Use this as the starting block near the end of the paper:

### Data availability

The data and code underlying this article are available in the project repository at [repository URL / DOI]. The repository contains corpus metadata, rewrite metadata, stylometric feature tables, model predictions, bootstrap confidence-interval outputs, semantic-fidelity audit materials, semantic-risk sensitivity outputs, manuscript tables, figure source files, and reproducibility scripts. Public-domain literary sources are identified in the corpus metadata; any third-party sources are cited according to their original licences.

### AI Disclosure Statement

This manuscript and the associated research workflow were prepared with assistance from ChatGPT (OpenAI, GPT-5.5 Thinking) and GitHub/Codex-style code assistance. These tools were used to support drafting, editing, code generation, code review, workflow construction, tabular summarization, and preliminary critique of manuscript wording. The authors retained responsibility for the research design, source selection, interpretation, verification of generated code, checking of reported numerical results, and final manuscript content. All AI-assisted text, code, tables, figures, and references were reviewed and approved by the authors before use.

### Funding

This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.

### Conflict of interest

The authors declare no competing interests.

### Ethics statement

This study analyzes public-domain or otherwise lawfully accessible literary texts and generated rewrites of those texts. It does not involve human-subject experiments, private personal data, medical data, or intervention with human participants. The semantic-fidelity review reported in the article is treated as a structured single-review validity audit rather than as a human-subject study or independent multi-annotator experiment.
