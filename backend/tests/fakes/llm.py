import asyncio
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any

from convfinqa.domain.ports.llm import LLMChunk, LLMMessage
from convfinqa.domain.value_objects import Usage


@dataclass(slots=True)
class FakeLLMPort:
    deltas: tuple[str, ...] = ("Hello ", "world")
    final_usage: Usage | None = field(
        default_factory=lambda: Usage(input_tokens=12, output_tokens=2)
    )
    raise_after: int | None = None
    raise_with: Exception | None = None
    seen_messages: list[Sequence[LLMMessage]] = field(
        default_factory=list[Sequence[LLMMessage]]
    )
    seen_systems: list[str] = field(default_factory=list[str])
    gate: asyncio.Event | None = None
    stream_started: asyncio.Event | None = None

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        system: str,
        tools: Any = None,
        generation_name: str | None = None,
        trace_user_id: str | None = None,
        session_id: str | None = None,
        environment: str | None = None,
    ) -> AsyncIterator[LLMChunk]:
        self.seen_messages.append(list(messages))
        self.seen_systems.append(system)
        if self.stream_started is not None:
            self.stream_started.set()
        if self.gate is not None:
            await self.gate.wait()
        for index, delta in enumerate(self.deltas):
            if self.raise_after is not None and index >= self.raise_after:
                raise self.raise_with or RuntimeError("fake llm boom")
            yield LLMChunk(text=delta)
        if self.final_usage is not None:
            yield LLMChunk(usage=self.final_usage)
