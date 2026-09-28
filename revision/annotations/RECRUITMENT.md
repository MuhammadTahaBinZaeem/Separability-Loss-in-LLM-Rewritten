# Recruiting independent reviewers

Updated 2026-09-26. The initial source-review return is registered; the corrected
corpus has a four-passage follow-up pending. No semantic returns are registered,
and the assistant has not hired anyone. This is an administrator's guide, not
an ethics approval, consent form approved by an institution, or proof of identity.

## Recommended route

Ask an English literature, linguistics, or digital-humanities department to help
recruit **two distinct postgraduate researchers or experienced research assistants**
who can read nineteenth-century English closely. A university contact and an
institutional email or brief introductory call provide practical accountability.
Do not collect passports or unnecessary identifying documents yourself. Disclose
personal, supervisory, financial, or coauthor relationships; avoid making both
reviewers dependent on the investigator for grades or employment decisions.

This is annotation work, not journal peer review. It cannot guarantee publication.
Prefer two people with strong close-reading ability over an anonymous service
promising to certify a paper, remove AI traces, or deliver guaranteed agreement.

Before recruitment, ask your institution's research-ethics contact whether this
paid annotation activity needs review, exemption, or another determination. Keep
the actual written determination. If unaffiliated, obtain qualified advice about
the applicable route; do not invent an institutional affiliation or exemption.

## Two separate human tasks

1. **Blinded semantic annotation:** under the intended six-arm expansion, each
   of two people independently rates the same 1,620 source/rewrite pairs, in
   different orders with different opaque IDs. It is **1,620 per person**:
   270 pairs per arm, for 3,240 judgments overall. The immutable Nano-only pilot
   packet has 270 pairs per reviewer and does not certify the expanded study.
   Follow `INSTRUCTIONS.md` exactly. The issued sample covers five valid pairs in
   every author/work/instruction/service cell. Forms are not issued until all
   generation outcomes are accounted for; do not start on a moving sample.
2. **Source-integrity sign-off:** a knowledgeable human checks all 360 frozen
   originals against their archived source contexts, confirming fictional-body
   boundaries and identifying editorial material, footnotes, introductions,
   mixed attribution, and uncertain extracts. An investigator may do this if
   qualified, with an honestly described role; independent review is stronger.
   If a semantic reviewer also performs this task, do it only **after both
   blinded returns have been sealed and registered**, because the source ledger
   reveals authors and works. A separate third source reviewer avoids this
   sequencing issue.

The initial registered source review covered 360 passages and flagged four.
The four replacements have exact archived spans and require a follow-up reading;
the assistant's correction checks do not supply that sign-off. Record a verdict, substantive notes, the
passage ID, reviewer pseudonym, actual review date/time, and corpus hash for each
source item. Preserve this dated original record privately. A real contamination
finding can require a new, versioned corpus and affected generations/analyses;
neither a signature nor an AI check can promise that no scientific revision
will be necessary.

## Qualification, workload and fair payment

Use a paid practice/calibration exercise on about 10–15 **non-study** pairs. Check
that applicants understand facts, omissions, speakers, narrative order and the
rating scale. Discuss ambiguities in the rubric before main ratings; do not
select reviewers for agreeing with the expected study result. Main ratings are
independent, and substantive rubric changes require a documented amendment.

Measure actual minutes per pair, then budget:

`hours per reviewer = 1,620 × pilot minutes per pair / 60 + training and breaks`.

For example, six minutes per pair is 162 working hours each before training and
breaks; adding 20% produces about 194 hours each. This is an illustration, not a
measured estimate or a pay-rate recommendation. At illustrative rates of $15–25
per hour, that is roughly $5,832–9,720 for both reviewers before fees and the
source follow-up. This is separate from the user's $35 API-generation cap.
Four reviewers could divide the work into two disjoint pools, keeping two
independent ratings per item, but that requires a separately frozen assignment
mapping and additional accounts before issue; it is not yet configured. Agree a fair rate
appropriate to expertise and location, pay training, and adjust if real workload
is higher. Do not make payment depend on favorable ratings or agreement.

Use manageable sessions, breaks and an agreed deadline. Warn reviewers that
historical fiction may contain violence, racism, offensive language or distressing
themes. Explain withdrawal, payment, data retention and contact arrangements in
the actual consent/engagement materials approved for your setting.

