# Step 7 Candidate Generation Report — Canonical Gutenberg Layer

## Status

Candidate generation has been rerun on the canonical Project Gutenberg plain-text layer.

## Overall counts

- total candidate rows: 1,879
- passing candidates: 1,879
- failed length candidates: 0
- failed low-sentence candidates: 0

## Passing candidates by author

- austen: 395 PASS
- dickens: 471 PASS
- poe: 255 PASS
- shelley: 342 PASS
- twain: 252 PASS
- wilde: 164 PASS

## Critical Step 7 finding

The old PDF-layer Wilde blocker is resolved. Wilde now has 164 passing candidate passages, which is above the Step 6 target of 120 candidate passages per author and above the Step 8 final target of 60 passages per author.

## Output artifacts

The full text-bearing candidate pool is tracked by checksum and packaged in the local handoff archive because direct connector upload of the full text CSV is not reliable.

- candidate_passages.csv SHA256: `0b0e457db3880318685c1401ce81c3175bbc8ea0550ad8e686321781f2c49d95`
- candidate_passage_metadata.csv SHA256: `22e648806a0cfb68d588a8bf4c34e23dd96ccf422cf8854f1072d085b6a26907`

## Step 7 conclusion

Step 7 is complete for the canonical Project Gutenberg layer. The corpus is now balance-ready for Step 8 final passage selection.
