"""Scan Git's nonignored publication candidates without displaying secret values."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import zipfile

from .credentials import read_env
from .io import ROOT, file_hash, write_json

# Token boundaries avoid matching accidental `sk-` substrings inside opaque
# base64url ciphertext. Exact configured-secret matching never uses boundaries.
PATTERNS = (rb"(?<![0-9A-Za-z_-])AIza[0-9A-Za-z_-]{30,}",
            rb"(?<![0-9A-Za-z_-])(?:ghp_|github_pat_)[0-9A-Za-z_]{30,}",
            rb"(?<![0-9A-Za-z_-])sk-(?:proj-)?[0-9A-Za-z_-]{32,}",
            rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
MARKERS = ((b"AIza",), (b"ghp_", b"github_pat_"), (b"sk-",), (b"-----BEGIN",))


def pattern_match(data):
    return any(any(marker in data for marker in markers) and re.search(pattern, data)
               for markers, pattern in zip(MARKERS, PATTERNS))


def credential_values(env_file):
    needles = {v.encode() for k, v in read_env(env_file).items() if len(v) >= 12 and not v.startswith(("http://", "https://"))}
    for private in (ROOT / "revision/review_app/private", ROOT / "revision/expanded_v3/private/review_app"):
        for credential in (private / "credentials.json", private / "access.json"):
            if credential.exists():
                needles.update(v.encode() for v in json.loads(credential.read_text()).values() if isinstance(v, str) and len(v) >= 12)
        for db in private.glob("*.sqlite3"):
            with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as con:
                tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if "assignments" in tables:
                    needles.update(r[0].encode() for r in con.execute("SELECT token FROM assignments") if r[0])
    return needles


def scan(env_file):
    names = sorted(set(subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")) - {""})
    needles = credential_values(env_file)
    matches, inventory = [], {}
    for name in names:
        path = ROOT / name
        if not path.is_file():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            matches.append({"file": name, "reason": "unsafe_path"}); continue
        if (any(p.casefold() in {"private", "returns"} for p in Path(name).parts) or path.suffix.lower() in {".env", ".sqlite3", ".db"}
                or "private_access" in path.name.casefold() or path.name.casefold() in {"credentials.json", "private_join_key.csv", "reviewer_registry.json"}):
            matches.append({"file": name, "reason": "private_artifact"}); continue
        payloads = [path.read_bytes()]
        if path.suffix == ".gz":
            payloads.append(gzip.decompress(payloads[0]))
        elif path.suffix.lower() in {".zip", ".docx", ".xlsx"}:
            with zipfile.ZipFile(path) as archive:
                payloads.extend(archive.read(n) for n in archive.namelist() if not n.endswith("/"))
        if any(any(n in data for n in needles) or pattern_match(data) for data in payloads):
            matches.append({"file": name, "reason": "possible_secret_value"})
        if path.stat().st_size >= 100_000_000:
            matches.append({"file": name, "reason": "requires_large_file_handling"})
        inventory[name] = file_hash(path)
    result = {"passed": not matches, "candidate_files": len(inventory), "known_secret_values_checked": len(needles),
              "matches": matches, "compressed_members_scanned": True,
              "scope": "Nonignored Git candidates; exact configured secrets and key patterns, not a proof that every possible private detail is absent."}
    write_json(ROOT / "revision/expanded_v3/verification/git_publication_scan.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    result = scan(args.env_file)
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)
