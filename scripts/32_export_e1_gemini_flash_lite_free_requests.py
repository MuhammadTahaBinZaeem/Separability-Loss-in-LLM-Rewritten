"""
E1 free-access Gemini Flash-Lite request exporter.

This exports blinded rewrite requests for a Gemini free-tier-friendly model.
It does not call the API. Use the exported JSONL with legitimate Google AI
Studio / Gemini API access.

Run:
    python scripts/32_export_e1_gemini_flash_lite_free_requests.py
"""

from __future__ import annotations

import json
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "26_e1_multillm_batch_manager.py"
OUT_DIR = ROOT / "data" / "interim" / "e1_free_model_replication" / "provider_exports" / "gemini_flash_lite_free"
OUT_FILE = OUT_DIR / "gemini_flash_lite_free_requests.jsonl"

spec = importlib.util.spec_from_file_location("e1_batch_manager", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)  # type: ignore[union-attr]

MODEL = {
    "replication_model_id": "gemini_flash_lite_free",
    "provider": "google",
    "provider_label": "Gemini Flash-Lite free-tier candidate",
    "provider_model_name": "gemini-3.1-flash-lite",
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
            "provider": "google",
            "model": row["provider_model_name"],
            "generation_config": {
                "temperature": row["temperature"],
                "top_p": row["top_p"],
                "response_mime_type": "application/json",
            },
            "contents": [
                {"role": "user", "parts": [{"text": row["system_prompt"] + "\n\n" + row["user_prompt"]}]}
            ],
            "expected_response_format": row["output_schema_note"],
        })
    write_jsonl(OUT_FILE, exported)
    print(f"Exported {len(exported)} Gemini Flash-Lite requests to {OUT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
