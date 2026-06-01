"""
E1 Gemini-specific request exporter.

This creates Gemini-targeted request files from the common E1 request design.
It does not call the API. Use the exported JSONL as the input for legitimate
Google AI Studio / Gemini API workflows you are authorised to use.

Run:
    python scripts/28_export_e1_gemini_requests.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUESTS_ALL = ROOT / "data" / "interim" / "e1_multillm_replication" / "requests" / "e1_rewrite_requests_all.jsonl"
OUT_DIR = ROOT / "data" / "interim" / "e1_multillm_replication" / "provider_exports" / "gemini_1_5_pro"
OUT_FILE = OUT_DIR / "gemini_1_5_pro_requests.jsonl"


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
    rows = [row for row in read_jsonl(REQUESTS_ALL) if row.get("replication_model_id") == "gemini_1_5_pro"]
    exported = []
    for row in rows:
        exported.append({
            "request_id": row["request_id"],
            "provider": "google",
            "model": row["provider_model_name"],
            "generation_config": {
                "temperature": row["temperature"],
                "top_p": row["top_p"],
                "response_mime_type": "application/json",
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": row["system_prompt"] + "\n\n" + row["user_prompt"]}
                    ],
                }
            ],
            "expected_response_format": row["output_schema_note"],
        })
    write_jsonl(OUT_FILE, exported)
    print(f"Exported {len(exported)} Gemini requests to {OUT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
