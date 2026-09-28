# Continuation on the transferred Linux workspace

Continuation began on 28 September 2026 in `/shared/Paper`, on
`repair/research-validity-v2` at `843c2a8f5cca51d7005174dab75d5bcc6d07db74`.
The transferred private original source return matched the frozen SHA-256.
The initial Astra audit passed with 162 recorded outputs and 918 remaining.
The original 121 tests passed before new worker dispatch.

## Runtime

The original Windows virtual environment is preserved. The separate Linux
environment uses CPython 3.12.11 and all 24 distributions from the unchanged
`requirements-v2.lock`, installed with hash verification. On this NixOS host:

```sh
cd /shared/Paper
/home/zaruka/.local/share/paper-research-py312/run-python -m research_v2.session_workers audit
/home/zaruka/.local/share/paper-research-py312/run-python -m research_v2.expanded_readiness check
/home/zaruka/.local/share/paper-research-py312/run-python -m research_v2.review_app serve --port 8765
```

The external launcher supplies the NixOS C++ and zlib library paths. The managed
Python executable's interpreter path points to the installed NixOS loader.
No computational method, generation prompt, source, dependency pin, or previous
rewrite was modified to accommodate the host.

## Preserved state and review delivery

The ignored local directory
`private/resume_20260928T124700Z/` holds the starting file-hash inventory,
copies of previous ledgers and verification receipts, SQLite backups, and copies
of the existing analysis artifacts. It must remain private and must not be
committed or included in a public archive. Older unrelated working-tree changes
were present when the workspace arrived and were left intact.

The review application now supports explicit former research-root aliases in
each store's ignored `path_relocations.json`:

```json
{"previous_research_roots": ["C:\\Users\\Empty\\Documents\\Paper\\revision"]}
```

The expanded store has the corresponding `revision\\expanded_v3` former root.
Aliases resolve existing export and account-link paths at runtime. They do not
rewrite stored paths, account credentials, responses, returns, or attestations.
Unregistered roots are not remapped; traversal and symlink escape are rejected.
The old packets remain available through their existing accounts. Accessing an
account or attaching a packet does not establish independent review completion.

## Replay portability evidence

The first Luna transfer replay on Linux failed the strict byte comparison with
the Windows checkpoint. All 105 compressed transform files differed only in
gzip's OS header byte: Windows `0x0a`, Linux `0x03`. Their compressed payloads
and decompressed contents matched; every other output hash matched. The failure
is retained in `verification/luna56_cross_platform_replay_20260928.json`.
The Windows artifacts and the first Linux run are preserved separately. A later
successful Linux replay must not be described as cross-platform byte identity.

## Current progress

Use the actual generation/completion ledgers, replay receipts, and
`checkpoint.json` for current counts and gates. Workers g/h/i were launched
explicitly as `gpt-6-astra`, `xhigh`, `fork_turns="none"`; actual launch paths
and bounded task limits are appended to the delegation ledger. There are no
Astra API calls. Full review packets require complete first-outcome accounting.
No reviewer judgments or manuscript prose are supplied by this continuation.
