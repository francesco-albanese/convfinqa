from datetime import UTC, datetime

from convfinqa.application.agent.wire import history_to_wire
from convfinqa.application.prompts.system_prompt import build_system_prompt
from convfinqa.application.prompts.tool_docs import build_tool_docs
from convfinqa.domain.entities import Conversation, Document, Message
from convfinqa.domain.value_objects import Role


def _document(
    pre_text: str | None = "",
    post_text: str | None = "",
    conv_questions: tuple[str, ...] | None = None,
) -> Document:
    return Document(
        id="doc-id",
        ticker="ACME",
        year=2024,
        page=1,
        title="ACME 2024 annual report",
        pre_text=pre_text,
        post_text=post_text,
        table_data={"rev": [1, 2]},
        conv_questions=conv_questions,
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


CANONICAL_QUESTIONS = (
    "what is the net cash from operating activities in 2009?",
    "what about in 2008?",
    "what is the net change?",
)


def test_system_prompt_never_leaks_canonical_conv_questions() -> None:
    document = _document(
        pre_text="some narrative",
        post_text="more narrative",
        conv_questions=CANONICAL_QUESTIONS,
    )

    system_prompt = (
        build_system_prompt("YOU ARE CONVFINQA", document) + "\n\n" + build_tool_docs()
    )

    for question in CANONICAL_QUESTIONS:
        assert question not in system_prompt


def test_wire_message_history_carries_only_real_turns_not_conv_questions() -> None:
    now = datetime.now(UTC)
    conversation = Conversation(
        id="conv-1",
        user_id="user-1",
        document_id="doc-id",
        created_at=now,
        messages=(
            Message(
                id="m1",
                conversation_id="conv-1",
                role=Role.USER,
                content="what was revenue?",
                created_at=now,
            ),
            Message(
                id="m2",
                conversation_id="conv-1",
                role=Role.ASSISTANT,
                content="Revenue was 1.2B.",
                created_at=now,
            ),
        ),
    )

    wire = history_to_wire(conversation, user_text="and operating income?")

    wire_text = [message["content"] for message in wire]
    assert wire_text == [
        "what was revenue?",
        "Revenue was 1.2B.",
        "and operating income?",
    ]
    serialized = str(wire)
    for question in CANONICAL_QUESTIONS:
        assert question not in serialized
