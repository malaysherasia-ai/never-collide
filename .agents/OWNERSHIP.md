# File ownership

This repository currently has one implementation surface. Claim the exact
files or directories you will edit with `ncl` before starting. Ownership
boundaries for adopter repositories belong in their own `.agents/OWNERSHIP.md`
and should name each tool plus the paths it owns.

Suggested adopter boundaries from the project brief:

- UI agent: `src/components/**`, `src/styles/**`, `design-tokens/**`, and
  page-level layout in `src/app/**/page.tsx`.
- Logic agent: `src/lib/**`, `src/app/api/**`, `supabase/**`, `tests/**`,
  configuration, and CI.
- Shared by contract: `src/types/**`.

These are starter boundaries. Claims are checked by the hooks; the
boundaries themselves are a convention, enforced by a linter such as
`dependency-cruiser` or ESLint `no-restricted-imports` if you add one.
