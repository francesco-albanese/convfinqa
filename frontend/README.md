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

Routes, theme tokens, shadcn/ui, Vitest, and Playwright land in subsequent
foundation tasks (see beads epic `convfinqa-0hu`).
