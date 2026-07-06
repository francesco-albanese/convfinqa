import pytest
from pydantic import ValidationError

from convfinqa.application.parts_schema import (
    TOOL_CALL_ARGS_MAX_BYTES,
    TOOL_RESULT_MAX_BYTES,
    TRUNCATION_MARKER,
    MessagePartsEnvelope,
    ToolCallPart,
    ToolResultPart,
    build_envelope,
)


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
    result = build_envelope(
        [
            {
                "kind": "tool_call",
                "call_id": "call_1",
                "name": "add",
                "args": oversized_args,
            }
        ]
    )
    args = result["parts"][0]["args"]

    assert args.endswith(TRUNCATION_MARKER)
    assert len(args.encode("utf-8")) <= TOOL_CALL_ARGS_MAX_BYTES


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
    result = build_envelope(
        [
            {
                "kind": "tool_result",
                "call_id": "call_2",
                "is_error": False,
                "result": oversized_result,
            }
        ]
    )
    content = result["parts"][0]["result"]

    assert content.endswith(TRUNCATION_MARKER)
    assert len(content.encode("utf-8")) <= TOOL_RESULT_MAX_BYTES


def test_discriminated_union_parses_tool_call_kind() -> None:
    envelope = MessagePartsEnvelope(
        schema_version=1,
        parts=[
            ToolCallPart(
                kind="tool_call",
                call_id="call_x",
                name="multiply",
                args="{}",
            )
        ],
    )

    assert envelope.parts[0].kind == "tool_call"


def test_discriminated_union_parses_tool_result_kind() -> None:
    envelope = MessagePartsEnvelope(
        schema_version=1,
        parts=[
            ToolResultPart(
                kind="tool_result",
                call_id="call_x",
                is_error=False,
                result="42",
            )
        ],
    )

    assert envelope.parts[0].kind == "tool_result"
