# ConvFinQA frontend

Vite + React 19 + TypeScript SPA. Talks to the FastAPI backend at `/v1/*`.

## Develop

```bash
bun install       # one-time
bun run dev       # http://localhost:5173
bun run build     # tsc -b && vite build → dist/
bun run lint
```

Routes, theme tokens, shadcn/ui, Vitest, and Playwright land in subsequent
foundation tasks (see beads epic `convfinqa-0hu`).
