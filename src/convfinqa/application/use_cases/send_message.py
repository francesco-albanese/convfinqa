from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from convfinqa.domain.entities import Conversation, Message
from convfinqa.domain.ports.llm import LLMMessage, LLMPort
from convfinqa.domain.ports.repository import ConversationRepository
from convfinqa.domain.value_objects import Role, StopReason, Usage


@dataclass(frozen=True, slots=True)
class ConversationCreated:
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


StreamEvent = ConversationCreated | MessageStarted | TextDelta | Finish | ErrorEvent


class ConversationNotFoundError(Exception):
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
        system_prompt: str,
    ) -> None:
        self._llm = llm
        self._conversations = conversations
        self._system_prompt = system_prompt

    async def stream(
        self,
        user_id: str,
        conversation_id: str | None,
        user_text: str,
    ) -> AsyncGenerator[StreamEvent]:
        conversation = await self._resolve_conversation(conversation_id, user_id)
        yield ConversationCreated(conversation_id=conversation.id)

        now = datetime.now(UTC)
        user_message = Message(
            id=_new_message_id(),
            conversation_id=conversation.id,
            role=Role.USER,
            content=user_text,
            created_at=now,
        )
        await self._conversations.append_message(conversation.id, user_message)

        assistant_id = _new_message_id()
        yield MessageStarted(message_id=assistant_id)

        buffered: list[str] = []
        usage: Usage | None = None
        stop_reason = StopReason.END_TURN
        errored = False
        error_detail = ""

        llm_messages = _to_llm_messages(conversation, user_text)

        try:
            async for chunk in self._llm.stream(llm_messages, self._system_prompt):
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

    async def _resolve_conversation(
        self, conversation_id: str | None, user_id: str
    ) -> Conversation:
        if conversation_id is None:
            return await self._conversations.create(user_id)
        existing = await self._conversations.get(conversation_id, user_id)
        if existing is None:
            raise ConversationNotFoundError(conversation_id)
        return existing

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
