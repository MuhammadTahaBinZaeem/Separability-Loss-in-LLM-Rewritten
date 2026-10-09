"""Deterministic UTF-8/LF artifacts and explicit cryptographic provenance."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "revision"


def normalized_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_text(value: str) -> str:
    return digest_bytes(normalized_text(value).encode("utf-8"))


def file_hash(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return [{k: normalized_text(v) if isinstance(v, str) else v for k, v in row.items()}
                for row in csv.DictReader(stream)]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalized_text(text), encoding="utf-8", newline="\n")


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if not fields and not rows:
        raise ValueError("Empty tables require explicit columns")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    write_text(path, "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
