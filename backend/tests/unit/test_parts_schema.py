import pytest
from pydantic import ValidationError

from convfinqa.application.parts_schema import (
    ENVELOPE_MAX_BYTES,
    PARTS_MAX_COUNT,
    REASONING_MAX_BYTES,
    TEXT_MAX_BYTES,
    TOOL_CALL_ARGS_MAX_BYTES,
    TOOL_RESULT_MAX_BYTES,
    TRUNCATION_MARKER,
    CitationPart,
    MessagePartsEnvelope,
    ToolCallPart,
    ToolResultPart,
    build_envelope,
)


def test_valid_envelope_with_text_and_reasoning_parts() -> None:
    parts = [
        {"kind": "text", "content": "Hello"},
        {"kind": "reasoning", "id": "rsn_abc123", "content": "Let me think..."},
    ]
    result = build_envelope(parts)
    assert result["schema_version"] == 1
    assert len(result["parts"]) == 2
    assert result["parts"][0]["kind"] == "text"
    assert result["parts"][1]["kind"] == "reasoning"


def test_oversized_reasoning_content_is_truncated() -> None:
    oversized = "x" * (REASONING_MAX_BYTES + 1000)
    parts = [{"kind": "reasoning", "id": "rsn_big", "content": oversized}]
    result = build_envelope(parts)
    content = result["parts"][0]["content"]
    assert content.endswith(TRUNCATION_MARKER)
    assert len(content.encode("utf-8")) <= REASONING_MAX_BYTES


def test_oversized_text_content_is_truncated() -> None:
    oversized = "y" * (TEXT_MAX_BYTES + 5000)
    parts = [{"kind": "text", "content": oversized}]
    result = build_envelope(parts)
    content = result["parts"][0]["content"]
    assert content.endswith(TRUNCATION_MARKER)
    assert len(content.encode("utf-8")) <= TEXT_MAX_BYTES


def test_parts_array_over_256_items_truncated_to_256() -> None:
    parts = [
        {"kind": "text", "content": f"item {i}"} for i in range(PARTS_MAX_COUNT + 10)
    ]
    result = build_envelope(parts)
    assert len(result["parts"]) == PARTS_MAX_COUNT


def test_missing_kind_discriminator_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        MessagePartsEnvelope(
            schema_version=1,
            parts=[{"content": "no kind here"}],  # type: ignore[list-item]
        )


def test_extra_fields_in_part_raise_validation_error() -> None:
    with pytest.raises(ValidationError):
        MessagePartsEnvelope(
            schema_version=1,
            parts=[{"kind": "text", "content": "ok", "extra_field": "not allowed"}],  # type: ignore[list-item]
        )


def test_total_envelope_byte_cap_trims_parts_list() -> None:
    chunk_size = ENVELOPE_MAX_BYTES // 4
    large_content = "z" * chunk_size
    parts = [{"kind": "text", "content": large_content} for _ in range(6)]
    result = build_envelope(parts)
    import json

    total = len(json.dumps(result["parts"], separators=(",", ":")).encode("utf-8"))
    assert total <= ENVELOPE_MAX_BYTES
    assert len(result["parts"]) < len(parts)


# --- ToolCallPart ---


def test_tool_call_part_valid() -> None:
    part = ToolCallPart(
        kind="tool_call",
        call_id="call_abc",
        name="add",
        args='{"a": "1", "b": "2"}',
    )
    assert part.kind == "tool_call"
    assert part.call_id == "call_abc"
    assert part.name == "add"


def test_tool_call_part_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        ToolCallPart(
            kind="tool_call",
            call_id="call_abc",
            name="add",
            args="{}",
            extra="not allowed",  # type: ignore[call-arg]
        )


def test_tool_call_args_truncated_when_over_4kb() -> None:
    oversized_args = "x" * (TOOL_CALL_ARGS_MAX_BYTES + 500)
    parts = [
        {
            "kind": "tool_call",
            "call_id": "call_1",
            "name": "add",
            "args": oversized_args,
        }
    ]
    result = build_envelope(parts)
    args = result["parts"][0]["args"]
    assert args.endswith(TRUNCATION_MARKER)
    assert len(args.encode("utf-8")) <= TOOL_CALL_ARGS_MAX_BYTES


# --- ToolResultPart ---


def test_tool_result_part_valid() -> None:
    part = ToolResultPart(
        kind="tool_result",
        call_id="call_abc",
        is_error=False,
        result='{"result": "3"}',
    )
    assert part.kind == "tool_result"
    assert part.is_error is False


def test_tool_result_part_error_flag() -> None:
    part = ToolResultPart(
        kind="tool_result",
        call_id="call_abc",
        is_error=True,
        result="division by zero",
    )
    assert part.is_error is True


def test_tool_result_part_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        ToolResultPart(
            kind="tool_result",
            call_id="call_abc",
            is_error=False,
            result="ok",
            extra="not allowed",  # type: ignore[call-arg]
        )


def test_tool_result_truncated_when_over_32kb() -> None:
    oversized_result = "y" * (TOOL_RESULT_MAX_BYTES + 1000)
    parts = [
        {
            "kind": "tool_result",
            "call_id": "call_2",
            "is_error": False,
            "result": oversized_result,
        }
    ]
    result = build_envelope(parts)
    content = result["parts"][0]["result"]
    assert content.endswith(TRUNCATION_MARKER)
    assert len(content.encode("utf-8")) <= TOOL_RESULT_MAX_BYTES


# --- discriminated union parsing ---


def test_discriminated_union_parses_tool_call_kind() -> None:
    envelope = MessagePartsEnvelope(
        schema_version=1,
        parts=[  # type: ignore[list-item]
            {
                "kind": "tool_call",
                "call_id": "call_x",
                "name": "multiply",
                "args": "{}",
            }
        ],
    )
    assert envelope.parts[0].kind == "tool_call"


def test_discriminated_union_parses_tool_result_kind() -> None:
    envelope = MessagePartsEnvelope(
        schema_version=1,
        parts=[  # type: ignore[list-item]
            {
                "kind": "tool_result",
                "call_id": "call_x",
                "is_error": False,
                "result": "42",
            }
        ],
    )
    assert envelope.parts[0].kind == "tool_result"


# --- CitationPart ---


def test_citation_part_valid() -> None:
    part = CitationPart(kind="citation", row_label="net cash from operations", col_label="Year ended June 30, 2009")
    assert part.kind == "citation"
    assert part.row_label == "net cash from operations"
    assert part.col_label == "Year ended June 30, 2009"


def test_citation_part_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        CitationPart(
            kind="citation",
            row_label="revenue",
            col_label="2009",
            extra="not allowed",  # type: ignore[call-arg]
        )


def test_citation_part_round_trips_through_envelope() -> None:
    parts = [{"kind": "citation", "row_label": "net income", "col_label": "FY2009"}]
    result = build_envelope(parts)
    assert result["parts"][0]["kind"] == "citation"
    assert result["parts"][0]["row_label"] == "net income"
    assert result["parts"][0]["col_label"] == "FY2009"


def test_discriminated_union_parses_citation_kind() -> None:
    envelope = MessagePartsEnvelope(
        schema_version=1,
        parts=[  # type: ignore[list-item]
            {"kind": "citation", "row_label": "revenue", "col_label": "FY2009"}
        ],
    )
    assert envelope.parts[0].kind == "citation"
