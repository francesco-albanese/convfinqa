from convfinqa.application.prompts.system_prompt import build_system_prompt
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


def test_prompt_embeds_framing_title_ticker_and_year() -> None:
    prompt = build_system_prompt("YOU ARE CONVFINQA", _document())

    assert prompt.startswith("YOU ARE CONVFINQA")
    assert "ACME 2024 annual report" in prompt
    assert "Ticker: ACME" in prompt
    assert "Year: 2024" in prompt


def test_prompt_does_not_inline_table_json() -> None:
    prompt = build_system_prompt("f", _document())

    assert '"rev"' not in prompt
    assert "Table (JSON)" not in prompt


def test_prompt_embeds_full_pre_and_post_text_verbatim() -> None:
    huge_pre = "PRE-" + "A" * 50_000
    huge_post = "POST-" + "B" * 50_000
    prompt = build_system_prompt("f", _document(pre_text=huge_pre, post_text=huge_post))

    assert huge_pre in prompt
    assert huge_post in prompt
    assert "[truncated]" not in prompt


def test_prompt_handles_none_text_fields_without_crashing() -> None:
    prompt = build_system_prompt("f", _document(pre_text=None, post_text=None))

    assert "Pre-table narrative" in prompt
    assert "Post-table narrative" in prompt
