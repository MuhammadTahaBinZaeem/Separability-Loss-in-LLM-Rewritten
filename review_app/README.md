# Local Research Review Desk

A local-only editor for the current study's source and semantic reviews. It uses
the existing Python environment plus standard-library HTTP/SQLite components;
there are no new packages, CDNs, analytics, model calls or hosting accounts.
It does not turn AI ratings into human evidence or certify publication readiness.

The browser portal uses neutral reviewer wording and provides only source review
and semantic reviewer A/B. It has no origin selector or AI preflight workspace.
Existing machine-assisted records and the CLI retain their explicit provenance;
they are not presented as independent reviewer assignments. Credentials, canonical
response formats and the requirement for personal, independent completion are
unchanged by this presentation change.

## Start and reopen

From the repository root in PowerShell:

```powershell
.\scripts\start_review_app.ps1
```

Or:

```powershell
.\.venv\Scripts\python.exe -m research_v2.review_app serve --open
```

The app binds **only to 127.0.0.1**, normally at http://127.0.0.1:8765. Keep that
terminal/process running; Ctrl+C stops it. Data survives server/browser restarts.
To reopen an already running administrator workspace without copying a token:

```powershell
.\.venv\Scripts\python.exe -m research_v2.review_app open
```

Use `--port 8766` consistently on `serve`/`open` if the default port is occupied.
Do not expose the server with a public tunnel or change its bind address. A
localhost link is usable only on the computer running the app. Secure remote
collection needs a separately reviewed deployment/packet-sharing arrangement;
do not send the full unblinded repository to a semantic reviewer.

## Workflow

1. The administrator creates an assignment, choosing the packet and a reviewer
   pseudonym for one independently working reviewer.
   Human semantic accounts can be reserved before their forms are issued. Their
   logins work immediately but show **Waiting for your review packet**; no
   placeholder packet, answers, export or attestation is created. Assign each
   pseudonym to one actual person and retain that identity mapping privately.
2. Open the assigned workspace or copy its private reviewer link. Give a human
   only their own link, not the administrator link or another person's link.
3. Read the whole passage/pair and rate it. Source review includes local archived
   context, work boundaries and a full-source download. Semantic workspaces
   contain only opaque item IDs and paired texts, never the author/model join key.
4. **Save** or **Save & next** persists the answers in SQLite and updates the
   correctly formatted CSV/JSONL draft on disk. Ctrl/Cmd+S also saves. Partial
   answers are allowed as drafts, but do not count as complete.
5. **Download current return** downloads the saved canonical draft. It does not
   silently include unsaved edits. **Check missing responses** locates missing
   ratings or required notes.
6. **Finish review** validates every item and seals an immutable return. An
   actual human must personally check the attestation box. A genuine human
   return is then registered using the existing `source_review.ingest` or
   `annotations.ingest` importer. A failed registration does not discard the
   sealed file; address the cause and use **Retry study registration**.

Two human semantic slots require different people. The application prevents
known source/semantic identity overlap before both blinded reviews are sealed.
It cannot detect undisclosed alternate identities or source exposure elsewhere.
If the two human rating sets are identical throughout, the administrator page
provides the separate human provenance-check form required by the validator.
Identical ratings alone are not evidence of misconduct.

### Packet availability

- **Source integrity:** the frozen 360 originals; JSONL output with unchanged
  identifiers, offsets, hashes and source text, plus `verdict` and `notes`.
- **Semantic A/B:** canonical independently randomized human packets. These stay
  unavailable until both providers have complete accounting and the study's
  official forms have been issued. The app does not fabricate a partial human
  packet to make the gate look complete. Once the forms are issued, the
  administrator clicks **Attach issued packet** on each reserved account.
  The existing reviewer key remains valid. The reviewer clicks **Check packet
  availability** or reloads to begin. This does not change the two-reviewer design.
- **CLI-only AI semantic preflight:** a fixed snapshot of all technically valid rewrites
  currently available from inactive provider ledgers. This has separate `ai_…`
  IDs and is never eligible for the independent-human importer. Later generations
  do not silently expand an existing snapshot; create a new AI snapshot if needed.

The administrator's **Prepare / check canonical forms** button calls the
existing preparation functions only when no generation writer is active.

## Exactly what Save writes

Private data lives under the Git-ignored folder:

```text
revision/review_app/private/
  access.json                         # private local access capabilities
  reviews.sqlite3                     # authoritative assignments/answers/events
  sessions/<assignment-id>/
    assignment.json                   # immutable origin/packet identity
    activation.json                   # issued-packet linkage for a reserved account
    private_access_8765.txt            # optional private login card; contains a key
    packet.json                       # immutable issued-packet snapshot
    revision_000001.answers.json       # immutable per-save answer/event record
    current.draft.jsonl                # source draft, or current.draft.csv
    human_completed.jsonl             # created only on actual human submission
    ai_assisted_completed.csv         # example of a separate AI return
    completion.json                   # origin, actual submission time and hashes
```

Completed-file extensions follow packet type: `.jsonl` for source, `.csv` for
semantic. Each save preserves an immutable answer revision and refreshes one
derived draft; it does not store thousands of full duplicate corpus snapshots.
The draft is rebuilt from the database on download/export. Original issued text
cannot be edited through either interface. Optimistic revision checks reject a
stale browser/agent save instead of overwriting newer answers.

Successful human registration also preserves the exact completed return in the
pre-existing canonical location:

- Source: `revision/source_review/private/original_return.jsonl` and attestation.
- Semantic: `revision/annotations/returns/` and `reviewer_registry.json`.

