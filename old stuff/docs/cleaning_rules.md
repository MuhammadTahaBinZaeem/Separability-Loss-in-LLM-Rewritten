# Step 4 Cleaning Rules

## Step

**Step 4 — Text Cleaning Rules and Metadata Removal**

## Purpose

Step 4 defines deterministic cleaning rules for converting extracted PDF text into research-usable literary text while preserving stylistic signals needed for the paper.

The central research object is authorial style separability. Therefore, cleaning must be conservative. It must remove source noise and metadata, but it must **not** erase punctuation, sentence rhythm, dialect-like prose, archaic spelling, quotation structure, or author-specific syntax.

## Cleaning philosophy

The cleaning process should remove things that are clearly not part of the literary text:

- PDF extraction artifacts
- page headers and footers
- page numbers
- publisher metadata
- title-page material
- table of contents material
- OCR/layout leftovers
- excessive whitespace
- repeated source banners

The cleaning process should preserve things that may carry style:

- punctuation
- semicolons
- dashes
- ellipses
- quotation marks
- contractions
- archaic spellings
- dialect-like spelling
- paragraph breaks
- sentence length variation
- capitalization inside literary prose

## Main cleaning stages

### 1. UTF-8 normalization

- Read files as UTF-8 with replacement for invalid characters.
- Normalize line endings to `\n`.
- Remove null bytes and control characters except newline and tab.

### 2. Unicode punctuation normalization

Normalize only visually equivalent punctuation:

- curly double quotes remain quotes but may be normalized consistently
- curly single quotes remain apostrophes/quotes
- em dash and en dash are preserved as dash-like punctuation, not deleted
- ellipses are preserved as ellipsis or three dots consistently

Do **not** remove punctuation.

### 3. Page artifact removal

Remove lines that are likely pure page artifacts:

- lines containing only digits
- lines containing page-like markers
- repeated title/author headers if they appear across many pages
- isolated form-feed markers

### 4. Source metadata removal

Remove obvious front/back matter such as:

- Project Gutenberg boilerplate
- PDF Room banners if present
- Standard Ebooks front-matter if outside the literary work
- copyright pages
- scanner notes
- table of contents
- index material
- publisher advertisements

Boundary decisions for complete-works/container PDFs must be documented later in Step 5/Step 6.

### 5. Whitespace repair

- Collapse more than two blank lines to two blank lines.
- Collapse repeated spaces within lines.
- Preserve paragraph boundaries.
- Do not join all lines into one block.

### 6. Hyphenation handling

PDF extraction may split words at line breaks:

```text
exam-
ple
```

The cleaner may repair simple hyphenated line breaks only when the split clearly occurs inside a word. It must not remove stylistic dashes.

### 7. Deletion logging

Every cleaned file must record before/after counts:

- raw characters
- cleaned characters
- raw words
- cleaned words
- raw lines
- cleaned lines
- removed line count
- cleaning warning flags

## Explicitly forbidden cleaning actions

The cleaner must not:

- lowercase all text
- remove punctuation
- remove quotation marks
- remove apostrophes
- remove contractions
- standardize dialect spellings
- modernize archaic spelling
- remove semicolons/dashes/exclamation marks
- sentence-tokenize and rejoin the text destructively
- remove all short lines automatically
- remove dialogue-heavy passages automatically

## Author-specific protection notes

### Jane Austen

Preserve syntactic structure, semicolons, commas, and clause movement. These may support irony-bearing syntax and social narration.

### Edgar Allan Poe

Preserve punctuation intensity, dashes, exclamation marks, semicolons, and rhythm-shaping punctuation.

### Mark Twain

Preserve colloquial spelling, contractions, dialect-like prose, and speech-like rhythm.

### Oscar Wilde

Preserve aphoristic compression, balanced punctuation, short polished sentence structures, and witty phrasing.

### Charles Dickens

Preserve descriptive accumulation, long sentences, comma chains, and catalog-like prose.

### Mary Shelley

Preserve elevated diction, Gothic register, emotional abstraction, and older syntactic forms.

## Output locations

Expected input:

```text
data/raw/text_extracted/
```

Expected output:

```text
data/interim/cleaned_books/
```

Expected report:

```text
logs/cleaning_report.csv
```

## Step 4 completion standard

Step 4 is complete when the repository contains:

- this cleaning-rules document
- a deterministic cleaning configuration
- a cleaning script
- a cleaning report schema
- a status report explaining whether actual cleaned text files were generated or deferred

Actual cleaned text generation requires extracted text files to be present locally or regenerated from raw PDFs.
