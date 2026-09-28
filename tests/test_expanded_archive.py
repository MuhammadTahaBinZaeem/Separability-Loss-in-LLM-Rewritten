import pytest

from research_v2.expanded_archive import safe_member


@pytest.mark.parametrize("name", ["private/returns.jsonl", "annotations/returns/reviewer.csv", "api.env", "private_access_8765.txt", "credentials.json", "reviews.sqlite3", "RUNNING.lock"])
def test_expanded_archive_rejects_private_and_live_paths(tmp_path, name):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetic test", encoding="utf-8")
    with pytest.raises(ValueError, match="Private"):
        safe_member(path, tmp_path)


def test_expanded_archive_rejects_escape_and_accepts_explicit_data(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    data = root / "outcomes.jsonl"
    data.write_text("synthetic test", encoding="utf-8")
    assert safe_member(data, root) == data
    outside = tmp_path / "outside.txt"
    outside.write_text("synthetic test", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsafe"):
        safe_member(root / ".." / "outside.txt", root)
