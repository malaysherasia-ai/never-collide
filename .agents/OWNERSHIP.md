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

These are starter examples, not enforced rules in version 0.1.0.