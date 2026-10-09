# Reproducibility Notes

This file is initialized in Step 1 and will become the full reproducibility guide by Step 20.

## Reproducibility goals

A future researcher should be able to reconstruct the final datasets and results from:

1. raw source files or their exact checksums,
2. deterministic scripts,
3. fixed prompt templates,
4. stored LLM outputs,
5. logged metadata,
6. recorded environment/dependency versions,
7. final repository commit.

## Important LLM reproducibility rule

LLM output generation is not perfectly reproducible unless raw outputs are stored. Therefore, the project must preserve:

- input passage,
- prompt template,
- model name,
- model version if available,
- generation timestamp,
- raw output,
- cleaned output,
- output checksum.

The pipeline should be reproducible from stored LLM outputs, and auditable from the prompts and metadata.

## Environment

Environment files are initialized in Step 1:

- `requirements.txt`
- `environment.yml`

These will be updated when scripts are added.

## Current Step 1 limitation

Raw PDFs are inventoried by checksum but are not physically uploaded through the available connector. Use Git LFS to preserve PDFs in the repository if full raw-file storage is required.
