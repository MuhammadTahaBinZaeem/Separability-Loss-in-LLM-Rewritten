"""Synthetic fixtures only: no test writes ratings or attestations into the real study."""
import http.client
import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer

import pytest

from research_v2.io import digest_text, file_hash, read_csv, read_json, read_jsonl, write_csv, write_json, write_jsonl, write_text
from research_v2.review_app import ReviewError, ReviewStore, SEMANTIC_FIELDS, handler_for, row_errors


@pytest.fixture
def review_store(tmp_path):
    research = tmp_path / "synthetic_study"
    issued = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    text = "A fictional test passage, with a comma.\nAnd another line."
    raw = "Test preface.\n" + text + "\nTest afterword."
    source = research / "sources/pg1.txt"
    write_text(source, raw)
    write_json(source.with_suffix(".json"), {"raw_sha256": file_hash(source)})
    rows = [{"passage_id": f"p{i}", "author_id": "synthetic_author", "work_id": "synthetic_work",
             "gutenberg_id": "1", "source_start_char": str(raw.index(text)),
             "source_end_char": str(raw.index(text) + len(text)), "text_sha256": digest_text(text),
             "text": text, "verdict": "", "notes": ""} for i in range(2)]
    write_jsonl(research / "source_review/blank_review.jsonl", rows)
    write_json(research / "source_review/issued_manifest.json",
               {"blank_sha256": file_hash(research / "source_review/blank_review.jsonl"), "issued_utc": issued,
                "corpus_sha256": "synthetic", "items": len(rows)})
    write_csv(research / "corpus/originals.csv", [{k: v for k, v in r.items() if k not in {"verdict", "notes"}} for r in rows])
    write_csv(research / "corpus/work_registry.csv", [{"author_id": "synthetic_author", "work_id": "synthetic_work", "title": "Synthetic test work"}])
    forms = {}
    for a in ("A", "B"):
        forms[a] = [{"item_id": a + str(i), "original_text": text, "rewritten_text": "A fictional rewritten test passage.",
                     **{f: "" for f in SEMANTIC_FIELDS}} for i in range(2)]
        write_csv(research / f"annotations/forms/reviewer_{a}.csv", forms[a])
    write_json(research / "annotations/issued_manifest.json",
               {"issued_utc": issued, "items_per_reviewer": 2,
                "forms_sha256": {a: file_hash(research / f"annotations/forms/reviewer_{a}.csv") for a in ("A", "B")}})
    rewrite = {"passage_id": "p0", "request_id": "synthetic-request", "source_sha256": digest_text(text),
               "rewritten_text": "Synthetic rewrite.", "rewrite_sha256": digest_text("Synthetic rewrite."), "qc_status": "warning"}
    write_csv(research / "generation/azure_replication/rewrites.csv", [rewrite])
    return ReviewStore(research / "review_app/private", research)


def semantic_answers():
    return {"added_facts": "1", "omitted_facts": "0", "order_changed": "0", "relationships_changed": "0",
            "tone_drift": "1", "meaning_preservation": "3", "usable": "no",
            "notes": 'Synthetic test only: "claim", comma, newline\nUnicode café.'}


def test_source_save_is_canonical_resumable_and_revision_safe(review_store):
    session = review_store.create("source", "ai_assisted", "synthetic-ai")
    result = review_store.save(session["id"], "p0", {"verdict": "needs_correction", "notes": "Synthetic fixture boundary concern."}, 0)
    assert result["saved"] and not result["errors"]
    saved = read_jsonl(review_store.export(session["id"]))
    blank = read_jsonl(review_store.research / "source_review/blank_review.jsonl")
    assert saved[0]["verdict"] == "needs_correction"
    assert all(saved[0][k] == v for k, v in blank[0].items() if k not in {"verdict", "notes"})
    with pytest.raises(ReviewError, match="newer save"):
        review_store.save(session["id"], "p0", {"notes": "Stale edit must not win"}, 0)
    reopened = ReviewStore(review_store.private, review_store.research)
    assert reopened.show(session["id"], "p0")["row"]["notes"] == saved[0]["notes"]
    assert reopened.status(session["id"])["revision"] == 1
    assert (review_store.private / "sessions" / session["id"] / "revision_000001.answers.json").exists()


