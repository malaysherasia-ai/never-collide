# Example: a multi-location clinic site

The first adopter, anonymised. A Next.js site on Vercel with Supabase behind
it, one repository, two tools every day:

- **Antigravity** owns the UI: components, styles, design tokens, page
  layout.
- **Claude Code** owns the logic: `src/lib`, API routes, database, tests,
  configuration and CI.
- `src/types` is shared by contract: components consume typed props; logic
  never lives in a UI file.

What is in this folder:

- `OWNERSHIP.md`: the `.agents/OWNERSHIP.md` used in that repo.
- `settings.json`: the `.claude/settings.json` fragment that gives Claude
  Code its identity and registers the edit hook. The installer writes it.

Antigravity gets its identity from the environment it is launched with:

```sh
export AGENT_NAME=antigravity AGENT_TOOL=antigravity
```

Task branches are `claude/WCR-42` and `antigravity/WCR-42`. A day in the
ledger looks like this:

```
09:02  antigravity  claimed      WCR-42  src/app/locations/**       Add per-location hero
09:05  claude       claimed      WCR-43  src/lib/locations/**       Location data loader
10:40  claude       in_progress  WCR-43  src/lib/locations/**       Schema changed: LocationHero props
11:15  antigravity  requested    WCR-43 -> claude  need src/types/location.ts for the hero props
11:20  claude       handoff      WCR-43 -> antigravity  src/types/location.ts is yours; props are final
13:30  claude       done         WCR-43  PR 118
14:05  claude       tested       WCR-43  CI green, preview checked at 390/768/1440
16:10  antigravity  done         WCR-42  PR 119
```

The first week ran with every hook in warn mode. Deny came after.
