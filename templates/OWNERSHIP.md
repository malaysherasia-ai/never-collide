# Path ownership

Assign paths to the tools that own them, then claim those paths dynamically
before each task. Adjust these examples for the repository:

- UI agent: `src/components/**`, `src/styles/**`, `design-tokens/**`, and
  page-level layout in `src/app/**/page.tsx`.
- Logic agent: `src/lib/**`, `src/app/api/**`, `supabase/**`, `tests/**`,
  configuration, and CI.
- Shared by contract: `src/types/**`.

Claims are checked by the hooks. The boundaries themselves are a convention;
enforce them with `dependency-cruiser` or ESLint `no-restricted-imports`.
