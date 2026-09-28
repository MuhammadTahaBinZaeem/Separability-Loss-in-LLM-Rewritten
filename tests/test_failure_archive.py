from research_v2.failure_archive import visible_segments


def test_native_refusal_and_partial_prose_are_retained_without_inventing_text():
    response = {"output": [{"type": "reasoning", "summary": [{"text": "not rewrite text"}]},
                           {"type": "message", "content": [{"type": "output_text", "text": '{"rewritten_text":"partial'},
                                                            {"type": "refusal", "refusal": "Synthetic refusal fixture."}]}]}
    result = visible_segments("azure_responses", response)
    assert [r["kind"] for r in result] == ["text", "refusal"]
    assert result[0]["text"] == '{"rewritten_text":"partial'
    assert result[1]["text"] == "Synthetic refusal fixture."
    assert visible_segments("azure_responses", {}) == []
    gem = {"candidates": [{"content": {"parts": [{"thought": True, "text": "not output"}, {"text": "visible"}]}}]}
    assert [r["text"] for r in visible_segments("gemini_native", gem)] == ["visible"]
