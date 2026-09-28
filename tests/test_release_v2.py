"""Offline release helpers must not turn missing evidence into success."""
import pytest

from research_v2.io import write_text


@pytest.fixture
def archive_study(tmp_path, monkeypatch):
    """Test package policy independently of mutable, local research results."""
    import research_v2.archive as module
    from research_v2.io import write_json
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "OUT", tmp_path / "revision")
    for name in module.EXPLICIT:
        write_text(tmp_path / name, "synthetic public artifact\n")
    write_json(tmp_path / "revision/generation_plan.json", {"models": {}})
    return module, tmp_path


def test_archive_never_includes_private_review_administration(archive_study):
    module, root = archive_study
    private = ["revision/annotations/private_join_key.csv",
               "revision/annotations/reviewer_registry.json",
               "revision/annotations/returns/A.csv",
               "revision/review_app/private/access.json",
               "revision/review_app/private/reviews.sqlite3",
               "api.env"]
    for name in private:
        write_text(root / name, "synthetic private artifact\n")
    paths=module.package_files()
    assert not set(paths) & {root / name for name in private}
    assert not any(p.name in {"private_join_key.csv","reviewer_registry.json","api.env","RUNNING.lock"} for p in paths)
    assert not any("returns" in p.parts for p in paths)


@pytest.mark.parametrize("stale_part", ["input", "output", "verification"])
def test_archive_rejects_stale_extension_evidence(archive_study, stale_part):
    from research_v2.io import write_json, file_hash
    module, root = archive_study
    folder = root / "revision/extensions/jql_v1/azure_replication"
    source = root / "revision/PROTOCOL.md"
    output = folder / "synthetic_result.txt"
    write_text(output, "synthetic result\n")
    manifest = folder / "manifest.json"
    write_json(manifest, {"inputs": {"revision/PROTOCOL.md": file_hash(source)},
                          "output_hashes": {output.name: file_hash(output)}})
    write_json(folder / "verification.json", {"manifest_sha256": file_hash(manifest)})
    assert output in module.package_files()
    if stale_part == "input":
        write_text(source, "changed protocol\n")
    elif stale_part == "output":
        write_text(output, "changed result\n")
    else:
        write_json(folder / "verification.json", {"manifest_sha256": "stale"})
    with pytest.raises(ValueError):
        module.package_files()


def test_secret_scan_reports_paths_not_values(tmp_path,monkeypatch):
    import research_v2.archive as module
    monkeypatch.setattr(module,"ROOT",tmp_path)
    env=tmp_path / "outside.env"; artifact=tmp_path / "artifact.txt"
    credential="private-token-that-must-not-appear-in-the-report"
    write_text(env,f"zenodo_token={credential}\n")
    write_text(artifact,f"accidental value: {credential}")
    report=module.scan([artifact],env)
    assert not report["passed"] and report["matched_files"]==["artifact.txt"]
    assert credential not in str(report)


def test_no_published_record_means_no_verified_doi(tmp_path,monkeypatch):
    import research_v2.release as module
    monkeypatch.setattr(module,"OUT",tmp_path)
    report=module.published_archive_check()
    assert not report["passed"] and "doi" not in report


def test_pending_manuscript_has_no_invented_results(tmp_path,monkeypatch):
    import research_v2.paper_assets as module
    from research_v2.io import OUT,write_csv
    write_text(tmp_path / "manuscript_v2_template.md",(OUT / "manuscript_v2_template.md").read_text(encoding="utf-8"))
    write_csv(tmp_path / "corpus/work_registry.csv",[{"author_id":"austen","title":"Emma","source_id":"158","outer_fold":"0"}])
    monkeypatch.setattr(module,"OUT",tmp_path)
    monkeypatch.setattr(module,"FOLDER",tmp_path / "paper_assets")
    report=module.run()
    text=(tmp_path / "paper_assets/manuscript_REVIEW_DRAFT.md").read_text(encoding="utf-8")
    assert report["submission_ready"] is False and report["computational_results_included"] is False
    assert "Pending complete, current-code analysis" in text
    assert "{{" not in text and "No published, checksum-verified archival DOI" in text


def test_active_generation_blocks_offline_rebuild(tmp_path,monkeypatch):
    import research_v2.reproduce as module
    from research_v2.io import write_json
    write_json(tmp_path / "generation_plan.json",{"models":{"test":{}}})
    write_text(tmp_path / "generation/test/RUNNING.lock","123")
    monkeypatch.setattr(module,"OUT",tmp_path)
    with pytest.raises(ValueError,match="Generation is active"):
        module.run()
