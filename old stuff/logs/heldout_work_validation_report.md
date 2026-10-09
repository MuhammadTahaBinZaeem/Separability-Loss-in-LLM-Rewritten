# E2 Held-Out-Work Validation Report

## Status

Complete when generated locally and checker passes.

## Design

- two folds: first-work-to-second-work and second-work-to-first-work.
- training condition for transfer: original only.
- evaluation conditions: original, paraphrase, modernize, simplify on held-out works.

## Output rows

- fold registry rows: 12
- transfer prediction rows: 4320
- transfer summary rows: 36
- same-condition summary rows: 36
- distance summary rows: 24

## Mean-across-fold nearest-centroid transfer summary

- original: macro_f1=0.601154, loss=0.0, rows=360
- paraphrase: macro_f1=0.421357, loss=0.179796, rows=360
- modernize: macro_f1=0.499157, loss=0.101997, rows=360
- simplify: macro_f1=0.475768, loss=0.125387, rows=360

## Mean-across-fold distance ratios

- function_word / original: ratio=1.0
- function_word / paraphrase: ratio=0.824602584
- function_word / modernize: ratio=0.892516328
- function_word / simplify: ratio=0.863369023
- all_features / original: ratio=1.0
- all_features / paraphrase: ratio=0.840368543
- all_features / modernize: ratio=0.900911819
- all_features / simplify: ratio=0.878210609