The app does not alter the frozen corpus, redo generation, compute manuscript
claims, hire people, make ethics declarations, publish a DOI or submit a paper.
Flagged source passages still fail the appropriate scientific readiness gate.

## AI / CLI contract

The CLI uses the same database, validation and exports as the website. It emits
JSON and exits with code 2 on invalid requests. **CLI review writes are limited
to explicitly AI-assisted assignments.** No command can generate a human
attestation. Never copy AI judgments into a supposedly independent human return.
CLI/agent accounts do not open browser review workspaces. Use the CLI/API to
inspect their explicitly labeled records.

```powershell
# Inspect available packets and progress (no access tokens or human ratings).
.\.venv\Scripts\python.exe -m research_v2.review_app status
.\.venv\Scripts\python.exe -m research_v2.review_app schema

# Create an explicitly non-human assignment; the result includes its ID.
.\.venv\Scripts\python.exe -m research_v2.review_app create --kind source --reviewer-id ai-source-01
.\.venv\Scripts\python.exe -m research_v2.review_app create --kind semantic_preflight --reviewer-id ai-semantic-01

# Replace ASSIGNMENT_ID with the returned ID. "next" selects an incomplete item.
.\.venv\Scripts\python.exe -m research_v2.review_app show ASSIGNMENT_ID --item next

# Supply only the judgment you actually made, not placeholder/all-pass answers.
# The JSON file contains editable field names and string values; no source text.
# Use the current revision returned by show/status, and the exact returned item ID.
.\.venv\Scripts\python.exe -m research_v2.review_app save ASSIGNMENT_ID --item ITEM_ID --revision CURRENT_REVISION --values-file PATH_TO_YOUR_RATING_JSON

.\.venv\Scripts\python.exe -m research_v2.review_app check ASSIGNMENT_ID
.\.venv\Scripts\python.exe -m research_v2.review_app export ASSIGNMENT_ID
.\.venv\Scripts\python.exe -m research_v2.review_app seal ASSIGNMENT_ID --revision CURRENT_REVISION
```

`show` returns the exact row, editable fields, per-item validation errors,
current revision and source context where appropriate. `save` returns the new
revision, validation messages, exact export path/hash and review origin. It
does not select ratings automatically. `seal` refuses incomplete packets and
preserves AI origin rather than registering human evidence.

### Local HTTP API

For automation requiring HTTP, read only the **agent** capability from ignored
`access.json` inside the local client and send `Authorization: Bearer TOKEN`.
Do not paste access capabilities into an LLM prompt, URL query, log, Git commit
or public file. Prefer the CLI, which does not require exposing a token.

```text
GET  /api/me
GET  /api/status
POST /api/sessions                        {kind, mode: "ai_assisted", reviewer_id}
GET  /api/sessions/<id>
GET  /api/sessions/<id>/items/next
GET  /api/sessions/<id>/items/<item-id>
POST /api/sessions/<id>/items/<item-id>    {revision: integer, values: {field: string}}
GET  /api/sessions/<id>/check
GET  /api/sessions/<id>/download
POST /api/sessions/<id>/seal               {revision: integer, attest_human: false}
```

POST requests require `Content-Type: application/json`. Errors are JSON with
`error`; status 409 means a stale revision, locked/incomplete packet or evidence
conflict. Reload the item and reassess rather than blindly resending old values.
An agent token cannot access human answers, create human assignments, access
human-only source material through semantic assignments, or submit a human
provenance check. Each reviewer token is limited to its own assignment.

Administrator-only `POST /api/sessions/<id>/access-card` writes that assignment's
private login card into its ignored session directory and returns only its path,
not the key. `POST /api/sessions/<id>/activate` attaches an actually issued packet
to a reserved human account. Neither operation supplies ratings or attestations;
neither is available to agent or reviewer credentials. Do not send all three
private access cards to one semantic reviewer: give each person only their own.

## Security, backups and limitations

Loopback binding, per-assignment capabilities, strict Host/Origin checks,
server-side authorization, a restrictive content-security policy and no remote
dependencies protect the local browser workflow. Tokens travel in URL fragments
when opening a workspace, then are removed from the address bar and retained
only in that tab's session storage. HTTP logging does not record tokens/answers.
Ratings use safe text rendering rather than HTML injection.

This is **not** an identity verification service or protection against someone
who controls this computer/account. Access capabilities and the database are
local plaintext, not encrypted. Use a trusted OS account, disk encryption,
restricted filesystem permissions and appropriate institutional storage.
Human identities/independence are attested, not cryptographically proved; an
automated browser action cannot become genuine human review by ticking a box.

Stop the server before making a filesystem backup of the **entire private
directory**, not only the draft exports. Keep its contents out of the public
research archive. Save revisions preserve previous answers, but do not replace
an external backup. Treat CSV files as data: if opening in a spreadsheet, import
as text and disable formula execution rather than altering canonical passages.

The public code/static UI and tests can be archived; private app records,
tokens, draft responses and human registries are excluded from the archive
allowlist. Human-reviewed release materials still require the investigator's
consent and rights decisions before any public sharing.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_review_app.py
node --check review_app/app.js
```

Tests use synthetic temporary packets only. They check persistence, canonical
CSV/JSONL compatibility, immutable text and sealed returns, partial-review
validation, revision conflicts, source-context linkage, separation of human/AI
and reviewer A/B, authentication, origin/host restrictions and live HTTP
save/download behavior. No test represents a real human review. Browser visual
testing is separate from these checks and has not been asserted.
