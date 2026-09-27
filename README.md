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

The installer copies the `ncl` CLI into `.claude/never-collide/`, adds
starter `AGENTS.md`, `.agents/OWNERSHIP.md` and `.agents/PROTOCOL.md` only when
they do not exist, adds a marked block to `CLAUDE.md` without replacing it,
and ignores local state. Safe to re-run.

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

## Version 0.1.0

This release is the ledger CLI, the protocol templates and the installer.
Nothing yet stops an agent that skips `ncl`; the protocol in `AGENTS.md`
and PR review do. Edit-time hooks, a commit hook and a PR check are the next
releases. See [CHANGELOG.md](CHANGELOG.md).

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
