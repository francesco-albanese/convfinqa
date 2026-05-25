import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

REASONING_MAX_BYTES = 16 * 1024
TEXT_MAX_BYTES = 64 * 1024
TOOL_CALL_ARGS_MAX_BYTES = 4 * 1024
TOOL_RESULT_MAX_BYTES = 32 * 1024
PARTS_MAX_COUNT = 256
ENVELOPE_MAX_BYTES = 256 * 1024
TRUNCATION_MARKER = "...[truncated]"


class TextPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["text"]
    content: str


class ReasoningPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["reasoning"]
    id: str
    content: str


class ToolCallPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool_call"]
    call_id: str
    name: str
    args: str


class ToolResultPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool_result"]
    call_id: str
    is_error: bool
    result: str


class CitationPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["citation"]
    row_label: str
    col_label: str


Part = Annotated[
    TextPart | ReasoningPart | ToolCallPart | ToolResultPart | CitationPart,
    Field(discriminator="kind"),
]


class MessagePartsEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    parts: list[Part] = Field(max_length=PARTS_MAX_COUNT)


def _truncate(text: str, max_bytes: int) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    marker_bytes = TRUNCATION_MARKER.encode("utf-8")
    truncated = encoded[: max_bytes - len(marker_bytes)].decode(
        "utf-8", errors="ignore"
    )
    return truncated + TRUNCATION_MARKER


def _truncate_envelope_total(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for part in parts:
        candidate = [*result, part]
        envelope_bytes = json.dumps(
            {"schema_version": 1, "parts": candidate},
            separators=(",", ":"),
        ).encode("utf-8")
        if len(envelope_bytes) > ENVELOPE_MAX_BYTES:
            break
        result.append(part)
    return result


def build_envelope(parts_in_order: list[dict[str, Any]]) -> dict[str, Any]:
    capped: list[dict[str, Any]] = []
    for part in parts_in_order:
        kind = part["kind"]
        if kind == "reasoning":
            capped.append(
                {**part, "content": _truncate(part["content"], REASONING_MAX_BYTES)}
            )
        elif kind == "text":
            capped.append(
                {**part, "content": _truncate(part["content"], TEXT_MAX_BYTES)}
            )
        elif kind == "tool_call":
            capped.append(
                {**part, "args": _truncate(part["args"], TOOL_CALL_ARGS_MAX_BYTES)}
            )
        elif kind == "tool_result":
            capped.append(
                {**part, "result": _truncate(part["result"], TOOL_RESULT_MAX_BYTES)}
            )
        else:
            capped.append(part)

    capped = _truncate_envelope_total(capped[:PARTS_MAX_COUNT])

    envelope = MessagePartsEnvelope(schema_version=1, parts=capped)  # type: ignore[arg-type]
    return envelope.model_dump()
