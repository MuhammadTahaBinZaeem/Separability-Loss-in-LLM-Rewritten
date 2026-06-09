# Corpus Source-Text and Copyright Documentation

## Purpose

This document records the source-text provenance and copyright/reuse framing for the literary corpus used in the LLM rewrite and stylometric degradation study. It is intended to support the Methods, Data Availability, and Ethics/Source Text sections of the manuscript.

## Corpus design summary

The study uses a balanced literary corpus built from Project Gutenberg source texts. The locked corpus contains:

- 6 authors;
- 12 works;
- 360 selected original passages;
- 30 selected passages per work;
- 60 selected passages per author;
- 3 LLM rewrite conditions per passage: paraphrase, modernize, simplify;
- 1440 final rows in `data/final/master_text_dataset.csv` after joining originals and rewrites.

These counts are verified by the existing master dataset metadata and selected-work metadata.

## Source-text register

The formal machine-readable source register is:

```text
metadata/source_text_copyright_register.csv
```

It records author, work, Project Gutenberg ebook number, Gutenberg landing page, plain-text URL, selected passage count, reuse note, and non-US copyright caution.

## Works included

| author | work | Project Gutenberg ebook no. | selected passages |
|---|---|---:|---:|
| Jane Austen | Pride and Prejudice | 1342 | 30 |
| Jane Austen | Emma | 158 | 30 |
| Charles Dickens | Great Expectations | 1400 | 30 |
| Charles Dickens | Oliver Twist | 730 | 30 |
| Edgar Allan Poe | The Works of Edgar Allan Poe Volume 1 | 2147 | 30 |
| Edgar Allan Poe | The Works of Edgar Allan Poe Volume 2 | 2148 | 30 |
| Mark Twain | Adventures of Huckleberry Finn | 76 | 30 |
| Mark Twain | The Adventures of Tom Sawyer | 74 | 30 |
| Mary Shelley | Frankenstein or The Modern Prometheus | 84 | 30 |
| Mary Shelley | The Last Man | 18247 | 30 |
| Oscar Wilde | The Picture of Dorian Gray | 174 | 30 |
| Oscar Wilde | Lord Arthur Savile's Crime and Other Stories | 773 | 30 |

## Manuscript wording: source texts

Use the following wording in Methods or Data:

> The source corpus was assembled from twelve Project Gutenberg texts: two works each by Jane Austen, Charles Dickens, Edgar Allan Poe, Mary Shelley, Mark Twain, and Oscar Wilde. For each work, thirty passages were selected, producing 360 original passages. Each passage was then associated with three controlled rewrite conditions: paraphrase, modernization, and simplification, yielding a 1440-row master dataset after joining original and rewritten texts. The source-text register records the Project Gutenberg ebook number, landing page, plain-text URL, selected passage count, and source-use note for every work.

## Manuscript wording: copyright and reuse

Use the following wording in Data Availability or Ethics/Source Texts:

> The source texts were obtained from Project Gutenberg editions identified in the repository source-text register. Project Gutenberg distinguishes between the underlying texts that are not restricted by U.S. copyright law and the Project Gutenberg trademark/license material attached to its distributed files. The study records the ebook number and URL for each source and treats non-US copyright status as jurisdiction-dependent. Researchers reusing the corpus outside the United States should verify local copyright law and should follow Project Gutenberg's license and trademark guidance when redistributing source-derived text.

## Important limits

Do not overclaim global public-domain status. The safe wording is:

- Project Gutenberg source texts are used as documented sources;
- Project Gutenberg states that many texts are not restricted under U.S. copyright law;
- Project Gutenberg also warns non-US users to check local laws;
- redistribution should avoid misuse of the Project Gutenberg trademark and should respect license/trademark terms.

## Reviewer attack this document prevents

A reviewer might ask:

1. Which exact editions were used?
2. How many passages came from each work?
3. Are the source texts legally reusable?
4. Is the corpus balanced by author and work?
5. Are the text sources reproducible?

This document answers those questions and points to machine-readable metadata.

## Final paper checklist

Before submission, ensure that the paper includes:

- a short corpus-source paragraph in Methods;
- a citation or reference entry for Project Gutenberg;
- a Data Availability statement pointing to the repository and source-text register;
- no claim that all texts are globally public domain;
- a note that copyright status outside the United States is jurisdiction-dependent;
- no large unnecessary republication of original literary passages in the article body.
