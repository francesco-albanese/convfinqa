import json

from convfinqa.application.prompts.system_prompt import (
    MAX_TEXT_BYTES,
    build_system_prompt,
)
from convfinqa.domain.entities import Document


def _document(pre_text: str | None = "", post_text: str | None = "") -> Document:
    return Document(
        id="doc-id",
        ticker="ACME",
        year=2024,
        page=1,
        title="ACME 2024 annual report",
        pre_text=pre_text,
        post_text=post_text,
        table_data={"rev": [1, 2]},
    )


def test_prompt_embeds_framing_title_ticker_year_and_table_json() -> None:
    prompt = build_system_prompt("YOU ARE CONVFINQA", _document())

    assert prompt.startswith("YOU ARE CONVFINQA")
    assert "ACME 2024 annual report" in prompt
    assert "Ticker: ACME" in prompt
    assert "Year: 2024" in prompt
    assert json.dumps({"rev": [1, 2]}, separators=(",", ":")) in prompt


def test_prompt_truncates_pre_and_post_above_8kb_each() -> None:
    huge = "A" * (MAX_TEXT_BYTES + 5000)
    prompt = build_system_prompt("f", _document(pre_text=huge, post_text=huge))

    assert "[truncated]" in prompt
    assert prompt.count("[truncated]") == 2
    framing_overhead_bound = 4 * 1024
    assert len(prompt.encode("utf-8")) < 2 * MAX_TEXT_BYTES + framing_overhead_bound


def test_prompt_handles_none_text_fields_without_crashing() -> None:
    prompt = build_system_prompt("f", _document(pre_text=None, post_text=None))

    assert "Pre-table narrative" in prompt
    assert "Post-table narrative" in prompt


def test_prompt_truncates_multi_byte_utf8_at_split_boundary_without_decode_error() -> (
    None
):
    multi_byte = "é" * (MAX_TEXT_BYTES + 5000)
    prompt = build_system_prompt(
        "f", _document(pre_text=multi_byte, post_text=multi_byte)
    )

    assert prompt.count("[truncated]") == 2
