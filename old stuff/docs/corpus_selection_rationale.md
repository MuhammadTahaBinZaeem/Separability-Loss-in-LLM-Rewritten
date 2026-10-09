# Corpus Selection Rationale — Step 2

## Purpose

Step 2 converts the uploaded source inventory into a formal author/work map for the main research corpus.

The target paper is:

> **Authorial Style Separability Loss in LLM-Rewritten Fiction: A Controlled Stylometric Framework for Measuring Literary Style Flattening**

The corpus must support controlled comparison across six literary authors while avoiding genre confounds. Therefore, the main dataset should use **English prose fiction**, not poetry, drama, essays, travel writing, letters, biography, or mixed editorial material.

## Locked authors

The six target authors remain:

1. Jane Austen
2. Edgar Allan Poe
3. Mark Twain
4. Oscar Wilde
5. Charles Dickens
6. Mary Shelley

These authors are kept because they support distinct literary-style anchors:

| Author | Style anchor for later interpretation |
|---|---|
| Jane Austen | irony-bearing syntax, social narration, clause control |
| Edgar Allan Poe | punctuation intensity, suspense rhythm, heightened diction |
| Mark Twain | colloquial rhythm, informal prose, speech-like movement |
| Oscar Wilde | aphoristic compression, wit, balanced phrasing |
| Charles Dickens | descriptive accumulation, long syntactic build-up |
| Mary Shelley | Gothic register, elevated diction, emotional abstraction |

## Inclusion rules

A work is eligible for the main corpus if it is:

- prose fiction,
- public-domain or source-provided for research processing,
- long enough to support 450–650 word passage extraction,
- not primarily drama, poetry, essays, letters, travel writing, biography, or editorial commentary,
- extractable into reasonably clean text,
- not collaborative unless used only as an explicit backup,
- the author's original prose, not a simplified retelling/adaptation by another writer.

## Planned main sources by author

### Jane Austen

Current uploaded source:

- `source/austenJane/_OceanofPDF.com_Complete_Works_Extras_-_Austen_Jane_compressed.pdf`

Initial PDF inspection confirms a complete-works table of contents containing Austen's major novels. Main candidates:

- *Pride and Prejudice* — main
- *Emma* — main

Backups:

- *Sense and Sensibility*
- *Mansfield Park*
- *Persuasion*
- *Northanger Abbey*

Rationale: Austen is retained for irony-bearing syntax, social narration, and controlled clause structure. Exact internal work boundaries must be extracted in later steps.

### Charles Dickens

Current uploaded sources include many individual Dickens PDFs. Main candidates:

- *Great Expectations*
- *Oliver Twist*

Backups:

- *David Copperfield*
- *A Tale of Two Cities*
- *Bleak House*
- *Hard Times*
- *Dombey and Son*
- *Martin Chuzzlewit*
- *Our Mutual Friend*
- *Barnaby Rudge*
- *Nicholas Nickleby*
- *Little Dorrit*

Excluded or deferred:

- *American Notes* — non-fiction/travel
- *A House to Let* — collaborative
- *The Mystery of Edwin Drood* — unfinished
- *Sketches by Boz* — sketch/mixed form; backup only if scope changes
- *Master Humphrey's Clock* — serial frame/mixed form; backup only if needed

Rationale: Dickens is retained for descriptive accumulation and long syntactic build-up. Main candidates are individual novel PDFs with sufficient length.

### Edgar Allan Poe

Current uploaded source:

- `source/EdgarPoe/the-complete-works-of-edgar-allan-poe.pdf`

Main candidate:

- selected prose fiction tales

Backup:

- *The Narrative of Arthur Gordon Pym of Nantucket*

Excluded:

- poems
- essays/reviews

Rationale: Poe is retained for punctuation intensity, suspense rhythm, and heightened diction. Because Poe wrote many short works, later steps must define a balanced short-fiction selection instead of sampling poetry or criticism.

