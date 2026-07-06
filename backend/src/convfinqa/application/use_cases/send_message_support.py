import asyncio
import contextlib
import logging
import uuid
from collections.abc import AsyncGenerator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from convfinqa.application.agent.stream_events import Finish, StreamEvent, TextDelta
from convfinqa.application.domain_boundary import (
    APP_CAPABILITY_REASON,
    PROTECTED_INTERNALS_REASON,
    ROLE_CHANGE_REASON,
    DomainBoundaryAction,
    DomainBoundaryPolicy,
)
from convfinqa.application.parts_schema import build_envelope
from convfinqa.application.prompt_injection_detector import (
    PROMPT_INJECTION_REFUSAL,
    PromptInjectionAction,
    PromptInjectionDetector,
    PromptInjectionSurface,
)
from convfinqa.application.prompts.ab_selector import (
    DEFAULT_LABEL,
    resolve_served_label,
)
from convfinqa.application.security_signals import SecuritySignals
from convfinqa.application.suspicious_attempt_throttle import (
    SUSPICIOUS_ACTIVITY_REFUSAL,
    SuspiciousAttemptThrottle,
)
from convfinqa.domain.entities import Conversation, Document, Message
from convfinqa.domain.ports.llm import PromptRef
from convfinqa.domain.ports.prompts import PromptProviderPort
from convfinqa.domain.ports.repository import (
    ConversationRepository,
    DocumentRepository,
)
from convfinqa.domain.value_objects import Role, StopReason
from convfinqa.logging import get_logger

logger = get_logger("convfinqa.send_message")

SYSTEM_PROMPT_NAME = "convfinqa-system"


async def resolve_system_prompt(
    prompt_provider: PromptProviderPort,
    system_prompt_label: str,
    user_id: uuid.UUID,
    variables: Mapping[str, object],
) -> tuple[str, PromptRef | None]:
    compiled_prompt = await prompt_provider.compile(
        SYSTEM_PROMPT_NAME, system_prompt_label, variables
    )
    served_label = system_prompt_label

    if system_prompt_label == DEFAULT_LABEL:
        served_label, malformed = resolve_served_label(
            compiled_prompt.config.get("ab"), str(user_id)
        )
        if malformed:
            logger.warning(
                "malformed_ab_config",
                extra={"prompt_name": SYSTEM_PROMPT_NAME, "user_id": str(user_id)},
            )
        if served_label != system_prompt_label:
            compiled_prompt = await prompt_provider.compile(
                SYSTEM_PROMPT_NAME, served_label, variables
            )

    prompt_ref = (
        PromptRef(
            name=SYSTEM_PROMPT_NAME, label=served_label, version=compiled_prompt.version
        )
        if compiled_prompt.version is not None
        else None
    )
    return compiled_prompt.text, prompt_ref


SUSPICIOUS_BOUNDARY_REASONS = frozenset(
    {PROTECTED_INTERNALS_REASON, ROLE_CHANGE_REASON}
)


class ConversationNotFoundError(Exception):
    pass


class DocumentNotFoundError(Exception):
    pass


class DocumentIdRequiredError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class UserTurnGuardResult:
    response: str | None = None
    detector_failed: bool = False


async def guard_user_turn(
    *,
    detector: PromptInjectionDetector,
    domain_boundary: DomainBoundaryPolicy,
    user_text: str,
    document: Document,
    conversation_id: str,
    user_id: uuid.UUID,
    model: str,
    security_signals: SecuritySignals,
    suspicious_throttle: SuspiciousAttemptThrottle | None,
) -> UserTurnGuardResult:
    try:
        injection_decision = detector.decide(
            user_text,
            PromptInjectionSurface.USER_TEXT,
        )
    except Exception as exc:  # noqa: BLE001
        logger.log(
            logging.WARNING,
            "prompt_injection_detector_failed",
            extra={
                "exc_type": exc.__class__.__name__,
                "exc_message": str(exc) or exc.__class__.__name__,
                "conversation_id": conversation_id,
            },
        )
        security_signals.prompt_injection_detected(
            conversation_id=conversation_id,
            document_id=document.id,
            model=model,
            action=PromptInjectionAction.BLOCK.value,
            families=(),
            surfaces=(),
            detector_failed=True,
        )
        return UserTurnGuardResult(
            response=PROMPT_INJECTION_REFUSAL,
            detector_failed=True,
        )

    if injection_decision.action != PromptInjectionAction.ALLOW:
        security_signals.prompt_injection_detected(
            conversation_id=conversation_id,
            document_id=document.id,
            model=model,
            action=injection_decision.action.value,
            families=(finding.family.value for finding in injection_decision.findings),
            surfaces=(finding.surface.value for finding in injection_decision.findings),
        )
    if injection_decision.action == PromptInjectionAction.BLOCK:
        refusal = await suspicious_refusal(
            security_signals=security_signals,
            suspicious_throttle=suspicious_throttle,
            user_id=user_id,
            conversation_id=conversation_id,
            refusal=PROMPT_INJECTION_REFUSAL,
        )
        return UserTurnGuardResult(response=refusal)

    boundary_decision = domain_boundary.decide(user_text, document)
    if boundary_decision.action == DomainBoundaryAction.RESPOND_WITH_POLICY_MESSAGE:
        response = boundary_decision.response or ""
        if boundary_decision.reason != APP_CAPABILITY_REASON:
            security_signals.domain_boundary_blocked(
                conversation_id=conversation_id,
                document_id=document.id,
                model=model,
                reason=boundary_decision.reason,
            )
        if boundary_decision.reason in SUSPICIOUS_BOUNDARY_REASONS:
            response = await suspicious_refusal(
                security_signals=security_signals,
                suspicious_throttle=suspicious_throttle,
                user_id=user_id,
                conversation_id=conversation_id,
                refusal=response,
            )
        return UserTurnGuardResult(response=response)

    return UserTurnGuardResult()


