# Final Paper-Readiness Summary

## Current readiness

The repository now contains a complete, traceable empirical pipeline from public-domain source selection through final paper-facing tables and figures.

## Locked empirical core

- 12 canonical Gutenberg works across 6 authors.
- 360 selected original passages.
- 1080 controlled LLM rewrites across paraphrase, modernize, and simplify conditions.
- 1440 master text rows.
- 205 stylometric features across 6 feature families.
- Passage-level train/validation/test split.
- Original baseline classification.
- Original-to-rewritten degradation analysis.
- Same-condition rewritten classification.
- Burrows Delta and inter-author distance analysis.
- Feature-family vulnerability analysis.
- Bootstrap confidence intervals and SVG figures.

## Main paper-facing statistical result

- paraphrase: macro-F1 loss 0.381133642, 95% CI [0.264839149, 0.503284926], p_loss_le_zero=0.0
- modernize: macro-F1 loss 0.216210995, 95% CI [0.100501182, 0.343607038], p_loss_le_zero=0.0
- simplify: macro-F1 loss 0.313294321, 95% CI [0.194675605, 0.451590826], p_loss_le_zero=0.0

## Next manuscript work

Write the paper around the completed empirical package. The remaining work is manuscript composition, final figure styling, and human interpretation, not dataset construction.
