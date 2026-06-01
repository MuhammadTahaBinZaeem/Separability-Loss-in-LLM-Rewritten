"""
E1 OpenAI-specific request exporter.

This creates OpenAI-targeted request files from the common E1 request design.
It does not call the API. Use the exported JSONL as the input for whichever
legitimate OpenAI API workflow you are authorised to use.

Run:
    python scripts/27_export_e1_openai_requests.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUESTS_ALL = ROOT / "data" / "interim" / "e1_multillm_replication" / "requests" / "e1_rewrite_requests_all.jsonl"
OUT_DIR = ROOT / "data" / "interim" / "e1_multillm_replication" / "provider_exports" / "openai_gpt4o"
OUT_FILE = OUT_DIR / "openai_gpt4o_requests.jsonl"


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
    rows = [row for row in read_jsonl(REQUESTS_ALL) if row.get("replication_model_id") == "gpt_4o"]
    exported = []
    for row in rows:
        exported.append({
            "request_id": row["request_id"],
            "provider": "openai",
            "model": row["provider_model_name"],
            "temperature": row["temperature"],
            "top_p": row["top_p"],
            "messages": [
                {"role": "system", "content": row["system_prompt"]},
                {"role": "user", "content": row["user_prompt"]},
            ],
            "expected_response_format": row["output_schema_note"],
        })
    write_jsonl(OUT_FILE, exported)
    print(f"Exported {len(exported)} OpenAI requests to {OUT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
