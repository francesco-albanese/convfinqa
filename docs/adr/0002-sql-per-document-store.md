# Per-document SQL store via ephemeral in-process SQLite + sql_query tool

Date: 25-05-2026

## Context

The LLM needs deterministic access to the pinned Document's Table cells. Inlining the full Table as JSON in the system prompt (today's approach) gives the model no way to *verify* it read the right cell, prevents cell-level citations (mockup E), and grows the prompt linearly with table size. ConvFinQA tables are tiny (median ~12 cells), but cell lookup must be deterministic and auditable.

## Decision

A single Lookup Tool, `sql_query(sql: str) → list[dict]`, exposed to the LLM. Each invocation builds a fresh in-process `:memory:` SQLite from the pinned Document's Table using the **Cells schema** — `cells(row_label TEXT, col_label TEXT, value_num REAL NULL, value_text TEXT NULL)` — runs the validated `SELECT`, and discards the connection. The Document JSON in Postgres is the single source of truth; the SQLite is a transient query target.

## Considered and rejected

- **Per-conversation cached SQLite in process memory** — premature optimisation given the ~1–3 ms rebuild for tables this small, and breaks across multi-instance ECS deployments (a follow-up request landing on a different container rebuilds anyway).
- **Materialised `cells` table in Aurora** — couples the LLM's SQL to Postgres dialect, adds a migration, and trades ECS-instance-locality for an Aurora write per Document import; the LLM cannot be allowed to issue arbitrary Postgres SQL against shared Aurora.
- **Higher-level `lookup_cell(row, col)` tool** — simpler schema for the LLM but loses your "tables in SQL" intent and forbids slightly more complex retrievals (multi-row queries, sums of line items).
- **DuckDB instead of SQLite** — better numeric SQL, but these tables are too tiny to benefit, and SQLite is in stdlib.

## Consequences

The SQL validator is now a security-critical component: SELECT-only enforcement, multi-statement reject, dangerous-keyword reject (`DROP`, `ATTACH`, `PRAGMA`, `INSERT/UPDATE/DELETE`), row-limit cap. Unit-tested separately from the agent loop. The Cells schema is identical across every Document, so the system prompt can teach the LLM one canonical query shape.
