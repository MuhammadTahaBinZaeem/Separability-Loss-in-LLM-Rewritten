"""
E1 local Ollama request exporter.

This exports blinded rewrite requests for a local/offline model workflow. It does
not call Ollama. Use the exported JSONL with a local model such as llama3.1,
mistral, qwen2.5, or any other model you can run legally on your own machine.

Run:
    python scripts/35_export_e1_ollama_local_requests.py
"""

from __future__ import annotations

import json
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "26_e1_multillm_batch_manager.py"
OUT_DIR = ROOT / "data" / "interim" / "e1_free_model_replication" / "provider_exports" / "ollama_local"
OUT_FILE = OUT_DIR / "ollama_local_requests.jsonl"

spec = importlib.util.spec_from_file_location("e1_batch_manager", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)  # type: ignore[union-attr]

MODEL = {
    "replication_model_id": "ollama_local_qwen_or_llama",
    "provider": "local_ollama",
    "provider_label": "Local Ollama open model candidate",
    "provider_model_name": "qwen2.5:7b-instruct-or-llama3.1:8b-instruct",
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
            "provider": "local_ollama",
            "suggested_models": ["qwen2.5:7b-instruct", "llama3.1:8b-instruct", "mistral:7b-instruct"],
            "temperature": row["temperature"],
            "top_p": row["top_p"],
            "prompt": row["system_prompt"] + "\n\n" + row["user_prompt"],
            "expected_response_format": row["output_schema_note"],
        })
    write_jsonl(OUT_FILE, exported)
    print(f"Exported {len(exported)} local Ollama requests to {OUT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
