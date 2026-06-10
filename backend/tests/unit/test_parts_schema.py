import pytest
from pydantic import ValidationError

from convfinqa.application.parts_schema import (
    ENVELOPE_MAX_BYTES,
    PARTS_MAX_COUNT,
    REASONING_MAX_BYTES,
    TEXT_MAX_BYTES,
    TRUNCATION_MARKER,
    MessagePartsEnvelope,
    build_envelope,
)
from tests.unit.parts_schema_helpers import (
    build_and_measure_parts,
    build_oversized_text_parts,
)


def test_valid_envelope_with_text_and_reasoning_parts() -> None:
    parts = [
        {"kind": "text", "content": "Hello"},
        {"kind": "reasoning", "id": "rsn_abc123", "content": "Let me think..."},
    ]
    result = build_envelope(parts)

    assert result["schema_version"] == 1
    assert [part["kind"] for part in result["parts"]] == ["text", "reasoning"]


def test_oversized_reasoning_content_is_truncated() -> None:
    oversized = "x" * (REASONING_MAX_BYTES + 1000)
    result = build_envelope(
        [{"kind": "reasoning", "id": "rsn_big", "content": oversized}]
    )
    content = result["parts"][0]["content"]

    assert content.endswith(TRUNCATION_MARKER)
    assert len(content.encode("utf-8")) <= REASONING_MAX_BYTES


def test_oversized_text_content_is_truncated() -> None:
    oversized = "y" * (TEXT_MAX_BYTES + 5000)
    result = build_envelope([{"kind": "text", "content": oversized}])
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
    parts = build_oversized_text_parts()
    kept_count, total_bytes = build_and_measure_parts(parts)

    assert total_bytes <= ENVELOPE_MAX_BYTES
    assert kept_count < len(parts)