## Secure, independent collection

- Give reviewer A only `forms/reviewer_A.csv` and `INSTRUCTIONS.md`; give B only
  the B version. Wait for `issued_manifest.json` before distributing either.
- Use two separately permissioned institutional/approved encrypted file-share
  folders with named access and MFA. Never use an anyone-with-the-link folder.
- Keep the source-author/model/condition join key, identities, consent,
  payment records and results in a separate administrator-only location. Share
  neither credentials nor the complete repository with reviewers.
- Reviewers must not see one another's ratings or the hypothesized direction
  of results. Each reads both texts fully, supplies their own notes and makes
  their own decisions. No generative-AI assistance or outsourced ratings.
- Agree accessibility arrangements in advance. Do not mistake assistive reading
  technology for fabricated responses or use undisclosed invasive monitoring.
- Obtain an explicit signed or authenticated statement from each real person:
  "I personally read and rated these items independently, without generative-AI
  assistance, another person's ratings, or another person completing the form."
  Collect actual completion date/time and timezone. Do not pre-sign for them.
- Keep the received file unchanged. Register its hash before making any working
  copy. Resolve missing fields by requesting a dated corrected return while
  retaining the earlier one; never fill human judgments yourself.
- Keep discrepancies and uncertainty. Identical choices trigger a separate
  human provenance check in the validator, not an automatic accusation.

No AI detector, identity check or secure folder proves that someone did all the
reading unaided. Accountability, a paid practice task, independently returned
forms and brief consented follow-up questions provide a defensible process,
not a guarantee. Do not reject work solely on an AI-text-detector score.

## Ready-to-send invitation

Subject: Paid independent literary-text annotation (research project)

Hello,

I am seeking two independent reviewers with strong English close-reading skills,
preferably postgraduate training in literature, linguistics or digital humanities.
The task is to compare original fiction passages with rewritten versions and
rate factual, narrative and meaning preservation using a fixed rubric. Each
reviewer will assess 540 pairs independently. Sources and rewriting conditions
are blinded where practical. Generative-AI assistance and shared ratings are not
permitted; payment does not depend on the answers or agreement.

There will be a paid non-study practice exercise before the main task. We will
agree an hourly rate, realistic time allowance, secure file access and engagement/
consent arrangements before work starts. Some historical texts contain offensive
or distressing material. Please reply with relevant experience and availability;
please do not send sensitive identity documents.

Thank you.

Administrator: replace this invitation's generic identity with your real name
and contact details. Agree the actual fee and dates separately. Do not claim
ethics approval until the applicable determination exists.

## If university recruitment is unavailable

Prolific is a possible alternative, subject to current researcher eligibility,
project suitability and platform rules. Use a paid expertise screen and recruit
the same two eligible people for the full independent task, potentially in
planned longitudinal batches; do not silently replace the design with many
one-off crowd ratings. Confirm this long task and batching arrangement with the
platform before launching. A changed rater/sample design needs an amendment.

Prolific describes identity-vetted participants and pseudonymous IDs; that does
not certify literary expertise or absence of AI use. On that platform use its
participant IDs and rules, **not** requests for personal emails, names or IDs.
Its current minimum is £6/$8 per hour and recommended floor £9/$12, not a target
rate for specialist close reading. Each longitudinal wave must be paid fairly.
Fees are additional. Official guidance checked 2026-09-21:

- [Participant vetting and identifiers](https://researcher-help.prolific.com/en/articles/449610-participant-vetting-and-identifiers)
- [AI-use prevention and detection](https://researcher-help.prolific.com/en/articles/445207-how-to-prevent-and-detect-ai-or-large-language-model-llm-use-in-studies)
- [Payment model](https://researcher-help.prolific.com/en/articles/445230-prolific-s-payment-model)
- [Pricing](https://researcher-help.prolific.com/en/articles/445239-what-is-your-pricing)

## After real returns arrive

The investigator must supply the real files and attestations. Import each using
`python -m research_v2.annotations ingest --help`; never use example identities
or dates as actual records. Then run `annotations validate` and the full offline
reproduction. Agreement, disagreement tables and the predeclared semantic
sensitivity are calculated from the registered original returns. This does not
make unaudited pairs semantically certified or settle manuscript authorship,
licensing, ethics, source corrections or the final journal submission decision.
