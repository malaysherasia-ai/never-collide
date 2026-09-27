# Path ownership

Static boundaries. Claim dynamically within them before each task.

## Antigravity (UI)

- `src/components/**`
- `src/styles/**`
- `design-tokens/**`
- page-level layout: `src/app/**/page.tsx`, `src/app/**/layout.tsx`

## Claude Code (logic)

- `src/lib/**`
- `src/app/api/**`
- `supabase/**`
- `tests/**`
- configuration and CI: `*.config.*`, `.github/**`, `package.json`

## Shared by contract

- `src/types/**`: components consume typed props; logic never lives in a UI
  file. Either side may claim a file here, narrowly, and must `ncl note` any
  change to an exported type.

## Enforced by the linter

UI cannot import `src/lib/db`; lib cannot import components. ESLint
`no-restricted-imports` carries that rule, so it holds even when nobody is
looking.
