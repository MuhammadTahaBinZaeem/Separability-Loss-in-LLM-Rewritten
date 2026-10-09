# Step 15 Original-to-Rewritten Degradation Report

## Status

Complete when generated locally and checker passes.

## Training design

- training rows: 252
- training condition: original only
- scaler fit scope: train/original only
- feature columns: 205

## Best original-test model

- model: nearest_centroid
- original test macro F1: 0.776931
- original test accuracy: 0.777778

## Test degradation for best original-test model

- original: macro_f1=0.776931, macro_f1_loss=0.0
- paraphrase: macro_f1=0.395797, macro_f1_loss=0.381134
- modernize: macro_f1=0.56072, macro_f1_loss=0.216211
- simplify: macro_f1=0.463636, macro_f1_loss=0.313295
