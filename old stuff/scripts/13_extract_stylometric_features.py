"""
Step 12: extract stylometric features from the master text dataset.

Run from repository root after Step 11:

    python scripts/13_extract_stylometric_features.py

Input:
- data/final/master_text_dataset.csv

Outputs:
- data/features/stylometric_features.csv
- metadata/stylometric_feature_summary.csv
- metadata/stylometric_feature_family_counts.csv
- metadata/stylometric_feature_manifest.csv
- logs/step_12_feature_extraction_report.md
"""

from __future__ import annotations

import csv
import hashlib
import math
import re
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "final" / "master_text_dataset.csv"
FEATURE_DIR = ROOT / "data" / "features"
META = ROOT / "metadata"
LOGS = ROOT / "logs"
FEATURES = FEATURE_DIR / "stylometric_features.csv"
SUMMARY = META / "stylometric_feature_summary.csv"
FAMILY_COUNTS = META / "stylometric_feature_family_counts.csv"
MANIFEST = META / "stylometric_feature_manifest.csv"
REPORT = LOGS / "step_12_feature_extraction_report.md"

WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)
SENT_RE = re.compile(r"[^.!?]+[.!?]+(?:[\"”’]+)?|[^.!?]+$", re.UNICODE)
PUNCT_CHARS = set(".,;:!?—–-\"“”‘’'…")
FUNCTION_WORDS = [
    "the", "and", "of", "to", "a", "in", "that", "it", "is", "was", "i", "for", "with", "as", "his", "he", "be", "not", "by", "but",
    "had", "you", "at", "on", "her", "which", "have", "or", "from", "this", "my", "me", "all", "so", "were", "they", "him", "she", "there",
    "no", "one", "their", "we", "what", "if", "would", "when", "who", "will", "more", "an", "do", "are", "than", "could", "them", "been",
]
ARCHAIC_RE = re.compile(r"\b(thou|thee|thy|thine|hath|doth|art|wilt|shalt|ere|nay)\b", re.I)
CONTRACTION_RE = re.compile(r"\b\w+[’']\w+\b", re.UNICODE)
ABSTRACT_RE = re.compile(r"\b\w+(?:tion|sion|ity|ness|ment|ance|ence)\b", re.I)
EXPECTED_CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
EXPECTED_AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
CHAR3_LIMIT = 120


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def tokens(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def sentence_lengths(text: str) -> list[int]:
    out = []
    for match in SENT_RE.finditer(text):
        n = len(WORD_RE.findall(match.group(0)))
        if n:
            out.append(n)
    return out


def paragraphs(text: str) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def per_1000(count: int | float, n_words: int) -> float:
    return round(float(count) / n_words * 1000, 6) if n_words else 0.0


def char3s(text: str) -> Counter[str]:
    normalized = re.sub(r"\s+", " ", text.lower())
    return Counter(normalized[i:i+3] for i in range(max(0, len(normalized) - 2)))


def select_char3_vocab(rows: list[dict[str, str]]) -> list[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        if row["condition"] == "original":
            counts.update(char3s(row["text"]))
    vocab = []
    for gram, count in counts.most_common():
        if len(gram) == 3 and gram.strip() and not any(ch.isdigit() for ch in gram):
            safe = gram.replace(" ", "_space_").replace("\n", "_nl_")
            if re.match(r"^[a-z_ ,.;:'\"!?-]+$", gram):
                vocab.append(gram)
        if len(vocab) >= CHAR3_LIMIT:
            break
    return vocab


def base_features(text: str, char_vocab: list[str]) -> dict[str, float | int]:
    toks = tokens(text)
    n = len(toks)
    types = set(toks)
    hapax = sum(1 for _tok, c in Counter(toks).items() if c == 1)
    lens = sentence_lengths(text)
    p_count = len(paragraphs(text))
    punct_count = sum(1 for ch in text if ch in PUNCT_CHARS)
    quote_count = sum(text.count(ch) for ch in ['"', '“', '”', '‘', '’'])
    apostrophe_count = text.count("'") + text.count("’")
    dash_count = text.count("—") + text.count("–") + len(re.findall(r"(?<!\w)-(?!\w)", text))
    long_sentence_count = sum(1 for x in lens if x >= 40)
    short_sentence_count = sum(1 for x in lens if x <= 10)
    avg_word_len = sum(len(t) for t in toks) / n if n else 0.0
    long_word_count = sum(1 for t in toks if len(t) >= 8)
    short_word_count = sum(1 for t in toks if len(t) <= 3)

    feats: dict[str, float | int] = {
        "word_count_feature": n,
        "sentence_count_feature": len(lens),
        "paragraph_count_feature": p_count,
        "mean_sentence_words": round(sum(lens) / len(lens), 6) if lens else 0.0,
        "median_sentence_words": round(statistics.median(lens), 6) if lens else 0.0,
        "std_sentence_words": round(statistics.pstdev(lens), 6) if len(lens) > 1 else 0.0,
        "short_sentence_ratio": round(short_sentence_count / len(lens), 6) if lens else 0.0,
        "long_sentence_ratio": round(long_sentence_count / len(lens), 6) if lens else 0.0,
        "punctuation_per_1000w": per_1000(punct_count, n),
        "comma_per_1000w": per_1000(text.count(","), n),
        "semicolon_per_1000w": per_1000(text.count(";"), n),
        "colon_per_1000w": per_1000(text.count(":"), n),
        "dash_per_1000w": per_1000(dash_count, n),
        "question_per_1000w": per_1000(text.count("?"), n),
        "exclamation_per_1000w": per_1000(text.count("!"), n),
        "quote_mark_per_1000w": per_1000(quote_count, n),
        "apostrophe_per_1000w": per_1000(apostrophe_count, n),
        "ellipsis_per_1000w": per_1000(text.count("...") + text.count("…"), n),
        "type_token_ratio": round(len(types) / n, 6) if n else 0.0,
        "root_type_token_ratio": round(len(types) / math.sqrt(n), 6) if n else 0.0,
        "hapax_ratio": round(hapax / n, 6) if n else 0.0,
        "avg_word_length": round(avg_word_len, 6),
        "long_word_ratio": round(long_word_count / n, 6) if n else 0.0,
        "short_word_ratio": round(short_word_count / n, 6) if n else 0.0,
        "contraction_per_1000w": per_1000(len(CONTRACTION_RE.findall(text)), n),
        "archaic_marker_per_1000w": per_1000(len(ARCHAIC_RE.findall(text)), n),
        "abstract_suffix_per_1000w": per_1000(len(ABSTRACT_RE.findall(text)), n),
        "dialogue_marker_per_1000w": per_1000(quote_count, n),
    }
    tok_counts = Counter(toks)
    for fw in FUNCTION_WORDS:
        feats[f"fw_{fw}_per_1000w"] = per_1000(tok_counts.get(fw, 0), n)
    c3_counts = char3s(text)
    total_c3 = sum(c3_counts.values())
    for gram in char_vocab:
        safe = gram.replace(" ", "_space_").replace("'", "apos").replace('"', "quote").replace(",", "comma").replace(".", "dot").replace(";", "semi").replace(":", "colon").replace("?", "qmark").replace("!", "emark").replace("-", "dash")
        feats[f"char3_{safe}"] = round(c3_counts.get(gram, 0) / total_c3 * 1000, 6) if total_c3 else 0.0
    return feats


def feature_family(feature_name: str) -> str:
    if feature_name.startswith("fw_"):
        return "function_word"
    if feature_name.startswith("char3_"):
        return "char3"
    if feature_name in {"word_count_feature", "sentence_count_feature", "paragraph_count_feature", "mean_sentence_words", "median_sentence_words", "std_sentence_words", "short_sentence_ratio", "long_sentence_ratio"}:
        return "length_rhythm"
    if "punctuation" in feature_name or feature_name.endswith("_per_1000w") and any(x in feature_name for x in ["comma", "semicolon", "colon", "dash", "question", "exclamation", "quote", "apostrophe", "ellipsis"]):
        return "punctuation"
    if feature_name in {"type_token_ratio", "root_type_token_ratio", "hapax_ratio", "avg_word_length", "long_word_ratio", "short_word_ratio"}:
        return "lexical_richness"
    return "register_marker"


def main() -> int:
    if not MASTER.exists():
        print(f"Missing master dataset: {MASTER.relative_to(ROOT)}")
        return 1
    rows = read_csv(MASTER)
    if len(rows) != 1440:
        print(f"Expected 1440 master rows, found {len(rows)}")
        return 1
    char_vocab = select_char3_vocab(rows)
    feature_rows: list[dict[str, object]] = []
    id_cols = ["text_id", "passage_id", "condition", "author_id", "author_name", "work_id", "work_title", "qc_status", "qc_flags"]
    feature_columns: list[str] | None = None
    for row in rows:
        feats = base_features(row["text"], char_vocab)
        if feature_columns is None:
            feature_columns = list(feats.keys())
        out = {col: row.get(col, "") for col in id_cols}
        out.update(feats)
        feature_rows.append(out)

    assert feature_columns is not None
    write_csv(FEATURES, feature_rows, id_cols + feature_columns)

    family_counts = Counter(feature_family(col) for col in feature_columns)
    family_rows = [{"feature_family": family, "feature_count": count} for family, count in sorted(family_counts.items())]
    write_csv(FAMILY_COUNTS, family_rows, ["feature_family", "feature_count"])

    condition_counts = Counter(row["condition"] for row in feature_rows)
    author_counts = Counter(row["author_id"] for row in feature_rows)
    summary_rows = [
        {"metric": "feature_rows", "value": len(feature_rows)},
        {"metric": "unique_text_ids", "value": len({row["text_id"] for row in feature_rows})},
        {"metric": "feature_columns", "value": len(feature_columns)},
        {"metric": "identifier_columns", "value": len(id_cols)},
        {"metric": "total_columns", "value": len(id_cols) + len(feature_columns)},
        {"metric": "conditions", "value": len(condition_counts)},
        {"metric": "authors", "value": len(author_counts)},
        {"metric": "original_rows", "value": condition_counts.get("original", 0)},
        {"metric": "paraphrase_rows", "value": condition_counts.get("paraphrase", 0)},
        {"metric": "modernize_rows", "value": condition_counts.get("modernize", 0)},
        {"metric": "simplify_rows", "value": condition_counts.get("simplify", 0)},
        {"metric": "char3_vocabulary_size", "value": len(char_vocab)},
        {"metric": "stylometric_features_sha256", "value": sha_file(FEATURES)},
    ]
    write_csv(SUMMARY, summary_rows, ["metric", "value"])

    manifest_rows = [
        {"artifact": "stylometric_features", "path": FEATURES.relative_to(ROOT).as_posix(), "size_bytes": FEATURES.stat().st_size, "sha256": sha_file(FEATURES)},
        {"artifact": "stylometric_feature_summary", "path": SUMMARY.relative_to(ROOT).as_posix(), "size_bytes": SUMMARY.stat().st_size, "sha256": sha_file(SUMMARY)},
        {"artifact": "stylometric_feature_family_counts", "path": FAMILY_COUNTS.relative_to(ROOT).as_posix(), "size_bytes": FAMILY_COUNTS.stat().st_size, "sha256": sha_file(FAMILY_COUNTS)},
    ]
    write_csv(MANIFEST, manifest_rows, ["artifact", "path", "size_bytes", "sha256"])

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Step 12 Stylometric Feature Extraction Report\n\n"
        "## Status\n\nComplete when generated locally and checker passes.\n\n"
        "## Expected output\n\n"
        f"- feature rows: {len(feature_rows)}\n"
        f"- feature columns: {len(feature_columns)}\n"
        f"- identifier columns: {len(id_cols)}\n"
        f"- total columns: {len(id_cols) + len(feature_columns)}\n"
        f"- char3 vocabulary size: {len(char_vocab)}\n\n"
        "## Feature families\n\n" + "".join(f"- {row['feature_family']}: {row['feature_count']}\n" for row in family_rows),
        encoding="utf-8",
    )
    print(f"Extracted {len(feature_columns)} stylometric features for {len(feature_rows)} text rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
