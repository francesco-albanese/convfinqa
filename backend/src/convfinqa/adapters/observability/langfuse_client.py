import asyncio
import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from langfuse._client.attributes import (
    LangfuseOtelSpanAttributes,  # type: ignore[import-untyped]
)
from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from convfinqa.adapters.observability.mask import mask
from convfinqa.config import Settings
from convfinqa.domain.ports.observability import ObservabilityPort, ObservabilitySpan


def _serialize_redacted(value: Any) -> str:
    redacted = mask(value)
    return redacted if isinstance(redacted, str) else json.dumps(redacted, default=str)


class _OtelSpanWrapper:
    def __init__(self, span: trace.Span) -> None:
        self._span = span

    def set_output(self, output: str) -> None:
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            parsed = output
        self._span.set_attribute(
            LangfuseOtelSpanAttributes.OBSERVATION_OUTPUT,
            _serialize_redacted(parsed),
        )

    def set_error(self) -> None:
        self._span.set_status(StatusCode.ERROR)
        self._span.set_attribute(LangfuseOtelSpanAttributes.OBSERVATION_LEVEL, "ERROR")


class LangfuseClient:
    def __init__(self, tracer: trace.Tracer) -> None:
        self._tracer = tracer

    @asynccontextmanager
    async def start_as_current_observation(
        self, as_type: str, name: str, input: dict[str, Any] | None = None
    ) -> AsyncGenerator[ObservabilitySpan]:
        span = self._tracer.start_span(name)
        # Streaming responses enter this scope in the request-handler task but
        # exit it in the task Starlette spawns to send the body. That second
        # task runs on a *copy* of the handler's Context, where resetting the
        # handler's token is impossible ("token was created in a different
        # Context"). The copy is discarded with its task, so when the exit
        # lands in another task the detach must be skipped, not attempted.
        attach_task = asyncio.current_task()
        token = otel_context.attach(trace.set_span_in_context(span))
        try:
            span.set_attribute(LangfuseOtelSpanAttributes.OBSERVATION_TYPE, as_type)
            if input is not None:
                span.set_attribute(
                    LangfuseOtelSpanAttributes.OBSERVATION_INPUT,
                    _serialize_redacted(input),
                )
            yield _OtelSpanWrapper(span)  # type: ignore[misc]
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(StatusCode.ERROR)
            raise
        finally:
            if asyncio.current_task() is attach_task:
                otel_context.detach(token)
            span.end()

    def propagate_attributes(
        self,
        user_id: str,
        session_id: str,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        span = trace.get_current_span()
        span.set_attribute(LangfuseOtelSpanAttributes.TRACE_USER_ID, user_id)
        span.set_attribute(LangfuseOtelSpanAttributes.TRACE_SESSION_ID, session_id)
        if metadata is not None:
            for key, value in metadata.items():
                attr_key = f"{LangfuseOtelSpanAttributes.TRACE_METADATA}.{key}"
                redacted = mask(value)
                serialized = (
                    redacted
                    if isinstance(redacted, (str, int, float, bool))
                    else json.dumps(redacted, default=str)
                )
                span.set_attribute(attr_key, serialized)
        if tags is not None:
            span.set_attribute(LangfuseOtelSpanAttributes.TRACE_TAGS, json.dumps(tags))

    def update_current_generation(self, **kwargs: Any) -> None:
        import langfuse

        langfuse.get_client().update_current_generation(**kwargs)

    async def flush(self) -> None:
        provider = trace.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush(timeout_millis=5000)  # type: ignore[attr-defined]


class _NoOpSpan:
    def set_output(self, output: str) -> None:
        pass

    def set_error(self) -> None:
        pass


class NoOpLangfuseClient:
    @asynccontextmanager
    async def start_as_current_observation(
        self, as_type: str, name: str, input: dict[str, Any] | None = None
    ) -> AsyncGenerator[ObservabilitySpan]:
        yield _NoOpSpan()  # type: ignore[misc]

    def propagate_attributes(
        self,
        user_id: str,
        session_id: str,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        pass

    def update_current_generation(self, **kwargs: Any) -> None:
        pass

    async def flush(self) -> None:
        pass


def init_langfuse(settings: Settings) -> ObservabilityPort:
    if not settings.langfuse_enabled:
        return NoOpLangfuseClient()  # type: ignore[return-value]
    tracer = trace.get_tracer("convfinqa")
    return LangfuseClient(tracer)  # type: ignore[return-value]
