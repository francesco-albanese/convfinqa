# LiteLLM adapter rules

LiteLLM ships poorly-typed public APIs (`acompletion` returns `ModelResponse | CustomStreamWrapper` with extras hidden behind `**kwargs`; chunk shapes are pydantic models with attributes set in `__init__` rather than declared as fields). Strict pyright will not see the attributes you actually consume.

## Pattern: Protocol-typed boundary, single cast

Define `Protocol`s for ONLY the attributes the adapter actually reads. Cast LiteLLM's response to that Protocol once at the boundary. The iteration body is then fully typed without `Any` everywhere.

```python
from collections.abc import AsyncIterable, AsyncIterator, Sequence
from typing import Any, Protocol, cast

import litellm

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

async def _open_stream(model: str, wire: Sequence[dict[str, str]]) -> AsyncIterable[_LiteLLMChunk]:
    acompletion: Any = litellm.acompletion  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
    response = await acompletion(model=model, messages=list(wire), stream=True, stream_options={"include_usage": True})
    return cast(AsyncIterable[_LiteLLMChunk], response)
```

The `# pyright: ignore` covers TWO codes (`reportUnknownVariableType` AND `reportUnknownMemberType`). Single-code ignores leak.

## Cross-provider portability

Keep the adapter's external surface (the domain port) provider-neutral. Switching `LLM_MODEL` from `bedrock/...` to `gemini/...` should require zero adapter changes — LiteLLM normalizes `chunk.choices[0].delta.content` across providers. Document any provider-specific gotcha (Bedrock streaming-usage off-by-1000, Gemini empty-delta regression) inline.

## Streaming usage

LiteLLM emits a final chunk with `choices=[]` and a populated `usage` field when `stream_options={"include_usage": True}`. Map it to your domain `Usage(input_tokens, output_tokens)` and yield it as a separate event. `usage` is OPTIONAL on the wire — don't crash if it's absent.