def test_current_draft_rebuilds_from_authoritative_database(review_store):
    session = review_store.create("source", "ai_assisted", "synthetic-ai")
    review_store.save(session["id"], "p0", {"notes": "Saved synthetic note."}, 0)
    path = review_store.export(session["id"])
    write_text(path, "Interrupted or externally corrupted derived draft")
    repaired = read_jsonl(review_store.export(session["id"]))
    assert repaired[0]["notes"] == "Saved synthetic note."
    assert len(list(path.parent.glob("*.draft.jsonl"))) == 1


def test_partial_ratings_save_but_do_not_count_as_complete(review_store):
    session = review_store.create("semantic_A", "ai_assisted", "synthetic-ai")
    result = review_store.save(session["id"], "A0", {"added_facts": "1"}, 0)
    assert result["errors"] and review_store.status(session["id"])["complete"] == 0
    with pytest.raises(ReviewError, match="Complete every"):
        review_store.seal(session["id"], 1)


def test_text_ids_and_invalid_choices_are_rejected(review_store):
    session = review_store.create("source", "ai_assisted", "synthetic-ai")
    for value in ({"text": "modified"}, {"passage_id": "different"}, {"verdict": "probably"}, {"notes": 7}):
        with pytest.raises(ReviewError):
            review_store.save(session["id"], "p0", value, 0)
    with pytest.raises(ReviewError):
        review_store.save(session["id"], "p0", {"notes": "x"}, False)
    assert review_store.status(session["id"])["revision"] == 0


def test_ai_interfaces_cannot_access_or_attest_human_ratings(review_store):
    session = review_store.create("source", "human", "synthetic-human")
    with pytest.raises(ReviewError) as denied:
        review_store.authorize({"role": "agent"}, session["id"])
    assert denied.value.status == 403
    with pytest.raises(ReviewError):
        review_store.save(session["id"], "p0", {"verdict": "pass", "notes": "Not a real review"}, 0)
    with pytest.raises(ReviewError):
        review_store.seal(session["id"], 0, True, "agent_cli")
    ai = review_store.create("source", "ai_assisted", "synthetic-ai")
    with pytest.raises(ReviewError):
        review_store.seal(ai["id"], 0, True)


def test_versioned_packets_reuse_login_only_with_explicit_link(review_store, tmp_path):
    from research_v2.review_batches import ReviewRouter
    parent = review_store.create("source", "human", "synthetic-source")
    child_store = ReviewStore(tmp_path / "new_private", review_store.research)
    child = child_store.create("source", "human", "synthetic-source")
    other = child_store.create("semantic_A", "human", "synthetic-other")
    router = ReviewRouter([("Previous", review_store), ("Follow-up", child_store)])
    token = review_store.assignment(parent["id"])["token"]
    principal = router.authenticate(token)
    with pytest.raises(ReviewError):
        router.authorize(principal, child["id"])
    write_json(child_store.private / "account_links.json", [{"from_research": str(review_store.research), "from_session_id": parent["id"], "to_session_id": child["id"]}])
    principal = router.authenticate(token)
    assert principal["session_id"] == child["id"]
    assert len(principal["assignments"]) == 2
    assert router.authorize(principal, parent["id"])["id"] == parent["id"]
    assert router.authorize(principal, child["id"])["id"] == child["id"]
    with pytest.raises(ReviewError):
        router.authorize(principal, other["id"])
    assert router.show(child["id"], "p0")["context"]["selected_raw"]
    assert router.status(parent["id"])["saved"] == 0


def test_new_waiting_packet_does_not_masquerade_as_old_complete_scope(review_store, tmp_path):
    from research_v2.review_batches import ReviewRouter
    parent = review_store.create("semantic_A", "human", "synthetic-A")
    child_store = ReviewStore(tmp_path / "new_private", tmp_path / "new_study")
    child = child_store.create("semantic_A", "human", "synthetic-A")
    assert child["status"] == "awaiting_packet"
    write_json(child_store.private / "account_links.json", [{"from_research": str(review_store.research), "from_session_id": parent["id"], "to_session_id": child["id"]}])
    router = ReviewRouter([("Previous", review_store), ("Updated", child_store)])
    principal = router.authenticate(review_store.assignment(parent["id"])["token"])
    assert principal["session_id"] == child["id"]
    assert router.status(parent["id"])["total"] == 2
    assert router.status(child["id"])["total"] == 0


