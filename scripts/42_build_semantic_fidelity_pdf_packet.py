"""Build a PDF annotation packet containing actual E4 audit passages.

Reads:
- data/audit/semantic_fidelity_sample.csv

Writes:
- data/audit/semantic_fidelity_annotation_packet.pdf
- logs/semantic_fidelity_pdf_packet_report.md

The PDF includes each sampled original/rewrite pair followed by MCQ-style coding
fields. This is for annotators. It does not fabricate annotations.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data/audit/semantic_fidelity_sample.csv"
OUT = ROOT / "data/audit/semantic_fidelity_annotation_packet.pdf"
REPORT = ROOT / "logs/semantic_fidelity_pdf_packet_report.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def clean(text: str) -> str:
    return escape(text).replace("\n", "<br/>")


def checkbox(label: str) -> str:
    return f"[ ] {escape(label)}"


def build(max_items: int | None = None) -> int:
    rows = read_csv(SAMPLE)
    if max_items is not None:
        rows = rows[:max_items]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4, rightMargin=1.3*cm, leftMargin=1.3*cm,
        topMargin=1.15*cm, bottomMargin=1.15*cm
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("PacketTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=18, leading=22, spaceAfter=12)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=13, leading=16, spaceBefore=8, spaceAfter=5)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=10.5, leading=13, spaceBefore=4, spaceAfter=3)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=8.2, leading=10.3, spaceAfter=4)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=7.4, leading=9.2)
    mcq = ParagraphStyle("MCQ", parent=styles["BodyText"], fontSize=8.0, leading=10.0, leftIndent=8)

    story = []
    story += [Paragraph("Semantic Fidelity Audit - Annotator Packet", title)]
    story += [Paragraph("Purpose", h1), Paragraph("For each item, compare the original passage with the rewritten passage. Mark whether the rewrite preserved meaning. Do not judge author style. Do not try to identify the source author.", body)]
    story += [Paragraph("MCQ coding fields", h1)]
    coding_rows = [
        [Paragraph("Field", small), Paragraph("Choices", small)],
        [Paragraph("added_facts_0_1", small), Paragraph("0 = no added material fact; 1 = added important fact/detail/event/object/relationship", small)],
        [Paragraph("omitted_facts_0_1", small), Paragraph("0 = no important omission; 1 = omitted important fact/detail/event/object/relationship", small)],
        [Paragraph("narrative_order_change_0_1", small), Paragraph("0 = order preserved; 1 = event/reasoning/dialogue order changed", small)],
        [Paragraph("speaker_or_character_relation_change_0_1", small), Paragraph("0 = preserved; 1 = who speaks/acts/relates changed", small)],
        [Paragraph("tone_drift_0_2", small), Paragraph("0 = no meaningful drift; 1 = mild drift; 2 = strong tone drift", small)],
        [Paragraph("meaning_preservation_1_5", small), Paragraph("1 = badly changed; 2 = substantial change; 3 = partly preserved; 4 = mostly preserved; 5 = very close", small)],
        [Paragraph("overall_usable_yes_no", small), Paragraph("yes = usable for controlled style experiment; no = semantic drift too severe", small)],
    ]
    table = Table(coding_rows, colWidths=[5.0*cm, 12.0*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [table, PageBreak()]

    for i, r in enumerate(rows, start=1):
        item_title = f"Item {i:03d} / {r['audit_id']} / condition: {r['condition']}"
        story.append(Paragraph(item_title, h1))
        story.append(Paragraph("Original passage", h2))
        story.append(Paragraph(clean(r["original_text"]), body))
        story.append(Spacer(1, 5))
        story.append(Paragraph("Rewritten passage", h2))
        story.append(Paragraph(clean(r["rewritten_text"]), body))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Mark your answers", h2))
        choices = [
            "added_facts_0_1: " + checkbox("0") + "   " + checkbox("1"),
            "omitted_facts_0_1: " + checkbox("0") + "   " + checkbox("1"),
            "narrative_order_change_0_1: " + checkbox("0") + "   " + checkbox("1"),
            "speaker_or_character_relation_change_0_1: " + checkbox("0") + "   " + checkbox("1"),
            "tone_drift_0_2: " + checkbox("0") + "   " + checkbox("1") + "   " + checkbox("2"),
            "meaning_preservation_1_5: " + checkbox("1") + " " + checkbox("2") + " " + checkbox("3") + " " + checkbox("4") + " " + checkbox("5"),
            "overall_usable_yes_no: " + checkbox("yes") + "   " + checkbox("no"),
            "notes: ________________________________________________________________",
            "      ________________________________________________________________",
        ]
        for c in choices:
            story.append(Paragraph(c, mcq))
        if i != len(rows):
            story.append(PageBreak())

    doc.build(story)
    counts = Counter(r["condition"] for r in rows)
    REPORT.write_text(
        "# Semantic Fidelity PDF Packet Report\n\n"
        f"- pdf: `{OUT.relative_to(ROOT)}`\n"
        f"- items_in_pdf: {len(rows)}\n"
        f"- condition_counts: {dict(sorted(counts.items()))}\n",
        encoding="utf-8"
    )
    print(f"Built PDF packet: {OUT} ({len(rows)} items)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-items", type=int, default=None)
    args = parser.parse_args()
    return build(args.max_items)

if __name__ == "__main__":
    raise SystemExit(main())