async def suspicious_refusal(
    *,
    security_signals: SecuritySignals,
    suspicious_throttle: SuspiciousAttemptThrottle | None,
    user_id: uuid.UUID,
    conversation_id: str,
    refusal: str,
) -> str:
    if suspicious_throttle is None:
        return refusal
    try:
        decision = await suspicious_throttle.register_blocked_attempt(user_id)
    except Exception as exc:  # noqa: BLE001
        logger.log(
            logging.WARNING,
            "suspicious_attempt_tracking_failed",
            extra={
                "exc_type": exc.__class__.__name__,
                "exc_message": str(exc) or exc.__class__.__name__,
                "conversation_id": conversation_id,
            },
        )
        return refusal
    if not decision.throttled:
        return refusal
    security_signals.suspicious_activity_throttled(
        conversation_id=conversation_id,
        attempts=decision.attempts,
        window_seconds=suspicious_throttle.window_seconds,
    )
    return SUSPICIOUS_ACTIVITY_REFUSAL


async def resolve_conversation_and_document(
    *,
    conversations: ConversationRepository,
    documents: DocumentRepository,
    conversation_id: str | None,
    user_id: uuid.UUID,
    document_id: str | None,
) -> tuple[Conversation, Document]:
    if conversation_id is None:
        if document_id is None:
            raise DocumentIdRequiredError(
                "document_id is required when starting a new conversation"
            )
        document = await fetch_document(documents, document_id)
        conversation = await conversations.create(user_id, document_id)
        return conversation, document

    existing = await conversations.get(conversation_id, user_id)
    if existing is None:
        raise ConversationNotFoundError(conversation_id)
    document = await fetch_document(documents, existing.document_id)
    return existing, document


async def fetch_document(documents: DocumentRepository, document_id: str) -> Document:
    document = await documents.get(document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)
    return document


async def respond_without_model(
    conversations: ConversationRepository,
    conversation_id: str,
    message_id: str,
    content: str,
) -> AsyncGenerator[StreamEvent]:
    parts_in_order: list[dict[str, Any]] = [{"kind": "text", "content": content}]
    yield TextDelta(text=content)
    finished_at = await persist_assistant(
        conversations,
        conversation_id,
        message_id,
        content,
        StopReason.END_TURN,
        parts_in_order,
        {},
    )
    yield Finish(stop_reason=StopReason.END_TURN, usage=None, created_at=finished_at)


async def persist_assistant(
    conversations: ConversationRepository,
    conversation_id: str,
    message_id: str,
    content: str,
    stop_reason: StopReason,
    parts_in_order: list[dict[str, Any]],
    reasoning_signatures: dict[str, str],
) -> datetime:
    created_at = datetime.now(UTC)
    parts_dict = build_envelope(parts_in_order) if parts_in_order else None
    sigs: dict[str, str] | None = reasoning_signatures if reasoning_signatures else None
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
    await conversations.append_message(conversation_id, message)
    return created_at


async def resolve_title(
    conversations: ConversationRepository,
    title_task: asyncio.Task[str | None],
    conversation_id: str,
) -> str | None:
    try:
        title = await title_task
        if title is None:
            return None
        await conversations.set_title(conversation_id, title)
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


def should_generate_title(conversation: Conversation) -> bool:
    title = getattr(conversation, "title", None)
    messages = getattr(conversation, "messages", ())
    return not (title or "").strip() and not any(
        message.role == Role.USER for message in messages
    )


async def cancel_title_task(title_task: asyncio.Task[str | None] | None) -> None:
    if title_task is None or title_task.done():
        return
    title_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await title_task
