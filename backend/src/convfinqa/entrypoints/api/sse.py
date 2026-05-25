import json
from collections.abc import AsyncIterator
from typing import cast

from convfinqa.application.use_cases.send_message import (
    ConcurrentRequest,
    ConversationResolved,
    ErrorEvent,
    Finish,
    MessageStarted,
    ReasoningDelta,
    ReasoningEnd,
    ReasoningStart,
    StreamEvent,
    TextDelta,
)


async def prepend_event(
    first: StreamEvent, rest: AsyncIterator[StreamEvent]
) -> AsyncIterator[StreamEvent]:
    yield first
    async for event in rest:
        yield event


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
            case ConversationResolved(conversation_id=cid):
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
                yield _frame(
                    {"type": "text-delta", "id": cast(str, text_id), "delta": text}
                )
            case ReasoningStart(id=block_id):
                yield _frame({"type": "reasoning-start", "id": block_id})
            case ReasoningDelta(id=block_id, text=text):
                yield _frame({"type": "reasoning-delta", "id": block_id, "delta": text})
            case ReasoningEnd(id=block_id):
                yield _frame({"type": "reasoning-end", "id": block_id})
            case Finish():
                if text_id is not None:
                    yield _frame({"type": "text-end", "id": text_id})
                yield _frame({"type": "finish"})
                yield DONE_FRAME
            case ErrorEvent(detail=detail):
                yield _frame({"type": "error", "errorText": detail})
                yield DONE_FRAME
            case ConcurrentRequest():
                # exhaustiveness only: the route peeks the first event and converts
                # ConcurrentRequest into a 409 problem+json before constructing
                # StreamingResponse, so this branch cannot be reached at runtime.
                return
