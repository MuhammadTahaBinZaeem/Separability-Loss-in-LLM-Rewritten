# Step 2 Status Report

## Step

**Step 2 — Corpus Inventory and Author-Work Map**

## Status

Complete, with Wilde source gap partially repaired after additional uploads.

## Files created or updated

- `metadata/author_work_map.csv`
- `metadata/source_item_review.csv`
- `metadata/source_inventory.csv`
- `metadata/wilde_new_source_review.csv`
- `docs/corpus_selection_rationale.md`
- `docs/wilde_source_addendum.md`
- `logs/step_02_status.md`

## What Step 2 did

Step 2 converted the uploaded source inventory into a formal author/work map for the six-author literary corpus.

The main corpus remains focused on English prose fiction, not poetry, drama, essays, travel writing, letters, biography, or mixed editorial matter.

## Locked target authors

- Jane Austen
- Edgar Allan Poe
- Mark Twain
- Oscar Wilde
- Charles Dickens
- Mary Shelley

## Target corpus size

The intended original corpus remains:

```text
6 authors × 60 passages = 360 original passages
```

Each passage should later be extracted at approximately:

```text
450–650 words
```

## Main work candidates after Step 2 update

| Author | Main candidate works/status |
|---|---|
| Jane Austen | `Pride and Prejudice`, `Emma` from complete-works PDF |
| Charles Dickens | `Great Expectations`, `Oliver Twist` from individual PDFs |
| Edgar Allan Poe | selected prose fiction tales from complete-works PDF |
| Mark Twain | `Adventures of Huckleberry Finn` from uploaded volume |
| Mary Shelley | `Frankenstein` 1818 and `The Last Man` from complete-works PDF |
| Oscar Wilde | `Lord Arthur Savile’s Crime and Other Stories` from newly uploaded prose-fiction PDF |

## Wilde source update

The earlier Wilde source gap is now partially repaired.

New usable Wilde source:

```text
Lord Arthur Savile’s Crime and Other Stories - Oscar Wilde - PDF Room.pdf
```

This is accepted as a usable prose-fiction Wilde source after extraction validation.

Still excluded:

```text
Complete works of Oscar Wilde (1921) 6.pdf
```

Reason: drama volume, not suitable for the main prose-fiction corpus.

Also excluded:

```text
THE PICTURE OF DORIAN GRAY.pdf
```

Reason: Oxford Bookworms 1989 retelling by Jill Nevile, not Wilde's original prose. It must not be used for authorial-style analysis.

Remaining desired source gap:

```text
Original public-domain The Picture of Dorian Gray
```

This remains preferred but is not currently available in the repo.

## Other notes

- Austen, Shelley, and Poe are stored as complete/container PDFs, so later steps must extract internal work boundaries.
- Dickens has many individual PDFs and is source-rich.
- Twain appears to have one usable main source, `Huckleberry Finn`; a second Twain work would improve balance but is not strictly required if 60 passages can be extracted cleanly.
- Some Dickens short works or previously failed extraction files need rechecking in Step 3/Step 4.

## Step 2 completion judgment

Step 2 is complete because the repository now contains a formal author-work map, source-level decisions, and corpus-selection rationale.

The project may proceed to Step 3. Wilde is no longer completely missing, but the preferred original *Dorian Gray* source is still absent and the uploaded retelling is excluded.
