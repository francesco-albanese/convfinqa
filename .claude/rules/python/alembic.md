# Alembic migration rules

## Revision string length ≤ 32 chars

`alembic_version.version_num` is `VARCHAR(32)`. Revision strings longer than 32 chars
cause `StringDataRightTruncationError` when alembic writes the version after upgrade.

Keep revision strings to 32 characters or fewer. The filename can be more descriptive;
only the `revision:` variable inside the file must fit.

```python
# WRONG (36 chars)
revision: str = "0007_add_cache_ratelimit_idempotency"

# RIGHT (32 chars)
revision: str = "0007_cache_ratelimit_idempotency"
```

## Postgres partial index predicates must be IMMUTABLE

`now()` and `current_timestamp` are `STABLE`, not `IMMUTABLE`. Postgres rejects
partial index predicates that call STABLE functions:

```sql
-- WRONG — CREATE INDEX fails
CREATE INDEX ON output_cache (prompt_hash, model) WHERE expires_at > now();

-- RIGHT — plain index; query WHERE clause does the filtering
CREATE INDEX ix_output_cache_expires_at ON output_cache (expires_at);
```

In alembic: use `op.create_index("ix_...", "table", ["expires_at"])` without a
`postgresql_where` argument. The read-side query `WHERE expires_at > now()` still
hits the index via a range scan.
