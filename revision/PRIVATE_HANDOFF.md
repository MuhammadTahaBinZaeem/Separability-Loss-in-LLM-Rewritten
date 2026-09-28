# Private handoff dependencies — not pushed to GitHub

The research code, corpus, native outcomes, failure evidence, prompt/output
receipts, analyses, tests and public instructions belong in the repository.
Credentials and private review evidence do not. Nothing below was deleted.

Prefer opening the existing `C:\Users\Empty\Documents\Paper` workspace in the
new Codex session. It already contains these ignored local files and preserves
the same reviewer logins. A fresh GitHub clone alone does not contain them.

| Local location | Why it must stay private / when needed |
|---|---|
| `C:\Users\Empty\Documents\Paper-secrets\api.env` | API/Zenodo credentials; not needed for actual Codex Astra rewriting |
| `revision/source_review/private/` | Original source review and attestation; `expanded_study.verify()` currently checks the exact original return hash |
| `revision/review_app/private/` | Existing review database, tokens, private access cards, original returns and backups |
| `revision/expanded_v3/private/` | Shared budget SQLite, HTTP/transport details, dispatch locking database and expanded review database/account links |
| `revision/expanded_v3/source_review/private/` | Any genuine replacement-source returns/attestation, when received |
| `revision/annotations/private_join_key.csv` and `revision/expanded_v3/annotations/private_join_key.csv` | Blinding keys; the latter exists only after full issuance |
| `revision/annotations/returns/`, registry/independence files, and `revision/expanded_v3/annotations/private/` | Private reviewer identities and original responses, where present |

If using another computer, the owner must transfer the required private files
through a trusted private channel, preserving paths and hashes. Never paste their
contents into a public issue, commit, handoff prompt or terminal output. Never
invent missing attestations or regenerate reviewer tokens/budget history just
to make a clone run. Never use public review examples as actual evidence.

For Astra generation on a fresh clone, the existing verifier currently requires
`revision/source_review/private/original_return.jsonl` in addition to public corpus
files. Its required SHA-256 is recorded in `expanded_v3/corpus/freeze.json`.
Without that file, request private transfer or implement a clearly separated
public corpus-only verification path without falsely passing the independent
review gate. Do not change frozen hashes or fabricate the missing return.

The public budget/checkpoint summaries are informative, not substitutes for the
private transactional ledger when authorizing further paid requests. Local ZIP
archives, caches, the virtual environment, secret HTTP bodies, logs and database
backups remain local; regenerate public derived packages from their instructions.

The old `revision/agent_rewrite/private_join_key.csv` also remains locally but is
no longer tracked. It was tracked in earlier commits; this handoff does not rewrite
repository history or claim that historical copies have been removed.
