"""
Step 6/7 script: candidate passage extraction.

Step 6 freezes the extraction protocol and this script scaffold.
Step 7 will run this script to generate the candidate passage pool.

Purpose
-------
Extract non-overlapping, style-preserving candidate passages from cleaned texts.
The extractor is conservative and sentence-aware: it avoids mid-sentence cuts
where possible and uses word-gap stepping to prevent overlapping candidates.

The final 360-passage dataset is NOT selected here; final selection and balance
belong to Step 8.

Run
---
python scripts/03_extract_candidate_passages.py
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Iterable

CONFIG_PATH = Path("metadata/passage_extraction_config.json")
SOURCE_ID_MAP_PATH = Path("metadata/source_id_map.csv")
WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]+(?:[\"”’]+)?|[^.!?]+$", re.UNICODE)
PUNCT_CHARS = set(".,;:!?—–-\"“”‘’'…")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def word_count(text: str) -> int:
    return len(words(text))


def paragraph_count(text: str) -> int:
    return len([p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()])


def per_1000(count: int, word_total: int) -> float:
    return round(count / word_total * 1000, 3) if word_total else 0.0


def sentence_spans(text: str) -> list[tuple[int, int, str, int]]:
    spans: list[tuple[int, int, str, int]] = []
    for match in SENTENCE_RE.finditer(text):
        sentence = match.group(0).strip()
        wc = word_count(sentence)
        if wc > 0:
            spans.append((match.start(), match.end(), sentence, wc))
    return spans


def passage_metrics(text: str) -> dict[str, int | float]:
    toks = words(text)
    word_total = len(toks)
    sentences = sentence_spans(text)
    sent_lens = [s[3] for s in sentences]
    punctuation_total = sum(1 for c in text if c in PUNCT_CHARS)
    dialogue_marker_count = sum(text.count(ch) for ch in ['"', "“", "”", "‘", "’"])
    semicolon_count = text.count(";")
    dash_count = text.count("—") + text.count("–") + len(re.findall(r"(?<!\w)-(?!\w)", text))
    apostrophe_count = text.count("'") + text.count("’")
    long_sentence_count = sum(1 for n in sent_lens if n >= 40)
    return {
        "word_count": word_total,
        "sentence_count": len(sent_lens),
        "paragraph_count": paragraph_count(text),
        "dialogue_marker_count": dialogue_marker_count,
        "dialogue_marker_per_1000w": per_1000(dialogue_marker_count, word_total),
        "punctuation_per_1000w": per_1000(punctuation_total, word_total),
        "semicolon_per_1000w": per_1000(semicolon_count, word_total),
        "dash_per_1000w": per_1000(dash_count, word_total),
        "apostrophe_per_1000w": per_1000(apostrophe_count, word_total),
        "mean_sentence_words": round(sum(sent_lens) / len(sent_lens), 3) if sent_lens else 0.0,
        "long_sentence_ratio": round(long_sentence_count / len(sent_lens), 6) if sent_lens else 0.0,
    }


def locate_cleaned_text(cleaned_root: Path, source_path: str) -> Path | None:
    expected_name = Path(source_path).with_suffix(".txt").name
    matches = list(cleaned_root.rglob(expected_name))
    if len(matches) == 1:
        return matches[0]
    return None


def make_candidate_id(author_id: str, source_id: str, index: int) -> str:
    return f"{author_id.upper()}_{source_id.upper()}_{index:04d}"


def word_index_at_char(text: str, char_offset: int) -> int:
    count = 0
    for match in WORD_RE.finditer(text):
        if match.start() >= char_offset:
            break
        count += 1
    return count


def extract_sentence_aware_windows(
    text: str,
    preferred_words: int,
    min_words: int,
    max_words: int,
    gap_words: int,
) -> Iterable[tuple[int, int, int, int, int, str]]:
    """Yield non-overlapping, sentence-boundary candidate windows.

    The extractor starts at a sentence boundary, accumulates full sentences until
    the passage reaches the preferred length, then accepts it if it is within
    hard bounds. The next start advances by passage length plus the configured
    word gap, which prevents overlapping candidates.
    """
    sentences = sentence_spans(text)
    if not sentences:
        return

    candidate_index = 1
    start_sentence = 0
    while start_sentence < len(sentences):
        total_words = 0
        end_sentence = start_sentence
        while end_sentence < len(sentences) and total_words < preferred_words:
            total_words += sentences[end_sentence][3]
            end_sentence += 1

        if total_words < min_words:
            break

        # If the preferred chunk is too long, back off by one sentence if possible.
        while total_words > max_words and end_sentence - start_sentence > 1:
            end_sentence -= 1
            total_words -= sentences[end_sentence][3]

        start_char = sentences[start_sentence][0]
        end_char = sentences[end_sentence - 1][1]
        passage = text[start_char:end_char].strip()
        actual_words = word_count(passage)

        if actual_words >= min_words:
            start_word_index = word_index_at_char(text, start_char)
            end_word_index = start_word_index + actual_words
            yield candidate_index, start_word_index, end_word_index, start_char, end_char, passage
            candidate_index += 1

        # Advance by at least the passage length plus configured gap.
        target_advance = max(actual_words + gap_words, preferred_words + gap_words)
        advanced_words = 0
        next_start = start_sentence
        while next_start < len(sentences) and advanced_words < target_advance:
            advanced_words += sentences[next_start][3]
            next_start += 1
        if next_start <= start_sentence:
            next_start = start_sentence + 1
        start_sentence = next_start


def infer_work_fields(source_row: dict[str, str]) -> tuple[str, str]:
    # Step 7/8 will refine work boundaries for complete-works containers.
    status = source_row["main_corpus_status"]
    if status == "eligible_container":
        return "unknown_container_section", "Unknown container section pending boundary extraction"
    return "source_level_work", "Source-level work pending final work mapping"


def main() -> None:
    config = read_json(CONFIG_PATH)
    source_rows = read_csv(SOURCE_ID_MAP_PATH)
    cleaned_root = Path(config["input_dir"])
    out_candidates = Path(config["output_candidate_passages"])
    out_metadata = Path(config["output_candidate_metadata"])
    report_path = Path(config["candidate_generation_report"])
    allowed_statuses = set(config["allowed_source_statuses"])

    out_candidates.parent.mkdir(parents=True, exist_ok=True)
    out_metadata.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    candidate_rows: list[dict[str, object]] = []
    source_report_rows: list[tuple[str, str, int, str]] = []

    for source_row in source_rows:
        source_id = source_row["source_id"]
        author_id = source_row["author_id"]
        status = source_row["main_corpus_status"]
        if status not in allowed_statuses:
            source_report_rows.append((source_id, author_id, 0, f"skipped_status_{status}"))
            continue

        cleaned_path = locate_cleaned_text(cleaned_root, source_row["source_path"])
        if cleaned_path is None:
            source_report_rows.append((source_id, author_id, 0, "missing_cleaned_text"))
            continue

        text = cleaned_path.read_text(encoding="utf-8", errors="replace")
        work_id, work_title = infer_work_fields(source_row)
        count = 0
        for idx, start_word, end_word, start_char, end_char, passage in extract_sentence_aware_windows(
            text,
            int(config["preferred_words_per_passage"]),
            int(config["minimum_words_per_passage"]),
            int(config["maximum_words_per_passage"]),
            int(config["minimum_gap_words_same_source"]),
        ):
            m = passage_metrics(passage)
            candidate_status = "candidate_pass_length"
            exclusion_reason = ""
            if m["word_count"] < int(config["minimum_words_per_passage"]) or m["word_count"] > int(config["maximum_words_per_passage"]):
                candidate_status = "candidate_fail_length"
                exclusion_reason = "outside_hard_word_bounds"
            elif m["sentence_count"] < int(config["minimum_sentence_count"]):
                candidate_status = "candidate_fail_low_sentence_count"
                exclusion_reason = "too_few_sentences"

            candidate_rows.append({
                "candidate_id": make_candidate_id(author_id, source_id, idx),
                "source_id": source_id,
                "author_id": author_id,
                "author_name": source_row["author_name"],
                "work_id": work_id,
                "work_title": work_title,
                "source_path": source_row["source_path"],
                "candidate_index_within_source": idx,
                "start_word_index": start_word,
                "end_word_index": end_word,
                "start_char": start_char,
                "end_char": end_char,
                **m,
                "extraction_rule_version": config["extraction_rule_version"],
                "candidate_status": candidate_status,
                "exclusion_reason": exclusion_reason,
                "text": passage,
            })
            count += 1
        source_report_rows.append((source_id, author_id, count, "processed"))

    fieldnames = [
        "candidate_id", "source_id", "author_id", "author_name", "work_id", "work_title", "source_path",
        "candidate_index_within_source", "start_word_index", "end_word_index", "word_count", "sentence_count",
        "paragraph_count", "start_char", "end_char", "dialogue_marker_count", "dialogue_marker_per_1000w",
        "punctuation_per_1000w", "semicolon_per_1000w", "dash_per_1000w", "apostrophe_per_1000w",
        "mean_sentence_words", "long_sentence_ratio", "extraction_rule_version", "candidate_status",
        "exclusion_reason", "text",
    ]
    with out_candidates.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(candidate_rows)

    metadata_fieldnames = [name for name in fieldnames if name != "text"]
    with out_metadata.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=metadata_fieldnames)
        writer.writeheader()
        for row in candidate_rows:
            writer.writerow({k: row[k] for k in metadata_fieldnames})

    author_counts: dict[str, int] = {}
    for row in candidate_rows:
        if row["candidate_status"] == "candidate_pass_length":
            author_counts[str(row["author_id"])] = author_counts.get(str(row["author_id"]), 0) + 1

    lines = [
        "# Candidate Generation Report",
        "",
        f"Total candidate rows: {len(candidate_rows)}",
        "",
        "## Passing candidates by author",
        "",
    ]
    for author_id, count in sorted(author_counts.items()):
        lines.append(f"- {author_id}: {count}")
    lines.extend(["", "## Source processing summary", ""])
    for source_id, author_id, count, status in source_report_rows:
        lines.append(f"- {source_id} / {author_id}: {count} ({status})")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {len(candidate_rows)} candidates to {out_candidates}")


if __name__ == "__main__":
    main()
