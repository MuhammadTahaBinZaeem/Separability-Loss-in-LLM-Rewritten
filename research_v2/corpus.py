"""Source-boundary audit and deterministic, balanced, frozen fiction corpus."""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict

from .io import OUT, ROOT, digest_text, file_hash, normalized_text, read_csv, read_json, write_csv, write_json, write_text

AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
SEED = 20260915
WORD = re.compile(r"\b[\w’'-]+\b", re.UNICODE)
END = re.compile(r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", re.I)
NOTE_MARKER = re.compile(r"\[(?:\d+|[A-Z])\]|\(\*\d+\)")


def words(text: str) -> int:
    return len(WORD.findall(text))


def clean_text(text: str) -> str:
    """Preserve paragraphs/punctuation; remove line wrapping and note callouts only."""
    return "\n\n".join(re.sub(r"\s+", " ", NOTE_MARKER.sub("", p)).strip()
                       for p in re.split(r"\n\s*\n", normalized_text(text).strip()) if p.strip())


def source_text(gid: int) -> str:
    path = OUT / "sources" / f"pg{gid}.txt"
    if file_hash(path) != read_json(path.with_suffix(".json"))["raw_sha256"]:
        raise ValueError(f"Source hash mismatch {gid}")
    return normalized_text(path.read_text(encoding="utf-8-sig"))


def anchor_position(text: str, anchor: str, start: int = 0) -> int:
    pattern = r"\s+".join(re.escape(w) for w in anchor.split())
    matches = list(re.finditer(pattern, text[start:], flags=re.I))
    if len(matches) != 1:
        raise ValueError(f"Anchor must be unique after offset {start}: {anchor!r}; matches={len(matches)}")
    return start + matches[0].start()


def bounds(spec: dict, raw: str) -> tuple[int, int]:
    start = anchor_position(raw, spec["start"])
    if spec["end"] == "__GUTENBERG_END__":
        match = END.search(raw, start)
        if not match:
            raise ValueError("Missing Gutenberg end marker")
        end = match.start()
    else:
        end = anchor_position(raw, spec["end"], start + len(spec["start"]))
    if end <= start:
        raise ValueError("Invalid work boundaries")
    return start, end


def paragraph_issue(text: str) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    if re.search(r"\b(?:Illustration|Transcriber|Redactor|Footnotes|Gutenberg|Copyright|CHISWICK PRESS)\b", flat, re.I):
        return "editorial_or_illustration"
    if re.match(r"^\s*(?:\[Footnote|\(\*\d+\)|\[(?:\d+|[A-Z])\]|Notes\s+(?:to|[—-])|NOTE\.—)", text, re.I):
        return "note_body"
    if re.match(r"^(?:CHAPTER|CHAP\.|BOOK|VOLUME|CONTENTS|PREFACE|CONCLUSION)\b", flat, re.I):
        return "section_heading"
    if re.fullmatch(r"[_ ]*[IVXLCDM]+[._ ]*", flat):
        return "section_heading"
    if len(flat) < 200 and re.fullmatch(r"[A-Z\s\d—.,:;'’\-]+", flat) and len(flat.split()) > 1:
        return "uppercase_heading_or_insert"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 2 and max(map(len, lines)) < 65 and (re.match(r"^-{2,}", flat) or re.search(r"\[[A-Z]\]$", flat)):
        return "quoted_verse"
    if len(lines) >= 3 and sum(len(line) < 48 for line in lines) / len(lines) >= 0.8:
        return "verse_table_or_short_line_insert"
    if len(flat) > 30 and sum(c.isalpha() for c in flat) / len(flat) < 0.5:
        return "nonprose_or_cipher"
    return ""


def editorial_spans(raw: str) -> list[tuple[int, int]]:
    """Entire bracketed illustrations, including captions separated by blank lines."""
    spans = []
    for match in re.finditer(r"\[(?:Illustration|Transcriber|Redactor)\b", raw, re.I):
        depth, end = 0, None
        for i in range(match.start(), len(raw)):
            if raw[i] == "[":
                depth += 1
            elif raw[i] == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            raise ValueError("Unclosed editorial bracket in archived source")
        spans.append((match.start(), end))
    return spans


def candidates(spec: dict, raw: str) -> tuple[list[dict], list[dict]]:
    left, right = bounds(spec, raw)
    body = raw[left:right]
    excluded = []
    blocked = editorial_spans(raw)
    blocks: list[list[tuple[int, int]]] = [[]]
    for match in re.finditer(r"\S[\s\S]*?(?=\n\s*\n|\Z)", body):
        a, b = left + match.start(), left + match.end()
        text = raw[a:b]
        issue = "editorial_bracket_span" if any(a < end and b > start for start,end in blocked) else paragraph_issue(text)
        if spec.get("exclude_editorial_interpolations") and "[" in NOTE_MARKER.sub("", text):
            issue = "editorial_interpolation_in_critical_edition"
        if issue:
            excluded.append({"work_id": spec["work_id"], "source_id": spec["source_id"],
                             "start_char": a, "end_char": b, "reason": issue,
                             "excerpt": re.sub(r"\s+", " ", text)[:200]})
            blocks.append([])
            continue
        # Use sentence ends even in short paragraphs to avoid preferentially
        # discarding long-paragraph authors or exhausting shorter fiction works.
        # Whitespace following an abbreviation does not count as a boundary.
        cursor = a
        for sep in re.finditer(r"[.!?][\"”’']*\s+(?=[A-Z\"“‘])", text):
            prefix = text[max(0, sep.start()-12):sep.start()+1]
            if re.search(r"\b(?:Mr|Mrs|Ms|Dr|St|Rev|Prof|Mme|Mlle|vs|etc)\.$", prefix):
                continue
            boundary = a + sep.end()
            blocks[-1].append((cursor, boundary))
            cursor = boundary
        if cursor < b:
            blocks[-1].append((cursor, b))
    result = []
    for block in blocks:
        i = 0
        while i < len(block):
            first = i
            start = block[i][0]
            stop = block[i][1]
            count = words(clean_text(raw[start:stop]))
            while count < 450 and i + 1 < len(block):
                if words(clean_text(raw[start:block[i+1][1]])) > 650:
                    break
                i += 1
                stop = block[i][1]
                count = words(clean_text(raw[start:stop]))
            if 450 <= count <= 650:
                text = clean_text(raw[start:stop])
                result.append({"author_id": spec["author_id"], "work_id": spec["work_id"],
                               "work_title": spec["title"], "gutenberg_id": spec["source_id"],
                               "source_start_char": start, "source_end_char": stop,
                               "word_count": count, "text_sha256": digest_text(text), "text": text})
                i += 1
            else:
                i = first + 1
    return result, excluded


def flat_with_map(text: str) -> tuple[str, list[int]]:
    """Whitespace-normalized lookup with a reversible map to archived source offsets."""
    chars, positions = [], []
    for match in re.finditer(r"\S+", text):
        if chars:
            chars.append(" "); positions.append(match.start() - 1)
        chars.extend(match.group()); positions.extend(range(match.start(), match.end()))
    return "".join(chars), positions


def legacy_audit(specs: list[dict], sources: dict[int, str]) -> list[dict]:
    rows = read_csv(ROOT / "data/processed/selected_original_passages.csv")
    cache = {gid: flat_with_map(text) for gid, text in sources.items()}
    by_source = defaultdict(list)
    for spec in specs:
        a, b = bounds(spec, sources[spec["source_id"]])
        by_source[spec["source_id"]].append((a, b, spec))
    results = []
    for row in rows:
        gid = int(row["gutenberg_ebook_no"])
        flat, positions = cache[gid]
        needle = " ".join(row["text"].split())
        loc = flat.find(needle)
        source_start, source_end, work, reason = -1, -1, "", ""
        if loc == -1:
            reason = "no_exact_match_in_archived_edition"
        else:
            source_start, source_end = positions[loc], positions[loc + len(needle) - 1] + 1
            containing = [(a,b,s) for a,b,s in by_source[gid] if a <= source_start and source_end <= b]
            if containing:
                work = containing[0][2]["work_id"]
                issues = sorted({paragraph_issue(p) for p in re.split(r"\n\s*\n", row["text"]) if paragraph_issue(p)})
                reason = ";".join(issues)
            else:
                reason = "outside_v2_fiction_boundaries_or_crosses_works"
        # This is an eligibility audit, not a declaration that every unselected work is non-fiction.
        results.append({"legacy_passage_id": row["passage_id"], "author_id": row["author_id"],
                        "legacy_volume": row["work_id"], "gutenberg_id": gid,
                        "source_start_char": source_start, "source_end_char": source_end,
                        "independent_work_id": work,
                        "disposition": "eligible_body" if not reason else "exclude_or_review",
                        "reason": reason or "exact_source_match_within_verified_work_body",
                        "review_method": "AI-assisted source-boundary mapping plus paragraph rules",
                        "human_independent_review": "no", "legacy_text_sha256": digest_text(row["text"]),
                        "opening": needle[:160], "closing": needle[-120:]})
    if len(results) != 360 or len({r["legacy_passage_id"] for r in results}) != 360:
        raise ValueError("Historical audit must cover every one of the 360 passages exactly once")
    return results


def build(supersede_draft: bool = False) -> None:
    specs = read_json(OUT / "work_specs.json")
    sources = {gid: source_text(gid) for gid in sorted({s["source_id"] for s in specs} | {2148})}
    selected, all_excluded, registry = [], [], []
    for spec in specs:
        pool, exclusions = candidates(spec, sources[spec["source_id"]])
        all_excluded.extend(exclusions)
        if len(pool) < 20:
            raise ValueError(f"Insufficient nonoverlapping fiction candidates in {spec['work_id']}: {len(pool)}")
        # All candidate windows are nonoverlapping; spread fixed count through each work.
        chosen = [pool[round(i * (len(pool)-1) / 19)] for i in range(20)]
        work_order = sorted([s["work_id"] for s in specs if s["author_id"] == spec["author_id"]],
                            key=lambda w: digest_text(f"{SEED}:{spec['author_id']}:{w}"))
        fold = work_order.index(spec["work_id"])
        for index, row in enumerate(chosen, start=1):
            selected.append({"passage_id": f"V2_{row['author_id']}_{row['work_id']}_{index:03d}",
                             "outer_fold": fold, **row})
        a, b = bounds(spec, sources[spec["source_id"]])
        registry.append({**spec, "exclude_editorial_interpolations": bool(spec.get("exclude_editorial_interpolations")),
                         "body_start_char": a, "body_end_char": b, "candidate_count": len(pool),
                         "selected_count": 20, "outer_fold": fold,
                         "body_sha256": digest_text(sources[spec["source_id"]][a:b]),
                         "source_sha256": file_hash(OUT / "sources" / f"pg{spec['source_id']}.txt")})
        print(f"{spec['author_id']}/{spec['work_id']}: {len(pool)} eligible windows, selected 20", flush=True)
    selected.sort(key=lambda r: r["passage_id"])
    if Counter(r["author_id"] for r in selected) != Counter({a: 60 for a in AUTHORS}):
        raise ValueError("Corpus not balanced")
    if len({r["text_sha256"] for r in selected}) != len(selected):
        raise ValueError("Duplicate selected text")
    content_hash = digest_text("\n".join(f"{r['passage_id']}:{r['text_sha256']}:{r['outer_fold']}" for r in selected))
    freeze_path = OUT / "corpus/freeze.json"
    if freeze_path.exists() and read_json(freeze_path)["corpus_sha256"] != content_hash:
        if not supersede_draft:
            raise ValueError("Frozen corpus would change: explicitly archive the unsubmitted draft before rebuilding")
        if any(OUT.glob("generation/*/raw_responses.jsonl")):
            raise ValueError("Cannot supersede a corpus after provider generation; create a separate experiment")
        import shutil
        old_hash = read_json(freeze_path)["corpus_sha256"]
        archive = OUT / "history" / ("pre_generation_draft_" + old_hash[:12])
        if archive.exists():
            raise ValueError("Draft archive already exists")
        archive.mkdir(parents=True)
        for name in ("corpus", "generation", "results"):
            old = (OUT / name).resolve()
            if not old.is_relative_to(OUT.resolve()):
                raise ValueError("Unsafe draft archive target")
            if old.exists():
                shutil.move(str(old), str(archive / name))
        write_text(archive / "README.md", "# Withdrawn pre-generation draft\n\n"
                   "Superseded during source review on 2026-09-19, before provider API generation.\n"
                   "Found multi-paragraph illustration captions in Pride and Prejudice and\n"
                   "editorial interpolations/quoted verse in the critical Mathilda edition.\n"
                   "Original draft artifacts are retained for audit; never use them as final evidence.\n"
                   "The separate agent feasibility packets refer to this draft and require source revalidation.\n")
    write_csv(OUT / "corpus/originals.csv", selected)
    write_csv(OUT / "corpus/work_registry.csv", registry)
    write_csv(OUT / "corpus/excluded_source_blocks.csv", all_excluded)
    audit = legacy_audit(specs, sources)
    write_csv(OUT / "corpus/legacy_360_audit.csv", audit)
    write_json(freeze_path, {"version": 2, "seed": SEED, "corpus_sha256": content_hash,
                            "originals_file_sha256": file_hash(OUT / "corpus/originals.csv"),
                            "work_specs_sha256": file_hash(OUT / "work_specs.json"),
                            "protocol_sha256_at_freeze": file_hash(OUT / "PROTOCOL.md"),
                            "author_count": 6, "work_count": 18, "passage_count": 360,
                            "generation_conditions": ["paraphrase", "modernize", "simplify"]})
    for author in AUTHORS:
        review = [f"# Revised corpus: {author}", "", "Source-boundary review; no human semantic ratings are asserted.", ""]
        for row in selected:
            if row["author_id"] != author:
                continue
            review += [f"## {row['passage_id']}", "", f"Work: {row['work_title']}; source: pg{row['gutenberg_id']}; "
                       f"characters {row['source_start_char']}–{row['source_end_char']}; words: {row['word_count']}", "", row["text"], ""]
        write_text(OUT / f"corpus/review/{author}.md", "\n".join(review))
    write_json(OUT / "corpus/audit_summary.json", {"legacy_rows_reviewed": len(audit),
               "legacy_dispositions": dict(Counter(r["disposition"] for r in audit)),
               "legacy_reasons": dict(Counter(r["reason"] for r in audit)),
               "review_is_ai_assisted": True, "independent_human_review": False,
               "new_passages": len(selected), "new_works": len(registry), "excluded_source_blocks": len(all_excluded)})
    print(f"Frozen corpus: {content_hash}")


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supersede-unsubmitted-draft",action="store_true")
    args=parser.parse_args()
    build(args.supersede_unsubmitted_draft)


if __name__ == "__main__":
    main()
