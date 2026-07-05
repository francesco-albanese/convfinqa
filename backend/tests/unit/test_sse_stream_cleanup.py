from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest

from convfinqa.application.agent.stream_events import (
    ConversationResolved,
    Finish,
    MessageStarted,
    StreamEvent,
    TextDelta,
)
from convfinqa.domain.value_objects import StopReason
from convfinqa.entrypoints.api.sse import DONE_FRAME, ui_message_stream_body


@pytest.mark.asyncio
async def test_source_generator_is_closed_in_the_consuming_task() -> None:
    cleanup_ran = False

    async def events() -> AsyncGenerator[StreamEvent]:
        nonlocal cleanup_ran
        try:
            yield ConversationResolved(conversation_id="conv-1")
            yield MessageStarted(message_id="msg-1")
            yield TextDelta(text="answer")
            yield Finish(
                stop_reason=StopReason.END_TURN,
                usage=None,
                created_at=datetime.now(UTC),
            )
        finally:
            cleanup_ran = True

    source = events()
    first = await anext(source)

    frames = [frame async for frame in ui_message_stream_body(first, source)]

    assert frames[-1] == DONE_FRAME
    assert cleanup_ran, (
        "the use-case generator must be closed by the SSE body iterator itself, "
        "not left for event-loop GC finalization in a foreign context"
    )
