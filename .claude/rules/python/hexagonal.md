# Hexagonal architecture invariants

These are HARD rules, not preferences. Audit every change against them.

## Layer dependency direction (one-way)

```
entrypoints  →  application  →  domain
adapters     →  domain (via ports)
container    →  adapters + application + domain (composition root)
```

- **`src/convfinqa/domain/`** — zero framework imports. Allowed: `dataclasses`, `datetime`, `enum`, `typing`, `collections.abc`. Forbidden: `fastapi`, `sqlalchemy`, `litellm`, `pydantic_settings`, `pythonjsonlogger`. Pydantic only for value objects (none today — frozen dataclasses).
- **`src/convfinqa/domain/ports/`** — every port is a `typing.Protocol` (NOT an ABC). Methods are async where I/O is involved.
- **`src/convfinqa/application/`** — imports only `convfinqa.domain.*`. Never `sqlalchemy`, `fastapi`, `litellm`.
- **`src/convfinqa/adapters/`** — implements ports. Adapters import `convfinqa.domain.*` only. NEVER import from `application/` or `entrypoints/`.
- **`src/convfinqa/entrypoints/`** — depends on `application/`, `domain/`, `container/`, FastAPI/Typer. Never imports from `adapters/` directly — composition happens in `container.py`.
- **`src/convfinqa/container.py`** — the only place where adapters are instantiated and wired into the use case.

## Quick audit commands

```bash
# Domain must not see frameworks
grep -rE "fastapi|sqlalchemy|litellm|pydantic_settings|pythonjsonlogger" src/convfinqa/domain/ && echo VIOLATION

# Application must not see frameworks
grep -rE "fastapi|sqlalchemy|litellm" src/convfinqa/application/ && echo VIOLATION

# Adapters must not see application/entrypoints
grep -rE "convfinqa\.application|convfinqa\.entrypoints" src/convfinqa/adapters/ && echo VIOLATION

# Entrypoints must not see adapters
grep -rE "convfinqa\.adapters" src/convfinqa/entrypoints/ && echo VIOLATION
```

## Use cases that stream

When a use case can be consumed by both a sync presenter (e.g. `POST /v1/chat`) and a streaming presenter (`POST /v1/chat/stream`), expose **ONE** async-generator method. The sync presenter consumes the generator and assembles a snapshot; the streaming presenter consumes the same generator and emits SSE frames. NEVER add a parallel `complete()` method — that's the drift the architecture exists to prevent.
