import json
from collections.abc import AsyncIterator
from typing import cast

from convfinqa.application.use_cases.send_message import (
    Citation,
    ConcurrentRequest,
    ConversationResolved,
    ConversationTitle,
    ErrorEvent,
    Finish,
    MessageStarted,
    ReasoningDelta,
    ReasoningEnd,
    ReasoningStart,
    StreamEvent,
    TextDelta,
    ToolCallArgsComplete,
    ToolCallArgsDelta,
    ToolCallStart,
    ToolResult,
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


def _safe_json(raw: str) -> object:
    """Parse JSON safely; return the raw string on failure rather than crashing."""
    if raw == "":
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


async def to_ui_message_stream(
    events: AsyncIterator[StreamEvent],
) -> AsyncIterator[str]:
    conversation_id: str | None = None
    text_id: str | None = None
    tool_names: dict[str, str] = {}

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
            case ToolCallStart(call_id=cid, name=name):
                tool_names[cid] = name
                yield _frame(
                    {
                        "type": "tool-input-start",
                        "toolCallId": cid,
                        "toolName": name,
                        "dynamic": True,
                    }
                )
            case ToolCallArgsDelta(call_id=cid, delta=delta):
                yield _frame(
                    {
                        "type": "tool-input-delta",
                        "toolCallId": cid,
                        "inputTextDelta": delta,
                    }
                )
            case ToolCallArgsComplete(call_id=cid, args=args):
                yield _frame(
                    {
                        "type": "tool-input-available",
                        "toolCallId": cid,
                        "toolName": tool_names.get(cid, ""),
                        "input": _safe_json(args),
                        "dynamic": True,
                    }
                )
            case ToolResult(call_id=cid, result=result, is_error=is_error):
                if is_error:
                    yield _frame(
                        {
                            "type": "tool-output-error",
                            "toolCallId": cid,
                            "errorText": result,
                        }
                    )
                else:
                    yield _frame(
                        {
                            "type": "tool-output-available",
                            "toolCallId": cid,
                            "output": _safe_json(result),
                        }
                    )
            case Finish():
                if text_id is not None:
                    yield _frame({"type": "text-end", "id": text_id})
                yield _frame({"type": "finish"})
                yield DONE_FRAME
            case ErrorEvent(detail=detail):
                yield _frame({"type": "error", "errorText": detail})
                yield DONE_FRAME
            case Citation(row_label=row_label, col_label=col_label):
                yield _frame(
                    {
                        "type": "data-citation",
                        "data": {"rowLabel": row_label, "colLabel": col_label},
                    }
                )
            case ConversationTitle(conversation_id=cid, title=title):
                yield _frame(
                    {
                        "type": "data-title",
                        "data": {"conversationId": cid, "title": title},
                    }
                )
            case ConcurrentRequest():
                return
