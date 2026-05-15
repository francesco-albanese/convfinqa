# asyncpg UUID casting in raw SQL

## The trap

asyncpg uses `$1, $2, ...` placeholders internally. When SQLAlchemy's `text()` renders `:param::uuid` (PostgreSQL cast syntax), the `::` conflicts with parameter binding and produces:

```
ProgrammingError: syntax error at or near ":"
[SQL: INSERT INTO t (id) VALUES (:id::uuid)]
```

## The fix

Always use the SQL standard `CAST()` syntax in `text()` queries:

```python
# WRONG
text("INSERT INTO users (id) VALUES (:id::uuid)")

# RIGHT  
text("INSERT INTO users (id) VALUES (CAST(:id AS uuid))")
```

This applies anywhere a UUID-typed column must receive a Python string in a raw `text()` call — inserts, updates, WHERE clauses.

## Why it works

`CAST(:id AS uuid)` keeps `:id` as a clean SQLAlchemy-style parameter placeholder. asyncpg then receives the value as a text parameter and PostgreSQL does the implicit `TEXT → UUID` cast. The `::uuid` form embeds the cast directly in the parameter token, breaking asyncpg's parameter rendering.
