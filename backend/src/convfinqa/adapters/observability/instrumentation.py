import logging
from collections.abc import Iterable
from typing import Any

from fastapi import FastAPI
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.trace import Span

from convfinqa.config import Settings

FASTAPI_EXCLUDED_URLS = "/healthz,/readyz"
DEFAULT_CAPTURE_HEADERS = ("x-request-id", "x-correlation-id", "traceparent")
SENSITIVE_CAPTURE_HEADERS = frozenset({"authorization", "cookie", "set-cookie"})

INSTRUMENTED_GLOBALS: set[str] = set()
INSTRUMENTED_FASTAPI_APPS: set[int] = set()


def register_auto_instrumentations(
    settings: Settings,
    *,
    app: FastAPI | None = None,
    http_capture_headers_server_request: Iterable[str] | None = None,
) -> None:
    del settings

    if app is not None:
        app_id = id(app)
        if app_id not in INSTRUMENTED_FASTAPI_APPS:
            FastAPIInstrumentor.instrument_app(
                app,
                excluded_urls=FASTAPI_EXCLUDED_URLS,
                http_capture_headers_server_request=safe_capture_headers(
                    http_capture_headers_server_request
                ),
            )
            INSTRUMENTED_FASTAPI_APPS.add(app_id)

    instrument_once("sqlalchemy", SQLAlchemyInstrumentor)
    instrument_once("asyncpg", AsyncPGInstrumentor)
    instrument_once("httpx", HTTPXClientInstrumentor)
    instrument_once("botocore", BotocoreInstrumentor)
    instrument_once(
        "logging",
        LoggingInstrumentor,
        instrument_kwargs={
            "set_logging_format": False,
            "log_hook": add_trace_context_to_log_record,
        },
    )
    instrument_once("system_metrics", SystemMetricsInstrumentor)


def configure_auto_instrumentation() -> None:
    register_auto_instrumentations(Settings())


def safe_capture_headers(headers: Iterable[str] | None) -> list[str]:
    requested = headers if headers is not None else DEFAULT_CAPTURE_HEADERS
    safe_headers: list[str] = []
    for header in requested:
        normalized = header.strip().lower()
        if normalized and normalized not in SENSITIVE_CAPTURE_HEADERS:
            safe_headers.append(normalized)
    return safe_headers


def add_trace_context_to_log_record(span: Span, record: logging.LogRecord) -> None:
    context = span.get_span_context()
    record.trace_id = format(context.trace_id, "032x")
    record.span_id = format(context.span_id, "016x")


def instrument_once(
    key: str,
    instrumentor_factory: type[Any],
    *,
    instrument_kwargs: dict[str, Any] | None = None,
) -> None:
    if key in INSTRUMENTED_GLOBALS:
        return
    instrumentor = instrumentor_factory()
    instrumentor.instrument(**(instrument_kwargs or {}))
    INSTRUMENTED_GLOBALS.add(key)
