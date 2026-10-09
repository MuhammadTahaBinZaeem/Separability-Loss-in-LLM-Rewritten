"""Local-only review desk, canonical draft exports, and an explicitly AI-assisted CLI."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import secrets
import sqlite3
import threading
import webbrowser
from datetime import datetime, timezone
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PureWindowsPath
from urllib.parse import urlsplit

from .io import OUT, ROOT, digest_text, file_hash, read_csv, read_json, read_jsonl

PRIVATE = OUT / "review_app/private"
STATIC = ROOT / "review_app"
SEMANTIC_FIELDS = ["added_facts", "omitted_facts", "order_changed", "relationships_changed",
                   "tone_drift", "meaning_preservation", "usable", "notes"]
RATINGS = {"added_facts": ["0", "1"], "omitted_facts": ["0", "1"],
           "order_changed": ["0", "1"], "relationships_changed": ["0", "1"],
           "tone_drift": ["0", "1", "2"], "meaning_preservation": ["1", "2", "3", "4", "5"],
           "usable": ["yes", "no"]}
KINDS = ("source", "semantic_A", "semantic_B", "semantic_preflight")
MODES = ("human", "ai_assisted")


def now():
    return datetime.now(timezone.utc).isoformat()


def immutable(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


class ReviewError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def editable(kind):
    return ["verdict", "notes"] if kind == "source" else SEMANTIC_FIELDS


def item_id(row):
    return row.get("item_id", row.get("passage_id"))


def row_errors(kind, values):
    if kind == "source":
        errors = []
        if values.get("verdict") not in {"pass", "needs_correction"}:
            errors.append("Choose a source verdict.")
        if not values.get("notes", "").strip():
            errors.append("Explain what you checked in a source-review note.")
        return errors
    errors = [f"Complete {field.replace('_', ' ')}." for field, choices in RATINGS.items()
              if values.get(field) not in choices]
    note_needed = (any(values.get(f) == "1" for f in ("added_facts", "omitted_facts", "order_changed", "relationships_changed"))
                   or values.get("meaning_preservation") in {"1", "2", "3"} or values.get("usable") == "no")
    if note_needed and not values.get("notes", "").strip():
        errors.append("Identify the affected fact, event, speaker or relationship in Notes.")
    return errors


def encode_return(kind, rows):
    if kind == "source":
        return ("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)).encode("utf-8")
    stream = io.StringIO(newline="")
    fields = ["item_id", "original_text", "rewritten_text", *SEMANTIC_FIELDS]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


class ReviewStore:
    def __init__(self, private=PRIVATE, research=OUT, source_archive=None, registrar=None):
        self.private, self.research = Path(private).resolve(), Path(research).resolve()
        self.source_archive = Path(source_archive or research).resolve()
        self.registrar = registrar
        self.private.mkdir(parents=True, exist_ok=True)
        self.db = self.private / "reviews.sqlite3"
        self.mutex = threading.RLock()
        self.credentials_path = self.private / "access.json"
        if not self.credentials_path.exists():
            try:
                immutable(self.credentials_path, json_bytes({"admin": secrets.token_urlsafe(32), "agent": secrets.token_urlsafe(32)}))
            except FileExistsError:
                pass
        self.credentials = read_json(self.credentials_path)
        with self.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS assignments (
                  id TEXT PRIMARY KEY, kind TEXT NOT NULL, mode TEXT NOT NULL, reviewer_id TEXT NOT NULL,
                  token TEXT UNIQUE NOT NULL, created_utc TEXT NOT NULL, packet_sha TEXT NOT NULL,
                  revision INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'draft',
                  latest_export TEXT NOT NULL, final_file TEXT, completed_utc TEXT,
                  registration_error TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS responses (
                  session_id TEXT NOT NULL, item_id TEXT NOT NULL, values_json TEXT NOT NULL,
                  updated_utc TEXT NOT NULL, PRIMARY KEY (session_id,item_id),
                  FOREIGN KEY(session_id) REFERENCES assignments(id));
                CREATE TABLE IF NOT EXISTS events (
                  id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, created_utc TEXT NOT NULL,
                  action TEXT NOT NULL, actor TEXT NOT NULL, revision INTEGER NOT NULL,
                  payload_sha TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.db, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            with con:
                yield con
        finally:
            con.close()

    def assignment(self, sid, con=None):
        if con is None:
            with self.connect() as connection:
                return self.assignment(sid, connection)
        row = con.execute("SELECT * FROM assignments WHERE id=?", (sid,)).fetchone()
        if row is None:
            raise ReviewError("Assignment not found.", 404)
        return dict(row)

    def recorded_path(self, value):
        """Resolve explicitly registered former locations without rewriting records."""
        path = Path(value)
        aliases = self.private / "path_relocations.json"
        if not aliases.exists():
            return path
        for previous in read_json(aliases)["previous_research_roots"]:
            path_type = PureWindowsPath if PureWindowsPath(previous).drive else Path
            root, stored = path_type(previous), path_type(value)
            if not root.is_absolute() or ".." in root.parts:
                raise ReviewError("Invalid previous review workspace location.", 409)
            try:
                relative = stored.relative_to(root)
            except ValueError:
                continue
            if ".." in relative.parts:
                raise ReviewError("Recorded review path escapes its workspace.", 409)
            resolved = self.research.joinpath(*relative.parts)
            if not resolved.resolve().is_relative_to(self.research):
                raise ReviewError("Recorded review path escapes its workspace.", 409)
            return resolved
        return path

    def authenticate(self, token):
        if not token:
            raise ReviewError("Open your private assignment link or enter an access token.", 401)
        for role, value in self.credentials.items():
            if secrets.compare_digest(token, value):
                return {"role": role}
        with self.connect() as con:
            row = con.execute("SELECT id FROM assignments WHERE token=?", (token,)).fetchone()
        if row:
            return {"role": "reviewer", "session_id": row["id"]}
        raise ReviewError("This access token is not valid.", 401)

    def authorize(self, principal, sid, write=False):
        session = self.assignment(sid)
        if principal.get("role") == "reviewer" and principal.get("session_id") == sid:
            return session
        if principal.get("role") in {"agent", "admin"} and session["mode"] == "ai_assisted":
            return session
        raise ReviewError("Use this assignment's private reviewer link to access its responses.", 403)

    def availability(self):
        result = {"source": {"available": False}, "semantic_A": {"available": False},
                  "semantic_B": {"available": False}, "semantic_preflight": {"available": False}}
        source = self.research / "source_review/blank_review.jsonl"
        if source.exists():
            result["source"] = {"available": True, "items": len(read_jsonl(source))}
        manifest_path = self.research / "annotations/issued_manifest.json"
        if manifest_path.exists():
            manifest = read_json(manifest_path)
            for a in ("A", "B"):
                path = self.research / f"annotations/forms/reviewer_{a}.csv"
                result[f"semantic_{a}"] = {"available": path.exists() and file_hash(path) == manifest["forms_sha256"][a],
                                           "items": manifest["items_per_reviewer"]}
        else:
            for a in ("A", "B"):
                result[f"semantic_{a}"]["reason"] = "Review forms will be available once preparation of the fixed sample is complete."
        for path in (self.research / "generation").glob("*/rewrites.csv"):
            if path.parent.name in {"azure_replication", "gem31lite"} and not (path.parent / "RUNNING.lock").exists():
                result["semantic_preflight"]["available"] = True
        result["semantic_preflight"]["reason"] = "AI-only snapshot of available technically valid rewrites; never a human audit."
        return result

    def load_new_packet(self, kind, mode):
        if kind == "source":
            path = self.research / "source_review/blank_review.jsonl"
            manifest = read_json(self.research / "source_review/issued_manifest.json")
            if file_hash(path) != manifest["blank_sha256"]:
                raise ReviewError("Issued source packet hash changed; investigate before reviewing.", 409)
            rows = read_jsonl(path)
            provenance = {"blank_sha256": manifest["blank_sha256"], "issued_utc": manifest["issued_utc"]}
        elif kind in {"semantic_A", "semantic_B"}:
            a = kind[-1]
            path = self.research / f"annotations/forms/reviewer_{a}.csv"
            manifest_path = self.research / "annotations/issued_manifest.json"
            if not manifest_path.exists():
                raise ReviewError("Semantic review packets have not been issued yet.", 409)
            manifest = read_json(manifest_path)
            if file_hash(path) != manifest["forms_sha256"][a]:
                raise ReviewError("Issued semantic form hash changed.", 409)
            fields = ["item_id", "original_text", "rewritten_text", *SEMANTIC_FIELDS]
            rows = [{k: r[k] for k in fields} for r in read_csv(path)]
            provenance = {"form_sha256": file_hash(path), "issued_utc": manifest["issued_utc"]}
        elif kind == "semantic_preflight" and mode == "ai_assisted":
            originals = {r["passage_id"]: r for r in read_csv(self.research / "corpus/originals.csv")}
            rows, provenance = [], {"snapshot_utc": now(), "generation_sha256": {},
                                    "originals_sha256": file_hash(self.research / "corpus/originals.csv")}
            for model in ("azure_replication", "gem31lite"):
                folder = self.research / f"generation/{model}"
                path = folder / "rewrites.csv"
                if not path.exists() or (folder / "RUNNING.lock").exists():
                    continue
                provenance["generation_sha256"][model] = file_hash(path)
                for row in read_csv(path):
                    if row["qc_status"] not in {"pass", "warning"}:
                        continue
                    original = originals[row["passage_id"]]
                    if (digest_text(original["text"]) != original["text_sha256"] or row["source_sha256"] != original["text_sha256"]
                        or digest_text(row["rewritten_text"]) != row["rewrite_sha256"]):
                        raise ReviewError("AI snapshot text hashes do not match stored provenance.", 409)
                    rows.append({"item_id": "ai_" + digest_text(model + ":" + row["request_id"])[:20],
                                 "original_text": original["text"], "rewritten_text": row["rewritten_text"],
                                 **{f: "" for f in SEMANTIC_FIELDS}})
            if not rows:
                raise ReviewError("No stable parsed rewrites are available for an AI snapshot.", 409)
        else:
            raise ReviewError("Unknown packet, or an AI-only packet was requested as human evidence.")
        if len({item_id(r) for r in rows}) != len(rows) or not rows:
            raise ReviewError("Packet is empty or has duplicate item IDs.", 409)
        return {"kind": kind, "rows": rows, "provenance": provenance}

    def create(self, kind, mode, reviewer_id):
        reviewer_id = str(reviewer_id).strip()
        if kind not in KINDS or mode not in MODES or not reviewer_id or len(reviewer_id) > 120:
            raise ReviewError("Choose a packet, review origin and a pseudonymous reviewer ID (1–120 characters).")
        if kind == "semantic_preflight" and mode != "ai_assisted":
            raise ReviewError("Preflight snapshots are AI-assisted only.")
        waiting = (mode == "human" and kind in {"semantic_A", "semantic_B"}
                   and not (self.research / "annotations/issued_manifest.json").exists())
        packet = None if waiting else self.load_new_packet(kind, mode)
        with self.mutex, self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            existing = [dict(r) for r in con.execute("SELECT * FROM assignments WHERE mode='human'")]
            if mode == "human":
                registry_path = self.research / "annotations/reviewer_registry.json"
                registry = read_json(registry_path) if registry_path.exists() else {}
                external = [{"kind": f"semantic_{a}", "reviewer_id": r["reviewer_id"]} for a, r in registry.items()]
                source_attestation = self.research / "source_review/private/attestation.json"
                if source_attestation.exists():
                    external.append({"kind": "source", "reviewer_id": read_json(source_attestation)["reviewer_id"]})
                existing.extend(external)
                if any(r["kind"] == kind for r in existing):
                    raise ReviewError("This reviewer slot already has an assignment. Reopen it; do not create a second return.", 409)
                same_person = [r for r in existing if r["reviewer_id"].casefold() == reviewer_id.casefold()]
                if kind in {"semantic_A", "semantic_B"} and any(r["kind"] in {"semantic_A", "semantic_B"} for r in same_person):
                    raise ReviewError("A and B must be two different people.", 409)
                if same_person:
                    if set(registry) != {"A", "B"} or kind != "source":
                        raise ReviewError("Do not expose source metadata to a semantic reviewer before both blinded reviews are sealed. Assign another source reviewer.", 409)
            sid, token = secrets.token_hex(8), secrets.token_urlsafe(32)
            directory = self.private / "sessions" / sid
            raw = json_bytes(packet) if packet else b""
            packet_sha = hashlib.sha256(raw).hexdigest() if packet else ""
            extension = "jsonl" if kind == "source" else "csv"
            export = str(directory / f"current.draft.{extension}") if packet else ""
            if packet:
                immutable(directory / "packet.json", raw)
                immutable(Path(export), encode_return(kind, packet["rows"]))
            immutable(directory / "assignment.json", json_bytes({"id": sid, "kind": kind, "mode": mode,
                       "reviewer_id": reviewer_id, "created_utc": now(), "packet_sha256": packet_sha,
                       "initial_status": "awaiting_packet" if waiting else "draft",
                       "note": "Human is an assignment type, not proof that a human has completed any review."}))
            con.execute("INSERT INTO assignments(id,kind,mode,reviewer_id,token,created_utc,packet_sha,latest_export,status) VALUES(?,?,?,?,?,?,?,?,?)",
                        (sid, kind, mode, reviewer_id, token, now(), packet_sha, export, "awaiting_packet" if waiting else "draft"))
            con.execute("INSERT INTO events(session_id,created_utc,action,actor,revision,payload_sha) VALUES(?,?,?,?,?,?)",
                        (sid, now(), "create", "administrator" if mode == "human" else "ai_assisted", 0, hashlib.sha256(raw).hexdigest()))
        return self.status(sid)

    def activate(self, sid):
        """Administrator attaches an actually issued packet to a reserved account."""
        with self.mutex, self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            session = self.assignment(sid, con)
            if session["status"] != "awaiting_packet":
                raise ReviewError("Only an account awaiting its packet can be activated.", 409)
            if list((self.research / "generation").glob("*/RUNNING.lock")):
                raise ReviewError("Wait for active generation to stop before activating review packets.", 409)
            registry_path = self.research / "annotations/reviewer_registry.json"
            registry = read_json(registry_path) if registry_path.exists() else {}
            if session["kind"][-1] in registry:
                raise ReviewError("This reviewer slot already has a registered return. Investigate before assigning more work.", 409)
            if any(r["reviewer_id"].casefold() == session["reviewer_id"].casefold() for r in registry.values()):
                raise ReviewError("A and B must be two different people.", 409)
            source_attestation = self.research / "source_review/private/attestation.json"
            if source_attestation.exists() and read_json(source_attestation)["reviewer_id"].casefold() == session["reviewer_id"].casefold():
                raise ReviewError("Do not expose source metadata to a blinded semantic reviewer.", 409)
            packet = self.load_new_packet(session["kind"], session["mode"])
            raw = json_bytes(packet)
            packet_sha = hashlib.sha256(raw).hexdigest()
            directory = self.private / "sessions" / sid
            export = directory / "current.draft.csv"
            immutable(directory / "packet.json", raw)
            immutable(export, encode_return(session["kind"], packet["rows"]))
            stamp = now()
            immutable(directory / "activation.json", json_bytes({"activated_utc": stamp, "packet_sha256": packet_sha,
                       "provenance": packet["provenance"], "note": "Account activation is not a completed review or human attestation."}))
            con.execute("UPDATE assignments SET packet_sha=?,latest_export=?,status='draft' WHERE id=?",
                        (packet_sha, str(export), sid))
            con.execute("INSERT INTO events(session_id,created_utc,action,actor,revision,payload_sha) VALUES(?,?,?,?,?,?)",
                        (sid, stamp, "activate", "administrator", 0, packet_sha))
        return self.status(sid)

    def export_access_card(self, sid, port=8765):
        """Local administrator delivery; never expose an administrator/other reviewer's key."""
        if type(port) is not int or not 1 <= port <= 65535:
            raise ReviewError("Invalid local port.")
        session = self.assignment(sid)
        origin_line = "" if session["mode"] == "human" else f"Origin: {session['mode']}\n"
        review_note = ("Use this login for your own independent review. Read and rate every assigned item yourself before confirming completion.\n"
                       if session["mode"] == "human" else "This account is for AI-assisted review and cannot supply independent reviewer evidence.\n")
        data = (f"PRIVATE REVIEWER ACCESS — do not publish or share with another reviewer\n\n"
                f"Reviewer pseudonym: {session['reviewer_id']}\nAssignment: {session['kind']}\n{origin_line}\n"
                f"Open this private link on the computer running the app:\nhttp://127.0.0.1:{port}/#{session['token']}\n\n"
                f"Or paste this key into the app's Private access token box:\n{session['token']}\n\n"
                f"{review_note}"
                "Semantic accounts may show Waiting for your review packet until their issued forms are attached.\n"
                "Keep this pseudonym assigned to one person. Keep the identity mapping privately; do not share another reviewer's key or answers.\n"
                "Localhost is not remotely accessible. Do not upload this file to Git or a public archive.\n").encode("utf-8")
        path = self.private / "sessions" / sid / f"private_access_{port}.txt"
        if path.exists():
            if path.read_bytes() != data:
                raise ReviewError("Existing access card differs; it has not been overwritten.", 409)
        else:
            immutable(path, data)
        return path

    def packet(self, session):
        if session["status"] == "awaiting_packet":
            raise ReviewError("Your account is ready, but the fixed semantic review packet has not been attached yet.", 409)
        path = self.private / "sessions" / session["id"] / "packet.json"
        if file_hash(path) != session["packet_sha"]:
            raise ReviewError("Assignment packet was altered. No saves or submissions are allowed.", 409)
        return read_json(path)

    def rows(self, session, con=None):
        if con is None:
            with self.connect() as connection:
                return self.rows(session, connection)
        answers = {r["item_id"]: json.loads(r["values_json"]) for r in con.execute("SELECT * FROM responses WHERE session_id=?", (session["id"],))}
        return [{**row, **answers.get(item_id(row), {})} for row in self.packet(session)["rows"]]

    def status(self, sid):
        session = self.assignment(sid)
        if session["status"] == "awaiting_packet":
            return {k: session[k] for k in ("id", "kind", "mode", "reviewer_id", "created_utc", "revision", "status", "completed_utc", "registration_error")} | {
                "total": 0, "saved": 0, "complete": 0, "flagged": 0, "items": [], "latest_export": None,
                "independent_human_evidence": False,
                "waiting_reason": "Your account is ready. The study administrator will attach your fixed, blinded review packet after generation accounting is complete. No ratings or submission are available yet."}
        rows = self.rows(session)
        with self.connect() as con:
            saved = {r[0] for r in con.execute("SELECT item_id FROM responses WHERE session_id=?", (sid,))}
        items = [{"id": item_id(r), "position": i + 1, "saved": item_id(r) in saved,
                  "complete": not row_errors(session["kind"], r),
                  "flagged": r.get("verdict") == "needs_correction" or r.get("usable") == "no"
                  or any(r.get(f) == "1" for f in ("added_facts", "omitted_facts", "order_changed", "relationships_changed"))}
                 for i, r in enumerate(rows)]
        export = self.recorded_path(session["latest_export"])
        return {k: session[k] for k in ("id", "kind", "mode", "reviewer_id", "created_utc", "revision", "status", "completed_utc", "registration_error")} | {
            "total": len(rows), "saved": len(saved), "complete": sum(r["complete"] for r in items),
            "flagged": sum(r["flagged"] for r in items), "items": items,
            "latest_export": str(export.relative_to(self.research)) if export.is_relative_to(self.research) else session["latest_export"],
            "independent_human_evidence": session["mode"] == "human" and session["status"] == "registered"}

    def sessions(self, agent_only=False):
        with self.connect() as con:
            ids = [r[0] for r in con.execute("SELECT id FROM assignments" + (" WHERE mode='ai_assisted'" if agent_only else "") + " ORDER BY created_utc DESC")]
        return [{k: v for k, v in self.status(sid).items() if k != "items"} for sid in ids]

    def show(self, sid, index_or_id):
        session = self.assignment(sid)
        rows = self.rows(session)
        if index_or_id == "next":
            row = next((r for r in rows if row_errors(session["kind"], r)), rows[0])
        else:
            row = next((r for r in rows if item_id(r) == str(index_or_id)), None)
        if row is None:
            raise ReviewError("Item not found in this assignment.", 404)
        result = {"id": item_id(row), "row": row, "editable_fields": editable(session["kind"]),
                  "errors": row_errors(session["kind"], row), "revision": session["revision"],
                  "position": next(i + 1 for i, r in enumerate(rows) if item_id(r) == item_id(row))}
        if session["kind"] == "source":
            gid = str(row["gutenberg_id"])
            if not gid.isdigit():
                raise ReviewError("Invalid source identifier.", 409)
            path = self.source_archive / f"sources/pg{gid}.txt"
            if path.exists():
                metadata = read_json(path.with_suffix(".json"))
                if file_hash(path) != metadata["raw_sha256"]:
                    raise ReviewError("Archived source hash changed.", 409)
                text = path.read_text(encoding="utf-8-sig")
                a, b = int(row["source_start_char"]), int(row["source_end_char"])
                result["context"] = {"before": text[max(0, a - 2500):a], "selected_raw": text[a:b],
                                     "after": text[b:b + 2500], "start_char": a, "end_char": b}
            registry = self.source_archive / "corpus/work_registry.csv"
            work = next((r for r in read_csv(registry) if r["author_id"] == row["author_id"] and r["work_id"] == row["work_id"]), None) if registry.exists() else None
            result["work"] = work
        return result

    def source_bytes(self, sid, iid):
        session = self.assignment(sid)
        if session["kind"] != "source":
            raise ReviewError("Source metadata is not available to blinded semantic reviewers.", 403)
        row = next((r for r in self.packet(session)["rows"] if item_id(r) == iid), None)
        if row is None or not str(row["gutenberg_id"]).isdigit():
            raise ReviewError("Source item not found.", 404)
        path = self.source_archive / f"sources/pg{row['gutenberg_id']}.txt"
        if file_hash(path) != read_json(path.with_suffix(".json"))["raw_sha256"]:
            raise ReviewError("Archived source hash changed.", 409)
        return path.read_bytes(), path.name

    def export(self, sid):
        """SQLite + immutable answer events are authoritative; refresh a canonical draft."""
        with self.mutex, self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            session = self.assignment(sid, con)
            if session["status"] == "awaiting_packet":
                raise ReviewError("There is no review packet or return to download yet.", 409)
            path = self.recorded_path(session["latest_export"])
            if not path.resolve().is_relative_to(self.private):
                raise ReviewError("Export path is outside private review storage.", 409)
            if session["status"] != "draft":
                if file_hash(path) != read_json(path.parent / "completion.json")["return_sha256"]:
                    raise ReviewError("Sealed original return was altered.", 409)
            else:
                data = encode_return(session["kind"], self.rows(session, con))
                staged = path.with_name(f"export-{secrets.token_hex(8)}.tmp")
                immutable(staged, data)
                os.replace(staged, path)  # Replaces only the app-owned derived draft, never a sealed return.
            return path

    def save(self, sid, iid, values, expected_revision, actor="agent_cli"):
        if not isinstance(values, dict):
            raise ReviewError("Values must be a JSON object.")
        with self.mutex, self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            session = self.assignment(sid, con)
            if actor in {"agent_cli", "agent_api"} and session["mode"] != "ai_assisted":
                raise ReviewError("Agent saves are allowed only in explicitly AI-assisted assignments.", 403)
            if session["status"] != "draft":
                raise ReviewError("This return is sealed. Its original ratings cannot be overwritten.", 409)
            if type(expected_revision) is not int or expected_revision != session["revision"]:
                raise ReviewError("A newer save exists. Reload this item before saving; no answers were overwritten.", 409)
            if set(values) - set(editable(session["kind"])):
                raise ReviewError("Only rating fields and notes may change; source text and identifiers are read-only.")
            for key, value in values.items():
                if not isinstance(value, str) or len(value) > 20000:
                    raise ReviewError("Rating values must be strings; notes are limited to 20,000 characters.")
                choices = ["pass", "needs_correction"] if key == "verdict" else RATINGS.get(key)
                if choices and value not in ["", *choices]:
                    raise ReviewError(f"Invalid value for {key}.")
            rows = self.rows(session, con)
            row = next((r for r in rows if item_id(r) == iid), None)
            if row is None:
                raise ReviewError("Item not found in this assignment.", 404)
            row.update(values)
            answer = {f: row.get(f, "") for f in editable(session["kind"])}
            revision = session["revision"] + 1
            timestamp = now()
            con.execute("INSERT INTO responses VALUES(?,?,?,?) ON CONFLICT(session_id,item_id) DO UPDATE SET values_json=excluded.values_json,updated_utc=excluded.updated_utc",
                        (sid, iid, json.dumps(answer, ensure_ascii=False), timestamp))
            directory = self.private / "sessions" / sid
            extension = "jsonl" if session["kind"] == "source" else "csv"
            export = directory / f"current.draft.{extension}"
            immutable(directory / f"revision_{revision:06d}.answers.json", json_bytes({"item_id": iid, "values": answer,
                      "revision": revision, "saved_utc": timestamp, "actor": actor, "mode": session["mode"]}))
            con.execute("UPDATE assignments SET revision=?,latest_export=? WHERE id=?", (revision, str(export), sid))
            con.execute("INSERT INTO events(session_id,created_utc,action,actor,revision,payload_sha) VALUES(?,?,?,?,?,?)",
                        (sid, timestamp, "save:" + iid, actor, revision, digest_text(json.dumps(answer, sort_keys=True))))
        export = self.export(sid)
        return {"saved": True, "revision": revision, "errors": row_errors(session["kind"], row),
                "export_file": str(export), "export_sha256": file_hash(export), "review_origin": session["mode"]}

    def check(self, sid):
        session = self.assignment(sid)
        errors = [{"item_id": item_id(r), "errors": row_errors(session["kind"], r)} for r in self.rows(session)]
        errors = [r for r in errors if r["errors"]]
        return {"valid": not errors, "incomplete_items": len(errors), "errors": errors,
                "mode": session["mode"], "can_register_as_human": session["mode"] == "human" and not errors}

    def seal(self, sid, expected_revision, attest_human=False, actor="agent_cli"):
        with self.mutex, self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            session = self.assignment(sid, con)
            if session["status"] != "draft":
                raise ReviewError("This return is already sealed. Use Register again if registration needs retrying.", 409)
            if type(expected_revision) is not int or expected_revision != session["revision"]:
                raise ReviewError("A newer save exists; reload before sealing.", 409)
            if session["mode"] == "human" and (actor != "browser_reviewer" or attest_human is not True):
                raise ReviewError("The assigned reviewer must personally confirm completion in their workspace.", 403)
            if session["mode"] == "ai_assisted" and attest_human:
                raise ReviewError("AI-assisted work cannot be attested as independent human evidence.", 403)
            rows = self.rows(session, con)
            if any(row_errors(session["kind"], r) for r in rows):
                raise ReviewError("Complete every required rating and note before finishing.", 409)
            stamp = now()
            directory = self.private / "sessions" / sid
            extension = "jsonl" if session["kind"] == "source" else "csv"
            path = directory / f"{session['mode']}_completed.{extension}"
            immutable(path, encode_return(session["kind"], rows))
            metadata = {"review_origin": session["mode"], "reviewer_id": session["reviewer_id"],
                        "kind": session["kind"], "completed_utc": stamp, "return_sha256": file_hash(path),
                        "packet_sha256": session["packet_sha"], "attested_independent_human": bool(attest_human),
                        "actor": actor, "items": len(rows), "identity_is_attested_not_cryptographically_proven": True}
            immutable(directory / "completion.json", json_bytes(metadata))
            con.execute("UPDATE assignments SET status='sealed',final_file=?,latest_export=?,completed_utc=? WHERE id=?", (str(path), str(path), stamp, sid))
            con.execute("INSERT INTO events(session_id,created_utc,action,actor,revision,payload_sha) VALUES(?,?,?,?,?,?)",
                        (sid, stamp, "seal", actor, session["revision"], file_hash(path)))
        if session["mode"] == "human":
            return self.register(sid, actor)
        return self.status(sid)

    def register(self, sid, actor):
        session = self.assignment(sid)
        if actor != "browser_reviewer" or session["mode"] != "human" or session["status"] not in {"sealed", "registered"}:
            raise ReviewError("Only the assigned reviewer's sealed return can be registered.", 403)
        metadata = read_json(self.private / "sessions" / sid / "completion.json")
        path = self.recorded_path(session["final_file"])
        if not path.resolve().is_relative_to(self.private):
            raise ReviewError("Return path is outside private review storage.", 409)
        if metadata.get("attested_independent_human") is not True or metadata["return_sha256"] != file_hash(path):
            raise ReviewError("Sealed return or completion confirmation changed.", 409)
        if self.registrar is not None:
            try:
                result = self.registrar(session, path, metadata)
            except ValueError as exc:
                with self.connect() as con:
                    con.execute("UPDATE assignments SET registration_error=? WHERE id=?", (str(exc), sid))
                raise ReviewError("Your sealed return is preserved; registration needs attention: " + str(exc), 409) from None
            with self.connect() as con:
                con.execute("UPDATE assignments SET status='registered',registration_error='' WHERE id=?", (sid,))
            return {**self.status(sid), "study_validation": result}
        if self.research != OUT.resolve():
            raise ReviewError("Registration is supported only against this repository's canonical study.", 409)
        try:
            if session["kind"] == "source":
                from . import source_review
                registered = self.research / "source_review/private/attestation.json"
                if registered.exists():
                    record = read_json(registered)
                    if record["return_sha256"] != file_hash(path) or record["reviewer_id"] != session["reviewer_id"]:
                        raise ReviewError("Another source review is already registered; preserve it and investigate.", 409)
                    result = source_review.validate()
                else:
                    result = source_review.ingest(path, session["reviewer_id"], session["completed_utc"], True)
            elif session["kind"] in {"semantic_A", "semantic_B"}:
                from . import annotations
                annotations.ingest(session["kind"][-1], path, session["reviewer_id"], session["completed_utc"], True)
                result = annotations.validate()
            else:
                raise ReviewError("This packet is not eligible for reviewer registration.", 403)
        except ValueError as exc:
            with self.connect() as con:
                con.execute("UPDATE assignments SET registration_error=? WHERE id=?", (str(exc), sid))
            raise ReviewError("Your return was saved and sealed, but registration needs attention: " + str(exc), 409) from None
        with self.connect() as con:
            con.execute("UPDATE assignments SET status='registered',registration_error='' WHERE id=?", (sid,))
        return {**self.status(sid), "study_validation": result}

    def independence_status(self):
        registry_path = self.research / "annotations/reviewer_registry.json"
        if not registry_path.exists() or set(read_json(registry_path)) != {"A", "B"}:
            return {"available": False, "reason": "This check is relevant only after both reviewer returns are registered."}
        validation_path = self.research / "annotations/validation.json"
        state = read_json(validation_path) if validation_path.exists() else {}
        return {"available": bool(state.get("identical_choices_provenance_check_required")),
                "satisfied": state.get("provenance_check_satisfied", False), "registry_sha256": file_hash(registry_path),
                "reason": "Identical ratings are not proof of misconduct. A separate person must check genuine independence."}

    def independence_submit(self, values):
        status = self.independence_status()
        if not status["available"] or values.get("registry_sha256") != status["registry_sha256"]:
            raise ReviewError("No current identical-rating provenance check is available.", 409)
        if values.get("checked_by_human") is not True or any(not isinstance(values.get(k), str) or not values[k].strip()
                or len(values[k]) > 20000 for k in ("checker_id", "method", "notes")):
            raise ReviewError("The checker must supply their identity, method, notes and personal confirmation.")
        registry = read_json(self.research / "annotations/reviewer_registry.json")
        if values["checker_id"].strip().casefold() in {r["reviewer_id"].strip().casefold() for r in registry.values()}:
            raise ReviewError("Assign a separate checker for this step.")
        record = {k: values[k] for k in ("checker_id", "method", "notes", "registry_sha256")}
        record.update(checked_by_human=True, checked_utc=now(), outcome="independence_confirmed")
        path = self.research / "annotations/independence_check.json"
        try:
            immutable(path, json_bytes(record))
        except FileExistsError:
            raise ReviewError("A provenance record already exists. Do not overwrite original evidence.", 409) from None
        if self.research == OUT.resolve():
            from .annotations import validate
            return validate()
        return {"saved": True}


