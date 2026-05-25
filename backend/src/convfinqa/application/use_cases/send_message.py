import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from convfinqa.application.agent.chunks import process_llm_chunks
from convfinqa.application.agent.iteration import ITERATION_CAP, IterationState
from convfinqa.application.agent.replay import execute_and_replay_tools
from convfinqa.application.agent.stream_events import (
    Citation,
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
    ToolCallArgsComplete,
    ToolCallArgsDelta,
    ToolCallStart,
    ToolResult,
)
from convfinqa.application.agent.tool_executor import TOOL_TIMEOUT_MATH_S, execute_tool
from convfinqa.application.agent.wire import (
    build_tool_specs,
    history_to_wire,
    new_message_id,
)
from convfinqa.application.parts_schema import build_envelope
from convfinqa.application.prompts.system_prompt import build_system_prompt
from convfinqa.application.prompts.tool_docs import build_tool_docs
from convfinqa.domain.entities import Conversation, Document, Message
from convfinqa.domain.ports.llm import LLMPort
from convfinqa.domain.ports.lock import ConversationLockPort
from convfinqa.domain.ports.observability import ObservabilityPort
from convfinqa.domain.ports.repository import (
    ConversationRepository,
    DocumentRepository,
)
from convfinqa.domain.value_objects import Role, StopReason, Usage
from convfinqa.logging import get_logger

__all__ = [
    "SendMessageUseCase",
    "StreamEvent",
    "ConversationResolved",
    "MessageStarted",
    "TextDelta",
    "ReasoningStart",
    "ReasoningDelta",
    "ReasoningEnd",
    "ToolCallStart",
    "ToolCallArgsDelta",
    "ToolCallArgsComplete",
    "ToolResult",
    "Citation",
    "Finish",
    "ErrorEvent",
    "ConcurrentRequest",
    "ConversationNotFoundError",
    "DocumentNotFoundError",
    "DocumentIdRequiredError",
    "ITERATION_CAP",
    "TOOL_TIMEOUT_MATH_S",
    "_execute_tool",
]

UPSTREAM_LLM_PUBLIC_DETAIL = "upstream LLM error"

logger = get_logger("convfinqa.send_message")

_execute_tool = execute_tool


class ConversationNotFoundError(Exception):
    pass


class DocumentNotFoundError(Exception):
    pass


class DocumentIdRequiredError(Exception):
    pass


