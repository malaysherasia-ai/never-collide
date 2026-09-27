# never-collide

**Parallel coding on one repo, without the collisions.**

Claude Code, Antigravity, Codex, Gemini CLI and Copilot working on the same
codebase at the same time, without stepping on each other. Every agent calls
dibs before it touches a file, logs what it did, and logs when it was tested.
The other agents see it before they start.

Second member of the `never-*` family after
[never-again](https://github.com/malaysherasia-ai/claude-never-again). Same
install pattern, same runtime: bash, Python 3.7+ and git. No Node, no npm, no
service, no telemetry.

## Install

```sh
git clone --depth 1 https://github.com/malaysherasia-ai/never-collide.git
bash never-collide/install.sh .
```

PowerShell:

```powershell
git clone --depth 1 https://github.com/malaysherasia-ai/never-collide.git
& "C:\Program Files\Git\bin\bash.exe" never-collide/install.sh .
```

The installer copies the `ncl` CLI into `.claude/never-collide/`, the hook
dispatcher and git runner into `.claude/hooks/ncl/`, and the skill into
`.claude/skills/never-collide/`. It adds starter `AGENTS.md`,
`.agents/OWNERSHIP.md` and `.agents/PROTOCOL.md` only when they do not exist,
adds a marked block to `CLAUDE.md` without replacing it, ignores local state,
registers the edit hook in `.claude/settings.json` (merged, never replaced)
and installs the git pre-commit stub. Safe to re-run; that is also how you
upgrade.

Then give each tool its own identity. Claude Code reads
`.claude/settings.json`; the others take an environment variable:

```json
{ "env": { "AGENT_NAME": "claude", "AGENT_TOOL": "claude-code" } }
```

```sh
export AGENT_NAME=antigravity
```

## The ritual

`ncl` below means `python .claude/never-collide/ncl` (or add an alias).

1. **Identity.** `ncl whoami`. Unset, it fails; stop.
2. **Sync.** `ncl status` before planning any edit. Who holds what, right now.
3. **Claim.** Call dibs on the paths you will touch:

   ```sh
   ncl claim --task WCR-42 --paths 'src/app/locations/**' --intent 'Add per-location hero'
   ```

   Refused because another agent holds them? Ask, then stop:

   ```sh
   ncl handoff --task WCR-42 --to claude --paths 'src/app/locations/**' -m 'Need the hero page for styling'
   ```

4. **Work** on your own branch. `ncl start --task WCR-42`, and `ncl note` on
   any interface change another agent depends on.
5. **Done.** Commit, open the PR, `ncl done --task WCR-42 --pr 118`.
6. **Tested.** CI green, preview checked at 390 / 768 / 1440:

   ```sh
   ncl tested --task WCR-42 --evidence 'CI green, preview checked at 390/768/1440' --preview https://...
   ```

7. **Release.** After merge, `ncl release --task WCR-42`.

`ncl log` prints every event, oldest first (`--task`, `--agent`, `-n`).

## How it works

The ledger is one append-only `ledger.jsonl` on the orphan branch
`agents/ledger` of your `origin`. One JSON object per line; the newest state
record for a task is its current state. Git's fast-forward push is the lock:
`ncl claim` fetches the ledger, checks glob overlap against every active claim
by another agent, refuses on overlap, otherwise appends and pushes. If two
agents push within the same second, the second push is rejected, `ncl`
re-reads the ledger, re-runs the check and either retries or fails cleanly.

Statuses: `claimed → in_progress → done → tested → released`, plus `handoff`
and, by time, `expired`. Claims carry a TTL (default four hours) so a crashed
session never blocks anyone forever; any update to a task restarts its clock.
Overlap is checked conservatively on literal path prefixes, so two globs that
share a directory are treated as overlapping.

Timestamps are UTC in the ledger; `ncl status` prints local time.

## Enforcement, because agents forget

Two hooks check the same thing: is every path this agent is about to touch
covered by an active claim it holds?

- **Edit hook (Claude Code).** Registered by the installer in
  `.claude/settings.json` on `Edit|Write|MultiEdit|NotebookEdit`. An
  unclaimed path, or one held by another agent, is asked about with the
  reason and the holder's name. Other tools can point their own pre-tool hook
  at `.claude/hooks/ncl/dispatch --agent codex|gemini|copilot|antigravity`;
  the dispatcher reads each tool's payload shape and answers in its dialect.
  Only the Claude Code entry is installed and tested so far.
- **Commit hook (git).** A stub in `.git/hooks/pre-commit` runs the same check
  over the staged files, from any tool or terminal. A commit on `main` is
  flagged too. If never-again is installed, the two share the stub.

Every hook starts in **warn** mode: it asks, it does not stop. When the team
has run a week without false positives, promote it:

```sh
ncl enforce deny     # unclaimed edits and commits are refused
ncl enforce warn     # back to asking
ncl enforce off      # silent
```

The mode lives in `.agents/never-collide.json`, so it is committed and the
same for every agent. `exempt` there lists paths anyone may touch without a
claim. `ncl check <path>` answers the question by hand.

Hooks read a local ledger cache (`.ncl/`, ignored) refreshed at most every two
minutes, so an edit does not wait on the network; a claim refreshes it at
once. Offline, the last cache is used and the answer says so.

- **Pull-request check (GitHub Actions).** `.github/workflows/never-collide.yml`
  runs `ncl verify-pr` on every PR: each changed path must be covered by a
  claim recorded on the PR's branch, and that claim must be `done`. Switch
  `--require done` to `--require tested` once every agent records evidence
  before asking for a merge. A claim that has expired by TTL still counts
  here; done stays done.

Nobody commits to `main`: branch per agent per task, PR, preview, merge.
Real merge conflicts surface at PR time, where a person sees them.

See [CHANGELOG.md](CHANGELOG.md) for what each version added.

## Requirements

- Python 3.7+ and git
- A remote named `origin` that every participating agent can fetch and push

## Development

```sh
python -m unittest discover -s tests -v
python .claude/never-collide/ncl --version
```

This repo dogfoods itself: see [AGENTS.md](AGENTS.md).

MIT. Not affiliated with Anthropic, Google, OpenAI, GitHub or any other AI
tool provider.
