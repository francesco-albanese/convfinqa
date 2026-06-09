import asyncio
import contextlib
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
from convfinqa.application.agent.tool_executor import TOOL_TIMEOUT_MATH_S, execute_tool
from convfinqa.application.agent.wire import (
    build_tool_specs,
    history_to_wire,
    new_message_id,
)
from convfinqa.application.domain_boundary import (
    DomainBoundaryAction,
    DomainBoundaryPolicy,
)
from convfinqa.application.output_guard import StreamingOutputGuard
from convfinqa.application.parts_schema import build_envelope
from convfinqa.application.prompt_injection_detector import (
    PROMPT_INJECTION_REFUSAL,
    PromptInjectionAction,
    PromptInjectionDetector,
    PromptInjectionSurface,
)
from convfinqa.application.prompts.system_prompt import build_system_prompt
from convfinqa.application.prompts.tool_docs import build_tool_docs
from convfinqa.application.use_cases.title_generation import generate_title
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
    "ConversationTitle",
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
        prompt_injection_detector: PromptInjectionDetector | None = None,
    ) -> None:
        self._llm = llm
        self._conversations = conversations
        self._documents = documents
        self._locks = locks
        self._framing = system_prompt_framing
        self._observability = observability
        self._llm_model = llm_model
        self._environment = environment
        self._domain_boundary = DomainBoundaryPolicy()
        self._prompt_injection_detector = (
            prompt_injection_detector or PromptInjectionDetector()
        )

    async def stream(
        self,
        user_id: uuid.UUID,
        conversation_id: str | None,
        user_text: str,
        document_id: str | None = None,
        model: str | None = None,
    ) -> AsyncGenerator[StreamEvent]:
        resolved_model = model or self._llm_model
        async with self._observability.start_as_current_observation(
            as_type="agent",
            name="send_message",
            input={"user_text": user_text, "document_id": document_id},
        ) as span:
            try:
                conversation, document = await self._resolve_conversation_and_document(
                    conversation_id, user_id, document_id
                )
                self._observability.propagate_attributes(
                    user_id=str(user_id),
                    session_id=conversation.id,
                    metadata={"document_id": document.id, "llm_model": resolved_model},
                    tags=[f"environment:{self._environment}"],
                )
                system_prompt = (
                    build_system_prompt(self._framing, document)
                    + "\n\n"
                    + build_tool_docs()
                )
                tool_specs = build_tool_specs()
            except Exception:
                span.set_error()
                raise

            async with self._locks.try_acquire(conversation.id) as acquired:
                if not acquired:
                    yield ConcurrentRequest(conversation_id=conversation.id)
                    return

                yield ConversationResolved(conversation_id=conversation.id)

                assistant_id = new_message_id()
                yield MessageStarted(message_id=assistant_id)

                try:
                    injection_decision = self._prompt_injection_detector.decide(
                        user_text,
                        PromptInjectionSurface.USER_TEXT,
                    )
                except Exception as exc:  # noqa: BLE001
                    span.set_error()
                    logger.log(
                        logging.WARNING,
                        "prompt_injection_detector_failed",
                        extra={
                            "exc_type": exc.__class__.__name__,
                            "exc_message": str(exc) or exc.__class__.__name__,
                            "conversation_id": conversation.id,
                        },
                    )
                    span.set_output(PROMPT_INJECTION_REFUSAL)
                    async for event in self._respond_without_model(
                        conversation.id,
                        assistant_id,
                        PROMPT_INJECTION_REFUSAL,
                    ):
                        yield event
                    return
                if injection_decision.action == PromptInjectionAction.BLOCK:
                    span.set_output(PROMPT_INJECTION_REFUSAL)
                    async for event in self._respond_without_model(
                        conversation.id,
                        assistant_id,
                        PROMPT_INJECTION_REFUSAL,
                    ):
                        yield event
                    return

                boundary_decision = self._domain_boundary.decide(user_text, document)
                if (
                    boundary_decision.action
                    == DomainBoundaryAction.RESPOND_WITH_POLICY_MESSAGE
                ):
                    span.set_output(boundary_decision.response or "")
                    async for event in self._respond_without_model(
                        conversation.id,
                        assistant_id,
                        boundary_decision.response or "",
                    ):
                        yield event
                    return

                user_msg = Message(
                    id=new_message_id(),
                    conversation_id=conversation.id,
                    role=Role.USER,
                    content=user_text,
                    created_at=datetime.now(UTC),
                )
                await self._conversations.append_message(conversation.id, user_msg)

                title_task: asyncio.Task[str | None] | None = None
                if self._should_generate_title(conversation):
                    title_task = asyncio.create_task(
                        generate_title(self._llm, user_text, document, resolved_model)
                    )

                wire_messages = history_to_wire(conversation, user_text)
                parts_in_order: list[dict[str, Any]] = []
                text_chunks: list[str] = []
                current_text_buffer: list[str] = []
                reasoning_signatures: dict[str, str] = {}
                seen_citations: set[tuple[str, str]] = set()
                usage: Usage | None = None
                stop_reason = StopReason.END_TURN
                errored = False
                output_blocked = False

                try:
                    for iteration in range(ITERATION_CAP):
                        state = IterationState()
                        assistant_thinking_blocks: list[dict[str, Any]] = []
                        output_guard = StreamingOutputGuard()

                        async for event in process_llm_chunks(
                            self._llm.stream(
                                wire_messages,
                                system_prompt,
                                tool_specs,
                                generation_name=f"iteration-{iteration}",
                                trace_user_id=str(user_id),
                                session_id=conversation.id,
                                environment=self._environment,
                                model=resolved_model,
                            ),
                            state,
                            parts_in_order,
                            text_chunks,
                            current_text_buffer,
                            reasoning_signatures,
                            assistant_thinking_blocks,
                            output_guard,
                        ):
                            yield event

                        usage = state.usage
                        if output_guard.blocked:
                            output_blocked = True
                            break

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
                                {
                                    "kind": "text",
                                    "content": "".join(current_text_buffer),
                                }
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
                            self._observability,
                        ):
                            yield event

                except GeneratorExit:
                    stop_reason = StopReason.INTERRUPTED
                    span.set_error()
                    await self._cancel_title_task(title_task)
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

                try:
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

                    if output_blocked:
                        span.set_output("".join(text_chunks))
                        yield Finish(
                            stop_reason=stop_reason,
                            usage=usage,
                            created_at=finished_at,
                        )
                        return

                    if title_task is not None:
                        title = await self._resolve_title(title_task, conversation.id)
                        if title is not None:
                            yield ConversationTitle(
                                conversation_id=conversation.id, title=title
                            )

                    span.set_output("".join(text_chunks))
                    yield Finish(
                        stop_reason=stop_reason, usage=usage, created_at=finished_at
                    )
                finally:
                    await self._cancel_title_task(title_task)

    async def _resolve_title(
        self, title_task: asyncio.Task[str | None], conversation_id: str
    ) -> str | None:
        try:
            title = await title_task
            if title is None:
                return None
            await self._conversations.set_title(conversation_id, title)
            return title
        except Exception as exc:  # noqa: BLE001
            logger.log(
                logging.WARNING,
                "title_generation_failed",
                extra={
                    "exc_type": exc.__class__.__name__,
                    "exc_message": str(exc) or exc.__class__.__name__,
                    "conversation_id": conversation_id,
                },
            )
            return None

    @staticmethod
    def _should_generate_title(conversation: Conversation) -> bool:
        title = getattr(conversation, "title", None)
        messages = getattr(conversation, "messages", ())
        return not (title or "").strip() and not any(
            message.role == Role.USER for message in messages
        )

    @staticmethod
    async def _cancel_title_task(title_task: asyncio.Task[str | None] | None) -> None:
        if title_task is None or title_task.done():
            return
        title_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await title_task

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

    async def _respond_without_model(
        self, conversation_id: str, message_id: str, content: str
    ) -> AsyncGenerator[StreamEvent]:
        parts_in_order: list[dict[str, Any]] = [{"kind": "text", "content": content}]
        yield TextDelta(text=content)
        finished_at = await self._persist_assistant(
            conversation_id,
            message_id,
            content,
            StopReason.END_TURN,
            parts_in_order,
            {},
        )
        yield Finish(
            stop_reason=StopReason.END_TURN, usage=None, created_at=finished_at
        )

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