### Mark Twain

Current uploaded source:

- `source/Marktwain/completeworksofm09twaiiala.pdf`

Initial PDF text indicates:

- *Adventures of Huckleberry Finn*

Main candidate:

- *Adventures of Huckleberry Finn*

Gap:

- *The Adventures of Tom Sawyer* is desired as a second prose source but is not confirmed in the current uploaded PDF.

Rationale: Twain is retained for colloquial rhythm and speech-like prose. Current source may be enough for 60 passages, but relying on one work creates a balance risk.

### Mary Shelley

Current uploaded source:

- `source/Marryshelly/delphi-complete-works-of-mary-shelley-mary-shelley-_shelley_-mary_-2013-Delphi-Classics-147fa34700ef.pdf`

Initial PDF inspection confirms a complete-works table of contents. Main candidates:

- *Frankenstein* 1818 version
- *The Last Man*

Backups:

- *Valperga*
- *Lodore*
- *Falkner*
- short stories if needed

Excluded:

- travel writing
- non-fiction
- biographies
- poems
- adaptations by other authors

Rationale: Shelley is retained for Gothic register, elevated diction, emotional abstraction, and philosophical/introspective prose.

### Oscar Wilde

Uploaded Wilde sources now include:

- `source/Oscarwilde/Complete works of Oscar Wilde (1921) 6.pdf` — drama volume; excluded from main prose-fiction corpus.
- `source/Oscarwilde/Lord Arthur Savile’s Crime and Other Stories - Oscar Wilde - PDF Room.pdf` — usable prose-fiction collection; added after Step 2 and now accepted as Wilde's current usable source.
- `source/Oscarwilde/THE PICTURE OF DORIAN GRAY.pdf` — excluded because it is an Oxford Bookworms 1989 retelling by Jill Nevile, not Wilde's original prose.

Current main candidate:

- *Lord Arthur Savile's Crime and Other Stories* — main/backup usable prose source after extraction validation.

Remaining desired source gap:

- An original public-domain edition of *The Picture of Dorian Gray* remains preferred but is not currently available in the repo. The uploaded `THE PICTURE OF DORIAN GRAY.pdf` should not be used for authorial-style analysis.

Rationale: Wilde is retained for aphoristic compression, wit, and balanced phrasing. The drama source is excluded to avoid genre confounds, and the retelling is excluded to avoid measuring Jill Nevile's adapted prose instead of Wilde's original style.

## Main corpus strategy after Step 2 update

The target remains:

\[
6 \text{ authors} \times 60 \text{ passages} = 360 \text{ original passages}
\]

Each passage should be:

\[
450-650 \text{ words}
\]

The preferred main works are:

| Author | Preferred source(s) |
|---|---|
| Austen | *Pride and Prejudice*, *Emma* |
| Dickens | *Great Expectations*, *Oliver Twist* |
| Poe | Selected prose tales; backup: *Arthur Gordon Pym* |
| Twain | *Huckleberry Finn*; desired backup: *Tom Sawyer* |
| Shelley | *Frankenstein* 1818, *The Last Man* |
| Wilde | *Lord Arthur Savile's Crime and Other Stories*; desired original *Dorian Gray* still missing |

## Important Step 2 update

The earlier Wilde prose source gap is now partially fixed. A usable Wilde prose-fiction collection has been added, but the uploaded *Dorian Gray* file is not valid for the main corpus because it is a retelling.

## Files maintained by Step 2

- `metadata/author_work_map.csv`
- `metadata/source_item_review.csv`
- `metadata/source_inventory.csv`
- `metadata/wilde_new_source_review.csv`
- `docs/corpus_selection_rationale.md`
- `docs/wilde_source_addendum.md`
- `logs/step_02_status.md`

## Next step

Step 3 should preserve and verify raw/extracted text states, including rechecking failed text extraction files and preparing reliable checksums for the extractable corpus.
