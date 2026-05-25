from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class StopReason(StrEnum):
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    INTERRUPTED = "interrupted"
    ITERATION_CAP = "iteration_cap"


@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int
    output_tokens: int
