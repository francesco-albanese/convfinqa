import asyncio
import logging

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)

from convfinqa.adapters.observability.langfuse_client import LangfuseClient


class _CollectingExporter(SpanExporter):
    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def export(self, spans: object) -> SpanExportResult:
        self.spans.extend(spans)  # type: ignore[arg-type]
        return SpanExportResult.SUCCESS


def _client() -> tuple[LangfuseClient, _CollectingExporter]:
    exporter = _CollectingExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return LangfuseClient(provider.get_tracer("test")), exporter


@pytest.mark.asyncio
async def test_exit_in_another_task_ends_span_without_detach_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, exporter = _client()
    scope = client.start_as_current_observation(as_type="agent", name="send_message")

    with caplog.at_level(logging.ERROR, logger="opentelemetry.context"):
        await scope.__aenter__()
        await asyncio.create_task(_exit(scope))

    detach_errors = [
        record
        for record in caplog.records
        if "Failed to detach context" in record.getMessage()
    ]
    assert detach_errors == []
    assert [span.name for span in exporter.spans] == ["send_message"]


async def _exit(scope: object) -> None:
    await scope.__aexit__(None, None, None)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_same_task_exit_restores_previous_context() -> None:
    client, exporter = _client()

    async with client.start_as_current_observation(as_type="agent", name="obs") as _:
        assert trace.get_current_span().get_span_context().is_valid

    assert not trace.get_current_span().get_span_context().is_valid
    assert [span.name for span in exporter.spans] == ["obs"]
