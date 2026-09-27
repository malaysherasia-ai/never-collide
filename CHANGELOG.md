# Changelog

## 0.2.0 - 2026-09-27

Enforcement: hooks that check claims before an edit and before a commit.

- `ncl check [PATH...] [--staged] [--payload] [--hook RUNNER]`: is every path
  covered by an active claim held by this agent? Names the holder otherwise.
- Claude Code edit hook: `.claude/hooks/ncl/dispatch`, registered on
  `Edit|Write|MultiEdit|NotebookEdit` by the installer. Warn mode asks with
  the reason; deny mode refuses. Answers in the dialect of `--agent claude`,
  `codex`, `gemini`, `copilot` or `antigravity`; only Claude Code is wired
  and tested.
- Git pre-commit hook: `.claude/hooks/ncl/pre-commit` behind a stub in
  `.git/hooks/pre-commit`, checking the staged files from any tool or
  terminal. Commits on `main` are flagged. Shares the stub with never-again.
- `ncl enforce [warn|deny|off]`, stored in `.agents/never-collide.json`
  with `exempt` paths and the cache age. Every hook starts in warn mode.
- Real glob matching for coverage: `**` spans directories, `*` and `?` stay
  in one segment, a literal path covers its subtree.
- Local ledger cache in `.ncl/` (ignored), refreshed by any fetch or push and
  used by hooks while fresh, or when offline.
- `ncl install-hooks` (run by the installer): config, settings merge, git stub.
- `ncl.cmd` for PowerShell and cmd. Claude Code skill at
  `.claude/skills/never-collide/SKILL.md`.
- Tests: glob matching, payload shapes, hook modes and dialects, the git
  runner, the installer, and a real commit refused then allowed through
  git's own hook.

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
