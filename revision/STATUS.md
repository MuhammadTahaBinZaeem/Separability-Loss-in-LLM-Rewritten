# Research-validity revision status

This is a new, explicitly exploratory revision. Historical results are preserved,
not erased or retrospectively relabeled as valid v2 evidence.

| Stage | Implemented | Evidence still needed |
|---|---|---|
| 1. Source integrity | Traceable dispositions for all 360 historical passages; replacement corpus with 18 distinct fiction works, exact source offsets, exclusion ledger and hashes | AI-assisted structural review is not an independent human reading of all passages |
| 2. Frozen rerun | Frozen 360 originals and 2,160 blinded API requests; append-only responses and recomputed QC | Complete provider responses from both models |
| 3. Work-held-out evaluation | Three work-grouped folds; three works per author | Full rewritten-data evaluation |
| 4. Train-only preprocessing | Fold-fitted vocabulary, constant-feature removal and scaling; regression tests | Full-run fold evidence |
| 5. Statistical corrections | Actual shrinkage LDA, common-scale distances, work-aware paired uncertainty, multiplicity correction | Final recomputed results and verified semantic sensitivity |
| 6. Independent review | Blinded forms/immutable-return validation and agreement computation | Two real independent people, dated original returns and attestations |
| 7. Reproducibility/archive | Hash-locked Python environment, historical QC reconciliation; release checks under construction | All gates passed and a genuinely published archive DOI |

The separate older-model feasibility sample contains 54 agent outputs, including
four unchanged copies that fail QC. Only 48 outputs have source hashes matching
the final corpus; these sets can overlap. It is not primary experimental data or
human annotation. See `agent_rewrite/provenance.json` for the exact limitations.

No audit result establishes intent to deceive. Missing provenance, inconsistent
reports and methodological errors must be disclosed and repaired; they do not
alone prove fabrication. A final journal-ready claim requires empirical quality
and editorial assessment beyond passing software tests.
