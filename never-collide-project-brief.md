# never-collide — Project Brief

Multi-agent coordination for one shared repo. Claude Code, Antigravity, Codex,
Gemini CLI and Copilot working on the same codebase in parallel, without
stepping on each other.

Second member of the `never-*` family after never-again. Same install pattern,
same hook plumbing, same site.

Status: **decided, not started** (2026-09-27). This brief is the source of
truth for the claude.ai Project. Update it as decisions land.

---

## 1. The problem

One repo. Two or more AI coding tools, each in its own session, each pushing to
GitHub, site deployed on Vercel. Today nothing tells Claude Code that
Antigravity is halfway through the location page it is about to rewrite.

Git worktree isolation (Parallel Code and similar) solves this by keeping
agents on separate files. That is not our case: Antigravity owns UI, Claude
Code owns logic, and they meet on the same page files daily. We need agents
that *share* a repo and coordinate, not agents that are kept apart.

What we want, in the user's words: a drop-box where every tool logs before it
starts, checks whether another tool is working on or planning to work on the
same page, code or feature, and logs completed time and tested time when done.
Works for two tools, works for five. Nothing is missed, everyone stays in sync.

## 2. Decisions made

| Decision | Choice | Why |
|---|---|---|
| Name | **never-collide** | Sibling of never-again: one prefix, one promise style. Outcome-phrased ("what you'll never experience again"), not mechanism-phrased. "Collision" is the word developers already use. Namespace is clean on GitHub. |
| Rejected names | call-dibs (mechanism, not outcome); parallel-coding (collides with johannesjo's *Parallel Code*, 362 stars, same audience); never-mixup (means confusion, not collision — reserved, see §9) | |
| GitHub | `malaysherasia-ai/never-collide` | No `claude-` prefix. Safer on trademark, and the footer disclaimer is easier to stand behind. |
| Site | `claude-repo.com/never-collide` | Same hub as never-again. |
| CLI | **`ncl`** | `nc` is netcat on every Unix box; do not shadow it. Three letters, no collision. |
| Plain-language word | "dibs" | Docs and prompts say "call dibs before you touch a file", the way never-again says "say never again after a fix". |
| Runtime | bash + Python 3.7+, git. **No Node, no npm, no husky.** | Matches never-again exactly. Anyone with never-again installed adds this in the same two minutes. Shared hook dispatcher. |
| Enforcement | Claude Code `PreToolUse` hook + git `pre-commit` hook | Proven in never-again. Hook runs before an edit in Claude Code, and again before any tool commits. A `deny` runs before every permission mode. |
| Coordination store | Orphan branch `agents/ledger`, one append-only `ledger.jsonl` | No external service. Git push atomicity is the lock. Append-only means rebases never conflict. |
| Licence | MIT, free, no paid tier, no telemetry | Same as never-again. |
| Common language | `AGENTS.md` at repo root; `CLAUDE.md` contains `@AGENTS.md` | AGENTS.md is read natively by Codex, Gemini CLI, Copilot, Cursor and Antigravity. One file, every tool. |
| Rename never-again | `claude-never-again` → `malaysherasia-ai/never-again` | Do this first; see §8 step 1. |

## 3. Architecture — three layers

### Layer 1 — Static ownership (prevents most conflicts before any locking)

`.agents/OWNERSHIP.md`, mirrored in `CODEOWNERS`. For the first adopter:

- **Antigravity**: `src/components/**`, `src/styles/**`, `design-tokens/**`,
  page-level layout in `src/app/**/page.tsx`
- **Claude Code**: `src/lib/**`, `src/app/api/**`, `supabase/**`, `tests/**`,
  config, CI
- **Shared by contract only**: `src/types/**`. Components consume typed props;
  logic never lives in a UI file.

Machine-enforced with `dependency-cruiser` or ESLint `no-restricted-imports`:
UI cannot import `src/lib/db`; lib cannot import components. A boundary the
linter enforces is one agents cannot drift across.

### Layer 2 — Dynamic claims (the "log before you start" part)

Orphan branch `agents/ledger` holding `ledger.jsonl`, append-only, one JSON
object per line. Every tool runs the same commands:

```
ncl claim   --task WCR-42 --paths "src/app/locations/**" --intent "Add per-location hero"
ncl note    --task WCR-42 "Schema changed: LocationHero props"
ncl done    --task WCR-42 --pr 118
ncl tested  --task WCR-42 --evidence "CI green, preview checked 390px"
ncl release --task WCR-42
ncl handoff --task WCR-42 --to antigravity --paths "src/components/LocationHero.tsx"
ncl status                       # who holds what, right now
ncl whoami                       # prints AGENT_NAME or fails
```

`claim` fetches the ledger, checks glob overlap against every active claim by
*other* agents, refuses on overlap, otherwise appends and pushes. If two agents
claim the same path within seconds, the second push is rejected, the script
rebases, re-runs the overlap check and fails cleanly. That is the lock.

Record shape:

```json
{"id":"WCR-42","agent":"antigravity","tool":"antigravity/1.4","task":"WCR-42",
 "paths":["src/app/locations/**"],"status":"claimed",
 "intent":"Add per-location hero","branch":"antigravity/WCR-42",
 "ts":"2026-09-27T14:02:11Z","ttl_h":4}
```

Statuses: `claimed → in_progress → done → tested → released`, plus `expired`
and `handoff`. `done` records commit and PR. `tested` records CI result and
preview URL. Timestamps ISO-8601 UTC; `ncl status` prints Toronto time for
humans. Claims carry a TTL so a crashed session never blocks anyone forever.

### Layer 3 — Enforcement (because agents forget)

- Each tool sets `AGENT_NAME` in its own config (Claude Code settings,
  Antigravity env, etc.). Unset → `ncl whoami` fails → hooks refuse.
- **PreToolUse hook** (Claude Code): before Edit/Write, the target path must be
  covered by an active claim held by this agent. Warn first, promote to deny
  by a human command — same ask→deny ladder as never-again.
- **git pre-commit hook**: every changed file must be covered by an active claim
  by this agent. Runs from any tool or terminal.
- **GitHub Action on PR**: diff paths must match a claim on the PR's branch
  prefix (`claude/*`, `antigravity/*`, `codex/*`); merge blocked until ledger
  shows `done`; `tested` accepted only with CI green and a Vercel preview URL.
- Nobody commits to `main`. Branch-per-agent-per-task → PR → preview → merge.
  Real merge conflicts surface at PR time where a human sees them.

## 4. The ritual (goes in AGENTS.md, under ~150 lines)

1. **Identity** — run `ncl whoami`; if unset, stop.
2. **Sync** — `ncl status` before planning any edit.
3. **Claim** — `ncl claim` for the paths you will touch. Refused? Post
   `ncl handoff` describing what you need and stop. Never work around it.
4. **Work** — on your own branch. `ncl note` on any interface change another
   agent depends on.
5. **Done** — commit, open PR, `ncl done`.
6. **Tested** — CI green, preview checked at 390 / 768 / 1440, `ncl tested`.
7. **Release** — after merge, `ncl release`.

Definition of Done and coding standards live beside the ritual. Full spec in
`.agents/PROTOCOL.md`.

## 5. Failure modes and the answer

| Failure | Answer |
|---|---|
| Two agents genuinely need the same file | Script refuses; second agent records `handoff`; sequential by design |
| Stale claim from a crashed session | TTL expiry, visible in `ncl status` |
| Agent bypasses the script | PreToolUse hook + pre-commit hook + PR check; it cannot merge |
| Ledger merge conflict | Append-only JSONL; rebase never produces a content conflict |
| Adding a new tool (Gemini, Copilot, Codex) | One line in `OWNERSHIP.md` and an `AGENT_NAME` |

## 6. Repo layout (mirrors never-again)

```
never-collide/
  install.sh               # git clone --depth 1 … && bash never-collide/install.sh .
  AGENTS.md                # the protocol, dogfooded on its own repo
  CLAUDE.md                # @AGENTS.md
  .claude/never-collide/
    ncl                    # Python CLI
    hooks/                 # PreToolUse dispatcher, pre-commit, GitHub Action
    SKILL.md               # Claude Code skill
  templates/               # AGENTS.md, OWNERSHIP.md, PROTOCOL.md starters
  docs/                    # → claude-repo.com/never-collide
  examples/wecarerehab/    # first real adopter, anonymised
  LICENSE                  # MIT
```

Installer behaviour, same as never-again: adds a marked block to `CLAUDE.md`
instead of overwriting; leaves an existing `AGENTS.md` alone; gitignores local
state; re-runnable for upgrades.

## 7. Site and hub

- Nav mirrors never-again: Install · For you · Numbers · Why · Compare · FAQ ·
  Docs · GitHub. Live GitHub clone counter, `/proof` page, MIT, "not
  affiliated with Anthropic" footer.
- Tagline: **"parallel coding on one repo, without the collisions."** Keeps
  the search term without borrowing anyone's name.
- Compare table: *branch-per-agent alone* vs *CODEOWNERS alone* vs
  *Parallel Code (worktree isolation)* vs *never-collide*. Honest line on
  Parallel Code: "use both — it isolates tasks; we coordinate the ones that
  can't be isolated."
- `claude-repo.com/` becomes a short hub index: never-again ("mistakes that
  can't repeat"), never-collide ("agents that can't step on each other"),
  clone counts. Since the site is already Next.js on Vercel, one repo with
  `app/never-again` and `app/never-collide` routes, not rewrites to separate
  deployments.
- Two URLs served raw for tools: `/never-collide/AGENTS.md` and
  `/never-collide/PROTOCOL.md`.

## 8. Next steps — in order

1. **Rename never-again** on GitHub: `claude-never-again` →
   `malaysherasia-ai/never-again`. Same day: change the install line on the
   site to `bash never-again/install.sh .`; grep the repo for
   `claude-never-again` (na upgrade, daily update check, traffic-API counter,
   badges) and replace; confirm Vercel Git integration still deploys. Never
   create a new repo at the old name — that kills the redirect.
2. Create `malaysherasia-ai/never-collide`, MIT, empty README with the tagline.
3. Scaffold: `install.sh`, `ncl` (Python), PreToolUse + pre-commit hooks,
   GitHub Action, `SKILL.md`, templates. Dogfood it on its own repo from
   commit one.
4. Install into the We Care Rehab repo. Write its `OWNERSHIP.md` (§3, Layer 1)
   and `AGENT_NAME` for Claude Code and Antigravity. Run a real week with both
   tools before promoting any hook from warn to deny.
5. Docs page + hub index on claude-repo.com.
6. Add Codex / Gemini CLI / Copilot support entries once a second tool beyond
   Antigravity is actually used.

## 9. Reserved: never-mixup

Third family member, not started. Client and environment isolation for agents
working across many repos: stop an agent pulling one clinic's env vars into
another clinic's repo, deploying client A's Resend key to client B, or pasting
one location's phone number into another's page. Build it when the second
client site starts. Reserve the GitHub name now.

## 10. Hard rules for this project

- Do not tell me something works until you have run it.
- No Node dependency in the tool. bash, Python 3.7+, git only.
- Never shadow an existing system command (`nc`).
- Nothing leaves the machine except the release check, same as never-again.
- Surface what is still outstanding in your final summary, not buried in a file.

## Sources

- never-again: https://www.claude-repo.com/never-again ·
  https://github.com/malaysherasia-ai/claude-never-again
- Parallel Code (johannesjo): https://github.com/dscafati/parallel-code
- IFScale, instruction-following at scale (cited by never-again):
  https://arxiv.org/abs/2507.11538
