import json

import pytest

from research_v2 import archive, expanded_archive
from research_v2.expanded_archive import safe_member
from research_v2.io import file_hash, write_json


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


def test_returned_review_archive_is_derived_only_and_tamper_checked(tmp_path, monkeypatch):
    monkeypatch.setattr(expanded_archive, "ROOT", tmp_path)
    monkeypatch.setattr(expanded_archive, "BASE", tmp_path / "study")
    folder = tmp_path / "study/review_results/provisional_synthetic"
    outputs = {}
    for name in ("flags.csv", "agreement.csv", "rating_summary.csv", "comparisons.csv"):
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic aggregate only.\n", encoding="utf-8")
        outputs[name] = file_hash(path)
    private = tmp_path / "study/annotations/private/returned_batches/original.md"
    private.parent.mkdir(parents=True)
    private.write_text("Private synthetic identity.\n", encoding="utf-8")
    code = tmp_path / "research_v2/review_return_audit.py"
    code.parent.mkdir()
    code.write_text("# Synthetic code\n", encoding="utf-8")
    record = {"stage": "provisional_analysis_pending_reviewer_metadata", "review_provenance_complete": False,
              "submission_ready": False, "result_replay_passed": True, "output_hashes": outputs,
              "analysis_code_sha256": {code.name: file_hash(code)}}
    write_json(folder / "manifest.json", record)
    # safe_member's default root was bound at definition time; this fixture must
    # explicitly supply its synthetic root, never touch production artifacts.
    monkeypatch.setattr(expanded_archive, "safe_member", lambda path: safe_member(path, tmp_path))
    paths = set()
    expanded_archive.include_returned_review_results(paths)
    assert len(paths) == 5 and private not in paths
    (folder / "flags.csv").write_text("Tampered synthetic data.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="output changed"):
        expanded_archive.include_returned_review_results(set())
    record["output_hashes"]["../original.md"] = "synthetic"
    write_json(folder / "manifest.json", record)
    with pytest.raises(ValueError, match="scope"):
        expanded_archive.include_returned_review_results(set())


def test_reviewed_release_keeps_ethics_and_identity_claims_fail_closed(tmp_path, monkeypatch):
    root = tmp_path
    base = root / "study"
    monkeypatch.setattr(expanded_archive, "ROOT", root)
    monkeypatch.setattr(expanded_archive, "BASE", base)
    monkeypatch.setattr(expanded_archive, "safe_member", lambda path: safe_member(path, root))
    folder = base / "review_release/self_reported_synthetic"
    output_hashes = {}
    for name in expanded_archive.REVIEWED_OUTPUTS:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic de-identified output.\n", encoding="utf-8")
        output_hashes[name] = file_hash(path)
    code = root / "research_v2/review_finalize.py"
    code.parent.mkdir(parents=True)
    code.write_text("# Synthetic fixture only\n", encoding="utf-8")
    for relative in ("annotations/verified_flags.csv", "annotations/agreement.csv", "annotations/validation.json",
                     "semantic_sensitivity/comparisons.csv", "semantic_sensitivity/status.json"):
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic de-identified output.\n", encoding="utf-8")
    manifest = {"stage": "registered_investigator_reported_reviews", "review_complete": True, "submission_ready": False,
                "submission_ethics_gate_satisfied": False, "independence_objectively_verified": False,
                "public_ratings_replay_passed": True, "result_replay_passed": True,
                "output_hashes": output_hashes, "analysis_code_sha256": {code.name: file_hash(code)},
                "semantic_validation_sha256": file_hash(base / "annotations/validation.json")}
    status = {"complete": True, "release_folder": "review_release/self_reported_synthetic"}
    def save():
        write_json(folder / "manifest.json", manifest)
        status["manifest_sha256"] = file_hash(folder / "manifest.json")
        write_json(base / "review_release/status.json", status)
    save()
    paths = set()
    expanded_archive.include_current_review_release(paths)
    assert folder / "ratings.csv" in paths
    assert all("private" not in path.parts for path in paths)
    manifest["independence_objectively_verified"] = True
    save()
    with pytest.raises(ValueError, match="scope"):
        expanded_archive.include_current_review_release(set())
    manifest["independence_objectively_verified"] = False
    manifest["submission_ethics_gate_satisfied"] = True
    save()
    with pytest.raises(ValueError, match="scope"):
        expanded_archive.include_current_review_release(set())


def test_encrypted_reasoning_pattern_exception_keeps_exact_secret_scan(tmp_path, monkeypatch):
    monkeypatch.setattr(archive, "ROOT", tmp_path)
    monkeypatch.setattr(expanded_archive, "ROOT", tmp_path)
    path = tmp_path / "revision/expanded_v3/generation/codex51/outcomes.jsonl"
    path.parent.mkdir(parents=True)
    env = tmp_path / "test.env"
    env.write_text("AZURE_API_KEY=synthetic-exact-secret-value\n", encoding="utf-8")
    response = {"output": [{"type": "reasoning", "encrypted_content": "sk-" + "a" * 40},
                           {"type": "message", "content": [{"type": "output_text", "text": "safe rewrite"}]}]}
    event = {"response": response, "response_body": json.dumps(response)}
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    report = expanded_archive.scan_package([path], env)
    assert report["passed"] and report["exact_credential_scan"]
    assert report["encrypted_reasoning_pattern_exception"]["records"] == 1

    response["output"][1]["content"][0]["text"] = "synthetic-exact-secret-value"
    path.write_text(json.dumps({"response": response, "response_body": json.dumps(response)}) + "\n", encoding="utf-8")
    assert not expanded_archive.scan_package([path], env)["passed"]

    response["output"][1]["content"][0]["text"] = "safe rewrite"
    path.write_text(json.dumps({"response": response, "response_body": "{}"}) + "\n", encoding="utf-8")
    assert not expanded_archive.scan_package([path], env)["passed"]
