# Automated methods audit — not independent reviewer evidence

No confirmed bugs identified in the reviewed functions. One scientific limitation to note:

1. **Function**: `paired_uncertainty` (bootstrap loop).  
   **Limitation & Mechanism**: After sampling works with replacement for each author, the code resamples individual passages *within* each selected work (`rng.choice(indices, size=len(indices), replace=True)`). This two-stage resampling treats the 20 passages from a work as exchangeable IID draws, which can understate uncertainty if passages within a work exhibit correlation (the study text emphasizes “never treat the 20 passages of a work as 20 assignments”).  
   **Suggested check/correction**: Implement a strict cluster bootstrap by sampling works with replacement, then concatenating all passages in the selected works without an inner resampling step, e.g.:
   ```python
   sampled = np.concatenate([groups[g] for g in rng.choice(ag, size=len(ag), replace=True)])
   ```
   Compare confidence intervals from the current and cluster-only schemes to assess sensitivity.