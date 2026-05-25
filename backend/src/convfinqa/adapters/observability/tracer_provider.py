from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_NAMESPACE, Resource
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from convfinqa.config import Settings

LANGFUSE_OBSERVATION_TYPE_ATTR = "langfuse.observation.type"


def should_export_to_langfuse(span: ReadableSpan) -> bool:
    if span.attributes and LANGFUSE_OBSERVATION_TYPE_ATTR in span.attributes:
        return True

    from langfuse._client.span_filter import (  # type: ignore[import-untyped]
        is_default_export_span,
    )

    return bool(is_default_export_span(span))


def reset_tracer_provider_for_tests() -> None:
    trace._TRACER_PROVIDER = None  # pyright: ignore[reportPrivateUsage]
    trace._TRACER_PROVIDER_SET_ONCE._done = False  # pyright: ignore[reportPrivateUsage]


def init_tracer_provider(
    settings: Settings,
    extra_processors: list[SpanProcessor] | None = None,
) -> TracerProvider:
    resource = Resource.create(
        {
            SERVICE_NAME: settings.otel_service_name,
            SERVICE_NAMESPACE: "convfinqa",
            "deployment.environment": settings.environment,
        }
    )
    provider = TracerProvider(resource=resource)

    if (
        settings.langfuse_enabled
        and settings.langfuse_public_key
        and settings.langfuse_secret_key
    ):
        # LangfuseSpanProcessor is in a private submodule in langfuse 4.x;
        # it extends BatchSpanProcessor and wires Langfuse's OTel ingestion.
        from langfuse._client.span_processor import (
            LangfuseSpanProcessor,  # type: ignore[import-untyped]
        )

        provider.add_span_processor(
            LangfuseSpanProcessor(  # type: ignore[call-arg]
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                base_url=settings.langfuse_host,
                should_export_span=should_export_to_langfuse,
            )
        )

    if settings.otel_exporter_otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    if extra_processors:
        for processor in extra_processors:
            provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    return provider
