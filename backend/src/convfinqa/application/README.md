---
description: Application layer — use cases, orchestration, streaming generators. Imports domain only.
last_validated: 2026-05-15
related:
  - ../README.md
  - ../../../../.claude/rules/python/hexagonal.md
  - convfinqa-timestamp-single-source-of-truth-when-a
  - convfinqa-streaming-disconnect-test-pattern
---

# `application/` — use cases

## Hard rule

Imports ONLY `convfinqa.domain.*`. Never `fastapi`, `sqlalchemy`, `litellm`.

```bash
grep -rE 'fastapi|sqlalchemy|litellm' . && echo VIOLATION
```

## Single-generator use cases

A use case consumed by both `POST /v1/chat` and `POST /v1/chat/stream` exposes ONE async-generator method (e.g. `SendMessageUseCase.stream() -> AsyncIterator[StreamEvent]`).

- The **sync presenter** consumes the generator and assembles a snapshot response.
- The **streaming presenter** consumes the same generator and emits SSE frames.

NEVER add a parallel `complete()` method — that's the drift the architecture exists to prevent.

## Timestamp single source of truth

When a use case persists `created_at` and the presenter needs the same value in its response, the use case surfaces it (e.g. via a `Finish` event). Calling `datetime.now(UTC)` in both the use case AND the presenter causes ms drift between DB row and HTTP body → flaky tests, inconsistent UX.

## Streaming disconnect handling

`httpx` `ASGITransport` cannot mid-stream-disconnect (runs the ASGI app to completion). Test the `GeneratorExit` handler at the use-case layer with `await events.aclose()`. This is sound: Starlette's `StreamingResponse` cancels by calling `aclose()` on the body iterator on real client disconnect — same code path.
