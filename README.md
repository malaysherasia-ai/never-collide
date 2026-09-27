# never-collide

**Parallel coding on one repo, without the collisions.**

[![tests](https://github.com/malaysherasia-ai/never-collide/actions/workflows/tests.yml/badge.svg)](https://github.com/malaysherasia-ai/never-collide/actions/workflows/tests.yml)
[![release](https://img.shields.io/github/v/release/malaysherasia-ai/never-collide?label=release)](https://github.com/malaysherasia-ai/never-collide/releases)
[![python 3.7+](https://img.shields.io/badge/python-3.7%2B-blue)](#requirements)
[![MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Multi-agent coordination for one shared Git repository. Claude Code,
Google Antigravity, OpenAI Codex, Gemini CLI and GitHub Copilot working on
the same codebase at the same time, without stepping on each other. Every
AI coding agent calls dibs on the files it is about to touch, logs what it
did and when it was tested, and the other agents see it before they start.
An edit hook, a git pre-commit hook and a pull-request check make sure of
it.

Second member of the `never-*` family after
[never-again](https://github.com/malaysherasia-ai/claude-never-again),
which stops the same bug twice. Same install pattern, same runtime: bash,
Python 3.7+ and git. No Node, no npm, no service, no telemetry. MIT.

- Site: [claude-repo.com/never-collide](https://www.claude-repo.com/never-collide)
- Works with: Claude Code (edit hook wired and tested), Antigravity, Codex,
  Gemini CLI, Copilot (edit hooks registered from their docs), and any tool
  that can run a shell command and read `AGENTS.md`
- Problems and ideas: [GitHub Issues](https://github.com/malaysherasia-ai/never-collide/issues)
  or `ncl feedback`

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

**One clone per tool.** Two tools in one folder share one checkout and one
branch, so neither can work on its own branch and each sees the other's
half-finished edits. Clone the repo once per tool, open each clone in its
tool, and let the ledger on `origin` do the coordinating.

Then give each clone its identity. Claude Code's comes from
`.claude/settings.json`, which the installer writes:

```json
{ "env": { "AGENT_NAME": "claude", "AGENT_TOOL": "claude-code" } }
```

In the clone another tool works in, once:

```sh
python .claude/never-collide/ncl whoami --set antigravity
```

That writes `.ncl/agent` (local, ignored). `AGENT_NAME` in the environment
still wins when set.

### Other tools

Antigravity, Codex, Gemini CLI and Copilot read `AGENTS.md` natively, so
they get the ritual, and the git commit hook and the PR check cover their
work whatever tool made it. To also register the edit hook with them:

```sh
bash never-collide/install.sh --agent antigravity .      # repeatable: --agent codex ...
```

| Tool | Config written | Matcher | Rules and skill |
|---|---|---|---|
| Antigravity | `.agents/hooks.json` | `write_to_file\|replace_file_content\|multi_replace_file_content` | `AGENTS.md`, `.agents/skills/` |
| Codex | `.codex/hooks.json` | `Edit\|Write\|apply_patch` | `AGENTS.md`, `.agents/skills/` |
| Gemini CLI | `.gemini/settings.json` (`BeforeTool`) | `write_file\|replace\|edit` | `GEMINI.md` (`@AGENTS.md`), `.gemini/skills/` |
| Copilot | `.github/hooks/never-collide.json` | all | `.github/copilot-instructions.md`, `.github/skills/` |

Each entry runs `~/.never-collide/launch`, which the installer puts outside
every repo; the entry carries no path of your machine, so the committed
config works on every clone, and a clone without never-collide installed
exits quietly. The dispatcher reads each tool's payload and answers in its
documented shape. These entries follow each tool's own documentation and
were **not run here**; the first time a tool asks about an unclaimed file
is the confirmation. `ncl doctor` shows what is registered. Known from
field reports: Antigravity's hooks have been unreliable on Windows in some
versions.

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

Every hook starts in **warn** mode: it asks, it does not stop. One
exception, from Claude Code's own rules: in its auto permission mode an
`ask` counts as `deny`, so there warn mode already stops an unclaimed edit
and the agent claims and retries. When the team has run a week without
false positives, promote it:

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

## Numbers, and an optional hello

Usage is counted from GitHub clone statistics. `ncl` sends nothing home on
its own: the network calls it makes are ledger pushes to your `origin` and,
only when you run it, `ncl upgrade` against GitHub's release API.

The installer asks once per machine, and Enter skips it:

```
never-collide is free and sends nothing home on its own. Help us count you?
  [Enter] skip   [c] count me, anonymously   [f] count me and leave feedback
```

`c` sends the version, OS and Python version. `f` asks for a name, an email,
which tools you run and what you think, every field optional, then shows the
exact payload and sends it only on a yes. Later, or instead:

```sh
ncl feedback                      # same questions
ncl feedback --count --yes        # just count me
ncl feedback -m 'wish it did X'   # shows the payload, asks before sending
ncl feedback --dry-run -m '...'   # shows the payload, sends nothing
```

`NCL_NO_PROMPT=1` means never ask; CI is never asked. What the endpoint
receives and stores is in [docs/feedback-endpoint.md](docs/feedback-endpoint.md).

## When something goes wrong

The tool never edits your source files. It reads paths and appends one line
to a separate branch. The worst a bug can do is ask about, or refuse, an
edit or a commit, and `ncl enforce off` ends that.

- **The log.** `.claude/never-collide/ncl.log` (local, never committed)
  records every hook decision with its paths and reasons, every ledger
  write and every error. `ncl report` summarises it: counts, the last
  errors, the last hook questions. Paste either into an issue.
- **`ncl doctor`** checks Python, git, the origin, the ledger branch, your
  identity, the config, the files, the hook registration and the git stub,
  and says in plain words what to fix.
- **`ncl feedback --report`** attaches the counts from the log to what you
  send. Counts only: no paths, no names, no message text.
- **`ncl uninstall`** removes everything the installer added and leaves
  `AGENTS.md`, `.agents/` and the ledger branch, which are yours.

## Upgrade

```sh
ncl upgrade --check     # only look
ncl upgrade             # fetch the newest release and run its installer here
```

Or re-run `install.sh` from a fresh clone; it is the same thing.

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
