import json
from collections.abc import AsyncIterator

from convfinqa.application.use_cases.send_message import (
    ConversationCreated,
    ErrorEvent,
    Finish,
    MessageStarted,
    StreamEvent,
    TextDelta,
)

DONE_FRAME = "data: [DONE]\n\n"
UI_MESSAGE_STREAM_HEADERS = {
    "x-vercel-ai-ui-message-stream": "v1",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}


def _frame(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"


async def to_ui_message_stream(
    events: AsyncIterator[StreamEvent],
) -> AsyncIterator[str]:
    conversation_id: str | None = None
    text_id: str | None = None

    async for event in events:
        match event:
            case ConversationCreated(conversation_id=cid):
                conversation_id = cid
            case MessageStarted(message_id=mid):
                text_id = mid
                yield _frame({"type": "start", "messageId": mid})
                yield _frame(
                    {
                        "type": "data-conversation",
                        "data": {"conversationId": conversation_id},
                    }
                )
                yield _frame({"type": "text-start", "id": mid})
            case TextDelta(text=text):
                assert text_id is not None
                yield _frame({"type": "text-delta", "id": text_id, "delta": text})
            case Finish():
                if text_id is not None:
                    yield _frame({"type": "text-end", "id": text_id})
                yield _frame({"type": "finish"})
                yield DONE_FRAME
            case ErrorEvent(detail=detail):
                yield _frame({"type": "error", "errorText": detail})
                yield DONE_FRAME
