# Dependency injection rules

## Never read module-level singletons inside route handlers or use cases

`backend/src/convfinqa/config.py` exposes `SETTINGS = Settings()` so the lifespan can bootstrap the container once. Inside route handlers, use cases, and adapters, ALWAYS access settings via the container/DI dependency, never the singleton.

```python
# WRONG — leaks a hard-coded global into a route, breaks tests that override Settings
from convfinqa.config import SETTINGS

@router.post("/chat")
async def chat(...) -> ...:
    return ChatResponse(model=SETTINGS.llm_model, ...)

# RIGHT — Settings injected via container
from convfinqa.entrypoints.api.dependencies import SettingsDep

@router.post("/chat")
async def chat(..., settings: SettingsDep) -> ...:
    return ChatResponse(model=settings.llm_model, ...)
```

The container holds the active `Settings` instance. `Container.for_testing(settings=...)` lets tests inject a custom one. Reading `SETTINGS` directly defeats this.

## Container is the only composition root

Adapters are constructed in `Container.bootstrap_application()` (production) and `Container.for_testing()` (tests). Never `new` an adapter inside a use case, route, or other adapter.

## Use case timestamps

When a use case persists a row with a `created_at` and the presenter needs the same value in its response payload, the use case must surface it (e.g. via the `Finish` event). Never call `datetime.now(UTC)` twice for "the same" event — the DB row and the HTTP response will drift by milliseconds and cause flaky tests + inconsistent client UX.
