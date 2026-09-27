# Coding-agent coordination

Several AI coding tools share this repository. Call dibs before you touch a
file. `ncl` below means `python .claude/never-collide/ncl`.

1. **Identity.** `ncl whoami`. If `AGENT_NAME` is unset, stop and say so.
2. **Sync.** `ncl status` before planning any edit.
3. **Claim.** `ncl claim --task <id> --paths <globs> --intent '<one line>'`.
   Refused? `ncl handoff --task <id> --to <holder> -m '<what you need>'`,
   then stop. Never edit around a refused claim.
4. **Work** on your own branch, `<agent>/<task>`. `ncl start`, then
   `ncl note` on any interface change another agent depends on.
5. **Done.** Commit, open a PR, `ncl done --task <id> --pr <n>`.
6. **Tested.** CI green and preview checked: `ncl tested --task <id>
   --evidence '<what you checked>' --preview <url>`.
7. **Release.** After merge, `ncl release --task <id>`.

An edit hook and the git pre-commit hook check every path against the
ledger. When one asks about an unclaimed path, claim it or hand off; never
proceed past the question. Ownership boundaries are in
`.agents/OWNERSHIP.md`; the ledger protocol is in `.agents/PROTOCOL.md`.
Never commit directly to `main`.
