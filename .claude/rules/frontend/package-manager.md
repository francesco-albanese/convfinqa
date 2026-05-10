# Frontend package manager — pnpm ONLY

## Hard rule

**Always use pnpm. Never npm, yarn, bun, deno, or any other package manager.**

This applies to every frontend workspace in this repo (`frontend/` and any future siblings). It applies whether you are scaffolding from scratch, adding dependencies, running scripts, or writing CI / Dockerfiles / Makefile targets.

- `pnpm install` — never `npm install` / `yarn` / `bun install`
- `pnpm add <pkg>` — never `npm i` / `bun add`
- `pnpm exec <bin>` or `pnpm dlx <bin>` — never `npx` / `bunx`
- `pnpm-lock.yaml` is the only lockfile that ships. If you see `bun.lock`, `package-lock.json`, or `yarn.lock`, that is a bug — delete it and regenerate via `pnpm install`.

## Version

- pnpm >= 10.28.0
- Pin via `packageManager: "pnpm@10.x.y"` in `package.json` so corepack and CI agree.

## Supply-chain hardening (mandatory)

`frontend/pnpm-workspace.yaml` MUST include:

```yaml
packages:
  - .
minimumReleaseAge: 10080      # 1 week, in minutes — blocks freshly-published versions (supply-chain attack window)
blockExoticSubdeps: true      # block git/http/file: sub-dependencies sneaking in via transitive deps
```

`minimumReleaseAge` can equivalently live in `.npmrc` as `minimum-release-age=10080`; the workspace YAML is preferred (single source of truth, version-controlled, applies to the whole workspace).

## Scaffolding new workspaces

Do **NOT** run `bun create vite`, `npm create vite`, or any non-pnpm scaffolder. Use `pnpm create vite` and immediately delete any lockfile other than `pnpm-lock.yaml`.

## Why this rule exists

The convfinqa-0hu epic was originally scaffolded with Bun because the global rule's `paths:` glob (`**/package.json`, `**/.npmrc`, `**/pnpm-workspace.yaml`) didn't attach when the PRD was written — those files didn't exist yet. The PRD authored "Package manager: Bun" and downstream slices propagated it. This local rule has no `paths:` filter so it ALWAYS attaches in this repo, regardless of what files exist.

## CI

GitHub Actions: use `pnpm/action-setup@v4` (reads the `packageManager` field). Never `oven-sh/setup-bun` or `actions/setup-node` with npm caching.