def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        server_version = "LocalReviewDesk/1.0"

        def log_message(self, *_):
            pass  # No access tokens, ratings or notes in HTTP logs.

        def send(self, status, data, mime="application/json; charset=utf-8", download=None):
            if not isinstance(data, bytes):
                data = json_bytes(data)
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if download:
                self.send_header("Content-Disposition", f'attachment; filename="{download}"')
            self.end_headers()
            self.wfile.write(data)

        def guarded(self):
            port = self.server.server_address[1]
            valid_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            if self.headers.get("Host") not in valid_hosts:
                raise ReviewError("Unrecognized host. Use the loopback address printed at startup.", 403)
            origin = self.headers.get("Origin")
            if origin and origin not in {"http://" + h for h in valid_hosts}:
                raise ReviewError("Cross-origin requests are not allowed.", 403)
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                raise ReviewError("Cross-site requests are not allowed.", 403)

        def body(self):
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise ReviewError("Send application/json.", 415)
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise ReviewError("Invalid content length.") from None
            if not 0 < size <= 1048576:
                raise ReviewError("JSON body must be between 1 byte and 1 MiB.", 413)
            try:
                body = json.loads(self.rfile.read(size))
            except (ValueError, UnicodeDecodeError):
                raise ReviewError("Malformed JSON.") from None
            if not isinstance(body, dict):
                raise ReviewError("JSON body must be an object.")
            return body

        def dispatch(self, method):
            self.connection.settimeout(15)
            self.guarded()
            path = urlsplit(self.path).path
            if method == "GET" and path in {"/", "/app.js", "/style.css"}:
                name, mime = {"/": ("index.html", "text/html; charset=utf-8"),
                              "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                              "/style.css": ("style.css", "text/css; charset=utf-8")}[path]
                return self.send(200, (STATIC / name).read_bytes(), mime)
            auth = self.headers.get("Authorization", "")
            principal = store.authenticate(auth[7:] if auth.startswith("Bearer ") else "")
            body = self.body() if method == "POST" else {}
            role = principal["role"]
            if method == "GET" and path == "/api/me":
                return self.send(200, principal)
            if path == "/api/portal/status" and method == "GET" and role == "admin":
                kinds = {"source", "semantic_A", "semantic_B"}
                return self.send(200, {
                    "sessions": [s for s in store.sessions() if s["mode"] == "human" and s["kind"] in kinds],
                    "availability": {k: v for k, v in store.availability().items() if k in kinds},
                    "independence_check": store.independence_status()})
            if path == "/api/status" and method == "GET" and role in {"admin", "agent"}:
                return self.send(200, {"sessions": store.sessions(agent_only=role == "agent"),
                                       "availability": store.availability(), "independence_check": store.independence_status() if role == "admin" else None})
            if path == "/api/sessions" and method == "POST" and role in {"admin", "agent"}:
                mode = body.get("mode", "ai_assisted")
                if role == "agent" and mode != "ai_assisted":
                    raise ReviewError("Agent credentials create only AI-assisted assignments.", 403)
                return self.send(201, store.create(body.get("kind"), mode, body.get("reviewer_id", "")))
            if path == "/api/prepare" and method == "POST" and role == "admin":
                if list((store.research / "generation").glob("*/RUNNING.lock")):
                    raise ReviewError("Wait for active generation to stop before preparing canonical forms.", 409)
                from . import annotations, source_review
                source_review.prepare()
                return self.send(200, annotations.prepare())
            if path == "/api/independence" and method == "POST" and role == "admin":
                return self.send(200, store.independence_submit(body))
            parts = path.strip("/").split("/")
            if len(parts) >= 3 and parts[:2] == ["api", "sessions"]:
                sid = parts[2]
                if len(parts) == 4 and parts[3] == "link" and method == "GET" and role == "admin":
                    session = store.assignment(sid)
                    return self.send(200, {"fragment": session["token"]})
                if len(parts) == 4 and parts[3] == "activate" and method == "POST" and role == "admin":
                    return self.send(200, store.activate(sid))
                if len(parts) == 4 and parts[3] == "access-card" and method == "POST" and role == "admin":
                    card = store.export_access_card(sid, self.server.server_address[1])
                    return self.send(200, {"private_access_file": str(card)})
                session = store.authorize(principal, sid, write=method == "POST")
                if len(parts) == 6 and parts[3] == "items" and parts[5] == "source" and method == "GET":
                    data, name = store.source_bytes(sid, parts[4])
                    return self.send(200, data, "application/octet-stream", name)
                if method == "GET" and len(parts) == 3:
                    return self.send(200, store.status(sid))
                if len(parts) == 5 and parts[3] == "items":
                    if method == "GET":
                        return self.send(200, store.show(sid, parts[4]))
                    actor = "browser_reviewer" if role == "reviewer" and session["mode"] == "human" else "agent_api"
                    return self.send(200, store.save(sid, parts[4], body.get("values"), body.get("revision"), actor))
                if len(parts) == 4 and parts[3] == "check" and method == "GET":
                    return self.send(200, store.check(sid))
                if len(parts) == 4 and parts[3] == "download" and method == "GET":
                    file = store.export(sid)
                    name = (f"review_{session['kind']}_{session['status']}{file.suffix}" if session["mode"] == "human"
                            else f"{session['mode']}_{session['kind']}_{file.name}")
                    return self.send(200, file.read_bytes(), "application/octet-stream", name)
                if len(parts) == 4 and parts[3] in {"seal", "register"} and method == "POST":
                    actor = "browser_reviewer" if role == "reviewer" and session["mode"] == "human" else "agent_api"
                    if parts[3] == "seal":
                        return self.send(200, store.seal(sid, body.get("revision"), body.get("attest_human", False), actor))
                    return self.send(200, store.register(sid, actor))
            raise ReviewError("Route not found or not permitted for this access token.", 404)

        def respond(self, method):
            try:
                self.dispatch(method)
            except ReviewError as exc:
                self.send(exc.status, {"error": str(exc)})
            except (KeyError, FileNotFoundError):
                self.send(409, {"error": "Required packet evidence is missing. Ask the study administrator to prepare or repair it."})
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                pass
            except Exception:
                self.send(500, {"error": "The operation failed. Your prior saved revisions are preserved; inspect the local application before retrying."})

        def do_GET(self):
            self.respond("GET")

        def do_POST(self):
            self.respond("POST")
    return Handler


def serve(store, port=8765, open_browser=False):
    if not 1 <= port <= 65535:
        raise ReviewError("Port must be between 1 and 65535.")
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_for(store))
    server.daemon_threads = True
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"Review desk: {url}\nLocal only. Private drafts and return files stay in revision/review_app/private/.", flush=True)
    if open_browser:
        webbrowser.open(url + "/#" + store.credentials["admin"])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    server = sub.add_parser("serve", help="Start a loopback-only web app")
    server.add_argument("--port", type=int, default=8765)
    server.add_argument("--open", action="store_true")
    opened = sub.add_parser("open", help="Open local administrator page or a human assignment without printing tokens")
    opened.add_argument("--session")
    opened.add_argument("--port", type=int, default=8765)
    sub.add_parser("status", help="JSON summary (no human ratings or access tokens)")
    sub.add_parser("schema", help="JSON routes, CLI contract and allowed values")
    created = sub.add_parser("create", help="Create an AI-assisted assignment (never an independent human review)")
    created.add_argument("--kind", choices=KINDS, required=True)
    created.add_argument("--reviewer-id", required=True)
    for command in ("show", "save", "check", "export", "seal"):
        action = sub.add_parser(command)
        action.add_argument("session")
        if command in {"show", "save"}:
            action.add_argument("--item", default="next" if command == "show" else None, required=command == "save")
        if command == "save":
            values = action.add_mutually_exclusive_group(required=True)
            values.add_argument("--values", help="JSON rating object; strings, no source-text edits")
            values.add_argument("--values-file", type=Path, help="Read a JSON rating object from disk")
            action.add_argument("--revision", required=True, type=int)
        if command == "seal":
            action.add_argument("--revision", required=True, type=int)
    args = parser.parse_args()
    if args.command in {"serve", "open", "status"}:
        from .review_batches import ReviewRouter
        store = ReviewRouter()
    else:
        store = ReviewStore()
    try:
        if args.command == "serve":
            return serve(store, args.port, args.open)
        if args.command == "open":
            token = store.assignment(args.session)["token"] if args.session else store.credentials["admin"]
            webbrowser.open(f"http://127.0.0.1:{args.port}/#" + token)
            result = {"opened": True, "access_token_printed": False}
        elif args.command == "schema":
            result = {"default_origin": "http://127.0.0.1:8765", "cli_writes": "ai_assisted_only",
                      "kinds": KINDS, "ratings": RATINGS, "source_verdicts": ["pass", "needs_correction"],
                      "notes_required": "every source; flagged/low-meaning/unusable semantic items",
                      "save_body": {"revision": "current assignment revision integer", "values": "editable field/string map"},
                      "routes": ["GET /api/me", "GET /api/status", "POST /api/sessions",
                                 "GET /api/sessions/{session}", "GET /api/sessions/{session}/items/{item}",
                                 "POST /api/sessions/{session}/items/{item}", "GET /api/sessions/{session}/check",
                                 "GET /api/sessions/{session}/download", "POST /api/sessions/{session}/seal"],
                      "api_auth": "Bearer agent token from ignored local access.json; never expose it in prompts/logs",
                      "human_submission": "Only a genuine reviewer may personally attest in their private UI; automation cannot substitute for that review."}
        elif args.command == "status":
            result = {"availability": store.availability(), "sessions": store.sessions(), "independence_check": store.independence_status()}
        elif args.command == "create":
            created = store.create(args.kind, "ai_assisted", args.reviewer_id)
            result = {k: v for k, v in created.items() if k != "items"}
            result["first_item"] = created["items"][0]["id"]
        else:
            session = store.authorize({"role": "agent"}, args.session)
            if args.command == "show":
                result = store.show(args.session, args.item)
            elif args.command == "save":
                values = read_json(args.values_file) if args.values_file else json.loads(args.values)
                result = store.save(args.session, args.item, values, args.revision)
            elif args.command == "check":
                result = store.check(args.session)
            elif args.command == "export":
                path = store.export(args.session)
                result = {"file": str(path), "sha256": file_hash(path), "mode": session["mode"], "check": store.check(args.session)}
            else:
                result = store.seal(args.session, args.revision)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ReviewError, ValueError, FileNotFoundError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
