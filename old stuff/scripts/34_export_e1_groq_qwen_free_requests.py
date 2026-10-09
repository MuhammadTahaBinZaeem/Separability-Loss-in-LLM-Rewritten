"""
E1 free-access Groq Qwen request exporter.

This exports blinded rewrite requests for a Groq-hosted Qwen model candidate.
It does not call the API. Use the exported JSONL with legitimate Groq API access.

Run:
    python scripts/34_export_e1_groq_qwen_free_requests.py
"""

from __future__ import annotations

import json
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "26_e1_multillm_batch_manager.py"
OUT_DIR = ROOT / "data" / "interim" / "e1_free_model_replication" / "provider_exports" / "groq_qwen_free"
OUT_FILE = OUT_DIR / "groq_qwen_free_requests.jsonl"

spec = importlib.util.spec_from_file_location("e1_batch_manager", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)  # type: ignore[union-attr]

MODEL = {
    "replication_model_id": "groq_qwen_free",
    "provider": "groq",
    "provider_label": "Groq Qwen free-tier candidate",
    "provider_model_name": "qwen-qwq-32b",
    "default_runs": 1,
}


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    rows = helper.build_requests([MODEL], {})
    exported = []
    for row in rows:
        exported.append({
            "request_id": row["request_id"],
            "provider": "groq",
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
    print(f"Exported {len(exported)} Groq Qwen requests to {OUT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
