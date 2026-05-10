import json
from typing import Any, cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from convfinqa.adapters.persistence.sqlalchemy.models import MessageOrm
from convfinqa.application.use_cases.send_message import TextDelta
from convfinqa.container import Container
from tests.fakes.llm import FakeLLMPort

Frame = dict[str, Any] | str


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _parse_frames(body: str) -> list[Frame]:
    frames: list[Frame] = []
    for raw in body.split("\n\n"):
        if not raw.startswith("data: "):
            continue
        payload = raw[len("data: ") :]
        if payload == "[DONE]":
            frames.append("[DONE]")
        else:
            frames.append(cast(dict[str, Any], json.loads(payload)))
    return frames


def _types(frames: list[Frame]) -> list[str]:
    out: list[str] = []
    for f in frames:
        if isinstance(f, dict):
            out.append(cast(str, f["type"]))
        else:
            out.append(f)
    return out


async def _persisted_messages(
    session_factory: async_sessionmaker[AsyncSession],
) -> list[MessageOrm]:
    async with session_factory() as session:
        result = await session.execute(
            select(MessageOrm).order_by(MessageOrm.created_at)
        )
        return list(result.scalars().all())


@pytest.mark.asyncio
async def test_stream_chat_emits_ai_sdk_v5_frames_in_order_with_streaming_headers(
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with await _client(app) as client:
        response = await client.post(
            "/v1/chat/stream",
            headers={"X-User-Id": "alice"},
            json={"message": "hi"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
    assert response.headers["cache-control"] == "no-cache"

    frames = _parse_frames(response.text)
    assert _types(frames) == [
        "start",
        "data-conversation",
        "text-start",
        "text-delta",
        "text-delta",
        "text-end",
        "finish",
        "[DONE]",
    ]

    start = frames[0]
    data_conv = frames[1]
    text_start = frames[2]
    assert (
        isinstance(start, dict)
        and isinstance(data_conv, dict)
        and isinstance(text_start, dict)
    )

    message_id = cast(str, start["messageId"])
    conversation_id = cast(str, data_conv["data"]["conversationId"])
    assert message_id.startswith("msg_")
    assert conversation_id.startswith("conv_")
    assert text_start["id"] == message_id

    deltas = [
        cast(str, f["delta"])
        for f in frames
        if isinstance(f, dict) and f["type"] == "text-delta"
    ]
    assert "".join(deltas) == "Hello world"

    rows = await _persisted_messages(session_factory)
    assert [r.role for r in rows] == ["user", "assistant"]
    assert rows[1].content == "Hello world"
    assert rows[1].stop_reason == "end_turn"
    assert rows[0].conversation_id == conversation_id


@pytest.mark.asyncio
async def test_stream_chat_mid_stream_llm_error_emits_error_frame_and_done(
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
    fake_llm: FakeLLMPort,
) -> None:
    fake_llm.deltas = ("partial ", "more")
    fake_llm.raise_after = 1
    fake_llm.raise_with = RuntimeError("bedrock said no")

    async with await _client(app) as client:
        response = await client.post(
            "/v1/chat/stream",
            headers={"X-User-Id": "alice"},
            json={"message": "hi"},
        )

    assert response.status_code == 200
    frames = _parse_frames(response.text)
    types = _types(frames)
    assert types[-2:] == ["error", "[DONE]"]
    assert "finish" not in types

    error_frame = frames[-2]
    assert isinstance(error_frame, dict)
    assert "bedrock said no" in str(error_frame["errorText"])

    rows = await _persisted_messages(session_factory)
    assert [r.role for r in rows] == ["user", "assistant"]
    assert rows[1].content == "partial "
    assert rows[1].stop_reason == "interrupted"


@pytest.mark.asyncio
async def test_stream_chat_consumer_aborts_persists_interrupted(
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
    fake_llm: FakeLLMPort,
) -> None:
    # Targets the use-case GeneratorExit handler directly: httpx ASGITransport
    # cannot mid-stream-disconnect (runs the app to completion), but Starlette's
    # StreamingResponse cancels by calling aclose() on the body iterator on
    # client disconnect — so aclose() at the use-case layer exercises the same
    # path that real HTTP disconnect would.
    fake_llm.deltas = ("first ", "second ", "third ", "fourth ")

    container: Container = app.state.container
    events = container.send_message.stream(
        user_id="alice", conversation_id=None, user_text="hi"
    )

    seen_delta = False
    async for event in events:
        if isinstance(event, TextDelta):
            seen_delta = True
            break
    assert seen_delta

    await events.aclose()

    rows = await _persisted_messages(session_factory)
    assert [r.role for r in rows] == ["user", "assistant"]
    assert rows[1].stop_reason == "interrupted"
    assert "first " in rows[1].content


@pytest.mark.asyncio
async def test_stream_chat_provider_portability_handles_gemini_shaped_chunks(
    app: FastAPI,
    fake_llm: FakeLLMPort,
) -> None:
    # Provider-portability smoke: Gemini occasionally emits empty-string deltas
    # and may omit the final usage chunk (see .claude/rules/python/litellm.md).
    # The presenter must finish cleanly without those.
    fake_llm.deltas = ("", "x", "", "y")
    fake_llm.final_usage = None

    async with await _client(app) as client:
        response = await client.post(
            "/v1/chat/stream",
            headers={"X-User-Id": "alice"},
            json={"message": "hi"},
        )

    assert response.status_code == 200
    frames = _parse_frames(response.text)
    types = _types(frames)

    assert types[-3:] == ["text-end", "finish", "[DONE]"]
    deltas = [
        cast(str, f["delta"])
        for f in frames
        if isinstance(f, dict) and f["type"] == "text-delta"
    ]
    assert deltas == ["x", "y"]
