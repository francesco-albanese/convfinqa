from collections.abc import AsyncIterable, AsyncIterator, Sequence
from typing import Any, Protocol, cast

import litellm

from convfinqa.domain.ports.llm import LLMChunk, LLMToolSpec
from convfinqa.domain.value_objects import Usage
from convfinqa.logging import get_logger

LITELLM_LOG = get_logger("convfinqa.llm")
MIN_THINKING_BUDGET_TOKENS = 1024
DEFAULT_THINKING_BUDGET_TOKENS = 8000


def _attach_cost_to_current_generation(
    kwargs: dict[str, Any],
    response: Any,
    start_time: Any,
    end_time: Any,
) -> None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return

    completion_cost: Any = litellm.completion_cost  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    total_cost = completion_cost(
        model=kwargs.get("model"),
        completion_response=response,
    )
    import langfuse

    langfuse.get_client().update_current_generation(
        cost_details={"input": 0.0, "output": 0.0, "total": total_cost}
    )


async def _log_llm_failure(
    kwargs: dict[str, Any],
    exception: Any,
    start_time: Any,
    end_time: Any,
) -> None:
    LITELLM_LOG.warning(
        "llm_failure",
        extra={
            "exc_type": type(exception).__name__,
            "exc_message": str(exception),
            "model": kwargs.get("model", "unknown"),
        },
    )


def _register_callbacks() -> None:
    callbacks: Any = litellm.callbacks  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    if "langfuse_otel" not in callbacks:
        litellm.callbacks = [*callbacks, "langfuse_otel"]  # pyright: ignore[reportUnknownMemberType]
    successes: Any = litellm.success_callback  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    if _attach_cost_to_current_generation not in successes:
        litellm.success_callback = [  # pyright: ignore[reportUnknownMemberType]
            *successes,
            _attach_cost_to_current_generation,
        ]
    failure: Any = litellm.failure_callback  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    if _log_llm_failure not in failure:
        litellm.failure_callback = [*failure, _log_llm_failure]  # pyright: ignore[reportUnknownMemberType]


_register_callbacks()


class _LiteLLMDelta(Protocol):
    content: str | None
    reasoning_content: str | None


class _LiteLLMChoice(Protocol):
    delta: _LiteLLMDelta
    finish_reason: str | None


class _LiteLLMUsage(Protocol):
    prompt_tokens: int
    completion_tokens: int


class _LiteLLMChunk(Protocol):
    choices: Sequence[_LiteLLMChoice]
    usage: _LiteLLMUsage | None


def _tool_spec_to_litellm(spec: LLMToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.parameters,
        },
    }


async def _open_stream(
    model: str,
    wire_messages: Sequence[dict[str, Any]],
    timeout_seconds: float,
    max_output_tokens: int,
    thinking: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
    generation_name: str | None = None,
    trace_user_id: str | None = None,
    session_id: str | None = None,
    environment: str | None = None,
) -> AsyncIterable[_LiteLLMChunk]:
    acompletion: Any = litellm.acompletion  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": list(wire_messages),
        "stream": True,
        "stream_options": {"include_usage": True},
        "timeout": timeout_seconds,
        "max_tokens": max_output_tokens,
    }
    if thinking is not None:
        kwargs["thinking"] = thinking
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    metadata: dict[str, Any] = {}
    if generation_name is not None:
        metadata["generation_name"] = generation_name
    if trace_user_id is not None:
        metadata["trace_user_id"] = trace_user_id
    if session_id is not None:
        metadata["session_id"] = session_id
    if environment is not None:
        metadata["tags"] = [f"environment:{environment}"]
    if metadata:
        kwargs["metadata"] = metadata
    response = await acompletion(**kwargs)
    return cast(AsyncIterable[_LiteLLMChunk], response)


def _extract_block_id(chunk: Any) -> str | None:
    try:
        choices = chunk.choices
        if choices:
            delta = choices[0].delta
            return getattr(delta, "block_id", None) or getattr(
                delta, "thinking_block_id", None
            )
    except Exception:  # noqa: BLE001
        pass
    return None


def _extract_signature(chunk: Any) -> str | None:
    try:
        choices = chunk.choices
        if choices:
            delta = choices[0].delta
            return getattr(delta, "signature", None) or getattr(
                delta, "thinking_signature", None
            )
    except Exception:  # noqa: BLE001
        pass
    return None


