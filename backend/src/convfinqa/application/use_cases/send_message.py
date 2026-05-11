from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from convfinqa.application.prompts.system_prompt import build_system_prompt
from convfinqa.domain.entities import Conversation, Document, Message
from convfinqa.domain.ports.llm import LLMMessage, LLMPort
from convfinqa.domain.ports.lock import ConversationLockPort
from convfinqa.domain.ports.repository import (
    ConversationRepository,
    DocumentRepository,
)
from convfinqa.domain.value_objects import Role, StopReason, Usage


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
        user_id: str,
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
            usage: Usage | None = None
            stop_reason = StopReason.END_TURN
            errored = False
            error_detail = ""

            llm_messages = _to_llm_messages(conversation, user_text)

            try:
                async for chunk in self._llm.stream(llm_messages, system_prompt):
                    if chunk.text:
                        buffered.append(chunk.text)
                        yield TextDelta(text=chunk.text)
                    if chunk.usage is not None:
                        usage = chunk.usage
            except GeneratorExit:
                stop_reason = StopReason.INTERRUPTED
                await self._persist_assistant(
                    conversation.id, assistant_id, "".join(buffered), stop_reason
                )
                raise
            except Exception as exc:  # noqa: BLE001
                errored = True
                stop_reason = StopReason.INTERRUPTED
                error_detail = str(exc) or exc.__class__.__name__

            finished_at = await self._persist_assistant(
                conversation.id, assistant_id, "".join(buffered), stop_reason
            )

            if errored:
                yield ErrorEvent(detail=error_detail)
                return

            yield Finish(stop_reason=stop_reason, usage=usage, created_at=finished_at)

    async def _resolve_conversation_and_document(
        self,
        conversation_id: str | None,
        user_id: str,
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
    ) -> datetime:
        created_at = datetime.now(UTC)
        message = Message(
            id=message_id,
            conversation_id=conversation_id,
            role=Role.ASSISTANT,
            content=content,
            created_at=created_at,
            stop_reason=stop_reason,
        )
        await self._conversations.append_message(conversation_id, message)
        return created_at
