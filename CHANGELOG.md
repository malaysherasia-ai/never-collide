# Changelog

## 0.6.2 - 2026-09-27

- One walkthrough for setting up two tools on one repo, in the README, in
  the site docs and in what the installer prints when it finishes: second
  clone, install with `--agent`, pull request, `install-hooks` and
  `whoami --set` in the other clone, `doctor` in both, ownership, a week in
  warn mode. Nothing else changes.

## 0.6.1 - 2026-09-27

- `ncl upgrade` falls back to the full releases list when GitHub's
  `releases/latest` answers 404, which it does while every release is a
  pre-release. Found on the first real `ncl upgrade --check` against the
  published repo.

## 0.6.0 - 2026-09-27

Other tools, and identity without environment variables. Built after
checking the official hook documentation of Claude Code and Antigravity
(plus Codex, Gemini CLI and Copilot).

- `ncl whoami --set <tool>` records this clone's identity in `.ncl/agent`;
  `AGENT_NAME` in the environment still wins. `install.sh --identity <tool>`
  does the same at install time. One clone per tool is the documented setup.
- `install.sh --agent antigravity|codex|gemini|copilot` (repeatable) and
  `ncl install-hooks --agent`: registers the edit hook in each tool's own
  config (`.agents/hooks.json`, `.codex/hooks.json`,
  `.gemini/settings.json`, `.github/hooks/never-collide.json`) through a
  launcher at `~/.never-collide/launch`, copies the skill to each tool's
  skills folder, and creates `GEMINI.md` / `copilot-instructions.md` when
  missing. Remembered in `.agents/never-collide.json` so re-runs and
  upgrades keep them. Not run against those tools here.
- Antigravity output corrected to its documented shape: `decision` and
  `reason` only. The dispatcher always exits 0 as a hook, takes its
  identity from `--agent` when `AGENT_NAME` is unset, and finds the repo
  from its own location before falling back to the payload.
- `ncl doctor` lists registered tools and the launcher; `ncl uninstall`
  removes those registrations.
- README: in Claude Code's auto permission mode an `ask` counts as `deny`
  (from its docs), so warn mode already stops unclaimed edits there.

## 0.5.0 - 2026-09-27

A log inside the tool, and the commands a non-developer needs when
something goes wrong.

- `.claude/never-collide/ncl.log` (local, ignored): one JSON line per hook
  decision (runner, mode, decision, paths, reasons), per ledger write and
  per error. What to paste into a bug report.
- `ncl report`: counts from the log plus the last errors and the last hook
  questions. `--json` gives the counts alone.
- `ncl feedback --report` attaches those counts. Never paths, never names.
  Interactive feedback asks before attaching.
- `ncl doctor`: Python, git, repo, origin, ledger branch, identity, config,
  files, hook registration, git stub, workflow, log, never-again. FAIL
  lines say what to fix.
- `ncl uninstall [--yes]`: removes the tool's folders, the workflow, the
  settings entry, the git stub or its line, and the CLAUDE.md block. Keeps
  `AGENTS.md`, `.agents/`, `env.AGENT_NAME` and the ledger branch.

## 0.4.0 - 2026-09-27

Opt-in usage count and feedback, and `ncl upgrade`.

- `ncl feedback`: `--count` sends version, OS and Python only; `--name`,
  `--email`, `--tools`, `-m` add what the person typed. Shows the exact
  payload and sends only on a yes (`--yes` to skip; `--dry-run` to see it
  and send nothing). Endpoint contract in `docs/feedback-endpoint.md`; the
  site route is not built yet.
- The installer asks once per machine, Enter skips, never in CI (no TTY)
  and never with `NCL_NO_PROMPT=1`. The marker lives in `~/.never-collide/`
  (`NCL_HOME` overrides).
- `ncl upgrade [--check] [--yes] [--from DIR]`: GitHub's latest release,
  or a local clone, installed here through its own `install.sh`.
- `ncl version`.
- Tests: feedback against a local HTTP server, the silent prompt, an
  unreachable endpoint, upgrade from a local source, no-network upgrade.

## 0.3.0 - 2026-09-27

The pull-request check, the docs page and the adopter example.

- `ncl verify-pr --base --head --branch [--require done|tested]`: every path
  changed by the PR must be covered by a claim recorded on its branch (or
  whose task id is a segment of the branch name), and that claim must be
  `done`, or `tested` when required. TTL is ignored: done stays done.
- `.github/workflows/never-collide.yml`, installed when absent, runs it on
  every pull request.
- `docs/index.md`: the content for `claude-repo.com/never-collide`.
- `examples/wecarerehab/`: the first adopter's ownership map and Claude Code
  settings, anonymised.

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
