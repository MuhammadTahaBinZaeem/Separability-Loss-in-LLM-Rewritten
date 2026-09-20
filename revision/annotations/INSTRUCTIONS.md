# Independent human meaning-preservation review

Status: no human reviews have been supplied. Do not fill these ratings using an
LLM and do not duplicate one person's ratings under two IDs.

After complete generation, `python -m research_v2.annotations prepare` creates
two separately randomized CSV forms. Give each person only their own form and
these instructions. Keep the private join key, model identities, author identities,
condition names, analysis results, and the other person's ratings away from them.
Reviewers can infer some sources from text; blinding is not a guarantee of anonymity.

Read the original and rewrite in full. Judge preservation of the original, not
whether you prefer the rewrite. Rate each field:

- `added_facts`, `omitted_facts`, `order_changed`, `relationships_changed`: 0=no,
  1=yes. The last field covers speakers, characters, ownership and causal roles.
- `tone_drift`: 0=none, 1=noticeable but not fundamental, 2=substantial change in
  emotion, seriousness, irony or narrative stance.
- `meaning_preservation`: 5=all material meaning retained, 4=minor nonmaterial
  deviations, 3=material but localized distortion, 2=several material distortions,
  1=meaning largely changed or missing.
- `usable`: yes=the rewrite can support a study of stylistic change with meaning
  preserved; no=meaning changes materially confound that interpretation.
- `notes`: identify the exact event, claim, speaker or relation affected. Notes
  are required for any factual/order/relation change, score <=3, or unusable item.

Work independently. Do not consult the other reviewer or an AI to choose ratings.
You may pause between sessions. Return the original completed CSV without editing
the item IDs or passage text. Record a pseudonymous reviewer identity and the
actual completion date/time with timezone. The study administrator must retain
each original return, its hash and an explicit independence/human-review attestation.

Institutional review and consent: the investigator must establish any applicable
requirements before recruitment. No approval/exemption has been asserted here.

The importer stores an immutable copy and checks every response. Agreement and
kappa are computed from the two original reviews. Disagreements are retained in
a separate table for adjudication. For sensitivity, either reviewer's factual or
major meaning flag excludes the pair under the rule fixed before rating; unaudited
items remain unknown and are not counted as semantically certified.