def test_packet_link_cannot_change_role_or_reviewer(review_store, tmp_path):
    from research_v2.review_batches import ReviewRouter
    parent = review_store.create("source", "human", "synthetic-source")
    child_store = ReviewStore(tmp_path / "new_private", review_store.research)
    child = child_store.create("semantic_A", "human", "synthetic-other")
    write_json(child_store.private / "account_links.json", [{"from_research": str(review_store.research), "from_session_id": parent["id"], "to_session_id": child["id"]}])
    router = ReviewRouter([("Previous", review_store), ("New", child_store)])
    with pytest.raises(ReviewError, match="ownership"):
        router.authenticate(review_store.assignment(parent["id"])["token"])


def test_blinded_reviewers_cannot_see_other_assignments_or_sources(review_store):
    a = review_store.create("semantic_A", "human", "synthetic-A")
    b = review_store.create("semantic_B", "human", "synthetic-B")
    principal = review_store.authenticate(review_store.assignment(a["id"])["token"])
    with pytest.raises(ReviewError):
        review_store.authorize(principal, b["id"])
    assert review_store.authorize(principal, a["id"])["id"] == a["id"]
    view = review_store.show(a["id"], "A0")
    assert set(view["row"]) == {"item_id", "original_text", "rewritten_text", *SEMANTIC_FIELDS}
    assert "context" not in view and "work" not in view
    with pytest.raises(ReviewError):
        review_store.source_bytes(a["id"], "A0")


def test_source_context_matches_exact_archived_offsets(review_store):
    session = review_store.create("source", "ai_assisted", "synthetic-ai")
    item = review_store.show(session["id"], "p0")
    assert item["context"]["selected_raw"] == item["row"]["text"]
    assert "Test preface" in item["context"]["before"]
    assert "Test afterword" in item["context"]["after"]
    data, name = review_store.source_bytes(session["id"], "p0")
    assert name == "pg1.txt" and item["row"]["text"].encode() in data


def test_same_human_cannot_fill_both_slots_or_be_unblinded(review_store):
    review_store.create("semantic_A", "human", "Synthetic-Person")
    with pytest.raises(ReviewError, match="different people"):
        review_store.create("semantic_B", "human", "synthetic-person")
    with pytest.raises(ReviewError, match="metadata"):
        review_store.create("source", "human", "synthetic-person")
    with pytest.raises(ReviewError, match="already has"):
        review_store.create("semantic_A", "human", "another-person")


def test_ai_snapshot_uses_distinct_ids_and_is_not_a_human_form(review_store):
    session = review_store.create("semantic_preflight", "ai_assisted", "synthetic-ai")
    item = review_store.show(session["id"], "next")
    assert item["id"].startswith("ai_")
    assert session["total"] == 1
    with pytest.raises(ReviewError):
        review_store.create("semantic_preflight", "human", "person")
    write_text(review_store.research / "generation/azure_replication/RUNNING.lock", "synthetic")
    with pytest.raises(ReviewError, match="No stable"):
        review_store.create("semantic_preflight", "ai_assisted", "another-ai")


def test_ai_sealing_is_immutable_and_does_not_register_human(review_store):
    session = review_store.create("source", "ai_assisted", "synthetic-ai")
    for revision, iid in enumerate(["p0", "p1"]):
        review_store.save(session["id"], iid, {"verdict": "pass", "notes": "Synthetic test, not human evidence."}, revision)
    result = review_store.seal(session["id"], 2)
    assert result["status"] == "sealed" and not result["independent_human_evidence"]
    metadata = read_json(review_store.private / "sessions" / session["id"] / "completion.json")
    assert metadata["review_origin"] == "ai_assisted" and not metadata["attested_independent_human"]
    assert not (review_store.research / "source_review/private/attestation.json").exists()
    with pytest.raises(ReviewError, match="sealed"):
        review_store.save(session["id"], "p0", {"notes": "Overwrite"}, 2)
    path = review_store.export(session["id"])
    write_text(path, "tampered sealed data")
    with pytest.raises(ReviewError, match="altered"):
        review_store.export(session["id"])


