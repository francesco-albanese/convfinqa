---
name: quality-gates
description: Frontend quality gates — biome ci + tsc -b + vitest + vite build, all green before declaring done
paths:
  - frontend/**
last_validated: 2026-05-15
pillar: true
related:
  - package-manager
  - lefthook-pre-commit-must-chain-vite-build-pnpm
---

# Frontend quality gates

## The contract

Before declaring ANY frontend task complete (closing a `bd` issue, opening a PR, replying "done"), run all four gates from `frontend/` and confirm each exits 0:

```bash
pnpm exec biome ci    # read-only lint+format, CI parity
pnpm exec tsc -b      # full project-ref typecheck
pnpm test             # vitest run (one-shot, not watch)
pnpm exec vite build  # vite-only build; tsc already ran
```

A passing lefthook pre-commit is NOT a substitute. Lefthook only fires on commit; verify BEFORE committing so reports match reality.

## Why `biome ci`, not `biome check`

- `biome check --write` mutates files and passes if it can auto-fix — masks drift.
- `biome ci` is read-only and fails on the same drift. CI runs this (`.github/workflows/frontend.yml`). Match it locally.

## Why `vite build`, not `pnpm build`

`pnpm build` is `tsc -b && vite build`. The standalone `tsc -b` step above already covers types — `pnpm build` re-runs tsc for nothing. Call `vite build` directly.

## When a gate fails

Fix the root cause; don't bypass.
- Biome violations → fix the code, NOT add `// biome-ignore` unless the rule is genuinely wrong here.
- Type errors → fix types, NOT cast to `any`.
- Failing tests → fix the code, or fix the test if it asserts the wrong thing. NEVER delete a failing test to make the gate green.
- Build errors → fix imports/config, NOT skip routes or drop deps.

`--no-verify` on commits is forbidden unless the user explicitly asks for it. If lefthook blocks, fix and recommit.

## `routeTree.gen.ts` — generated but committed

Produced by `@tanstack/router-plugin` from `src/routes/`. Committed so `tsc -b` and IDEs work on clean clones.

- NEVER hand-edit. Plugin regenerates on every `vite build` / `vite dev`.
- After adding/renaming/deleting under `src/routes/`, the regenerated file is auto-staged by the lefthook build step.
- Excluded from Biome (`biome.json` `files.includes` has `"!src/routeTree.gen.ts"`). Don't remove that exclusion.

## Lefthook chains build → test, never parallel

`@tanstack/router-plugin` rewrites `routeTree.gen.ts` during every build. If build and test ran in parallel, vitest intermittently read a half-written route tree → flaky `authedShell.test.tsx` / `app.test.tsx`. Keep `build-and-test` as one piped command.

## Lint commands — quick reference

| Command | Use for |
| --- | --- |
| `pnpm format` | format only, no lint |
| `pnpm lint` | lint only, auto-fix |
| `pnpm check` | both, auto-fix (default while iterating) |
| `pnpm ci` | both, read-only, CI parity (the "done" check) |
