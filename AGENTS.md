# Agent coordination protocol

This repository dogfoods never-collide. `ncl` below means
`python .claude/never-collide/ncl`. Before editing anything here:

1. **Identity.** Set `AGENT_NAME` to your tool identity (`claude`,
   `antigravity`, `codex`, `gemini`, `copilot`) and run `ncl whoami`. If it
   fails, stop.
2. **Sync.** Run `ncl status` and read who holds what.
3. **Claim.** `ncl claim --task <id> --paths <globs> --intent '<one line>'`
   for the paths you will change. If the claim is refused, run
   `ncl handoff --task <id> --to <holder> -m '<what you need>'` and stop.
   Never edit around a refused claim.
4. **Work** on a task branch named `<agent>/<task>`. Run `ncl start`, and
   `ncl note` on any interface change another agent depends on.
5. **Done.** Commit, open a pull request, `ncl done --task <id> --pr <n>`.
6. **Tested.** Tests pass and manual checks are recorded:
   `ncl tested --task <id> --evidence '<what you ran>'`.
7. **Release.** After merge, `ncl release --task <id>`.

The edit hook and the git pre-commit hook check every path against the
ledger and run in warn mode here. When one asks, the answer is to claim or
to hand off, never to proceed. There is no pull-request check yet; do not
claim otherwise in docs or commit messages. Never commit directly to `main`.

## Definition of done

- Runtime stays bash, Python 3.7+ and git. No Node, no npm, no service.
- `python -m unittest discover -s tests` passes.
- The pull request describes behaviour, risks and test evidence.
- `ncl done`, `ncl tested` and `ncl release` reflect what actually happened.
- Do not say something works until you have run it.
