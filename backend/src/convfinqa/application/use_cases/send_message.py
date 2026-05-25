import logging
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from convfinqa.application.parts_schema import build_envelope
from convfinqa.application.prompts.system_prompt import build_system_prompt
from convfinqa.domain.entities import Conversation, Document, Message
from convfinqa.domain.ports.llm import LLMMessage, LLMPort
from convfinqa.domain.ports.lock import ConversationLockPort
from convfinqa.domain.ports.repository import (
    ConversationRepository,
    DocumentRepository,
)
from convfinqa.domain.value_objects import Role, StopReason, Usage
from convfinqa.logging import get_logger

UPSTREAM_LLM_PUBLIC_DETAIL = "upstream LLM error"

logger = get_logger("convfinqa.send_message")


@dataclass(frozen=True, slots=True)
class ConversationResolved:
    conversation_id: str


@dataclass(frozen=True, slots=True)
class MessageStarted:
    message_id: str


@dataclass(frozen=True, slots=True)
class TextDelta:
    text: str


@dataclass(frozen=True, slots=True)
class ReasoningStart:
    id: str


@dataclass(frozen=True, slots=True)
class ReasoningDelta:
    id: str
    text: str


@dataclass(frozen=True, slots=True)
class ReasoningEnd:
    id: str


@dataclass(frozen=True, slots=True)
class Finish:
    stop_reason: StopReason
    usage: Usage | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ErrorEvent:
    detail: str


@dataclass(frozen=True, slots=True)
class ConcurrentRequest:
    conversation_id: str


StreamEvent = (
    ConversationResolved
    | MessageStarted
    | TextDelta
    | ReasoningStart
    | ReasoningDelta
    | ReasoningEnd
    | Finish
    | ErrorEvent
    | ConcurrentRequest
)


class ConversationNotFoundError(Exception):
    pass


class DocumentNotFoundError(Exception):
    pass


class DocumentIdRequiredError(Exception):
    pass


def _new_message_id() -> str:
    return f"msg_{uuid4().hex}"


def _to_llm_messages(
    conversation: Conversation, latest_user_text: str
) -> list[LLMMessage]:
    history = [
        LLMMessage(role=m.role.value, content=m.content) for m in conversation.messages
    ]
    history.append(LLMMessage(role=Role.USER.value, content=latest_user_text))
    return history


class SendMessageUseCase:
    def __init__(
        self,
        llm: LLMPort,
        conversations: ConversationRepository,
        documents: DocumentRepository,
        locks: ConversationLockPort,
        system_prompt_framing: str,
    ) -> None:
        self._llm = llm
        self._conversations = conversations
        self._documents = documents
        self._locks = locks
        self._framing = system_prompt_framing

    async def stream(
        self,
        user_id: uuid.UUID,
        conversation_id: str | None,
        user_text: str,
        document_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent]:
        conversation, document = await self._resolve_conversation_and_document(
            conversation_id, user_id, document_id
        )
        system_prompt = build_system_prompt(self._framing, document)

        async with self._locks.try_acquire(conversation.id) as acquired:
            if not acquired:
                yield ConcurrentRequest(conversation_id=conversation.id)
                return

            user_message = Message(
                id=_new_message_id(),
                conversation_id=conversation.id,
                role=Role.USER,
                content=user_text,
                created_at=datetime.now(UTC),
            )
            await self._conversations.append_message(conversation.id, user_message)

            yield ConversationResolved(conversation_id=conversation.id)

            assistant_id = _new_message_id()
            yield MessageStarted(message_id=assistant_id)

            buffered: list[str] = []
            parts_in_order: list[dict[str, Any]] = []
            current_text_buffer: list[str] = []
            current_reasoning_id: str | None = None
            reasoning_buffer: list[str] = []
            usage: Usage | None = None
            stop_reason = StopReason.END_TURN
            errored = False

            llm_messages = _to_llm_messages(conversation, user_text)

            try:
                async for chunk in self._llm.stream(llm_messages, system_prompt):
                    if chunk.reasoning_event == "start":
                        if current_text_buffer:
                            parts_in_order.append(
                                {
                                    "kind": "text",
                                    "content": "".join(current_text_buffer),
                                }
                            )
                            current_text_buffer = []
                        current_reasoning_id = f"rsn_{uuid4().hex}"
                        yield ReasoningStart(id=current_reasoning_id)

                    elif (
                        chunk.reasoning_event == "delta"
                        and current_reasoning_id is not None
                    ):
                        reasoning_buffer.append(chunk.reasoning_text)
                        yield ReasoningDelta(
                            id=current_reasoning_id, text=chunk.reasoning_text
                        )

                    elif (
                        chunk.reasoning_event == "end"
                        and current_reasoning_id is not None
                    ):
                        completed_id = current_reasoning_id
                        parts_in_order.append(
                            {
                                "kind": "reasoning",
                                "id": completed_id,
                                "content": "".join(reasoning_buffer),
                            }
                        )
                        reasoning_buffer = []
                        current_reasoning_id = None
                        yield ReasoningEnd(id=completed_id)

                    if chunk.text:
                        buffered.append(chunk.text)
                        current_text_buffer.append(chunk.text)
                        yield TextDelta(text=chunk.text)

                    if chunk.usage is not None:
                        usage = chunk.usage

            except GeneratorExit:
                stop_reason = StopReason.INTERRUPTED
                await self._persist_assistant(
                    conversation.id,
                    assistant_id,
                    "".join(buffered),
                    stop_reason,
                    parts=None,
                )
                raise
            except Exception as exc:  # noqa: BLE001
                errored = True
                stop_reason = StopReason.INTERRUPTED
                logger.log(
                    logging.WARNING,
                    "upstream_llm_error",
                    extra={
                        "exc_type": exc.__class__.__name__,
                        "exc_message": str(exc) or exc.__class__.__name__,
                        "conversation_id": conversation.id,
                    },
                )

            if reasoning_buffer and current_reasoning_id is not None:
                parts_in_order.append(
                    {
                        "kind": "reasoning",
                        "id": current_reasoning_id,
                        "content": "".join(reasoning_buffer),
                    }
                )

            if current_text_buffer:
                parts_in_order.append(
                    {"kind": "text", "content": "".join(current_text_buffer)}
                )

            if not parts_in_order and buffered:
                parts_in_order = [{"kind": "text", "content": "".join(buffered)}]

            parts_dict = build_envelope(parts_in_order) if parts_in_order else None

            finished_at = await self._persist_assistant(
                conversation.id,
                assistant_id,
                "".join(buffered),
                stop_reason,
                parts=parts_dict,
            )

            if errored:
                yield ErrorEvent(detail=UPSTREAM_LLM_PUBLIC_DETAIL)
                return

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
        parts: dict[str, object] | None,
    ) -> datetime:
        created_at = datetime.now(UTC)
        message = Message(
            id=message_id,
            conversation_id=conversation_id,
            role=Role.ASSISTANT,
            content=content,
            created_at=created_at,
            stop_reason=stop_reason,
            parts=parts,
        )
        await self._conversations.append_message(conversation_id, message)
        return created_at
