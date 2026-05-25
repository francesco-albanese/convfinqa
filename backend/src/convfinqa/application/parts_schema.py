import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

REASONING_MAX_BYTES = 16 * 1024
TEXT_MAX_BYTES = 64 * 1024
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


Part = Annotated[TextPart | ReasoningPart, Field(discriminator="kind")]


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
    accumulated = 0
    for part in parts:
        serialized = json.dumps(part, separators=(",", ":")).encode("utf-8")
        if accumulated + len(serialized) > ENVELOPE_MAX_BYTES:
            break
        result.append(part)
        accumulated += len(serialized)
    return result


def build_envelope(parts_in_order: list[dict[str, Any]]) -> dict[str, Any]:
    capped: list[dict[str, Any]] = []
    for part in parts_in_order:
        if part["kind"] == "reasoning":
            capped.append(
                {**part, "content": _truncate(part["content"], REASONING_MAX_BYTES)}
            )
        elif part["kind"] == "text":
            capped.append(
                {**part, "content": _truncate(part["content"], TEXT_MAX_BYTES)}
            )
        else:
            capped.append(part)

    capped = _truncate_envelope_total(capped[:PARTS_MAX_COUNT])

    envelope = MessagePartsEnvelope(schema_version=1, parts=capped)  # type: ignore[arg-type]
    return envelope.model_dump()
