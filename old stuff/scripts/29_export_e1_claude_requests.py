"""
E1 Claude-specific request exporter.

This creates Claude-targeted request files from the common E1 request design.
It does not call the API. Use the exported JSONL as the input for legitimate
Anthropic API workflows you are authorised to use.

Run:
    python scripts/29_export_e1_claude_requests.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUESTS_ALL = ROOT / "data" / "interim" / "e1_multillm_replication" / "requests" / "e1_rewrite_requests_all.jsonl"
OUT_DIR = ROOT / "data" / "interim" / "e1_multillm_replication" / "provider_exports" / "claude_sonnet_3_5"
OUT_FILE = OUT_DIR / "claude_sonnet_3_5_requests.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    if not REQUESTS_ALL.exists():
        subprocess.check_call([sys.executable, "scripts/26_e1_multillm_batch_manager.py", "prepare", "--chunk-size", "100"], cwd=ROOT)
    rows = [row for row in read_jsonl(REQUESTS_ALL) if row.get("replication_model_id") == "claude_sonnet_3_5"]
    exported = []
    for row in rows:
        exported.append({
            "request_id": row["request_id"],
            "provider": "anthropic",
            "model": row["provider_model_name"],
            "temperature": row["temperature"],
            "top_p": row["top_p"],
            "max_tokens": 3000,
            "system": row["system_prompt"],
            "messages": [
                {"role": "user", "content": row["user_prompt"]}
            ],
            "expected_response_format": row["output_schema_note"],
        })
    write_jsonl(OUT_FILE, exported)
    print(f"Exported {len(exported)} Claude requests to {OUT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
