# Semantic Fidelity Annotation Extraction Report

## Source PDFs

- `semantic_fidelity_annotation_packet_filled.pdf`
- `semantic_fidelity_annotation_packet_revised_student_reader.pdf`

## Extraction status

- Extracted audit items from filled packet: 108
- Extracted audit items from revised student-reader packet: 108
- Missing choice fields in final revised extraction: 0
- Choice agreement between the two uploaded PDFs: 108/108 items (100.0%)

Important: the two PDFs have identical selected choices, so they should not be reported as two independent annotators. Use the revised student-reader packet as the final single annotation source unless you can document true annotator independence.

## Overall final annotation summary

- Rows: 108
- Added facts: 6 (5.6%)
- Omitted facts: 5 (4.6%)
- Narrative-order changes: 0 (0.0%)
- Speaker/character-relation changes: 0 (0.0%)
- Tone drift mean: 0.981481
- Tone drift counts: 0=10, 1=90, 2=8
- Mean meaning preservation: 4.527778
- Meaning preservation <= 3: 1
- Overall usable: 107/108 (99.1%)
- Any semantic issue flag: 17 (15.7%)

## Condition summary

| condition   |   rows |   added_facts_count |   added_facts_rate |   omitted_facts_count |   omitted_facts_rate |   narrative_order_change_count |   narrative_order_change_rate |   speaker_relation_change_count |   speaker_relation_change_rate |   tone_drift_mean |   tone_0_count |   tone_1_count |   tone_2_count |   meaning_preservation_mean |   meaning_preservation_median |   meaning_le_3_count |   usable_yes_count |   usable_no_count |   usable_rate |   any_semantic_issue_count |   any_semantic_issue_rate |   low_issue_level_count |   medium_issue_level_count |   high_issue_level_count |
|:------------|-------:|--------------------:|-------------------:|----------------------:|---------------------:|-------------------------------:|------------------------------:|--------------------------------:|-------------------------------:|------------------:|---------------:|---------------:|---------------:|----------------------------:|------------------------------:|---------------------:|-------------------:|------------------:|--------------:|---------------------------:|--------------------------:|------------------------:|---------------------------:|-------------------------:|
| ALL         |    108 |                   6 |           0.055556 |                     5 |             0.046296 |                              0 |                             0 |                               0 |                              0 |          0.981481 |             10 |             90 |              8 |                     4.52778 |                             5 |                    1 |                107 |                 1 |      0.990741 |                         17 |                  0.157407 |                      91 |                         16 |                        1 |
| modernize   |     36 |                   1 |           0.027778 |                     0 |             0        |                              0 |                             0 |                               0 |                              0 |          1.05556  |              0 |             34 |              2 |                     4.63889 |                             5 |                    0 |                 36 |                 0 |      1        |                          3 |                  0.083333 |                      33 |                          3 |                        0 |
| paraphrase  |     36 |                   3 |           0.083333 |                     2 |             0.055556 |                              0 |                             0 |                               0 |                              0 |          0.833333 |             10 |             22 |              4 |                     4.30556 |                             4 |                    1 |                 35 |                 1 |      0.972222 |                          7 |                  0.194444 |                      29 |                          6 |                        1 |
| simplify    |     36 |                   2 |           0.055556 |                     3 |             0.083333 |                              0 |                             0 |                               0 |                              0 |          1.05556  |              0 |             34 |              2 |                     4.63889 |                             5 |                    0 |                 36 |                 0 |      1        |                          7 |                  0.194444 |                      29 |                          7 |                        0 |

## Manuscript-safe wording

Use cautious wording:

> A single filled semantic-fidelity review of the 108-item audit sample found that 107/108 rewrites were marked usable, with a mean preservation score of 4.53/5. Because the uploaded filled and revised packets contain identical selected choices, these results should be treated as a single-review audit rather than independent double annotation.

Do not claim two independent human annotators unless you have separate independently completed sheets.
