---
description: Adapters — port implementations (sqlalchemy, litellm, cognito, cache). Imports domain only.
last_validated: 2026-05-15
related:
  - ../README.md
  - ../../../../.claude/rules/python/hexagonal.md
  - ../../../../.claude/rules/python/litellm.md
  - asyncpg-raw-sql-pattern-use-cast-param-as
  - asyncpg-pytest-asyncio-cannot-perform-operation-another-oper
  - alembic-revision-strings-must-be-32-chars-or
  - postgres-partial-index-predicates-must-use-immutable-functio
  - sqlalchemy-text-with-postgresql-type-cast-syntax-e
  - alembic-migrations-with-generated-tsvector-columns-inline-th
  - cognito-access-tokens-no-aud-claim-use-client
---

# `adapters/` — port implementations

## Hard rule

Adapters import `convfinqa.domain.*` ONLY. NEVER `convfinqa.application.*` or `convfinqa.entrypoints.*`. Adapters are constructed in `container.py`; never `new` an adapter inside another adapter, a use case, or a route.

```bash
grep -rE 'convfinqa\.application|convfinqa\.entrypoints' . && echo VIOLATION
```

## Persistence (`persistence/sqlalchemy/`)

**Engine config (Aurora Serverless v2 friendly)** — MUST set: `pool_recycle=300`, `pool_size=2`, `max_overflow=2`, `pool_pre_ping=True`. Without these Aurora never pauses.

**Raw SQL with UUIDs**: use `CAST(:id AS uuid)`, NOT `:id::uuid`. The `::` cast syntax conflicts with asyncpg's parameter rendering (same for `:year_min::int` → `CAST(:year_min AS int)`).

**Alembic**:
- Revision strings ≤ 32 chars (`alembic_version.version_num` is `VARCHAR(32)`).
- Partial-index predicates must use IMMUTABLE functions only (`now()` is STABLE → reject). Use a plain B-tree index on `expires_at`; the runtime `WHERE` clause does the filtering.
- For generated tsvector columns, inline the `to_tsvector(...)` expression as a string DIRECTLY in the migration. Do NOT import a shared constant from ORM models — migrations must be frozen snapshots.

## LLM (`llm/litellm_adapter.py`)

See [`litellm.md`](../../../../.claude/rules/python/litellm.md) for the Protocol-typed boundary pattern.

## Auth (`auth/cognito_jwks.py`)

Cognito **access tokens** have no `aud` claim — use `client_id`. The `email` field is absent (only in ID tokens). Always validate `token_use == 'access'` to reject ID tokens. Adapter takes an injectable `fetch_jwks` callable for testability.