def test_source_export_matches_existing_return_validator(review_store, monkeypatch):
    from research_v2 import source_review
    session = review_store.create("source", "human", "synthetic-human")
    for revision, iid in enumerate(["p0", "p1"]):
        review_store.save(session["id"], iid, {"verdict": "needs_correction", "notes": "Synthetic boundary finding."}, revision, "browser_reviewer")
    monkeypatch.setattr(review_store, "register", lambda sid, actor: review_store.status(sid))
    review_store.seal(session["id"], 2, True, "browser_reviewer")
    monkeypatch.setattr(source_review, "OUT", review_store.research)
    meta = read_json(review_store.private / "sessions" / session["id"] / "completion.json")
    rows = source_review.check_return(review_store.export(session["id"]),
                                     read_json(review_store.research / "source_review/issued_manifest.json"),
                                     "synthetic-human", meta["completed_utc"], True)
    assert len(rows) == 2 and rows[0]["verdict"] == "needs_correction"


def test_semantic_csv_round_trips_through_existing_importer(review_store, monkeypatch):
    from research_v2 import annotations
    session = review_store.create("semantic_A", "human", "synthetic-human-A")
    for revision, iid in enumerate(["A0", "A1"]):
        review_store.save(session["id"], iid, semantic_answers(), revision, "browser_reviewer")
    monkeypatch.setattr(review_store, "register", lambda sid, actor: review_store.status(sid))
    review_store.seal(session["id"], 2, True, "browser_reviewer")
    monkeypatch.setattr(annotations, "OUT", review_store.research)
    monkeypatch.setattr(annotations, "FOLDER", review_store.research / "annotations")
    path = review_store.export(session["id"])
    meta = read_json(path.parent / "completion.json")
    annotations.ingest("A", path, "synthetic-human-A", meta["completed_utc"], True)
    registry = read_json(review_store.research / "annotations/reviewer_registry.json")
    assert registry["A"]["source_sha256"] == file_hash(path)
    assert read_csv(path)[0]["notes"] == semantic_answers()["notes"]


def test_issued_snapshot_tampering_blocks_saves(review_store):
    session = review_store.create("source", "ai_assisted", "synthetic-ai")
    write_text(review_store.private / "sessions" / session["id"] / "packet.json", "{}")
    with pytest.raises(ReviewError, match="altered"):
        review_store.save(session["id"], "p0", {"notes": "x"}, 0)


def test_all_required_rating_rules_match_canonical_checker():
    from research_v2.annotations import check_ratings
    row = {"item_id": "synthetic", **semantic_answers()}
    assert not row_errors("semantic_A", row) and not check_ratings([row])
    row["notes"] = ""
    assert row_errors("semantic_A", row) and check_ratings([row])


@pytest.fixture
def http_server(review_store):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(review_store))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def request(server, path, token="", body=None, extra=None):
    con = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
    headers = {"Authorization": "Bearer " + token}
    if body is not None:
        headers["Content-Type"] = "application/json"
    headers.update(extra or {})
    con.request("GET" if body is None else "POST", path, body=None if body is None else json.dumps(body), headers=headers)
    response = con.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    con.close()
    return result


def test_http_auth_origin_rebinding_and_static_assets(review_store, http_server):
    assert request(http_server, "/api/status")[0] == 401
    admin = review_store.credentials["admin"]
    assert request(http_server, "/api/status", admin)[0] == 200
    assert request(http_server, "/api/status", admin, extra={"Origin": "https://untrusted.example"})[0] == 403
    assert request(http_server, "/api/status", admin, extra={"Host": "untrusted.example"})[0] == 403
    status, headers, data = request(http_server, "/")
    assert status == 200 and b"Research Review Desk" in data
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["Cache-Control"] == "no-store"
    assert admin.encode() not in data
    assert request(http_server, "/../../revision/review_app/private/access.json", admin)[0] == 404
    assert request(http_server, "/app.js")[0] == 200
    assert request(http_server, "/style.css")[0] == 200


