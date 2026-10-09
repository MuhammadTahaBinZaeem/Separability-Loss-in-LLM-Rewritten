"""The current reviewer handouts and visible page stay origin-neutral."""
import re

from research_v2.io import ROOT


def test_current_reviewer_materials_use_neutral_labels():
    paths = (
        ROOT / "review_app/index.html",
        ROOT / "revision/expanded_v3/annotations/REVIEWER_GUIDE.md",
        ROOT / "revision/expanded_v3/source_review/REVIEWER_GUIDE.md",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\b(?:AI|human|GPT|Gemini|machine-assisted)\b", text, re.I), path
    assert "1,620 pairs" in paths[1].read_text(encoding="utf-8")
    assert "four-passage" in paths[2].read_text(encoding="utf-8")
    recruitment = (ROOT / "revision/annotations/RECRUITMENT.md").read_text(encoding="utf-8")
    invitation = recruitment.split("## Ready-to-send invitation", 1)[1].split("## If university", 1)[0]
    assert not re.search(r"\b(?:AI|human|GPT|Gemini|machine-assisted)\b", invitation, re.I)


def test_completion_uses_short_confirmation_without_extra_checkbox():
    page = (ROOT / "review_app/index.html").read_text(encoding="utf-8")
    script = (ROOT / "review_app/app.js").read_text(encoding="utf-8")
    assert "Selecting <strong>Submit my review</strong> confirms these are your own independent judgments." in page
    assert 'id="reviewer-attest"' not in page
    assert 'id="checker-attest"' not in page
    assert "Selecting <strong>Save provenance record</strong> confirms you personally performed the check" in page
    assert 'attest_human:isReviewAssignment(assignment)' in script
    assert 'checked_by_human:true' in script
