---
name: never-collide
description: Coordinate with the other AI coding tools that share this repository. Use before editing any file, whenever a never-collide hook asks about an unclaimed path, when the user says "call dibs", "claim", "who is working on", "hand off", "is anyone touching", or when a task is finished, tested or merged and the ledger needs to know.
---

# Never Collide

Several AI tools push to this repo. Before you touch a file, call dibs on it,
so the tool halfway through that page is not surprised by your rewrite.

`ncl` below means `python .claude/never-collide/ncl`. PowerShell:
`.claude\never-collide\ncl.cmd`.

## The ritual

1. **Identity.** `ncl whoami`. If `AGENT_NAME` is unset, stop and tell the
   user; never guess an identity.
2. **Sync.** `ncl status`. Read every active claim and every message
   addressed to you before planning an edit.
3. **Claim.** `ncl claim --task <id> --paths <globs> --intent '<one line>'`.
   Claim narrowly: the files you will change, not the directory above them.
   Refused? Post `ncl handoff --task <id> --to <holder> -m '<what you
   need>'` and stop. Do not edit around a refused claim, do not widen your
   claim to swallow theirs, do not wait it out.
4. **Work** on your own branch, `<agent>/<task>`. `ncl start --task <id>`.
   `ncl note --task <id> '<what changed>'` on any interface another agent
   depends on: props, schema, API shape, route.
5. **Done.** Commit, open the PR, `ncl done --task <id> --pr <n>`.
6. **Tested.** Run the tests and check the preview, then
   `ncl tested --task <id> --evidence '<what you ran>' --preview <url>`.
   Never record `tested` for checks you did not run.
7. **Release.** After merge, `ncl release --task <id>`.

## When the hook asks

The edit hook fires when a path you are about to write is not covered by an
active claim you hold. The message names the path and, if another agent
holds it, who. The answer is never "proceed anyway":

- Unclaimed: `ncl claim` it, then retry the edit.
- Held by another agent: `ncl handoff --to <holder>` describing what you
  need, tell the user, and stop.
- `AGENT_NAME` unset: tell the user which identity this session should use.

The commit hook checks the same thing for every staged file. A commit on
`main` is warned about too; use a task branch.

## Useful

- `ncl log` shows every event; `ncl log --task <id>` one task.
- `ncl enforce` prints the current mode; `ncl enforce deny` stops
  unclaimed edits instead of asking. Only a person changes this.
- `ncl check <path>` says whether you may edit a path, without a hook.
