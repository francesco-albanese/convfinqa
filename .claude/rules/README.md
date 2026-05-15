---
description: Catalogue of standing rules — what each rule covers and which paths it attaches to
last_validated: 2026-05-15
related:
  - CLAUDE.md
---

# `.claude/rules/` — rule catalogue

Rules are **standing policy**: durable, scoped via `paths:` front-matter, lint-validated. Episodic gotchas live as `bd memories` (see `bd memories <keyword>`), not here.

When a memory has been hit on a second ticket AND applies to more than one file, promote it to a rule with `pillar: false`. Promote to `pillar: true` only after the policy has survived a re-review.

## Pillars (deletion requires `Allow-pillar-deletion: <slug>` trailer)

| Rule | Paths | Why pillar |
|---|---|---|
| [code-quality](python/code-quality.md) | `backend/src/**`, `backend/tests/**`, `scripts/**` | Cross-cutting Python conventions: naming, comments, imports, ruff exclusions |
| [hexagonal](python/hexagonal.md) | `backend/src/convfinqa/**` | Layering invariants are load-bearing — violation = architectural drift |
| [tests](python/tests.md) | `backend/tests/**` | Async + alembic test infra invariants applied to every new test |
| [quality-gates](frontend/quality-gates.md) | `frontend/**` | Defines "done" for frontend work |
| [csv-injection](frontend/csv-injection.md) | `frontend/src/lib/transforms/**`, `frontend/src/components/**` | Security — every CSV-emitting surface must honour this |
| [package-manager](frontend/package-manager.md) | `frontend/**` | pnpm-only, supply-chain hardening |
| [markdown-streaming](frontend/markdown-streaming.md) | `frontend/src/components/**`, `frontend/src/styles/**` | Streamdown over react-markdown is the architectural choice |
| [aws-architecture](infrastructure/aws-architecture.md) | `terraform/**`, `backend/src/convfinqa/adapters/persistence/**`, `backend/src/convfinqa/adapters/auth/**` | Cost-floor + same-origin-cookies invariants |

## Non-pillar rules

| Rule | Paths | Scope |
|---|---|---|
| [litellm](python/litellm.md) | `backend/src/convfinqa/adapters/llm/**` | Protocol-typed boundary pattern for one adapter |
| [logging](python/logging.md) | `backend/src/**` | `get_logger` + LogRecord reserved-name collisions |
| [ui-prototypes](frontend/ui-prototypes.md) | `frontend/src/components/**`, `frontend/src/routes/**`, `frontend/src/styles/**` | Visual mockups in `example-html/` are the design source of truth |

## Schema

Every rule MUST carry front-matter:

```yaml
---
name: <kebab-slug>           # unique, lint-checked against memory-index for collisions
description: <one line>      # used by humans grepping the catalogue
paths:                       # globs of files the rule attaches to (mandatory, must match ≥1 file)
  - some/path/**
last_validated: YYYY-MM-DD   # ISO date; future decay check
pillar: true|false           # pillar=true rules can't be deleted without trailer override
related:                     # array of memory slugs OR repo-relative file paths
  - convfinqa-some-memory-slug
  - frontend/README.md
---
```

`scripts/lint_knowledge.py` enforces the schema, path existence, link integrity, and dedup against `.claude/memory-index.json`. See [the validator](../../scripts/lint_knowledge.py) for the exact checks.

## Memory index

`.claude/memory-index.json` is regenerated from `bd memories --json` by the lefthook pre-commit step. Don't hand-edit; rerun `bd memories --json > .claude/memory-index.json` if needed.
