# convfinqa — agent map

Router file. Walk down to the area you're touching.

## Knowledge system

- **Standing policy** → [`.claude/rules/`](.claude/rules/README.md) (scoped by `paths:` front-matter, lint-validated)
- **Episodic gotchas** → `bd memories <keyword>` (index at `.claude/memory-index.json`)
- **Validator** → [`scripts/lint_knowledge.py`](scripts/lint_knowledge.py) (lefthook pre-commit + CI)

## Walk-up tree

| Working on… | Start here |
|---|---|
| Backend Python | [`backend/src/convfinqa/README.md`](backend/src/convfinqa/README.md) |
| Frontend | [`frontend/README.md`](frontend/README.md) |
| Infrastructure | [`terraform/README.md`](terraform/README.md) |
| AWS architecture | [`docs/aws-architecture.html`](docs/aws-architecture.html) |
| Hexagonal layering | [`docs/hexagonal.md`](docs/hexagonal.md) |
| Running locally | [`docs/how-to-run-the-app.md`](docs/how-to-run-the-app.md) |

## Issue tracking — `bd` only

```bash
bd ready              # find available work
bd update <id> --claim
bd close <id>
bd remember "…"       # save a gotcha as a memory
```

Do NOT use TodoWrite, TaskCreate, or markdown TODO lists. Run `bd prime` for full command reference.

## Session close

Before saying "done": `git pull --rebase && bd dolt push && git push`. `git status` must show "up to date with origin". If push fails, resolve and retry.

## Build & test

`make sync` (deps) · `make up` (full stack) · `make test` · `make down`. Full walkthrough in [`docs/how-to-run-the-app.md`](docs/how-to-run-the-app.md).

## House rules

- The user wants **guidance on syntax, core logic, and best practices**. Do NOT implement code unless asked explicitly.
- Don't write WHAT comments. Only WHY, and only when non-obvious.
- Never `--no-verify` on commits unless explicitly requested.
