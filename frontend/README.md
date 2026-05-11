# ConvFinQA frontend

Vite + React 19 + TypeScript SPA. Talks to the FastAPI backend at `/v1/*`.

## Develop

```bash
pnpm install --frozen-lockfile   # one-time
pnpm dev                         # http://localhost:5173
pnpm build                       # tsc -b && vite build → dist/
pnpm lint
```

Package manager: pnpm (>= 10.28). Supply-chain hardening (1-week minimum
release age, exotic-subdep block) lives in `pnpm-workspace.yaml`.

## `src/routeTree.gen.ts` is committed (and that's intentional)

TanStack Router's file-based routing generates `src/routeTree.gen.ts` from
the files under `src/routes/`. We commit it so:

- `tsc -b` works on a clean clone without first running Vite,
- IDE "go to definition" works immediately,
- CI doesn't need a separate generate step before typecheck.

The file is regenerated automatically by `pnpm exec vite build` (via the
`@tanstack/router-plugin`) and the pre-commit `build` hook re-stages it if
your route changes left it stale — so you shouldn't need to touch it
manually. It is excluded from Biome (see `biome.json`) and you should NOT
hand-edit it.

If you ever need to regenerate it explicitly without a full build, run
`pnpm dev` once — the plugin watches `src/routes/**` and writes the file.

Routes, theme tokens, shadcn/ui, Vitest, and Playwright land in subsequent
foundation tasks (see beads epic `convfinqa-0hu`).
