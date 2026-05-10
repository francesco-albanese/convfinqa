from collections.abc import AsyncGenerator
from typing import cast

import pytest

from convfinqa.application.use_cases.send_message import (
    ConversationResolved,
    MessageStarted,
    SendMessageUseCase,
    StreamEvent,
    TextDelta,
)
from convfinqa.config import Settings
from convfinqa.entrypoints.api.chat import ChatRequest, sync_chat
from convfinqa.entrypoints.api.errors import UpstreamLLMError


class _StubSendMessage:
    async def stream(
        self,
        user_id: str,
        conversation_id: str | None,
        user_text: str,
    ) -> AsyncGenerator[StreamEvent]:
        yield ConversationResolved(conversation_id="conv_xyz")
        yield MessageStarted(message_id="msg_xyz")
        yield TextDelta(text="hi")


@pytest.mark.asyncio
async def test_sync_chat_raises_upstream_error_when_finish_event_missing() -> None:
    with pytest.raises(UpstreamLLMError, match="missing Finish event"):
        await sync_chat(
            body=ChatRequest(message="hi"),
            user_id="alice",
            send_message=cast(SendMessageUseCase, _StubSendMessage()),
            settings=Settings(),
        )
