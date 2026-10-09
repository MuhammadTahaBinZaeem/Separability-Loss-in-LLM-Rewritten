"""
Step 3 helper script: preserve raw source state.

Purpose
-------
This script is intended to be run locally after the raw PDFs are placed under
`data/raw/pdf/`. It creates checksum and extraction-status metadata used by
Step 3 of the research pipeline.

Important
---------
The ChatGPT GitHub connector used during initial setup could not upload large
binary PDFs directly. Therefore, raw PDF files should be added separately using
Git LFS, then this script can be run to recreate the checksum tables.

Expected local layout
---------------------
data/raw/pdf/
  austenJane/
  CharlesDicken/
  EdgarPoe/
  Marktwain/
  Marryshelly/
  Oscarwilde/

Outputs
-------
metadata/raw_file_checksums.csv
metadata/text_extraction_status_summary.csv
logs/raw_preservation_log.md
"""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
from pathlib import Path
from typing import Iterable

RAW_DIR = Path("data/raw/pdf")
TEXT_DIR = Path("data/raw/text_extracted")
METADATA_DIR = Path("metadata")
LOGS_DIR = Path("logs")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def pdf_page_count(path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdfinfo", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        match = re.search(r"^Pages:\s+(\d+)", result.stdout, re.MULTILINE)
        return match.group(1) if match else ""
    except Exception:
        return ""


def extract_text(path: Path, out_path: Path) -> tuple[str, int, int, str]:
    """Extract text using pdftotext and return status, bytes, words, checksum."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(path), str(out_path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except Exception:
        return "failed", 0, 0, ""

    if not out_path.exists():
        return "failed", 0, 0, ""

    text = out_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return "empty", 0, 0, ""

    text_bytes = len(text.encode("utf-8"))
    words = len(re.findall(r"\b[\w’'-]+\b", text))
    return "extracted", text_bytes, words, sha256_text(text)


def iter_pdfs(root: Path) -> Iterable[Path]:
    return sorted(root.rglob("*.pdf"), key=lambda p: p.as_posix().lower())


def main() -> None:
    METADATA_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    raw_rows: list[dict[str, str | int]] = []
    extraction_rows: list[dict[str, str | int]] = []

    pdfs = list(iter_pdfs(RAW_DIR))
    for pdf in pdfs:
        rel = pdf.relative_to(RAW_DIR).as_posix()
        pages = pdf_page_count(pdf)
        checksum = sha256_file(pdf)
        text_rel = Path(rel).with_suffix(".txt")
        text_out = TEXT_DIR / text_rel
        status, text_bytes, words, text_sha = extract_text(pdf, text_out)

        raw_rows.append(
            {
                "source_path": f"source/{rel}",
                "repo_target_path": f"data/raw/pdf/{rel}",
                "size_bytes": pdf.stat().st_size,
                "pdf_pages": pages,
                "sha256": checksum,
                "raw_committed_to_repo": "true",
                "preservation_status": "available_in_data_raw_pdf",
            }
        )

        extraction_rows.append(
            {
                "source_pdf": rel,
                "text_path": f"data/raw/text_extracted/{text_rel.as_posix()}",
                "status": status,
                "pdf_pages": pages,
                "text_bytes_utf8": text_bytes,
                "words": words,
                "sha256": text_sha,
            }
        )

    raw_out = METADATA_DIR / "raw_file_checksums.csv"
    with raw_out.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "source_path",
            "repo_target_path",
            "size_bytes",
            "pdf_pages",
            "sha256",
            "raw_committed_to_repo",
            "preservation_status",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(raw_rows)

    extracted_count = sum(1 for row in extraction_rows if row["status"] == "extracted")
    failed_count = len(extraction_rows) - extracted_count
    total_words = sum(int(row["words"]) for row in extraction_rows)
    total_bytes = sum(int(row["text_bytes_utf8"]) for row in extraction_rows)

    summary_out = METADATA_DIR / "text_extraction_status_summary.csv"
    with summary_out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["tracked_pdf_count", len(pdfs)])
        writer.writerow(["text_extraction_attempted_count", len(pdfs)])
        writer.writerow(["text_extraction_success_count", extracted_count])
        writer.writerow(["text_extraction_failed_count", failed_count])
        writer.writerow(["extraction_tool", "pdftotext -layout -enc UTF-8"])
        writer.writerow(["total_extracted_words", total_words])
        writer.writerow(["total_extracted_text_bytes_utf8", total_bytes])

    log_out = LOGS_DIR / "raw_preservation_log.md"
    log_out.write_text(
        "# Raw Preservation Log\n\n"
        f"PDFs found: {len(pdfs)}\n\n"
        f"Extracted: {extracted_count}\n\n"
        f"Failed or empty: {failed_count}\n\n"
        f"Total extracted words: {total_words}\n\n"
        f"Total extracted text bytes: {total_bytes}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
