from collections.abc import AsyncIterable, AsyncIterator, Sequence
from typing import Any, Protocol, cast

import litellm

from convfinqa.domain.ports.llm import LLMChunk, LLMMessage
from convfinqa.domain.value_objects import Usage


class _LiteLLMDelta(Protocol):
    content: str | None


class _LiteLLMChoice(Protocol):
    delta: _LiteLLMDelta


class _LiteLLMUsage(Protocol):
    prompt_tokens: int
    completion_tokens: int


class _LiteLLMChunk(Protocol):
    choices: Sequence[_LiteLLMChoice]
    usage: _LiteLLMUsage | None


async def _open_stream(
    model: str, wire_messages: Sequence[dict[str, str]]
) -> AsyncIterable[_LiteLLMChunk]:
    acompletion: Any = litellm.acompletion  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
    response = await acompletion(
        model=model,
        messages=list(wire_messages),
        stream=True,
        stream_options={"include_usage": True},
    )
    return cast(AsyncIterable[_LiteLLMChunk], response)


class LiteLLMAdapter:
    def __init__(self, model: str) -> None:
        self._model = model

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        system: str,
    ) -> AsyncIterator[LLMChunk]:
        wire_messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        wire_messages.extend({"role": m.role, "content": m.content} for m in messages)

        stream = await _open_stream(self._model, wire_messages)

        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                text = getattr(delta, "content", None)
                if text:
                    yield LLMChunk(text=text)

            usage: _LiteLLMUsage | None = getattr(chunk, "usage", None)
            if usage is not None:
                yield LLMChunk(
                    usage=Usage(
                        input_tokens=usage.prompt_tokens,
                        output_tokens=usage.completion_tokens,
                    )
                )
