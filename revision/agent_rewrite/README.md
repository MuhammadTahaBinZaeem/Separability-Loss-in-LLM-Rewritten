# Supplemental agent rewrite feasibility sample

Requested by the author on 2026-09-19. One passage per work (18), three rewrite
conditions, requested agent model `gpt-5.5`. This small feasibility sample is
separate from the two provider-API experiments in PROTOCOL.md. It cannot replace
their missing outputs. Each condition is generated in one persistent agent
context with a blinded packet. That context includes multiple passages; outputs
are therefore not independent single-request API calls. No provider response IDs
or token usage are asserted. Record actual agent-task metadata and artifact
hashes. These rewrites are not human annotations. The source key is for the
pipeline; generation agents must receive only their packet.
