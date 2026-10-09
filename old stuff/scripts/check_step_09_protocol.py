"""
Consistency checker for Step 9 controlled rewriting protocol.

Run from repository root:

    python scripts/check_step_09_protocol.py

Exit code:
    0 = Step 9 protocol layer is complete
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/rewrite_protocol.md",
    "metadata/rewrite_condition_registry.csv",
    "metadata/rewrite_generation_config.json",
    "metadata/rewrite_output_schema.csv",
    "prompts/rewrite_system_prompt.txt",
    "prompts/rewrite_paraphrase_prompt.txt",
    "prompts/rewrite_modernize_prompt.txt",
    "prompts/rewrite_simplify_prompt.txt",
    "scripts/08_prepare_rewrite_requests.py",
    "scripts/09_validate_rewrite_outputs.py",
    "logs/step_09_status.md",
]

EXPECTED_CONDITIONS = ["paraphrase", "modernize", "simplify"]
FORBIDDEN_PROMPT_TERMS = [
    "Jane Austen", "Charles Dickens", "Edgar Allan Poe", "Mark Twain", "Mary Shelley", "Oscar Wilde",
    "Pride and Prejudice", "Emma", "Great Expectations", "Oliver Twist", "Frankenstein",
    "The Picture of Dorian Gray", "Project Gutenberg", "stylometric", "authorial style separability",
]


def read_csv(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    for rel in REQUIRED_FILES:
        check((ROOT / rel).exists(), f"missing required file: {rel}", failures)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    registry = read_csv("metadata/rewrite_condition_registry.csv")
    config = json.loads((ROOT / "metadata/rewrite_generation_config.json").read_text(encoding="utf-8"))
    schema = read_csv("metadata/rewrite_output_schema.csv")

    registry_conditions = [row["condition"] for row in registry]
    check(registry_conditions == ["original"] + EXPECTED_CONDITIONS, "rewrite condition registry order mismatch", failures)
    check(config.get("conditions") == EXPECTED_CONDITIONS, "config conditions mismatch", failures)
    check(config.get("expected_original_passages") == 360, "expected_original_passages mismatch", failures)
    check(config.get("expected_requests") == 1080, "expected_requests mismatch", failures)
    check(config.get("expected_final_text_rows_after_step_11") == 1440, "expected final text rows mismatch", failures)
    check(config.get("prompt_author_title_blinding") is True, "prompt blinding must be true", failures)
    check(config.get("temperature") == 0.2, "temperature mismatch", failures)

    schema_cols = {row["column"] for row in schema}
    required_schema_cols = {
        "passage_id", "condition", "rewritten_text", "model_provider", "model_name",
        "prompt_template_id", "prompt_template_sha256", "source_text_sha256",
        "rewritten_text_sha256", "original_word_count", "rewritten_word_count",
        "length_ratio", "qc_status", "qc_flags", "created_utc",
    }
    check(required_schema_cols.issubset(schema_cols), "rewrite output schema missing required columns", failures)

    prompt_files = [
        "prompts/rewrite_system_prompt.txt",
        "prompts/rewrite_paraphrase_prompt.txt",
        "prompts/rewrite_modernize_prompt.txt",
        "prompts/rewrite_simplify_prompt.txt",
    ]
    for rel in prompt_files:
        text = (ROOT / rel).read_text(encoding="utf-8")
        check("valid JSON" in text, f"{rel} does not enforce JSON output", failures)
        for forbidden in FORBIDDEN_PROMPT_TERMS:
            check(forbidden not in text, f"{rel} leaks forbidden term: {forbidden}", failures)

    system_text = (ROOT / "prompts/rewrite_system_prompt.txt").read_text(encoding="utf-8")
    check("Do not summarize" in system_text, "system prompt missing no-summarize rule", failures)
    check("must output only valid JSON" in system_text, "system prompt missing strict JSON rule", failures)

    status_text = (ROOT / "logs/step_09_status.md").read_text(encoding="utf-8")
    check("Complete" in status_text, "Step 9 status does not say complete", failures)
    check("1080 rewrite requests" in status_text, "Step 9 status missing 1080 request expectation", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: Step 9 controlled rewriting protocol is complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