def test_http_save_download_conflict_and_agent_separation(review_store, http_server):
    agent = review_store.credentials["agent"]
    assert request(http_server, "/api/sessions", agent, {"kind": "source", "mode": "human", "reviewer_id": "fake"})[0] == 403
    status, _, data = request(http_server, "/api/sessions", agent, {"kind": "source", "reviewer_id": "synthetic-ai"})
    sid = json.loads(data)["id"]
    assert status == 201
    body = {"revision": 0, "values": {"verdict": "needs_correction", "notes": "Synthetic HTTP test."}}
    assert request(http_server, f"/api/sessions/{sid}/items/p0", agent, body)[0] == 200
    assert request(http_server, f"/api/sessions/{sid}/items/p0", agent, body)[0] == 409
    status, headers, data = request(http_server, f"/api/sessions/{sid}/download", agent)
    assert status == 200 and "attachment" in headers["Content-Disposition"]
    rows = [json.loads(line) for line in data.splitlines()]
    assert rows[0]["notes"] == "Synthetic HTTP test." and rows[1]["notes"] == ""
    human = review_store.create("semantic_A", "human", "synthetic-person")
    assert request(http_server, f"/api/sessions/{human['id']}/items/A0", agent)[0] == 403
    assert human["id"].encode() not in request(http_server, "/api/status", agent)[2]


def test_portal_lists_only_reviewer_workspaces_without_changing_provenance(review_store, http_server):
    reviewer = review_store.create("source", "human", "synthetic-reviewer")
    preflight = review_store.create("semantic_preflight", "ai_assisted", "synthetic-preflight")
    original_assignment = review_store.assignment(reviewer["id"])
    admin, agent = review_store.credentials["admin"], review_store.credentials["agent"]
    status, _, data = request(http_server, "/api/portal/status", admin)
    result = json.loads(data)
    assert status == 200
    assert set(result["availability"]) == {"source", "semantic_A", "semantic_B"}
    assert [s["id"] for s in result["sessions"]] == [reviewer["id"]]
    assert request(http_server, "/api/portal/status")[0] == 401
    assert request(http_server, "/api/portal/status", agent)[0] == 404
    assert request(http_server, "/api/portal/status", original_assignment["token"])[0] == 404
    assert review_store.assignment(reviewer["id"]) == original_assignment
    assert review_store.status(preflight["id"])["mode"] == "ai_assisted"
    assert preflight["id"].encode() in request(http_server, "/api/status", agent)[2]
    status, headers, _ = request(http_server, f"/api/sessions/{reviewer['id']}/download", original_assignment["token"])
    assert status == 200 and 'review_source_draft.jsonl' in headers["Content-Disposition"]
    assert review_store.status(reviewer["id"])["complete"] == 0


def test_reserved_human_accounts_have_no_packet_responses_or_attestation(review_store):
    manifest_path = review_store.research / "annotations/issued_manifest.json"
    manifest = read_json(manifest_path)
    manifest_path.unlink()  # Synthetic fixture only: simulate unissued semantic forms.
    a = review_store.create("semantic_A", "human", "synthetic-A")
    b = review_store.create("semantic_B", "human", "synthetic-B")
    assert a["status"] == b["status"] == "awaiting_packet"
    assert a["total"] == a["saved"] == a["complete"] == 0
    assert a["latest_export"] is None and not a["independent_human_evidence"]
    sid = a["id"]
    directory = review_store.private / "sessions" / sid
    assert not (directory / "packet.json").exists()
    assert not (directory / "completion.json").exists()
    assert not (directory / "current.draft.csv").exists()
    with pytest.raises(ReviewError):
        review_store.show(sid, "next")
    with pytest.raises(ReviewError):
        review_store.save(sid, "A0", semantic_answers(), 0, "browser_reviewer")
    with pytest.raises(ReviewError):
        review_store.check(sid)
    with pytest.raises(ReviewError):
        review_store.export(sid)
    with pytest.raises(ReviewError):
        review_store.seal(sid, 0, True, "browser_reviewer")
    with pytest.raises(ReviewError, match="not been issued"):
        review_store.activate(sid)
    with pytest.raises(ReviewError, match="already has"):
        review_store.create("semantic_A", "human", "different-person")
    reopened = ReviewStore(review_store.private, review_store.research)
    assert reopened.status(sid)["status"] == "awaiting_packet"
    token = reopened.assignment(sid)["token"]
    assert reopened.authenticate(token) == {"role": "reviewer", "session_id": sid}
    write_json(manifest_path, manifest)
    before = (directory / "assignment.json").read_bytes()
    active = reopened.activate(sid)
    assert active["status"] == "draft" and active["total"] == 2
    assert active["saved"] == active["complete"] == 0 and not active["independent_human_evidence"]
    assert reopened.assignment(sid)["token"] == token
    assert (directory / "assignment.json").read_bytes() == before
    assert read_json(directory / "activation.json")["packet_sha256"] == file_hash(directory / "packet.json")
    assert read_csv(reopened.export(sid))[0]["item_id"] == "A0"
    with pytest.raises(ReviewError, match="Only an account awaiting"):
        reopened.activate(sid)


