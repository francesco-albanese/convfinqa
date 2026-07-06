import pytest
from pydantic import ValidationError

from convfinqa.application.parts_schema import (
    CitationPart,
    MessagePartsEnvelope,
    build_envelope,
)


def test_citation_part_valid() -> None:
    part = CitationPart(
        kind="citation",
        row_label="net cash from operations",
        col_label="Year ended June 30, 2009",
    )

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
    result = build_envelope(
        [{"kind": "citation", "row_label": "net income", "col_label": "FY2009"}]
    )

    assert result["parts"][0]["kind"] == "citation"
    assert result["parts"][0]["row_label"] == "net income"
    assert result["parts"][0]["col_label"] == "FY2009"


def test_discriminated_union_parses_citation_kind() -> None:
    envelope = MessagePartsEnvelope(
        schema_version=1,
        parts=[CitationPart(kind="citation", row_label="revenue", col_label="FY2009")],
    )

    assert envelope.parts[0].kind == "citation"