class SendMessageUseCase:
    def __init__(
        self,
        llm: LLMPort,
        conversations: ConversationRepository,
        documents: DocumentRepository,
        locks: ConversationLockPort,
        system_prompt_framing: str,
        observability: ObservabilityPort,
        llm_model: str,
        environment: str,
    ) -> None:
        self._llm = llm
        self._conversations = conversations
        self._documents = documents
        self._locks = locks
        self._framing = system_prompt_framing
        self._observability = observability
        self._llm_model = llm_model
        self._environment = environment

    async def stream(
        self,
        user_id: uuid.UUID,
        conversation_id: str | None,
        user_text: str,
        document_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent]:
        async with self._observability.start_as_current_observation(
            as_type="agent",
            name="send_message",
            input={"user_text": user_text, "document_id": document_id},
        ) as span:
            conversation, document = await self._resolve_conversation_and_document(
                conversation_id, user_id, document_id
            )
            self._observability.propagate_attributes(
                user_id=str(user_id),
                session_id=conversation.id,
                metadata={"document_id": document.id, "llm_model": self._llm_model},
                tags=[f"environment:{self._environment}"],
            )
            system_prompt = (
                build_system_prompt(self._framing, document) + "\n\n" + build_tool_docs()
            )
            tool_specs = build_tool_specs()

            async with self._locks.try_acquire(conversation.id) as acquired:
                if not acquired:
                    yield ConcurrentRequest(conversation_id=conversation.id)
                    return

                user_msg = Message(
                    id=new_message_id(),
                    conversation_id=conversation.id,
                    role=Role.USER,
                    content=user_text,
                    created_at=datetime.now(UTC),
                )
                await self._conversations.append_message(conversation.id, user_msg)

                yield ConversationResolved(conversation_id=conversation.id)

                assistant_id = new_message_id()
                yield MessageStarted(message_id=assistant_id)

                wire_messages = history_to_wire(conversation, user_text)
                parts_in_order: list[dict[str, Any]] = []
                text_chunks: list[str] = []
                current_text_buffer: list[str] = []
                reasoning_signatures: dict[str, str] = {}
                seen_citations: set[tuple[str, str]] = set()
                usage: Usage | None = None
                stop_reason = StopReason.END_TURN
                errored = False

                try:
                    for iteration in range(ITERATION_CAP):
                        state = IterationState()
                        assistant_thinking_blocks: list[dict[str, Any]] = []

                        async for event in process_llm_chunks(
                            self._llm.stream(wire_messages, system_prompt, tool_specs),
                            state,
                            parts_in_order,
                            text_chunks,
                            current_text_buffer,
                            reasoning_signatures,
                            assistant_thinking_blocks,
                        ):
                            yield event

                        usage = state.usage

                        if state.current_reasoning_id:
                            parts_in_order.append(
                                {
                                    "kind": "reasoning",
                                    "id": state.current_reasoning_id,
                                    "content": "".join(state.reasoning_buffer),
                                }
                            )
                            yield ReasoningEnd(id=state.current_reasoning_id)

                        if current_text_buffer:
                            parts_in_order.append(
                                {"kind": "text", "content": "".join(current_text_buffer)}
                            )
                            current_text_buffer.clear()

                        if not state.finish_reason_tool_use or not state.tool_calls:
                            break

                        if iteration == ITERATION_CAP - 1:
                            stop_reason = StopReason.ITERATION_CAP
                            break

                        async for event in execute_and_replay_tools(
                            state.tool_calls,
                            assistant_thinking_blocks,
                            parts_in_order,
                            wire_messages,
                            document,
                            seen_citations,
                        ):
                            yield event

                except GeneratorExit:
                    stop_reason = StopReason.INTERRUPTED
                    span.set_error()
                    if current_text_buffer:
                        parts_in_order.append(
                            {"kind": "text", "content": "".join(current_text_buffer)}
                        )
                    await self._persist_assistant(
                        conversation.id,
                        assistant_id,
                        "".join(text_chunks),
                        stop_reason,
                        parts_in_order,
                        reasoning_signatures,
                    )
                    raise
                except Exception as exc:  # noqa: BLE001
                    errored = True
                    stop_reason = StopReason.INTERRUPTED
                    span.set_error()
                    logger.log(
                        logging.WARNING,
                        "upstream_llm_error",
                        extra={
                            "exc_type": exc.__class__.__name__,
                            "exc_message": str(exc) or exc.__class__.__name__,
                            "conversation_id": conversation.id,
                        },
                    )

                if current_text_buffer:
                    parts_in_order.append(
                        {"kind": "text", "content": "".join(current_text_buffer)}
                    )

                finished_at = await self._persist_assistant(
                    conversation.id,
                    assistant_id,
                    "".join(text_chunks),
                    stop_reason,
                    parts_in_order,
                    reasoning_signatures,
                )

                if errored:
                    yield ErrorEvent(detail=UPSTREAM_LLM_PUBLIC_DETAIL)
                    return

                span.set_output("".join(text_chunks))
                yield Finish(stop_reason=stop_reason, usage=usage, created_at=finished_at)

    async def _resolve_conversation_and_document(
        self,
        conversation_id: str | None,
        user_id: uuid.UUID,
        document_id: str | None,
    ) -> tuple[Conversation, Document]:
        if conversation_id is None:
            if document_id is None:
                raise DocumentIdRequiredError(
                    "document_id is required when starting a new conversation"
                )
            document = await self._fetch_document(document_id)
            conversation = await self._conversations.create(user_id, document_id)
            return conversation, document
        existing = await self._conversations.get(conversation_id, user_id)
        if existing is None:
            raise ConversationNotFoundError(conversation_id)
        document = await self._fetch_document(existing.document_id)
        return existing, document

    async def _fetch_document(self, document_id: str) -> Document:
        document = await self._documents.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)
        return document

    async def _persist_assistant(
        self,
        conversation_id: str,
        message_id: str,
        content: str,
        stop_reason: StopReason,
        parts_in_order: list[dict[str, Any]],
        reasoning_signatures: dict[str, str],
    ) -> datetime:
        created_at = datetime.now(UTC)
        parts_dict = build_envelope(parts_in_order) if parts_in_order else None
        sigs: dict[str, str] | None = (
            reasoning_signatures if reasoning_signatures else None
        )
        message = Message(
            id=message_id,
            conversation_id=conversation_id,
            role=Role.ASSISTANT,
            content=content,
            created_at=created_at,
            stop_reason=stop_reason,
            parts=parts_dict,
            reasoning_signatures=sigs,
        )
        await self._conversations.append_message(conversation_id, message)
        return created_at
