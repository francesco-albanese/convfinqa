from __future__ import annotations

import importlib
import logging
from typing import Any

import pytest
from fastapi import FastAPI
from opentelemetry import trace

from convfinqa.adapters.observability.tracer_provider import init_tracer_provider
from convfinqa.config import Settings


def test_register_auto_instrumentations_is_idempotent_and_filters_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("convfinqa.adapters.observability.instrumentation")
    instrumentation = importlib.reload(module)
    calls: dict[str, int] = {
        "fastapi": 0,
        "sqlalchemy": 0,
        "asyncpg": 0,
        "httpx": 0,
        "botocore": 0,
        "logging": 0,
        "system_metrics": 0,
    }
    fastapi_kwargs: dict[str, Any] = {}

    def instrument_app(app: FastAPI, **kwargs: Any) -> None:
        calls["fastapi"] += 1
        fastapi_kwargs.update(kwargs)

    class Instrumentor:
        def __init__(self, key: str) -> None:
            self._key = key

        def instrument(self, **kwargs: Any) -> None:
            calls[self._key] += 1

    monkeypatch.setattr(
        instrumentation.FastAPIInstrumentor, "instrument_app", instrument_app
    )
    monkeypatch.setattr(
        instrumentation, "SQLAlchemyInstrumentor", lambda: Instrumentor("sqlalchemy")
    )
    monkeypatch.setattr(
        instrumentation, "AsyncPGInstrumentor", lambda: Instrumentor("asyncpg")
    )
    monkeypatch.setattr(
        instrumentation, "HTTPXClientInstrumentor", lambda: Instrumentor("httpx")
    )
    monkeypatch.setattr(
        instrumentation, "BotocoreInstrumentor", lambda: Instrumentor("botocore")
    )
    monkeypatch.setattr(
        instrumentation, "LoggingInstrumentor", lambda: Instrumentor("logging")
    )
    monkeypatch.setattr(
        instrumentation,
        "SystemMetricsInstrumentor",
        lambda: Instrumentor("system_metrics"),
    )

    app = FastAPI()
    settings = Settings(langfuse_enabled=False)

    instrumentation.register_auto_instrumentations(
        settings,
        app=app,
        http_capture_headers_server_request=[
            "authorization",
            "cookie",
            "set-cookie",
            "x-request-id",
        ],
    )
    instrumentation.register_auto_instrumentations(
        settings,
        app=app,
        http_capture_headers_server_request=["authorization", "x-request-id"],
    )

    assert calls == {
        "fastapi": 1,
        "sqlalchemy": 1,
        "asyncpg": 1,
        "httpx": 1,
        "botocore": 1,
        "logging": 1,
        "system_metrics": 1,
    }
    assert fastapi_kwargs["excluded_urls"] == "/healthz,/readyz"
    assert fastapi_kwargs["http_capture_headers_server_request"] == ["x-request-id"]


def test_log_records_include_trace_and_span_ids(
    caplog: pytest.LogCaptureFixture,
) -> None:
    module = importlib.import_module("convfinqa.adapters.observability.instrumentation")
    instrumentation = importlib.reload(module)
    settings = Settings(langfuse_enabled=False)
    init_tracer_provider(settings)
    instrumentation.register_auto_instrumentations(settings)

    logger = logging.getLogger("convfinqa.tests.instrumentation")
    tracer = trace.get_tracer(__name__)

    with caplog.at_level(logging.INFO, logger=logger.name):
        with tracer.start_as_current_span("logging-test"):
            logger.info("trace-linked log")

    record = next(
        record for record in caplog.records if record.message == "trace-linked log"
    )
    assert isinstance(vars(record)["trace_id"], str)
    assert isinstance(vars(record)["span_id"], str)