class LiteLLMAdapter:
    def __init__(
        self,
        model: str,
        request_timeout_seconds: float,
        max_output_tokens: int,
    ) -> None:
        self._model = model
        self._request_timeout_seconds = request_timeout_seconds
        self._max_output_tokens = max_output_tokens

    def _wants_thinking(self, model: str) -> bool:
        return "anthropic" in model or "bedrock" in model

    def _thinking_param(self, model: str) -> dict[str, Any] | None:
        if not self._wants_thinking(model):
            return None
        if self._max_output_tokens <= MIN_THINKING_BUDGET_TOKENS:
            return None
        return {
            "type": "enabled",
            "budget_tokens": min(
                DEFAULT_THINKING_BUDGET_TOKENS,
                self._max_output_tokens - 1,
            ),
        }

    async def stream(
        self,
        messages: Sequence[dict[str, Any]],
        system: str,
        tools: Sequence[LLMToolSpec] | None = None,
        generation_name: str | None = None,
        trace_user_id: str | None = None,
        session_id: str | None = None,
        environment: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[LLMChunk]:
        effective_model = model or self._model
        wire_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        wire_messages.extend(messages)

        thinking_param = self._thinking_param(effective_model)

        litellm_tools = [_tool_spec_to_litellm(t) for t in tools] if tools else None

        stream = await _open_stream(
            effective_model,
            wire_messages,
            self._request_timeout_seconds,
            self._max_output_tokens,
            thinking=thinking_param,
            tools=litellm_tools,
            generation_name=generation_name,
            trace_user_id=trace_user_id,
            session_id=session_id,
            environment=environment,
        )

        reasoning_active = False
        current_block_id: str | None = None
        pending_tool_calls: dict[int, dict[str, Any]] = {}

        async for chunk in stream:
            if chunk.choices:
                choice = chunk.choices[0]
                delta = choice.delta

                reasoning_content: str | None = getattr(
                    delta, "reasoning_content", None
                )
                if reasoning_content:
                    if not reasoning_active:
                        reasoning_active = True
                        current_block_id = (
                            _extract_block_id(chunk) or f"rsn_{id(chunk)}"
                        )
                        yield LLMChunk(
                            reasoning_event="start",
                            reasoning_block_id=current_block_id,
                        )
                    yield LLMChunk(
                        reasoning_text=reasoning_content,
                        reasoning_event="delta",
                        reasoning_block_id=current_block_id,
                    )

                text: str | None = getattr(delta, "content", None)
                if text:
                    if reasoning_active:
                        sig = _extract_signature(chunk)
                        reasoning_active = False
                        yield LLMChunk(
                            reasoning_event="end",
                            reasoning_block_id=current_block_id,
                            reasoning_signature=sig,
                        )
                        current_block_id = None
                    yield LLMChunk(text=text)

                raw_tool_calls: Any = getattr(delta, "tool_calls", None)
                if raw_tool_calls:
                    for tc in raw_tool_calls:
                        idx: int = getattr(tc, "index", 0)
                        tc_id: str | None = getattr(tc, "id", None)
                        fn: Any = getattr(tc, "function", None)
                        fn_name: str | None = getattr(fn, "name", None) if fn else None
                        fn_args: str | None = (
                            getattr(fn, "arguments", None) if fn else None
                        )

                        if idx not in pending_tool_calls:
                            pending_tool_calls[idx] = {
                                "id": tc_id or "",
                                "name": fn_name or "",
                                "args_chunks": [],
                            }
                            yield LLMChunk(
                                tool_call_event="start",
                                tool_call_id=tc_id or "",
                                tool_call_name=fn_name or "",
                            )
                        else:
                            if tc_id and not pending_tool_calls[idx]["id"]:
                                pending_tool_calls[idx]["id"] = tc_id
                            if fn_name and not pending_tool_calls[idx]["name"]:
                                pending_tool_calls[idx]["name"] = fn_name

                        if fn_args:
                            pending_tool_calls[idx]["args_chunks"].append(fn_args)
                            yield LLMChunk(
                                tool_call_event="delta",
                                tool_call_id=pending_tool_calls[idx]["id"],
                                tool_call_delta=fn_args,
                            )

                finish_reason: str | None = getattr(choice, "finish_reason", None)
                if finish_reason in ("tool_calls", "tool_use"):
                    if reasoning_active:
                        sig = _extract_signature(chunk)
                        reasoning_active = False
                        yield LLMChunk(
                            reasoning_event="end",
                            reasoning_block_id=current_block_id,
                            reasoning_signature=sig,
                        )
                        current_block_id = None

                    for tc_state in pending_tool_calls.values():
                        yield LLMChunk(
                            tool_call_event="complete",
                            tool_call_id=tc_state["id"],
                            tool_call_name=tc_state["name"],
                        )
                    pending_tool_calls = {}
                    yield LLMChunk(finish_reason_tool_use=True)

            usage: _LiteLLMUsage | None = getattr(chunk, "usage", None)
            if usage is not None:
                yield LLMChunk(
                    usage=Usage(
                        input_tokens=usage.prompt_tokens,
                        output_tokens=usage.completion_tokens,
                    )
                )

        if reasoning_active:
            yield LLMChunk(
                reasoning_event="end",
                reasoning_block_id=current_block_id,
            )

        for tc_state in pending_tool_calls.values():
            yield LLMChunk(
                tool_call_event="complete",
                tool_call_id=tc_state["id"],
                tool_call_name=tc_state["name"],
            )
