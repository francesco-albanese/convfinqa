---
name: hexagonal
description: Hexagonal layering invariants — one-way dependency direction, ports as Protocol, container as the only composition root, DI for settings
paths:
  - backend/src/convfinqa/**
last_validated: 2026-05-15
pillar: true
related:
  - convfinqa-settings-singleton-anti-pattern-src-convfinqa-conf
  - convfinqa-timestamp-single-source-of-truth-when-a
  - code-quality
---

# Hexagonal architecture (HARD rules)

## Layer direction

```
entrypoints  →  application  →  domain
adapters     →  domain (via ports)
container    →  adapters + application + domain
```

- `domain/` — zero framework imports. Allowed: `dataclasses`, `datetime`, `enum`, `typing`, `collections.abc`. Forbidden: `fastapi`, `sqlalchemy`, `litellm`, `pydantic_settings`, `pythonjsonlogger`.
- `domain/ports/` — every port is a `typing.Protocol` (NOT an ABC). Async where I/O is involved.
- `application/` — imports only `convfinqa.domain.*`. Never frameworks.
- `adapters/` — implements ports. Imports `convfinqa.domain.*` ONLY. Never `application/` or `entrypoints/`.
- `entrypoints/` — depends on `application/`, `domain/`, `container/`, FastAPI/Typer. Never imports from `adapters/`.
- `container.py` — the ONLY place adapters are instantiated and wired.

## Audit greps (run before merge)

```bash
grep -rE 'fastapi|sqlalchemy|litellm|pydantic_settings|pythonjsonlogger' backend/src/convfinqa/domain/ && echo VIOLATION
grep -rE 'fastapi|sqlalchemy|litellm' backend/src/convfinqa/application/ && echo VIOLATION
grep -rE 'convfinqa\.application|convfinqa\.entrypoints' backend/src/convfinqa/adapters/ && echo VIOLATION
grep -rE 'convfinqa\.adapters' backend/src/convfinqa/entrypoints/ && echo VIOLATION
```

## Settings DI (no module-level singleton reads)

`config.py:SETTINGS` exists ONLY so the lifespan can bootstrap the container once. Routes, use cases, and adapters MUST receive `Settings` via the container (`entrypoints/api/dependencies.py:SettingsDep`). Reading `SETTINGS` directly defeats `Container.for_testing(settings=...)`.

## Composition root

Adapters are constructed in `Container.bootstrap_application()` / `Container.for_testing()`. NEVER `new` an adapter inside a use case, route, or other adapter.

## Single-generator use cases (streaming + sync share one method)

A use case consumed by both `POST /v1/chat` and `POST /v1/chat/stream` exposes ONE async-generator method. Sync presenter assembles a snapshot; streaming presenter emits SSE frames. NEVER add a parallel `complete()` — that's the drift the architecture exists to prevent.

## Timestamp single source of truth

When a use case persists `created_at` and the presenter needs the same value in the response, the use case surfaces it (e.g. via a `Finish` event). Calling `datetime.now(UTC)` twice produces ms drift between DB row and HTTP body — flaky tests, inconsistent UX.