def test_reservations_preserve_blinding_and_reject_tampered_activation(review_store):
    manifest_path = review_store.research / "annotations/issued_manifest.json"
    manifest = read_json(manifest_path)
    manifest_path.unlink()
    a = review_store.create("semantic_A", "human", "Synthetic-Person")
    with pytest.raises(ReviewError, match="different people"):
        review_store.create("semantic_B", "human", "synthetic-person")
    with pytest.raises(ReviewError, match="metadata"):
        review_store.create("source", "human", "synthetic-person")
    with pytest.raises(ReviewError, match="not been issued"):
        review_store.create("semantic_A", "ai_assisted", "synthetic-ai")
    write_json(manifest_path, manifest)
    lock = review_store.research / "generation/azure_replication/RUNNING.lock"
    write_text(lock, "Synthetic active generation marker")
    with pytest.raises(ReviewError, match="active generation"):
        review_store.activate(a["id"])
    lock.unlink()
    write_text(review_store.research / "annotations/forms/reviewer_A.csv", "Synthetic corruption")
    with pytest.raises(ReviewError, match="hash changed"):
        review_store.activate(a["id"])
    assert review_store.status(a["id"])["status"] == "awaiting_packet"
    assert not (review_store.private / "sessions" / a["id"] / "packet.json").exists()


def test_access_cards_are_private_scoped_and_idempotent(review_store):
    a = review_store.create("semantic_A", "human", "synthetic-A")
    b = review_store.create("semantic_B", "human", "synthetic-B")
    path = review_store.export_access_card(a["id"])
    raw = path.read_text(encoding="utf-8")
    assert path.is_relative_to(review_store.private)
    assert review_store.assignment(a["id"])["token"] in raw
    assert review_store.assignment(b["id"])["token"] not in raw
    assert review_store.credentials["admin"] not in raw
    assert review_store.credentials["agent"] not in raw
    assert review_store.export_access_card(a["id"]) == path
    assert review_store.status(a["id"])["revision"] == 0


def test_reserved_http_login_activation_and_access_cards_are_role_scoped(review_store, http_server):
    manifest_path = review_store.research / "annotations/issued_manifest.json"
    manifest = read_json(manifest_path)
    manifest_path.unlink()
    admin, agent = review_store.credentials["admin"], review_store.credentials["agent"]
    status, _, data = request(http_server, "/api/sessions", admin,
                              {"kind": "semantic_A", "mode": "human", "reviewer_id": "synthetic-A"})
    assert status == 201
    sid = json.loads(data)["id"]
    token = review_store.assignment(sid)["token"]
    assert request(http_server, "/api/me", token)[0] == 200
    status, _, data = request(http_server, f"/api/sessions/{sid}", token)
    assert status == 200 and json.loads(data)["status"] == "awaiting_packet"
    assert request(http_server, f"/api/sessions/{sid}/download", token)[0] == 409
    assert request(http_server, f"/api/sessions/{sid}/activate", admin, {})[0] == 409
    assert request(http_server, f"/api/sessions/{sid}/activate", agent, {})[0] == 403
    assert request(http_server, f"/api/sessions/{sid}/activate", token, {})[0] == 404
    assert request(http_server, f"/api/sessions/{sid}/access-card", token, {})[0] == 404
    assert request(http_server, f"/api/sessions/{sid}/access-card", agent, {})[0] == 403
    status, _, data = request(http_server, f"/api/sessions/{sid}/access-card", admin, {})
    assert status == 200 and token.encode() not in data
    assert "private_access_file" in json.loads(data)
    write_json(manifest_path, manifest)
    assert request(http_server, f"/api/sessions/{sid}/activate", admin, {})[0] == 200
    assert request(http_server, f"/api/sessions/{sid}/items/next", token)[0] == 200
