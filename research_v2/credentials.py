"""Explicit, non-executing local secret loading; no values in logs or artifacts."""
from __future__ import annotations

import re
from pathlib import Path


def read_env(path: Path) -> dict[str,str]:
    values={}
    for number,line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(),1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match=re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)",line)
        if not match:
            raise ValueError(f"Invalid environment-file syntax at line {number}; contents withheld")
        key,value=match.groups()
        if key in values:
            raise ValueError(f"Duplicate environment variable at line {number}")
        value=value.strip()
        if len(value)>=2 and value[0]==value[-1] and value[0] in {"'",'"'}:
            value=value[1:-1]
        if "\x00" in value or "\r" in value or "\n" in value:
            raise ValueError(f"Invalid control character at line {number}")
        values[key]=value
    return values
