---
name: package-manager
description: Frontend uses pnpm exclusively, with supply-chain hardening (minimumReleaseAge + blockExoticSubdeps)
paths:
  - frontend/**
last_validated: 2026-05-15
pillar: true
related:
  - frontend-package-manager-always-pnpm-never-bun-npm
  - shadcn-cli-v4-7-monorepo-gate-resolved-2026
---

# Frontend package manager — pnpm ONLY

## Hard rule

**Always pnpm. Never npm, yarn, bun, deno.** Applies to every frontend workspace, every script, Dockerfile, CI, Makefile.

- `pnpm install` — never `npm install` / `yarn` / `bun install`
- `pnpm add <pkg>` — never `npm i` / `bun add`
- `pnpm exec <bin>` or `pnpm dlx <bin>` — never `npx` / `bunx`
- `pnpm-lock.yaml` is the only lockfile. Any other lockfile is a bug → delete + `pnpm install`.

## Version

- pnpm >= 10.28.0
- Pin via `packageManager: "pnpm@10.x.y"` in `package.json` so corepack + CI agree.

## Supply-chain hardening (mandatory)

`frontend/pnpm-workspace.yaml` MUST include:

```yaml
minimumReleaseAge: 10080      # 1 week, in minutes — blocks fresh versions (supply-chain attack window)
blockExoticSubdeps: true      # block git/http/file: sub-deps sneaking via transitive deps
```

OMIT the `packages:` key under the current single-package layout. shadcn CLI v4.7's "monorepo root" gate refuses every command when any `packages:` key is present — even `packages: [.]`. The key is functionally inert here (pnpm treats the project as a workspace member by default), so dropping it unblocks `pnpm dlx shadcn@latest add <component>`.

Re-add `packages:` only when a real multi-package layout is introduced (e.g. `apps/web` + `packages/ui`); then invoke shadcn with `-c apps/web`.

## Scaffolding

NEVER `bun create vite` / `npm create vite`. Use `pnpm create vite` and immediately delete any lockfile other than `pnpm-lock.yaml`.

## CI

GitHub Actions: `pnpm/action-setup@v4` (reads `packageManager`). Never `oven-sh/setup-bun` or `actions/setup-node` with npm caching.
