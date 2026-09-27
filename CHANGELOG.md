# Changelog

## 0.1.0 - 2026-09-27

First release: the ledger CLI.

- `ncl` with `whoami`, `status`, `log`, `claim`, `start`, `note`, `done`,
  `tested`, `release` and `handoff`.
- Append-only `ledger.jsonl` on the orphan `agents/ledger` branch; Git's
  fast-forward push is the lock, with fetch, re-check and retry on a lost race.
- Claims are refused when they overlap an active claim by another agent.
  Claims expire after a TTL (default four hours); any update restarts the clock.
- `handoff` from the holder releases paths to another agent; from anyone else
  it is a request that leaves the holder's state untouched. Both show in
  `ncl status`.
- `tested` records evidence and an optional preview URL; `done` records a PR.
- Idempotent `install.sh`: copies the CLI, adds starter `AGENTS.md`,
  `.agents/OWNERSHIP.md` and `.agents/PROTOCOL.md` when absent, adds a marked
  block to `CLAUDE.md`, ignores local state.
- Tests: pattern overlap, expiry, full lifecycle against a local bare remote,
  and the installer.

Not in this release: edit-time hooks, a commit hook, a PR check. Nothing yet
stops an agent that skips `ncl`.
