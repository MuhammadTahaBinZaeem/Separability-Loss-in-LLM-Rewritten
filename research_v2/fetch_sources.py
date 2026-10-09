"""Fetch and freeze public Gutenberg text; never silently replace a frozen source."""
from __future__ import annotations

import argparse
import time
import urllib.request
from datetime import datetime, timezone

from .io import OUT, file_hash, read_json, write_json

SOURCES = {
    1342: ("austen", "Pride and Prejudice"),
    158: ("austen", "Emma"),
    105: ("austen", "Persuasion"),
    1400: ("dickens", "Great Expectations"),
    730: ("dickens", "Oliver Twist"),
    98: ("dickens", "A Tale of Two Cities"),
    2147: ("poe", "The Works of Edgar Allan Poe Volume 1"),
    2148: ("poe", "The Works of Edgar Allan Poe Volume 2"),
    84: ("shelley", "Frankenstein"),
    18247: ("shelley", "The Last Man"),
    15238: ("shelley", "Mathilda"),
    76: ("twain", "Adventures of Huckleberry Finn"),
    74: ("twain", "The Adventures of Tom Sawyer"),
    86: ("twain", "A Connecticut Yankee in King Arthur's Court"),
    174: ("wilde", "The Picture of Dorian Gray"),
    773: ("wilde", "Lord Arthur Savile's Crime and Other Stories"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", nargs="*", type=int, default=sorted(SOURCES))
    args = parser.parse_args()
    for gid in args.ids:
        author, title = SOURCES[gid]
        dest = OUT / "sources" / f"pg{gid}.txt"
        meta = dest.with_suffix(".json")
        if dest.exists():
            if not meta.exists() or read_json(meta)["raw_sha256"] != file_hash(dest):
                raise ValueError(f"Source integrity failure: {dest}")
            print(f"Verified cached Gutenberg {gid}", flush=True)
            continue
        url = f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt"
        request = urllib.request.Request(url, headers={"User-Agent": "SeparabilityResearch/2.0 source-archival"})
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
        if b"GUTENBERG" not in raw.upper()[:20000]:
            raise ValueError(f"Unexpected source response for {gid}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        write_json(meta, {"gutenberg_id": gid, "author_id": author, "volume_title": title,
                         "canonical_url": f"https://www.gutenberg.org/ebooks/{gid}",
                         "download_url": url, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                         "raw_sha256": file_hash(dest), "raw_size_bytes": len(raw),
                         "copyright_notice": "See original source header and Gutenberg licence in the archived text."})
        print(f"Archived Gutenberg {gid}: {len(raw)} bytes", flush=True)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
