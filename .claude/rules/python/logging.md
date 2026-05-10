# Logging rules

## Always use `get_logger`, never `logging.getLogger` directly

`src/convfinqa/logging.py` exposes:

```python
from convfinqa.logging import get_logger
logger = get_logger("convfinqa.errors")
```

`get_logger(name)` lazily ensures `configure_logging()` has run (idempotent via the `_configured` flag), so JSON output is guaranteed even in tests where the FastAPI lifespan didn't run. Calling `logging.getLogger("...")` directly bypasses this and produces plain-text logs in environments where configuration didn't fire first.

## LogRecord reserved fields — DO NOT collide

`logger.log(level, msg, extra={...})` will raise `KeyError("Attempt to overwrite 'X' in LogRecord")` if `extra` contains any of: `message`, `asctime`, `name`, `levelname`, `module`, `funcName`, `lineno`, `pathname`, `filename`, `created`, `msecs`, `relativeCreated`, `thread`, `threadName`, `process`, `processName`, `args`, `exc_info`, `exc_text`, `stack_info`.

For your "the message of the exception" field, use `exc_message` not `message`. For "the route", `route` is fine. Pick names that don't shadow LogRecord built-ins.

## What to log on errors

Concise, structured. Whitelist of fields: `exc_type`, `exc_message`, `route`, `method`, `status`, `request_id`, `user_id`. No stack traces by default — only at `level=ERROR` for unexpected exceptions, and trim to the last 3 frames.
