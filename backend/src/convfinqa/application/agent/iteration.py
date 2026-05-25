from typing import Any

from convfinqa.domain.value_objects import Usage

ITERATION_CAP = 10


class IterationState:
    """Mutable accumulator for one LLM call within the agent loop."""

    def __init__(self) -> None:
        self.tool_calls: dict[str, dict[str, Any]] = {}
        self.current_reasoning_id: str | None = None
        self.reasoning_buffer: list[str] = []
        self.finish_reason_tool_use = False
        self.usage: Usage | None = None
