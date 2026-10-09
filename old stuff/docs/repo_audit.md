# Step 1 Repository Audit

## Project

**Repository:** `MuhammadTahaBinZaeem/litpaper`  
**Default branch:** `main`  
**Visibility:** public  
**Research title:** *Authorial Style Separability Loss in LLM-Rewritten Fiction: A Controlled Stylometric Framework for Measuring Literary Style Flattening*

## Step 1 purpose

Step 1 establishes the repository as a reproducible research workspace. It does **not** perform cleaning, passage extraction, rewriting, feature extraction, or analysis. Its job is to preserve the current source-state information, create the project skeleton, and define the rules for the remaining 19 steps.

## Current repository state after Step 1–3 consistency repair

The repository has been initialized and hardened with:

- `README.md`
- `.gitignore`
- `requirements.txt`
- `environment.yml`
- `docs/repo_audit.md`
- `docs/pipeline_20_steps.md`
- `docs/data_dictionary.md`
- `docs/reproducibility.md`
- `docs/raw_source_handling.md`
- `metadata/source_inventory.csv`
- `metadata/raw_file_checksums.csv`
- `metadata/text_extraction_status_summary.csv`
- `logs/step_01_status.md`
- `logs/step_02_status.md`
- `logs/raw_preservation_log.md`

## Uploaded source archive summary

The original uploaded archive inspected in this session was:

- Local file: `/mnt/data/source.zip`
- Files found in original ZIP: 27 PDFs
- Original ZIP PDF bytes: 162,141,311
- Top-level archive folder: `source/`
- Author folders detected:
  - `austenJane/`
  - `CharlesDicken/`
  - `EdgarPoe/`
  - `Marktwain/`
  - `Marryshelly/`
  - `Oscarwilde/`

Two additional Oscar Wilde PDFs were uploaded later, so the current tracked source inventory contains:

- Current tracked PDFs: 29
- Original ZIP PDFs: 27
- Later uploaded Wilde PDFs: 2

The detailed file-level inventory is stored in:

- `metadata/source_inventory.csv`
- `metadata/raw_file_checksums.csv`

## Raw PDF status

Raw PDFs are **not yet committed into the repository** as binary files. The available GitHub connector in this chat can write UTF-8 text files but does not expose a direct local binary-file upload action for large PDFs. Because of this, Step 1 and Step 3 preserve traceability through file names, sizes, page counts, and SHA256 checksums rather than pretending the PDF upload succeeded.

Recommended raw-PDF preservation route:

```bash
git lfs install
git lfs track "*.pdf"
mkdir -p data/raw/pdf
unzip source.zip -d /tmp/litpaper_source
rsync -av /tmp/litpaper_source/source/ data/raw/pdf/
# manually copy later uploaded Wilde PDFs into data/raw/pdf/Oscarwilde/
git add .gitattributes data/raw/pdf metadata/source_inventory.csv metadata/raw_file_checksums.csv
git commit -m "Add raw PDF sources via Git LFS"
git push
```

## Text extraction status

A Step 3 extraction pass was performed locally using:

```text
pdftotext -layout -enc UTF-8
```

Summary:

- PDFs attempted: 29
- Successful text extractions: 29
- Failed or empty extractions: 0
- Total extracted word count: 8,245,542
- Total extracted text bytes: 44,782,448

The earlier preliminary `metadata/text_extraction_manifest.csv` was removed because it contained stale `not_extracted_yet` rows after the source set changed. Current extraction status is stored in:

- `metadata/text_extraction_status_summary.csv`
- `logs/raw_preservation_log.md`

Important: Step 3 still does not treat these extracted texts as final research data. Text cleaning and validation are handled later in the pipeline.

## Project skeleton added in Step 1

The repository is organized around this intended structure:

```text
data/
  raw/
    pdf/
    text_extracted/
  interim/
  processed/
    original_passages/
    rewrites/
    features/
  final/
metadata/
scripts/
notebooks/
results/
  tables/
  figures/
logs/
docs/
```

Because Git does not track empty directories, `.gitkeep` files are used where necessary.

## Research direction locked for the repository

The repository is for one paper only:

> **Authorial Style Separability Loss in LLM-Rewritten Fiction: A Controlled Stylometric Framework for Measuring Literary Style Flattening**

Core research question:

> How do controlled LLM rewriting operations affect measurable authorial style separability across lexical, syntactic, rhythmic, and distributional stylometric dimensions in public-domain fiction?

Mandatory methods:

- Burrows’ Delta
- function-word analysis
- sentence-length distributions
- POS distributions
- inter-author distance
- statistical testing
- author-specific literary interpretation

Locked main authors:

- Jane Austen
- Edgar Allan Poe
- Mark Twain
- Oscar Wilde
- Charles Dickens
- Mary Shelley

Locked rewriting tasks:

1. Paraphrase
2. Modernize
3. Simplify

Summarization is not part of the main experiment because it introduces a major length confound.

## Step 1 completion criteria

Step 1 is complete when the repository contains:

- project README
- raw source inventory
- raw source handling note
- repository audit
- 20-step pipeline protocol
- initial data dictionary stub
- reproducibility stub
- directory skeleton
- environment/dependency stub
- clear statement of what has and has not been uploaded

## Step 1 limitations

- Raw PDFs are inventoried but not physically uploaded through this connector.
- No cleaned corpus exists yet.
- No final passage dataset exists yet.
- No LLM rewrites exist yet.
- No stylometric features or results exist yet.

## Step 1 completion judgment

Step 1 is now internally consistent after the Step 3 source-status repair. The raw binary upload limitation remains documented rather than hidden.

## Next step

Step 4 should define and apply deterministic text cleaning rules after the Step 3 preservation state is finalized.
