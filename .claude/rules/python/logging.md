---
name: logging
description: Logging conventions — use get_logger, avoid LogRecord reserved-name collisions, structured error fields
paths:
  - backend/src/**
last_validated: 2026-05-15
pillar: false
related:
  - backend/src/convfinqa/logging.py
---

# Logging rules

## Always use `get_logger`, never `logging.getLogger` directly

`backend/src/convfinqa/logging.py` exposes:

```python
from convfinqa.logging import get_logger
logger = get_logger("convfinqa.errors")
```

`get_logger(name)` lazily calls `configure_logging()` (idempotent via the `_configured` flag), guaranteeing JSON output even in tests where the FastAPI lifespan didn't run. `logging.getLogger("...")` bypasses this and produces plain-text logs when configuration didn't fire first.

## LogRecord reserved fields — DO NOT collide

`logger.log(level, msg, extra={...})` raises `KeyError("Attempt to overwrite 'X' in LogRecord")` if `extra` contains any of: `message`, `asctime`, `name`, `levelname`, `module`, `funcName`, `lineno`, `pathname`, `filename`, `created`, `msecs`, `relativeCreated`, `thread`, `threadName`, `process`, `processName`, `args`, `exc_info`, `exc_text`, `stack_info`.

For "the exception's message" use `exc_message`, not `message`.

## What to log on errors

Concise and structured. Whitelist: `exc_type`, `exc_message`, `route`, `method`, `status`, `request_id`, `user_id`. No stack traces by default — only at `level=ERROR` for unexpected exceptions, trimmed to the last 3 frames.
