# E7 Length-Band Robustness Report

## Status

Complete when generated locally and checker passes.

## Design

- transfer classifiers trained on all original-condition training rows.
- predictions stratified by actual text length and source-original passage length.
- bands: 450-500, 501-575, 576-650, outside bands.

## Output rows

- prediction rows: 1296
- transfer summary rows: 192
- distribution rows: 64

## Source-original length, nearest-centroid test focus

- band=501_575 / original: rows=42, macro_f1=0.781197, loss=0.0
- band=501_575 / paraphrase: rows=42, macro_f1=0.415453, loss=0.365744
- band=501_575 / modernize: rows=42, macro_f1=0.552973, loss=0.228224
- band=501_575 / simplify: rows=42, macro_f1=0.421154, loss=0.360043
- band=576_650 / original: rows=12, macro_f1=0.711111, loss=0.0
- band=576_650 / paraphrase: rows=12, macro_f1=0.288889, loss=0.422222
- band=576_650 / modernize: rows=12, macro_f1=0.550794, loss=0.160317
- band=576_650 / simplify: rows=12, macro_f1=0.472222, loss=0.238889
