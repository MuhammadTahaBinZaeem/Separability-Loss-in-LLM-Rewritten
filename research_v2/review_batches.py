"""Versioned packets behind the same loopback server and existing reviewer logins."""
from __future__ import annotations

from .io import OUT
from .review_app import ReviewError, ReviewStore


class ReviewRouter:
    def __init__(self, stores=None):
        if stores is None:
            stores = [("Original packet", ReviewStore())]
            from .expanded_study import BASE
            if (BASE / "source_review/issued_manifest.json").exists():
                from .expanded_review import register
                stores.append(("Updated study", ReviewStore(BASE / "private/review_app", BASE, source_archive=OUT, registrar=register)))
        self.stores = stores
        self.primary = stores[0][1]
        self.research, self.credentials = self.primary.research, self.primary.credentials

    def locate(self, sid):
        found = []
        for _, store in self.stores:
            try:
                store.assignment(sid)
                found.append(store)
            except ReviewError as exc:
                if exc.status != 404:
                    raise
        if len(found) != 1:
            raise ReviewError("Assignment not found or ambiguous.", 404)
        return found[0]

    def assignment(self, sid):
        return self.locate(sid).assignment(sid)

    def authenticate(self, token):
        owner = None
        principal = None
        for _, store in self.stores:
            try:
                candidate = store.authenticate(token)
            except ReviewError as exc:
                if exc.status != 401:
                    raise
                continue
            owner, principal = store, candidate
            break
        if principal is None:
            raise ReviewError("This access token is not valid.", 401)
        if principal["role"] != "reviewer":
            return principal
        original = owner.assignment(principal["session_id"])
        # Explicit persisted linkage, never infer ownership merely from a pseudonym.
        allowed = [{"id": original["id"], "label": next(label for label, s in self.stores if s is owner),
                    "status": original["status"]}]
        from .io import read_json, read_jsonl
        for label, store in self.stores:
            link_path = store.private / "account_links.json"
            links = read_json(link_path) if link_path.exists() else []
            links += read_jsonl(store.private / "account_link_additions.jsonl")
            for link in links:
                if owner.recorded_path(link["from_research"]) != owner.research or link["from_session_id"] != original["id"]:
                    continue
                target = store.assignment(link["to_session_id"])
                if (target["mode"] != original["mode"] or target["kind"] != original["kind"]
                        or target["reviewer_id"] != original["reviewer_id"]):
                    raise ReviewError("Packet ownership record does not match the reviewer assignment.", 409)
                if target["id"] not in {a["id"] for a in allowed}:
                    allowed.append({"id": target["id"], "label": label, "status": target["status"]})
        active = next((a for a in reversed(allowed) if a["status"] in {"draft", "awaiting_packet"}), allowed[-1])
        return {"role": "reviewer", "session_id": active["id"], "assignments": allowed}

    def authorize(self, principal, sid, write=False):
        allowed = {r["id"] for r in principal.get("assignments", [])}
        if principal.get("role") == "reviewer" and sid in allowed:
            return self.locate(sid).authorize({"role": "reviewer", "session_id": sid}, sid, write)
        return self.locate(sid).authorize(principal, sid, write)

    def sessions(self, agent_only=False):
        return [{**row, "packet_label": label} for label, store in self.stores for row in store.sessions(agent_only)]

    def __getattr__(self, name):
        if name in {"status", "show", "source_bytes", "export", "save", "check", "seal", "register", "activate", "export_access_card"}:
            return lambda sid, *args, **kwargs: getattr(self.locate(sid), name)(sid, *args, **kwargs)
        return getattr(self.primary, name)
