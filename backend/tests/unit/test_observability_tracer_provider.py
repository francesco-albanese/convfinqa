from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk.trace import TracerProvider

from convfinqa.adapters.observability.tracer_provider import (
    init_tracer_provider,
    should_export_to_langfuse,
)
from convfinqa.config import Settings


def _processor_count(provider: TracerProvider) -> int:
    return len(provider._active_span_processor._span_processors)  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "langfuse_enabled,langfuse_public_key,langfuse_secret_key,otel_endpoint,expected_count",
    [
        (False, None, None, None, 0),
        (False, None, None, "http://otel:4317", 1),
        (True, "pk-lf-xxx", "sk-lf-xxx", None, 1),
        (True, "pk-lf-xxx", "sk-lf-xxx", "http://otel:4317", 2),
        (True, None, None, None, 0),
    ],
)
def test_processor_count(
    langfuse_enabled: bool,
    langfuse_public_key: str | None,
    langfuse_secret_key: str | None,
    otel_endpoint: str | None,
    expected_count: int,
) -> None:
    settings = Settings(
        langfuse_enabled=langfuse_enabled,
        langfuse_public_key=langfuse_public_key,
        langfuse_secret_key=langfuse_secret_key,
        otel_exporter_otlp_endpoint=otel_endpoint,
    )

    with (
        patch(
            "langfuse._client.span_processor.LangfuseSpanProcessor",
            return_value=MagicMock(),
        ),
        patch(
            "convfinqa.adapters.observability.tracer_provider.OTLPSpanExporter",
            return_value=MagicMock(),
        ),
        patch(
            "convfinqa.adapters.observability.tracer_provider.BatchSpanProcessor",
            return_value=MagicMock(),
        ),
    ):
        provider = init_tracer_provider(settings)

    assert _processor_count(provider) == expected_count


def test_langfuse_filter_exports_convfinqa_observation_spans() -> None:
    span = MagicMock()
    span.attributes = {"langfuse.observation.type": "agent"}

    assert should_export_to_langfuse(span)


def test_langfuse_filter_delegates_default_export_rules() -> None:
    span = MagicMock()
    span.attributes = {}

    with patch(
        "langfuse._client.span_filter.is_default_export_span",
        return_value=True,
    ) as is_default_export_span:
        assert should_export_to_langfuse(span)

    is_default_export_span.assert_called_once_with(span)
