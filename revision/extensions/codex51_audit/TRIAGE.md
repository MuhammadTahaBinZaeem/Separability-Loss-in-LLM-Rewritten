# Bounded GPT-5.1 Codex methods audit

This is automated assistance, not independent reviewer evidence or an additional
experimental rewrite model. No reviewer responses were created.

## Calls and output budget

- Connectivity check: 11 reported output tokens; allowance 128.
- `20260925T154741Z`: no usable response or usage received; retain the full
  4,000-token reservation rather than assuming zero billable output.
- `20260925T155426Z`: 2,496 reported output tokens, all reasoning; no audit answer.
  The allowance was 2,500.
- `20260925T211904Z`: completed focused audit of `research_v2/inference.py`;
  4,832 reported output tokens, including 4,608 reasoning tokens; allowance 5,000.

Reported output across calls with usage is 7,339 tokens. Total conservative
reserved allowance, including the call with unknown usage, is 11,628 tokens,
well below the user's exclusive 3,000,000-output-token ceiling. No further
Codex calls are scheduled by this audit.

## Finding disposition

The completed response reported no confirmed code bugs. It recommended comparing
the current two-stage bootstrap with a work-only cluster bootstrap.

Local inspection confirms that `paired_uncertainty` samples works within each
fixed author, then paired passages within the selected work. Its permutation
test separately swaps whole works. The audit's cited comment about not treating
20 passages as 20 assignments belongs to that permutation-test section; it is
not evidence that the implemented permutation test violates the comment.

The suggestion is retained as a possible sensitivity analysis, not an established
finding of underestimated uncertainty. Its claimed direction of uncertainty
error has not been demonstrated on these data. No primary estimator, interval,
test, result or frozen protocol was silently changed following model advice.
Any added sensitivity analysis needs a recorded design before inspecting its
results, explicit limitations for only three works per author, and separate
reporting rather than replacement of an unfavorable result.

The complete native responses, requests, usage and input hashes are retained in
the dated subdirectories. This limited code audit does not certify corpus
authorship, semantic fidelity, generalizability, or publication readiness.
