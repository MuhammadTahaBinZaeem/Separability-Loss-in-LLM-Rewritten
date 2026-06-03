"""
E1 combined multi-LLM batch manager.

This script is intentionally provider-neutral. It does not call paid APIs and it
never manages multiple accounts. It prepares separated request batches, then
imports response files that you generated through authorised provider access.

Main modes:

    # 1) Prepare all request batches, registry, and report.
    python scripts/26_e1_multillm_batch_manager.py prepare --chunk-size 100

    # 2) After you place response JSONL files in the incoming folder, import/QC them.
    python scripts/26_e1_multillm_batch_manager.py import

    # 3) Show current completion counts.
    python scripts/26_e1_multillm_batch_manager.py status

All E1 outputs are kept separate from the original Gemini Flash core dataset.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MASTER_DATASET = ROOT / "data" / "final" / "master_text_dataset.csv"

E1_ROOT = ROOT / "data" / "interim" / "e1_multillm_replication"
REQUEST_DIR = E1_ROOT / "requests"
BATCH_DIR = E1_ROOT / "request_batches"
INCOMING_DIR = E1_ROOT / "incoming_raw_provider_responses"
RAW_ARCHIVE_DIR = E1_ROOT / "raw_response_archive"
PARSED_DIR = E1_ROOT / "parsed_outputs"

META_DIR = ROOT / "metadata"
LOGS_DIR = ROOT / "logs"
MODEL_REGISTRY = META_DIR / "e1_multillm_model_registry.csv"
BATCH_MANIFEST = META_DIR / "e1_multillm_batch_manifest.csv"
IMPORT_MANIFEST = META_DIR / "e1_multillm_import_manifest.csv"
QC_SUMMARY = META_DIR / "e1_multillm_qc_summary.csv"
REPORT = LOGS_DIR / "e1_multillm_batch_manager_report.md"

REQUESTS_ALL = REQUEST_DIR / "e1_rewrite_requests_all.jsonl"
PARSED_ALL = PARSED_DIR / "e1_multillm_rewrite_outputs_parsed.csv"

CONDITIONS = ["paraphrase", "modernize", "simplify"]
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 1.0

DEFAULT_MODELS = [
    {
        "replication_model_id": "gpt_4o",
        "provider": "openai",
        "provider_label": "GPT-4o",
        "provider_model_name": "gpt-4o",
        "default_runs": 1,
    },
    {
        "replication_model_id": "gemini_1_5_pro",
        "provider": "google",
        "provider_label": "Gemini 1.5 Pro",
        "provider_model_name": "gemini-1.5-pro",
        "default_runs": 1,
    },
    {
        "replication_model_id": "claude_sonnet_3_5",
        "provider": "anthropic",
        "provider_label": "Claude Sonnet 3.5",
        "provider_model_name": "claude-3-5-sonnet-20241022",
        "default_runs": 3,
    },
]

SYSTEM_PROMPT = """You are performing controlled literary passage rewriting for a research dataset.
Preserve the same events, objects, characters, speaker relationships, and narrative sequence.
Do not add plot information. Do not remove material facts. Do not summarize.
Do not mention authors, titles, Project Gutenberg, datasets, prompts, experiments, or analysis.
Do not add headings, bullets, notes, commentary, explanations, or markdown.
Output only a valid JSON object with exactly these fields:
{
  "passage_id": "...",
  "condition": "paraphrase|modernize|simplify",
  "rewritten_text": "..."
}
"""

CONDITION_INSTRUCTIONS = {
    "paraphrase": "Rewrite the passage lightly. Preserve meaning, plot content, characters, sequence, tone category, paragraph structure where possible, and approximate length. Change wording and local phrasing without summarizing or modernizing aggressively.",
    "modernize": "Rewrite the passage by updating archaic or nineteenth-century phrasing into contemporary English. Preserve content, tone category, events, characters, speaker relationships, narrative sequence, paragraph structure where possible, and approximate length. Do not summarize.",
    "simplify": "Rewrite the passage so it is easier for a general modern reader to understand. Preserve the same events, characters, core meaning, speaker relationships, narrative sequence, paragraph structure where possible, and approximate length. Do not summarize or remove material facts.",
}

OUTPUT_SCHEMA_NOTE = {
    "expected_response_json": {
        "passage_id": "same passage_id as request",
        "condition": "paraphrase|modernize|simplify",
        "rewritten_text": "controlled rewritten passage only",
    }
}

LEAKAGE_TERMS = ["project gutenberg", "gutenberg", "dataset", "experiment", "prompt"]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("_")


def ensure_dirs() -> None:
    for path in [REQUEST_DIR, BATCH_DIR, INCOMING_DIR, RAW_ARCHIVE_DIR, PARSED_DIR, META_DIR, LOGS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                rows.append({"_json_error": str(exc), "_line_number": line_number, "raw_line": line})
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def load_originals() -> list[dict[str, str]]:
    rows = read_csv(MASTER_DATASET)
    originals = [row for row in rows if row.get("condition") == "original"]
    if not originals:
        raise RuntimeError("No original-condition rows found in master dataset.")
    required = {"passage_id", "text", "text_sha256", "text_word_count", "author_id", "work_id"}
    missing = required - set(originals[0])
    if missing:
        raise RuntimeError(f"Master dataset missing required columns: {sorted(missing)}")
    originals.sort(key=lambda row: row["passage_id"])
    return originals


def user_prompt(passage_id: str, condition: str, source_text: str, original_word_count: int) -> str:
    return (
        f"passage_id: {passage_id}\n"
        f"condition: {condition}\n"
        f"original_word_count: {original_word_count}\n\n"
        f"Instruction:\n{CONDITION_INSTRUCTIONS[condition]}\n\n"
        "Original passage:\n"
        "<<<PASSAGE_START>>>\n"
        f"{source_text}\n"
        "<<<PASSAGE_END>>>"
    )


def parse_runs_by_model(value: str | None) -> dict[str, int]:
    if not value:
        return {}
    out = {}
    for part in value.split(","):
        if not part.strip():
            continue
        key, raw = part.split("=", 1)
        out[key.strip()] = int(raw.strip())
    return out


def build_requests(models: list[dict[str, Any]], runs_by_model: dict[str, int]) -> list[dict[str, Any]]:
    originals = load_originals()
    prompt_hash = sha256_text(SYSTEM_PROMPT + json.dumps(CONDITION_INSTRUCTIONS, sort_keys=True))
    requests = []
    for model in models:
        runs = runs_by_model.get(model["replication_model_id"], int(model["default_runs"]))
        for run_i in range(1, runs + 1):
            run_id = f"run_{run_i}"
            for original in originals:
                original_wc = int(float(original["text_word_count"]))
                for condition in CONDITIONS:
                    request_id = "|".join([model["replication_model_id"], run_id, original["passage_id"], condition])
                    requests.append({
                        "request_id": request_id,
                        "replication_model_id": model["replication_model_id"],
                        "provider": model["provider"],
                        "provider_label": model["provider_label"],
                        "provider_model_name": model["provider_model_name"],
                        "run_id": run_id,
                        "passage_id": original["passage_id"],
                        "condition": condition,
                        "temperature": DEFAULT_TEMPERATURE,
                        "top_p": DEFAULT_TOP_P,
                        "prompt_template_sha256": prompt_hash,
                        "source_text_sha256": original["text_sha256"],
                        "original_word_count": original_wc,
                        "system_prompt": SYSTEM_PROMPT,
                        "user_prompt": user_prompt(original["passage_id"], condition, original["text"], original_wc),
                        "output_schema_note": OUTPUT_SCHEMA_NOTE,
                    })
    return requests


def chunk_rows(rows: list[dict[str, Any]], chunk_size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + chunk_size] for i in range(0, len(rows), chunk_size)]


def prepare(args: argparse.Namespace) -> None:
    ensure_dirs()
    models = DEFAULT_MODELS
    runs_by_model = parse_runs_by_model(args.runs_by_model)
    requests = build_requests(models, runs_by_model)
    write_jsonl(REQUESTS_ALL, requests)

    registry_rows = []
    batch_rows = []
    by_model_run: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for req in requests:
        by_model_run[(req["replication_model_id"], req["run_id"])].append(req)

    for model in models:
        model_reqs = [r for r in requests if r["replication_model_id"] == model["replication_model_id"]]
        registry_rows.append({
            "replication_model_id": model["replication_model_id"],
            "provider": model["provider"],
            "provider_label": model["provider_label"],
            "provider_model_name": model["provider_model_name"],
            "default_runs": runs_by_model.get(model["replication_model_id"], model["default_runs"]),
            "planned_requests": len(model_reqs),
            "temperature": DEFAULT_TEMPERATURE,
            "top_p": DEFAULT_TOP_P,
            "notes": "Model name is configurable; verify provider availability before generation.",
        })

    for (model_id, run_id), rows in sorted(by_model_run.items()):
        chunks = chunk_rows(rows, args.chunk_size)
        for idx, chunk in enumerate(chunks, start=1):
            batch_id = f"{safe_id(model_id)}_{safe_id(run_id)}_batch_{idx:04d}"
            out = BATCH_DIR / f"{batch_id}.jsonl"
            write_jsonl(out, chunk)
            batch_rows.append({
                "batch_id": batch_id,
                "replication_model_id": model_id,
                "run_id": run_id,
                "batch_index": idx,
                "request_count": len(chunk),
                "path": out.relative_to(ROOT).as_posix(),
                "status": "prepared_not_generated",
            })

    write_csv(MODEL_REGISTRY, registry_rows, [
        "replication_model_id", "provider", "provider_label", "provider_model_name", "default_runs",
        "planned_requests", "temperature", "top_p", "notes",
    ])
    write_csv(BATCH_MANIFEST, batch_rows, [
        "batch_id", "replication_model_id", "run_id", "batch_index", "request_count", "path", "status",
    ])
    write_report("prepare", len(requests), 0, 0, 0)
    print(f"Prepared {len(requests)} E1 requests in {len(batch_rows)} batches.")
    print(f"Request root: {E1_ROOT.relative_to(ROOT)}")


def parse_model_json(text: str) -> tuple[str, dict[str, Any]]:
    raw = (text or "").strip()
    raw = re.sub(r"^\s*<think>.*?</think>\s*", "", raw, flags=re.DOTALL | re.IGNORECASE).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()
    try:
        return "json_ok", json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            try:
                return "json_extracted", json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    passage_match = re.search(r'"passage_id"\s*:\s*"([^"]+)"', raw)
    condition_match = re.search(r'"condition"\s*:\s*"([^"]+)"', raw)
    rewritten_match = re.search(r'"rewritten_text"\s*:\s*"', raw)
    if passage_match and condition_match and rewritten_match:
        rewritten = raw[rewritten_match.end():].strip()
        rewritten = re.sub(r"\s*}\s*$", "", rewritten).strip()
        rewritten = re.sub(r",\s*$", "", rewritten).strip()
        if rewritten.endswith('"'):
            rewritten = rewritten[:-1]
        if rewritten:
            return "json_repaired_loose_rewritten_text", {
                "passage_id": passage_match.group(1),
                "condition": condition_match.group(1),
                "rewritten_text": rewritten,
            }
    return "json_parse_failed_used_raw_content", {"rewritten_text": text or ""}


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+(?:['’-]\w+)?\b", text or ""))


def qc(req: dict[str, Any], parsed: dict[str, Any], parse_status: str) -> dict[str, Any]:
    flags = []
    status = "pass"
    rewritten = str(parsed.get("rewritten_text", "")).strip()
    if parse_status != "json_ok":
        flags.append(parse_status)
    if not rewritten:
        flags.append("empty_rewritten_text")
        status = "fail"
    if str(parsed.get("passage_id", req["passage_id"])).strip() != req["passage_id"]:
        flags.append("passage_id_mismatch")
    if str(parsed.get("condition", req["condition"])).strip() != req["condition"]:
        flags.append("condition_mismatch")
    lower = rewritten.lower()
    if any(term in lower for term in LEAKAGE_TERMS):
        flags.append("prompt_or_source_leakage_warning")
    if re.search(r"^\s*[-*#]", rewritten, flags=re.MULTILINE):
        flags.append("markdown_or_list_warning")

    original_wc = int(req["original_word_count"])
    rewritten_wc = word_count(rewritten)
    ratio = rewritten_wc / original_wc if original_wc else 0.0
    if ratio < 0.80 or ratio > 1.20:
        flags.append("length_hard_warning")
    elif ratio < 0.85 or ratio > 1.15:
        flags.append("length_soft_warning")

    if status != "fail" and flags:
        status = "warning"
    return {
        "rewritten_text": rewritten,
        "rewritten_word_count": rewritten_wc,
        "length_ratio": round(ratio, 6),
        "rewritten_text_sha256": sha256_text(rewritten) if rewritten else "",
        "qc_status": status,
        "qc_flags": ";".join(flags),
        "parse_status": parse_status,
    }


def load_request_map() -> dict[str, dict[str, Any]]:
    if not REQUESTS_ALL.exists():
        raise RuntimeError("Request file missing. Run prepare first.")
    return {row["request_id"]: row for row in read_jsonl(REQUESTS_ALL)}


def extract_response_text(row: dict[str, Any]) -> str:
    # Preferred neutral schema for incoming files:
    # {"request_id":"...", "response_text":"..."}
    if isinstance(row.get("response_text"), str):
        return row["response_text"]
    if isinstance(row.get("rewritten_text"), str):
        return json.dumps({
            "passage_id": row.get("passage_id", ""),
            "condition": row.get("condition", ""),
            "rewritten_text": row.get("rewritten_text", ""),
        }, ensure_ascii=False)
    if isinstance(row.get("raw_text"), str):
        return row["raw_text"]
    return json.dumps(row, ensure_ascii=False)


def import_outputs(_args: argparse.Namespace) -> None:
    ensure_dirs()
    req_by_id = load_request_map()
    incoming_files = sorted(INCOMING_DIR.glob("*.jsonl"))
    parsed_rows = []
    import_rows = []

    for incoming in incoming_files:
        rows = read_jsonl(incoming)
        imported = 0
        rejected = 0
        archive = RAW_ARCHIVE_DIR / incoming.name
        write_jsonl(archive, rows)
        for row in rows:
            request_id = row.get("request_id")
            if not request_id or request_id not in req_by_id:
                rejected += 1
                continue
            req = req_by_id[request_id]
            response_text = extract_response_text(row)
            parse_status, parsed = parse_model_json(response_text)
            q = qc(req, parsed, parse_status)
            parsed_rows.append({
                "request_id": request_id,
                "replication_model_id": req["replication_model_id"],
                "provider": req["provider"],
                "provider_label": req["provider_label"],
                "provider_model_name": req["provider_model_name"],
                "provider_model_version": row.get("provider_model_version", req["provider_model_name"]),
                "run_id": req["run_id"],
                "passage_id": req["passage_id"],
                "condition": req["condition"],
                "rewritten_text": q["rewritten_text"],
                "temperature": req["temperature"],
                "top_p": req["top_p"],
                "seed_requested": row.get("seed_requested", "unsupported_or_not_set"),
                "seed_effective": row.get("seed_effective", "unsupported_or_not_returned"),
                "prompt_template_sha256": req["prompt_template_sha256"],
                "source_text_sha256": req["source_text_sha256"],
                "rewritten_text_sha256": q["rewritten_text_sha256"],
                "original_word_count": req["original_word_count"],
                "rewritten_word_count": q["rewritten_word_count"],
                "length_ratio": q["length_ratio"],
                "qc_status": q["qc_status"],
                "qc_flags": q["qc_flags"],
                "parse_status": q["parse_status"],
                "created_utc": row.get("created_utc", utc_now()),
                "source_incoming_file": incoming.relative_to(ROOT).as_posix(),
            })
            imported += 1
        import_rows.append({
            "incoming_file": incoming.relative_to(ROOT).as_posix(),
            "archive_file": archive.relative_to(ROOT).as_posix(),
            "rows_seen": len(rows),
            "rows_imported": imported,
            "rows_rejected": rejected,
            "imported_utc": utc_now(),
        })

    existing = []
    if PARSED_ALL.exists():
        existing = read_csv(PARSED_ALL)
    combined_by_request = {row["request_id"]: row for row in existing}
    for row in parsed_rows:
        combined_by_request[row["request_id"]] = row
    combined = sorted(combined_by_request.values(), key=lambda r: r["request_id"])

    fieldnames = [
        "request_id", "replication_model_id", "provider", "provider_label", "provider_model_name",
        "provider_model_version", "run_id", "passage_id", "condition", "rewritten_text",
        "temperature", "top_p", "seed_requested", "seed_effective", "prompt_template_sha256",
        "source_text_sha256", "rewritten_text_sha256", "original_word_count", "rewritten_word_count",
        "length_ratio", "qc_status", "qc_flags", "parse_status", "created_utc", "source_incoming_file",
    ]
    write_csv(PARSED_ALL, combined, fieldnames)

    existing_imports = read_csv(IMPORT_MANIFEST) if IMPORT_MANIFEST.exists() else []
    write_csv(IMPORT_MANIFEST, existing_imports + import_rows, [
        "incoming_file", "archive_file", "rows_seen", "rows_imported", "rows_rejected", "imported_utc",
    ])
    write_qc_summary(combined)
    write_report("import", len(req_by_id), len(combined), len(parsed_rows), len([r for r in combined if r["qc_status"] == "fail"]))
    print(f"Imported {len(parsed_rows)} rows from {len(incoming_files)} incoming files.")
    print(f"Total parsed unique request IDs: {len(combined)}")


def write_qc_summary(rows: list[dict[str, Any]]) -> None:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["replication_model_id"], row["run_id"], row["condition"])].append(row)
    out = []
    for (model_id, run_id, condition), subset in sorted(groups.items()):
        counts = Counter(row["qc_status"] for row in subset)
        out.append({
            "replication_model_id": model_id,
            "run_id": run_id,
            "condition": condition,
            "rows": len(subset),
            "pass_rows": counts.get("pass", 0),
            "warning_rows": counts.get("warning", 0),
            "fail_rows": counts.get("fail", 0),
            "length_hard_warning_rows": sum("length_hard_warning" in str(row["qc_flags"]).split(";") for row in subset),
            "length_soft_warning_rows": sum("length_soft_warning" in str(row["qc_flags"]).split(";") for row in subset),
        })
    write_csv(QC_SUMMARY, out, [
        "replication_model_id", "run_id", "condition", "rows", "pass_rows", "warning_rows",
        "fail_rows", "length_hard_warning_rows", "length_soft_warning_rows",
    ])


def status(_args: argparse.Namespace) -> None:
    ensure_dirs()
    total = len(read_jsonl(REQUESTS_ALL)) if REQUESTS_ALL.exists() else 0
    parsed = read_csv(PARSED_ALL) if PARSED_ALL.exists() else []
    by_model = Counter(row["replication_model_id"] for row in parsed)
    print(f"Planned requests: {total}")
    print(f"Parsed imported rows: {len(parsed)}")
    for model_id, count in sorted(by_model.items()):
        print(f"- {model_id}: {count}")
    write_report("status", total, len(parsed), 0, len([r for r in parsed if r.get("qc_status") == "fail"]))


def write_report(mode: str, planned: int, parsed_total: int, imported_this_run: int, fail_total: int) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# E1 Multi-LLM Batch Manager Report\n\n"
        f"Generated UTC: {utc_now()}\n\n"
        f"Mode: `{mode}`\n\n"
        "## Separation rule\n\n"
        "All E1 replication artifacts are stored under `data/interim/e1_multillm_replication/` and `metadata/e1_multillm_*`. "
        "The original Gemini Flash core dataset remains separate.\n\n"
        "## Counts\n\n"
        f"- planned requests: {planned}\n"
        f"- parsed imported rows total: {parsed_total}\n"
        f"- imported rows this run: {imported_this_run}\n"
        f"- fail rows total: {fail_total}\n\n"
        "## Incoming response schema\n\n"
        "Place JSONL files in `data/interim/e1_multillm_replication/incoming_raw_provider_responses/`. "
        "Each line should minimally contain `request_id` and `response_text`. The response text should be the provider's raw textual answer, preferably the required JSON object.\n\n"
        "Example:\n\n"
        "```json\n"
        "{\"request_id\":\"gpt_4o|run_1|austen_001|paraphrase\",\"response_text\":\"{\\\"passage_id\\\":...}\"}\n"
        "```\n\n"
        "## Budget note\n\n"
        "Use small request batches and legitimate authorised API access. Do not use unauthorised accounts, fake accounts, or quota circumvention.\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E1 multi-LLM batch manager")
    sub = parser.add_subparsers(dest="command", required=True)
    p_prepare = sub.add_parser("prepare", help="Prepare request batches")
    p_prepare.add_argument("--chunk-size", type=int, default=100)
    p_prepare.add_argument("--runs-by-model", default=None, help="e.g. gpt_4o=1,gemini_1_5_pro=1,claude_sonnet_3_5=3")
    p_prepare.set_defaults(func=prepare)
    p_import = sub.add_parser("import", help="Import incoming provider response JSONL files")
    p_import.set_defaults(func=import_outputs)
    p_status = sub.add_parser("status", help="Print current completion status")
    p_status.set_defaults(func=status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
