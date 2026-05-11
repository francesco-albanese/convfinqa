# Frontend quality gates — run before declaring a task done

## The contract

Before declaring ANY frontend task complete (closing a `bd` issue, opening a PR, replying "done"), run all four gates from `frontend/` and confirm each exits 0:

```bash
pnpm exec biome ci   # read-only lint+format, fails on drift (CI parity)
pnpm exec tsc -b     # full project-ref typecheck
pnpm test            # vitest run (one-shot, not watch)
pnpm exec vite build # vite-only build; tsc already ran above
```

A passing lefthook pre-commit is NOT a substitute. Lefthook only fires on commit; verify BEFORE committing so the agent's report matches reality.

## Why `biome ci`, not `biome check`

- `biome check --write` mutates files and passes if it can auto-fix — masks drift.
- `biome ci` is read-only and fails on the same drift. This is what GitHub Actions runs (`.github/workflows/frontend.yml` → `frontend-unit` job). Run the same thing locally.

## Why `vite build`, not `pnpm build`

`pnpm build` is `tsc -b && vite build`. The standalone `tsc -b` step above already covers types — invoking `pnpm build` re-runs tsc for nothing. Call `vite build` directly to skip the duplicate.

## When a gate fails

Fix the root cause; do NOT bypass. Specifically:

- Biome violations → fix the code, NOT add per-file `// biome-ignore` unless the rule is genuinely wrong for that file.
- Type errors → fix types, NOT cast to `any` or sprinkle `as unknown as`.
- Failing tests → fix the code OR fix the test if the test is asserting the wrong thing. NEVER delete a failing test to make the gate green.
- Build errors → fix imports/config, NOT skip routes or drop dependencies.

`--no-verify` on commits is FORBIDDEN unless the user explicitly asks for it (per repo CLAUDE.md). If lefthook blocks a commit, fix the issue and recommit.

## Pre-commit hook coverage (defense-in-depth)

`lefthook.yml` runs all four gates in parallel on commit (biome write-mode + tsc + vitest + vite build). If a commit makes it through the hook, the gates were green at hook time. The rule above is the agent's pre-commit responsibility — get green before the hook fires, so the hook is a confirmation, not a discovery.

## `routeTree.gen.ts` — generated but committed

`frontend/src/routeTree.gen.ts` is produced by the `@tanstack/router-plugin` from the files in `src/routes/`. It is **committed to git** (decision documented in `frontend/README.md`) so `tsc -b` and IDEs work on a clean clone.

Rules when touching routes:

- NEVER hand-edit `routeTree.gen.ts`. The plugin regenerates it on every `vite build` / `vite dev`.
- After adding, renaming, or deleting anything under `src/routes/`, ensure the regenerated file is committed alongside. The pre-commit `build` hook re-runs `vite build` (with `stage_fixed: true`), so if you've staged a route change, the regenerated `routeTree.gen.ts` will be auto-restaged into the same commit. You do not need to regenerate manually unless the build hook is bypassed.
- It is excluded from Biome (`biome.json` `files.includes` has `"!src/routeTree.gen.ts"`). Do not remove that exclusion — formatting it creates churn that the next regen erases.

## `.vite/` is per-machine cache

Vite's dep pre-bundling cache (`frontend/.vite/deps/_metadata.json`, etc.) is gitignored. If you see it in `git status`, that gitignore entry is missing — restore it rather than committing the cache.

## Lint vs check vs ci — quick reference

| Command | Mode | Use for |
| --- | --- | --- |
| `pnpm format` | `biome format --write` | format only, no lint |
| `pnpm lint` | `biome lint --write` | lint only, auto-fix |
| `pnpm check` | `biome check --write` | both, auto-fix (default while iterating) |
| `pnpm ci` | `biome ci` | both, read-only, CI parity (use for the "done" check) |
