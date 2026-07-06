import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from convfinqa.application.agent.runner import AgentRunBuffers, stream_agent_iterations
from convfinqa.application.agent.stream_events import (
    ConcurrentRequest,
    ConversationResolved,
    ConversationTitle,
    ErrorEvent,
    Finish,
    MessageStarted,
    StreamEvent,
)
from convfinqa.application.agent.wire import (
    build_tool_specs,
    history_to_wire,
    new_message_id,
)
from convfinqa.application.domain_boundary import DomainBoundaryPolicy
from convfinqa.application.prompt_injection_detector import PromptInjectionDetector
from convfinqa.application.prompts.system_prompt import build_system_prompt_variables
from convfinqa.application.prompts.tool_docs import build_tool_docs
from convfinqa.application.security_signals import (
    SecuritySignals,
    classify_provider_error,
)
from convfinqa.application.suspicious_attempt_throttle import SuspiciousAttemptThrottle
from convfinqa.application.use_cases.send_message_support import (
    cancel_title_task,
    guard_user_turn,
    persist_assistant,
    resolve_conversation_and_document,
    resolve_title,
    respond_without_model,
    should_generate_title,
)
from convfinqa.application.use_cases.title_generation import generate_title
from convfinqa.domain.entities import Message
from convfinqa.domain.ports.llm import LLMPort, PromptRef
from convfinqa.domain.ports.lock import ConversationLockPort
from convfinqa.domain.ports.observability import ObservabilityPort
from convfinqa.domain.ports.prompts import PromptProviderPort
from convfinqa.domain.ports.repository import (
    ConversationRepository,
    DocumentRepository,
)
from convfinqa.domain.value_objects import Role, StopReason
from convfinqa.logging import get_logger

logger = get_logger("convfinqa.send_message")


class SendMessageUseCase:
    def __init__(
        self,
        llm: LLMPort,
        conversations: ConversationRepository,
        documents: DocumentRepository,
        locks: ConversationLockPort,
        prompt_provider: PromptProviderPort,
        observability: ObservabilityPort,
        llm_model: str,
        environment: str,
        prompt_injection_detector: PromptInjectionDetector | None = None,
        system_prompt_label: str = "production",
        security_signals: SecuritySignals | None = None,
        suspicious_throttle: SuspiciousAttemptThrottle | None = None,
    ) -> None:
        self._llm = llm
        self._conversations = conversations
        self._documents = documents
        self._locks = locks
        self._prompt_provider = prompt_provider
        self._observability = observability
        self._llm_model = llm_model
        self._environment = environment
        self._system_prompt_label = system_prompt_label
        self._domain_boundary = DomainBoundaryPolicy()
        self._prompt_injection_detector = (
            prompt_injection_detector or PromptInjectionDetector()
        )
        self._security_signals = security_signals or SecuritySignals()
        self._suspicious_throttle = suspicious_throttle

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
                conversation, document = await resolve_conversation_and_document(
                    conversations=self._conversations,
                    documents=self._documents,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    document_id=document_id,
                )
                self._observability.propagate_attributes(
                    user_id=str(user_id),
                    session_id=conversation.id,
                    metadata={"document_id": document.id, "llm_model": resolved_model},
                    tags=[f"environment:{self._environment}"],
                )
                compiled_prompt = await self._prompt_provider.compile(
                    "convfinqa-system",
                    self._system_prompt_label,
                    build_system_prompt_variables(document, build_tool_docs()),
                )
                system_prompt = compiled_prompt.text
                prompt_ref = (
                    PromptRef(
                        name="convfinqa-system",
                        label=self._system_prompt_label,
                        version=compiled_prompt.version,
                    )
                    if compiled_prompt.version is not None
                    else None
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

                guard_result = await guard_user_turn(
                    detector=self._prompt_injection_detector,
                    domain_boundary=self._domain_boundary,
                    user_text=user_text,
                    document=document,
                    conversation_id=conversation.id,
                    user_id=user_id,
                    model=resolved_model,
                    security_signals=self._security_signals,
                    suspicious_throttle=self._suspicious_throttle,
                )
                if guard_result.response is not None:
                    if guard_result.detector_failed:
                        span.set_error()
                    span.set_output(guard_result.response)
                    async for event in respond_without_model(
                        self._conversations,
                        conversation.id,
                        assistant_id,
                        guard_result.response,
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
                if should_generate_title(conversation):
                    title_task = asyncio.create_task(
                        generate_title(self._llm, user_text, document, resolved_model)
                    )

                buffers = AgentRunBuffers(
                    wire_messages=history_to_wire(conversation, user_text)
                )
                errored = False

                try:
                    async for event in stream_agent_iterations(
                        llm=self._llm,
                        buffers=buffers,
                        system_prompt=system_prompt,
                        tool_specs=tool_specs,
                        document=document,
                        observability=self._observability,
                        user_id=user_id,
                        conversation_id=conversation.id,
                        environment=self._environment,
                        model=resolved_model,
                        prompt_ref=prompt_ref,
                        security_signals=self._security_signals,
                    ):
                        yield event
                except GeneratorExit:
                    buffers.stop_reason = StopReason.INTERRUPTED
                    span.set_error()
                    await cancel_title_task(title_task)
                    buffers.flush_current_text_part()
                    await persist_assistant(
                        self._conversations,
                        conversation.id,
                        assistant_id,
                        buffers.content,
                        buffers.stop_reason,
                        buffers.parts_in_order,
                        buffers.reasoning_signatures,
                    )
                    raise
                except Exception as exc:  # noqa: BLE001
                    errored = True
                    buffers.stop_reason = StopReason.INTERRUPTED
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
                    provider_condition = classify_provider_error(exc)
                    if provider_condition is not None:
                        self._security_signals.provider_throttled(
                            conversation_id=conversation.id,
                            model=resolved_model,
                            condition=provider_condition,
                            exc_type=exc.__class__.__name__,
                        )

                buffers.flush_current_text_part()

                try:
                    finished_at = await persist_assistant(
                        self._conversations,
                        conversation.id,
                        assistant_id,
                        buffers.content,
                        buffers.stop_reason,
                        buffers.parts_in_order,
                        buffers.reasoning_signatures,
                    )

                    if errored:
                        yield ErrorEvent(detail="upstream LLM error")
                        return

                    if buffers.output_blocked:
                        span.set_output(buffers.content)
                        yield Finish(
                            stop_reason=buffers.stop_reason,
                            usage=buffers.usage,
                            created_at=finished_at,
                        )
                        return

                    if title_task is not None:
                        title = await resolve_title(
                            self._conversations, title_task, conversation.id
                        )
                        if title is not None:
                            yield ConversationTitle(
                                conversation_id=conversation.id, title=title
                            )

                    span.set_output(buffers.content)
                    yield Finish(
                        stop_reason=buffers.stop_reason,
                        usage=buffers.usage,
                        created_at=finished_at,
                    )
                finally:
                    await cancel_title_task(title_task)
