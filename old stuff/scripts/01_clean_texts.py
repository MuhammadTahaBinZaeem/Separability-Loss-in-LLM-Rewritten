"""
Step 4 script: conservative text cleaning for stylometric analysis.

This cleaner removes obvious PDF/source artifacts while preserving authorial style
signals such as punctuation, sentence rhythm, quotation structure, dialect-like
spelling, archaic spelling, and paragraph breaks.

Inputs
------
data/raw/text_extracted/**/*.txt

Outputs
-------
data/interim/cleaned_books/**/*.txt
logs/cleaning_report.csv

Important
---------
This script is intentionally conservative. It does not lowercase, remove
punctuation, standardize dialect, modernize spelling, or sentence-tokenize and
rejoin prose.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable

CONFIG_PATH = Path("metadata/cleaning_config.json")

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
REPEATED_SPACES_RE = re.compile(r"[ \t]{2,}")
SIMPLE_HYPHEN_BREAK_RE = re.compile(r"(?<=[A-Za-z])-\n(?=[a-z])")
WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)

DEFAULT_LINE_REMOVE_PATTERNS = [
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^\s*Page\s+\d+\s*$", re.IGNORECASE),
]


def load_config(path: Path = CONFIG_PATH) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Missing cleaning config: {path}")


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def normalize_unicode(text: str) -> str:
    # NFKC fixes compatibility characters but does not remove punctuation.
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = CONTROL_CHARS_RE.sub("", text)
    return text


def repair_hyphenated_line_breaks(text: str) -> str:
    return SIMPLE_HYPHEN_BREAK_RE.sub("", text)


def compile_patterns(patterns: Iterable[str]) -> list[re.Pattern[str]]:
    compiled: list[re.Pattern[str]] = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            continue
    return compiled


def is_removable_line(line: str, patterns: list[re.Pattern[str]]) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return any(pattern.search(stripped) for pattern in patterns)


def remove_artifact_lines(text: str, patterns: list[re.Pattern[str]]) -> tuple[str, int]:
    kept: list[str] = []
    removed = 0
    for line in text.split("\n"):
        if is_removable_line(line, patterns):
            removed += 1
            continue
        kept.append(line)
    return "\n".join(kept), removed


def normalize_whitespace(text: str, max_blank_lines: int = 2) -> str:
    lines = [REPEATED_SPACES_RE.sub(" ", line).rstrip() for line in text.split("\n")]
    out: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= max_blank_lines:
                out.append("")
        else:
            blank_run = 0
            out.append(line)
    return "\n".join(out).strip() + "\n"


def clean_text(raw: str, config: dict) -> tuple[str, dict[str, int | float]]:
    raw_chars = len(raw)
    raw_words = count_words(raw)
    raw_lines = raw.count("\n") + 1 if raw else 0

    text = normalize_unicode(raw)

    if config.get("repair_simple_hyphenated_line_breaks", True):
        text = repair_hyphenated_line_breaks(text)

    line_patterns = compile_patterns(config.get("remove_lines_matching", []))
    text, removed_lines = remove_artifact_lines(text, line_patterns)

    text = normalize_whitespace(text, int(config.get("max_consecutive_blank_lines", 2)))

    cleaned_chars = len(text)
    cleaned_words = count_words(text)
    cleaned_lines = text.count("\n") + 1 if text else 0

    char_loss_ratio = (raw_chars - cleaned_chars) / raw_chars if raw_chars else 0.0
    word_loss_ratio = (raw_words - cleaned_words) / raw_words if raw_words else 0.0

    metrics = {
        "raw_chars": raw_chars,
        "cleaned_chars": cleaned_chars,
        "raw_words": raw_words,
        "cleaned_words": cleaned_words,
        "raw_lines": raw_lines,
        "cleaned_lines": cleaned_lines,
        "removed_artifact_lines": removed_lines,
        "char_loss_ratio": round(char_loss_ratio, 6),
        "word_loss_ratio": round(word_loss_ratio, 6),
    }
    return text, metrics


def iter_text_files(input_dir: Path) -> Iterable[Path]:
    return sorted(input_dir.rglob("*.txt"), key=lambda p: p.as_posix().lower())


def warning_flags(metrics: dict[str, int | float], config: dict) -> str:
    thresholds = config.get("warning_thresholds", {})
    flags: list[str] = []
    max_char_loss = float(thresholds.get("max_character_loss_ratio", 0.35))
    max_word_loss = float(thresholds.get("max_word_loss_ratio", 0.35))
    min_words = int(thresholds.get("min_cleaned_words", 1000))

    if float(metrics["char_loss_ratio"]) > max_char_loss:
        flags.append("high_character_loss")
    if float(metrics["word_loss_ratio"]) > max_word_loss:
        flags.append("high_word_loss")
    if int(metrics["cleaned_words"]) < min_words:
        flags.append("low_cleaned_word_count")
    return ";".join(flags)


def main() -> None:
    config = load_config()
    input_dir = Path(config["input_dir"])
    output_dir = Path(config["output_dir"])
    report_path = Path(config["report_path"])

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str | int | float]] = []
    for src in iter_text_files(input_dir):
        rel = src.relative_to(input_dir)
        dst = output_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        raw = src.read_text(encoding="utf-8", errors="replace")
        cleaned, metrics = clean_text(raw, config)
        dst.write_text(cleaned, encoding="utf-8")

        row: dict[str, str | int | float] = {
            "source_text_path": src.as_posix(),
            "cleaned_text_path": dst.as_posix(),
            **metrics,
            "warning_flags": warning_flags(metrics, config),
        }
        rows.append(row)

    fieldnames = [
        "source_text_path",
        "cleaned_text_path",
        "raw_chars",
        "cleaned_chars",
        "raw_words",
        "cleaned_words",
        "raw_lines",
        "cleaned_lines",
        "removed_artifact_lines",
        "char_loss_ratio",
        "word_loss_ratio",
        "warning_flags",
    ]

    with report_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Cleaned {len(rows)} files")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
