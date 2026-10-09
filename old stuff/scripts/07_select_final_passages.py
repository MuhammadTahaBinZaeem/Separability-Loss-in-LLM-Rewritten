"""
Step 8: select the final balanced original-passage dataset.

Run from repository root after the Gutenberg candidate pool exists:

    python scripts/07_select_final_passages.py

Required input:
- data/interim/gutenberg_candidate_passages.csv

Outputs:
- data/processed/selected_original_passages.csv
- metadata/selected_original_passage_metadata.csv
- metadata/selected_counts_by_author.csv
- metadata/selected_counts_by_work.csv
- metadata/selection_summary.csv
- metadata/selection_filter_report.csv
- metadata/step8_output_manifest.csv
- data/processed/selected_passages_md/selected_passages_<author>.md
- metadata/selected_passage_md_manifest.csv
- logs/step_08_status.md

Selection design:
- 6 authors
- 2 works per author
- 30 selected original passages per work
- 60 selected original passages per author
- 360 selected original passages total

The selection is deterministic. It filters for good-quality candidate passages
and then samples evenly across each work's candidate sequence.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_CSV = ROOT / "data" / "interim" / "gutenberg_candidate_passages.csv"
OUT_DIR = ROOT / "data" / "processed"
META = ROOT / "metadata"
LOG = ROOT / "logs"
MD_DIR = OUT_DIR / "selected_passages_md"

FRONT_MATTER_RE = re.compile(
    r"Project Gutenberg|CONTENTS|Illustration|PREFACE|CHISWICK|GEORGE ALLEN|TRANSCRIBER|START OF|END OF",
    flags=re.IGNORECASE,
)

AUTHOR_ORDER = {
    "austen": 1,
    "dickens": 2,
    "poe": 3,
    "shelley": 4,
    "twain": 5,
    "wilde": 6,
}


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(paths: list[Path], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["artifact", "path", "size_bytes", "sha256"])
        writer.writeheader()
        for path in paths:
            writer.writerow({
                "artifact": path.name,
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha_file(path),
            })


def choose_evenly(group: pd.DataFrame, n: int = 30) -> pd.DataFrame:
    group = group.sort_values("candidate_index_within_source").reset_index(drop=True)
    if len(group) < n:
        raise ValueError(f"Not enough eligible candidates: required {n}, found {len(group)}")
    chosen_indices: list[int] = []
    remaining = list(range(len(group)))
    for k in range(n):
        target = int(min(len(group) - 1, (k + 0.5) * len(group) / n))
        if target in remaining:
            chosen = target
        else:
            chosen = min(remaining, key=lambda x: abs(x - target))
        chosen_indices.append(chosen)
        remaining.remove(chosen)
    selected = group.iloc[chosen_indices].copy()
    selected["selection_rank_within_work"] = range(1, n + 1)
    selected["selection_method"] = "deterministic_even_spread_30_per_work_after_quality_filters"
    return selected


def make_markdown_files(selected: pd.DataFrame) -> list[Path]:
    MD_DIR.mkdir(parents=True, exist_ok=True)
    for old in MD_DIR.glob("selected_passages_*.md"):
        old.unlink()
    paths: list[Path] = []
    for author_id, group in selected.groupby("author_id", sort=False):
        path = MD_DIR / f"selected_passages_{author_id}.md"
        lines = [
            f"# Selected Original Passages — {author_id.title()}\n\n",
            "These are the final selected original passages for Step 8. ",
            "Metadata is stored in `metadata/selected_original_passage_metadata.csv`.\n\n",
        ]
        for _, row in group.iterrows():
            text = str(row["text"]).replace("\r\n", "\n").replace("\r", "\n").strip()
            lines.append(f"## {row['passage_id']}\n\n")
            lines.append(
                f"- candidate_id: `{row['candidate_id']}`\n"
                f"- canonical_id: `{row['canonical_id']}`\n"
                f"- alias_id: `{row['alias_id']}`\n"
                f"- work_id: `{row['work_id']}`\n"
                f"- work_title: `{row['work_title']}`\n"
                f"- word_count: `{row['word_count']}`\n"
                f"- sentence_count: `{row['sentence_count']}`\n\n"
            )
            lines.append(f"```text\n{text}\n```\n\n")
        path.write_text("".join(lines), encoding="utf-8")
        paths.append(path)
    return paths


def main() -> int:
    if not CANDIDATE_CSV.exists():
        print(f"Missing candidate pool: {CANDIDATE_CSV}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    LOG.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(CANDIDATE_CSV)
    eligible = df[
        (df["candidate_status"] == "candidate_pass_length")
        & (df["word_count"].between(450, 650))
        & (df["sentence_count"] >= 5)
        & (df["candidate_index_within_source"] > 5)
        & (~df["text"].fillna("").str.contains(FRONT_MATTER_RE))
    ].copy()

    selected_parts = []
    for (author_id, work_id), group in eligible.groupby(["author_id", "work_id"], sort=True):
        selected_parts.append(choose_evenly(group, 30))

    selected = pd.concat(selected_parts, ignore_index=True)
    selected["author_order"] = selected["author_id"].map(AUTHOR_ORDER)
    selected = selected.sort_values(["author_order", "work_id", "selection_rank_within_work"]).reset_index(drop=True)
    selected["final_index_within_author"] = selected.groupby("author_id").cumcount() + 1
    selected["passage_id"] = selected.apply(
        lambda row: f"{row['author_id'].upper()}_{row['work_id'].upper()}_{int(row['selection_rank_within_work']):03d}",
        axis=1,
    )
    selected["condition"] = "original"

    ordered_columns = [
        "passage_id", "condition", "candidate_id", "canonical_id", "alias_id", "author_id", "author_name",
        "work_id", "work_title", "gutenberg_ebook_no", "selection_rank_within_work", "final_index_within_author",
        "candidate_index_within_source", "start_word_index", "end_word_index", "word_count", "sentence_count",
        "paragraph_count", "start_char", "end_char", "dialogue_marker_count", "dialogue_marker_per_1000w",
        "punctuation_per_1000w", "semicolon_per_1000w", "dash_per_1000w", "apostrophe_per_1000w",
        "mean_sentence_words", "long_sentence_ratio", "selection_method", "text",
    ]
    selected = selected[ordered_columns]

    selected_csv = OUT_DIR / "selected_original_passages.csv"
    metadata_csv = META / "selected_original_passage_metadata.csv"
    counts_author_csv = META / "selected_counts_by_author.csv"
    counts_work_csv = META / "selected_counts_by_work.csv"
    summary_csv = META / "selection_summary.csv"
    filter_report_csv = META / "selection_filter_report.csv"
    manifest_csv = META / "step8_output_manifest.csv"
    md_manifest_csv = META / "selected_passage_md_manifest.csv"
    status_md = LOG / "step_08_status.md"

    selected.to_csv(selected_csv, index=False)
    selected.drop(columns=["text"]).to_csv(metadata_csv, index=False)

    counts_author = selected.groupby("author_id").agg(
        selected_passages=("passage_id", "count"),
        mean_words=("word_count", "mean"),
        min_words=("word_count", "min"),
        max_words=("word_count", "max"),
        mean_sentence_count=("sentence_count", "mean"),
    ).reset_index()
    counts_author["mean_words"] = counts_author["mean_words"].round(2)
    counts_author["mean_sentence_count"] = counts_author["mean_sentence_count"].round(2)
    counts_author.to_csv(counts_author_csv, index=False)

    counts_work = selected.groupby(["author_id", "work_id", "work_title"]).agg(
        selected_passages=("passage_id", "count"),
        mean_words=("word_count", "mean"),
        min_words=("word_count", "min"),
        max_words=("word_count", "max"),
    ).reset_index()
    counts_work["mean_words"] = counts_work["mean_words"].round(2)
    counts_work.to_csv(counts_work_csv, index=False)

    eligible_counts = eligible.groupby(["author_id", "work_id"]).size().reset_index(name="eligible_after_filters")
    raw_counts = df.groupby(["author_id", "work_id"]).size().reset_index(name="raw_candidates")
    filter_report = raw_counts.merge(eligible_counts, on=["author_id", "work_id"])
    filter_report["selected"] = 30
    filter_report.to_csv(filter_report_csv, index=False)

    summary_rows = [
        ("selected_passages", len(selected)),
        ("authors", selected["author_id"].nunique()),
        ("works", selected["work_id"].nunique()),
        ("selected_per_author", 60),
        ("selected_per_work", 30),
        ("min_word_count", int(selected["word_count"].min())),
        ("max_word_count", int(selected["word_count"].max())),
        ("mean_word_count", round(float(selected["word_count"].mean()), 3)),
        ("candidate_source_rows", len(df)),
        ("eligible_after_filters", len(eligible)),
        ("selection_seed", "not_used_deterministic_even_spread"),
        ("selection_status", "complete"),
    ]
    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerows(summary_rows)

    md_paths = make_markdown_files(selected)
    with md_manifest_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["author_id", "path", "size_bytes", "sha256"])
        writer.writeheader()
        for path in md_paths:
            writer.writerow({
                "author_id": path.stem.replace("selected_passages_", ""),
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha_file(path),
            })

    write_manifest(
        [selected_csv, metadata_csv, counts_author_csv, counts_work_csv, summary_csv, filter_report_csv, md_manifest_csv] + md_paths,
        manifest_csv,
    )

    report_lines = [
        "# Step 8 Final Balanced Passage Selection Report\n\n",
        "## Status\n\nComplete.\n\n",
        "## Final dataset size\n\n",
        "- authors: 6\n",
        "- works: 12\n",
        "- selected passages per work: 30\n",
        "- selected passages per author: 60\n",
        "- total selected original passages: 360\n\n",
        "## Counts by author\n\n",
    ]
    for _, row in counts_author.iterrows():
        report_lines.append(f"- {row['author_id']}: {int(row['selected_passages'])} passages, mean words {row['mean_words']}\n")
    report_lines.extend([
        "\n## Completion judgment\n\n",
        "Step 8 is complete for the original-passage layer. The selected original passages are ready for later rewriting conditions: paraphrase, modernize, and simplify.\n",
    ])
    status_md.write_text("".join(report_lines), encoding="utf-8")

    print(f"Selected {len(selected)} passages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
