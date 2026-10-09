"""Blinded supplemental rewrite packets for explicitly disclosed agent generation."""
from __future__ import annotations

from collections import defaultdict

from .generation import INSTRUCTIONS, SYSTEM, verify_corpus
from .io import OUT, digest_text, read_csv, write_csv, write_json, write_text


def main() -> None:
    verify_corpus()
    originals = read_csv(OUT / "corpus/originals.csv")
    groups = defaultdict(list)
    for row in originals:
        groups[row["work_id"]].append(row)
    # A predeclared feasibility sample: one source passage per independent work.
    sample = [min(rows, key=lambda r:digest_text("agent_feasibility_20260919:"+r["passage_id"])) for rows in groups.values()]
    key_rows = []
    for condition in INSTRUCTIONS:
        packet = []
        for row in sample:
            rid = digest_text("agent_feasibility_20260919:"+row["passage_id"]+":"+condition)[:24]
            packet.append({"request_id":rid,"original_word_count":int(row["word_count"]),"text":row["text"]})
            key_rows.append({"request_id":rid,"passage_id":row["passage_id"],"condition":condition,"source_sha256":row["text_sha256"]})
        packet.sort(key=lambda r:r["request_id"])
        write_json(OUT / f"agent_rewrite/packets/{condition}.json",{"system_instruction":SYSTEM,
                    "condition_instruction":INSTRUCTIONS[condition],"requests":packet})
    write_csv(OUT / "agent_rewrite/private_join_key.csv",key_rows)
    write_text(OUT / "agent_rewrite/README.md", """# Supplemental agent rewrite feasibility sample

Requested by the author on 2026-09-19. One passage per work (18), three rewrite
conditions, requested agent model `gpt-5.5`. This small feasibility sample is
separate from the two provider-API experiments in PROTOCOL.md. It cannot replace
their missing outputs. Each condition is generated in one persistent agent
context with a blinded packet. That context includes multiple passages; outputs
are therefore not independent single-request API calls. No provider response IDs
or token usage are asserted. Record actual agent-task metadata and artifact
hashes. These rewrites are not human annotations. The source key is for the
pipeline; generation agents must receive only their packet.
""")


if __name__ == "__main__":
    main()
