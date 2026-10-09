# Step 16 Rewritten-Condition Author Classification Report

## Status

Complete when generated locally and checker passes.

## Design

- one same-condition classifier per condition
- train rows per condition: 252
- validation rows per condition: 54
- test rows per condition: 54
- scaler fit scope: train rows of each condition only
- feature columns: 205

## Best original-condition test model

- model: nearest_centroid
- original test macro F1: 0.776931
- original test accuracy: 0.777778

## Test same-condition separability for that model

- original: macro_f1=0.776931, survival_ratio=1.0
- paraphrase: macro_f1=0.623903, survival_ratio=0.803035
- modernize: macro_f1=0.682286, survival_ratio=0.878181
- simplify: macro_f1=0.682286, survival_ratio=0.878181
