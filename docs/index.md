# never-collide

**Parallel coding on one repo, without the collisions.**

Content for `claude-repo.com/never-collide`. Sections follow the hub nav:
Install · For you · Numbers · Why · Compare · FAQ · Docs · GitHub.

## Install

```sh
git clone --depth 1 https://github.com/malaysherasia-ai/never-collide.git
bash never-collide/install.sh .
```

Two minutes. bash, Python 3.7+ and git. No Node, no service, no telemetry.
If never-again is already installed, it is the same command and the two
share the git hook.

## For you

You run Claude Code for the logic and Antigravity for the UI on the same
Next.js site, both pushing to GitHub, Vercel building every branch. Yesterday
Antigravity restyled the location page while Claude Code was halfway through
rewriting it. Nobody told either of them.

never-collide is the drop box both tools check first. Before a tool touches
a file it calls dibs: task, paths, one line of intent. The other tool sees
that in `ncl status`, and its own hook stops it from editing those paths.
When the work is committed, tested and merged, the ledger says so, with
times. Two tools or five, same file, same ritual.

## Numbers

- Installs: counted from GitHub clone statistics, which is all we count.
  Nothing is sent from your machine unless you choose to (see FAQ).
- Every claim, note, hand-off and release is in `ncl log`, so the repo can
  answer "who worked on what, when, and was it tested" without a meeting.

## Why

Git worktree isolation keeps agents on separate files. That is the right
tool when tasks can be split by path. Ours cannot: the UI agent and the
logic agent meet on the same page files daily. They need to *share* a repo
and coordinate, not be kept apart.

Three layers:

1. **Static ownership.** `.agents/OWNERSHIP.md` says who owns what by path.
   Most conflicts never start.
2. **Dynamic claims.** An append-only `ledger.jsonl` on the orphan branch
   `agents/ledger`. Git's fast-forward push is the lock; a lost race is a
   fetch and a re-check, never a merge conflict.
3. **Enforcement.** An edit hook in the agent, a git pre-commit hook for
   every tool and terminal, and a pull-request check. Warn first, deny when
   the team says so.

## Compare

| | Branch per agent | CODEOWNERS | Parallel Code (worktrees) | never-collide |
|---|---|---|---|---|
| Stops two agents editing the same file now | no | no | yes, by separation | yes, by claim |
| Works when agents must share files | yes | yes | no | yes |
| Tells an agent what the other is doing | no | no | no | yes, `ncl status` |
| Records done and tested times | no | no | no | yes |
| Enforced before the edit | no | at review | by layout | edit hook, commit hook, PR check |
| Needs a service | no | GitHub | no | no |

Use Parallel Code and never-collide together: it isolates the tasks that can
be isolated; we coordinate the ones that cannot.

## FAQ

**Which tools?** Any tool that can run a shell command and read `AGENTS.md`:
Claude Code, Antigravity, Codex, Gemini CLI, Copilot. The edit hook is wired
for Claude Code; the dispatcher already speaks the other four dialects and
the entry line for each is in the README.

**What if a session crashes holding a claim?** Claims expire (default four
hours; any update restarts the clock). `ncl status` shows expired claims for
a day so the next agent knows to ask.

**What if two agents genuinely need the same file?** The second is refused,
records a hand-off request, and stops. Sequential by design. The holder
answers with `ncl handoff`.

**Can an agent bypass it?** It can skip `ncl`; the edit hook asks, the
commit hook asks, and the PR check refuses the merge. Deny mode stops the
first two outright.

**What leaves my machine?** Ledger pushes to your own `origin`. Nothing
else, unless you opt in to send feedback.

**Where is the ledger?** `git log origin/agents/ledger`, or `ncl log`.

## Docs

`AGENTS.md` and `.agents/PROTOCOL.md` are served raw at
`/never-collide/AGENTS.md` and `/never-collide/PROTOCOL.md` for tools that
want to read them directly.

MIT. Not affiliated with Anthropic, Google, OpenAI, GitHub or any other AI
tool provider.
