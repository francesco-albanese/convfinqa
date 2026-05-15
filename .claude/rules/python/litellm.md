---
name: litellm
description: LiteLLM adapter pattern — Protocol-typed boundary, single cast, provider-neutral streaming
paths:
  - backend/src/convfinqa/adapters/llm/**
last_validated: 2026-05-15
pillar: false
related:
  - backend/src/convfinqa/adapters/llm
  - hexagonal
---

# LiteLLM adapter rules

LiteLLM ships poorly-typed public APIs (`acompletion` returns `Any | ModelResponse | CustomStreamWrapper`; chunk attrs set in `__init__` rather than declared as fields). Strict pyright won't see the attributes you consume.

## Pattern: Protocol-typed boundary, single cast

Define `Protocol`s for only the attributes the adapter actually reads. Cast LiteLLM's response to that Protocol once at the boundary; the iteration body is then fully typed.

```python
from collections.abc import AsyncIterable, Sequence
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
    response = await acompletion(
        model=model, messages=list(wire), stream=True,
        stream_options={"include_usage": True},
    )
    return cast(AsyncIterable[_LiteLLMChunk], response)
```

The `# pyright: ignore` MUST cover both codes. Single-code ignores leak.

## Cross-provider portability

The domain port stays provider-neutral. Switching `LLM_MODEL` from `bedrock/...` to `gemini/...` should require zero adapter changes — LiteLLM normalises `chunk.choices[0].delta.content` across providers. Document provider gotchas inline (Bedrock streaming-usage off-by-1000, Gemini empty-delta regression).

## Streaming usage frame

LiteLLM emits a final chunk with `choices=[]` and a populated `usage` when `stream_options={"include_usage": True}`. Map it to your domain `Usage(input_tokens, output_tokens)` and yield it as a separate event. `usage` is OPTIONAL on the wire — don't crash if absent.
