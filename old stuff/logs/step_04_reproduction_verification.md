# Step 4 Reproduction Verification

## Purpose

This file verifies that the committed cleaning script is the script used to produce the Step 4 cleaned outputs.

## Verification method

A fresh local verification directory was created. The Step 3 extracted text files were copied into:

```text
data/raw/text_extracted/
```

The committed Step 4 cleaning configuration was placed at:

```text
metadata/cleaning_config.json
```

The committed Step 4 cleaning script was run:

```bash
python scripts/01_clean_texts.py
```

The regenerated cleaned text files were compared against the previously generated Step 4 cleaned outputs.

## Verification result

- cleaned files compared: 29
- exact SHA256 matches: 29
- mismatches: 0
- regenerated cleaning report matched previous cleaning report: yes

## Script identity

Committed script:

```text
scripts/01_clean_texts.py
```

Local verification SHA256 of script content:

```text
04913c4b2c3fa3c9716ab164b6bda17f77e7c453ee90b4508c5463eaaa29f8f5
```

## Configuration identity

Committed config:

```text
metadata/cleaning_config.json
```

Local verification SHA256 of config content:

```text
4740f7bf2e1fa6e6c8f5532969b2259cd47427a197f6d5e0ea02225987e087a3
```

## Cleaning report identity

Regenerated report:

```text
logs/cleaning_report.csv
```

SHA256:

```text
dc7d0c20395bf09013037bf33fd1dca6750b31979141b170d9046a5c0966b28f
```

## Local cleaned-output archive

The local archive created for handoff is:

```text
litpaper_step4_cleaned_outputs.zip
```

Archive SHA256:

```text
5c927f65a55af5dc68994a75f19432ad95e6acbe16406d570208caa7235cdf6d
```

## Conclusion

The committed `scripts/01_clean_texts.py` and `metadata/cleaning_config.json` reproduce the Step 4 cleaned outputs exactly. This verifies that the script in the repository is the script used for the Step 4 cleaning run.
