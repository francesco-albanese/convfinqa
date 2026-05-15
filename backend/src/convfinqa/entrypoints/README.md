---
description: Entrypoints — FastAPI routes, Typer CLI, SSE presenter. Wire boundary; depends on application + container.
last_validated: 2026-05-15
related:
  - ../README.md
  - ../../../../.claude/rules/python/hexagonal.md
  - health-endpoints-backend-exposes-healthz-and-readyz-at
---

# `entrypoints/` — wire boundary

## Hard rule

Depends on `application/`, `domain/`, `container/`, FastAPI/Typer. NEVER imports from `adapters/` — composition happens in `container.py`.

```bash
grep -rE 'convfinqa\.adapters' . && echo VIOLATION
```

## FastAPI conventions

### Status codes — use `fastapi.status`

```python
from fastapi import FastAPI, status

@app.get("/items/", status_code=status.HTTP_418_IM_A_TEAPOT)
def read_items():
    return [{"name": "Plumbus"}, {"name": "Portal Gun"}]
```

### Dependency injection — annotate `Depends`

```python
from typing import Annotated
from fastapi import Depends

async def common_parameters(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
async def read_items(commons: Annotated[dict, Depends(common_parameters)]):
    return commons
```

`Settings` is injected via `SettingsDep` from `entrypoints/api/dependencies.py`. Never read `config.py:SETTINGS` directly from a route — that defeats `Container.for_testing(settings=...)`.

## URL prefixes (canonical)

- `/api/v1/*` — versioned application endpoints (chat, etc.)
- `/api/auth/*` — Lambda BFF auth flows
- `/healthz`, `/readyz` — Kubernetes liveness/readiness convention, **unversioned**. Do NOT add `/v1/healthz`.

## SSE presenter (`api/sse.py`)

AI SDK v5 UI Message Stream. One `match`-stmt over `StreamEvent` yields `data: <json>\n\n` frames. Wire shapes verified against ai-sdk.dev:

- `start` carries `messageId`
- `text-delta` uses field name `delta` (NOT `textDelta`)
- `data-*` parts nest payload under `data` key
- Terminator: `data: [DONE]\n\n`
- Frame order: `start`, `data-conversation`, `text-start`, `text-delta*`, `text-end`, `finish`, `[DONE]`
- Error path: `error` frame + `[DONE]` (no `text-end`, no `finish`)
- Buffers `ConversationCreated` until `MessageStarted` arrives so `start-with-messageId` fires first
