"""
Export Gutenberg candidate passages to chunked Markdown files.

Run from repository root after `scripts/05_run_canonical_migration.py`:

    python scripts/06_export_gutenberg_candidates_md.py

Input:
- data/interim/gutenberg_candidate_passages.csv

Outputs:
- data/interim/gutenberg_candidate_passages_md/gutenberg_candidate_passages_part_###.md
- data/interim/gutenberg_candidate_passages_md/index.md
- metadata/gutenberg_candidate_text_md_manifest.csv

Purpose:
Keep the full candidate text visible in repository-friendly Markdown chunks while
keeping exact metadata in CSV files.
"""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_CSV = ROOT / "data" / "interim" / "gutenberg_candidate_passages.csv"
OUT_DIR = ROOT / "data" / "interim" / "gutenberg_candidate_passages_md"
MANIFEST = ROOT / "metadata" / "gutenberg_candidate_text_md_manifest.csv"
MAX_PART_BYTES = 850_000


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_candidates() -> list[dict[str, str]]:
    with CANDIDATE_CSV.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def header(part: int) -> str:
    return (
        f"# Gutenberg Candidate Passages — Part {part:03d}\n\n"
        "This file stores candidate passage text as Markdown for repository visibility. "
        "Exact row-level metadata is stored in `metadata/gutenberg_candidate_passage_metadata.csv`.\n\n"
    )


def block(row: dict[str, str]) -> str:
    text = row["text"].replace("\r\n", "\n").replace("\r", "\n")
    return (
        f"## {row['candidate_id']}\n\n"
        f"- canonical_id: `{row['canonical_id']}`\n"
        f"- alias_id: `{row.get('alias_id', '')}`\n"
        f"- author_id: `{row['author_id']}`\n"
        f"- work_id: `{row['work_id']}`\n"
        f"- word_count: `{row['word_count']}`\n"
        f"- sentence_count: `{row['sentence_count']}`\n\n"
        f"```text\n{text}\n```\n\n"
    )


def write_manifest(rows: list[dict[str, object]]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["part", "path", "size_bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if not CANDIDATE_CSV.exists():
        print(f"Missing input: {CANDIDATE_CSV}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("gutenberg_candidate_passages_part_*.md"):
        old.unlink()

    candidates = read_candidates()
    manifest_rows: list[dict[str, object]] = []
    part = 1
    chunks = [header(part)]
    current_bytes = len(chunks[0].encode("utf-8"))

    def flush() -> None:
        nonlocal part, chunks, current_bytes
        path = OUT_DIR / f"gutenberg_candidate_passages_part_{part:03d}.md"
        path.write_text("".join(chunks), encoding="utf-8")
        manifest_rows.append({
            "part": part,
            "path": path.relative_to(ROOT).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha_file(path),
        })
        part += 1
        chunks = [header(part)]
        current_bytes = len(chunks[0].encode("utf-8"))

    for row in candidates:
        passage_block = block(row)
        block_bytes = len(passage_block.encode("utf-8"))
        if len(chunks) > 1 and current_bytes + block_bytes > MAX_PART_BYTES:
            flush()
        chunks.append(passage_block)
        current_bytes += block_bytes

    if len(chunks) > 1:
        flush()

    index_lines = [
        "# Gutenberg Candidate Passage Text Index\n\n",
        "The candidate passage text is stored in chunked Markdown files.\n\n",
        "## Parts\n\n",
    ]
    for row in manifest_rows:
        index_lines.append(f"- `{row['path']}` — {row['size_bytes']} bytes\n")
    index_lines.extend([
        "\n## Metadata\n\n",
        "- `metadata/gutenberg_candidate_passage_metadata.csv` stores row metadata without passage text.\n",
        "- `metadata/gutenberg_candidate_text_md_manifest.csv` stores chunk paths and checksums.\n",
    ])
    (OUT_DIR / "index.md").write_text("".join(index_lines), encoding="utf-8")
    write_manifest(manifest_rows)
    print(f"Exported {len(candidates)} candidates to {len(manifest_rows)} Markdown chunks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
