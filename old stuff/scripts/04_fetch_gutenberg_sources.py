"""
Fetch canonical Project Gutenberg plain-text sources.

Run from repository root with internet access:

    python scripts/04_fetch_gutenberg_sources.py

Outputs:
- data/raw/gutenberg_texts/*.txt
- metadata/gutenberg_raw_text_checksums.csv
- logs/gutenberg_fetch_report.md

This script uses repository-relative paths only. It can be run from a local
machine or GitHub Actions without editing hard-coded absolute paths.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "metadata" / "gutenberg_canonical_registry.csv"
ALIAS_PATH = ROOT / "metadata" / "gutenberg_alias_map.csv"
OUTPUT_DIR = ROOT / "data" / "raw" / "gutenberg_texts"
CHECKSUM_PATH = ROOT / "metadata" / "gutenberg_raw_text_checksums.csv"
REPORT_PATH = ROOT / "logs" / "gutenberg_fetch_report.md"
WORD_RE = re.compile(r"\b[\w’'-]+\b", flags=re.UNICODE)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fetch_text(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "litpaper-research-source-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read()
    return data.decode("utf-8", errors="replace")


def strip_gutenberg_boilerplate(text: str) -> tuple[str, str, str]:
    start_patterns = [
        r"\*\*\* START OF THE PROJECT GUTENBERG EBOOK .*?\*\*\*",
        r"\*\*\* START OF THIS PROJECT GUTENBERG EBOOK .*?\*\*\*",
    ]
    end_patterns = [
        r"\*\*\* END OF THE PROJECT GUTENBERG EBOOK .*?\*\*\*",
        r"\*\*\* END OF THIS PROJECT GUTENBERG EBOOK .*?\*\*\*",
    ]

    start_status = "start_marker_not_found"
    end_status = "end_marker_not_found"
    body = text.replace("\r\n", "\n").replace("\r", "\n")

    for pattern in start_patterns:
        match = re.search(pattern, body, flags=re.IGNORECASE | re.DOTALL)
        if match:
            body = body[match.end():]
            start_status = "start_marker_removed"
            break

    for pattern in end_patterns:
        match = re.search(pattern, body, flags=re.IGNORECASE | re.DOTALL)
        if match:
            body = body[:match.start()]
            end_status = "end_marker_removed"
            break

    return body.strip() + "\n", start_status, end_status


def get_alias_rows() -> dict[str, str]:
    if not ALIAS_PATH.exists():
        return {}
    return {row["canonical_id"]: row["alias_id"] for row in read_csv(ALIAS_PATH)}


def safe_filename(row: dict[str, str], aliases: dict[str, str]) -> str:
    alias_id = aliases.get(row["canonical_id"], row["canonical_id"])
    return f"{alias_id}.txt"


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def main() -> int:
    if not REGISTRY_PATH.exists():
        print(f"Missing registry: {REGISTRY_PATH}", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHECKSUM_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows = read_csv(REGISTRY_PATH)
    aliases = get_alias_rows()
    out_rows: list[dict[str, str | int]] = []
    report_lines = [
        "# Gutenberg Fetch Report",
        "",
        f"Run timestamp UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    failures = 0
    for row in rows:
        out_file = OUTPUT_DIR / safe_filename(row, aliases)
        try:
            raw = fetch_text(row["plain_text_url"])
            body, start_status, end_status = strip_gutenberg_boilerplate(raw)
            out_file.write_text(body, encoding="utf-8")
            word_count = count_words(body)
            out_rows.append({
                "canonical_id": row["canonical_id"],
                "alias_id": aliases.get(row["canonical_id"], row["canonical_id"]),
                "author_id": row["author_id"],
                "work_id": row["work_id"],
                "gutenberg_ebook_no": row["gutenberg_ebook_no"],
                "plain_text_url": row["plain_text_url"],
                "local_path": out_file.relative_to(ROOT).as_posix(),
                "text_bytes_utf8": len(body.encode("utf-8")),
                "chars": len(body),
                "words": word_count,
                "sha256": sha256_text(body),
                "start_marker_status": start_status,
                "end_marker_status": end_status,
                "fetch_status": "ok",
            })
            report_lines.append(f"- OK {row['canonical_id']} -> {out_file.name}: {word_count} words")
        except Exception as exc:
            failures += 1
            out_rows.append({
                "canonical_id": row["canonical_id"],
                "alias_id": aliases.get(row["canonical_id"], row["canonical_id"]),
                "author_id": row["author_id"],
                "work_id": row["work_id"],
                "gutenberg_ebook_no": row["gutenberg_ebook_no"],
                "plain_text_url": row["plain_text_url"],
                "local_path": out_file.relative_to(ROOT).as_posix(),
                "text_bytes_utf8": 0,
                "chars": 0,
                "words": 0,
                "sha256": "",
                "start_marker_status": "not_processed",
                "end_marker_status": "not_processed",
                "fetch_status": f"failed: {exc}",
            })
            report_lines.append(f"- FAIL {row['canonical_id']}: {exc}")

    fieldnames = [
        "canonical_id", "alias_id", "author_id", "work_id", "gutenberg_ebook_no", "plain_text_url", "local_path",
        "text_bytes_utf8", "chars", "words", "sha256", "start_marker_status", "end_marker_status", "fetch_status",
    ]
    with CHECKSUM_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    report_lines.extend(["", f"Failures: {failures}"])
    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"Fetched {len(rows) - failures}/{len(rows)} Gutenberg sources")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
