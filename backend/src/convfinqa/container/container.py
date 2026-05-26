from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from convfinqa.application.use_cases.delete_conversation import (
    DeleteConversationUseCase,
)
from convfinqa.application.use_cases.get_chat_messages import GetChatMessagesUseCase
from convfinqa.application.use_cases.get_document import GetDocumentUseCase
from convfinqa.application.use_cases.list_chats import ListChatsUseCase
from convfinqa.application.use_cases.list_documents import ListDocumentsUseCase
from convfinqa.application.use_cases.send_message import SendMessageUseCase
from convfinqa.config import Settings
from convfinqa.domain.ports.cache import CachePort
from convfinqa.domain.ports.documents_port import DocumentsPort
from convfinqa.domain.ports.llm import LLMPort
from convfinqa.domain.ports.lock import ConversationLockPort
from convfinqa.domain.ports.observability import ObservabilityPort
from convfinqa.domain.ports.rate_limit import RateLimitPort
from convfinqa.domain.ports.repository import ConversationRepository, DocumentRepository
from convfinqa.domain.ports.session import SessionPort


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    llm: LLMPort
    conversations: ConversationRepository
    documents: DocumentRepository
    documents_port: DocumentsPort
    locks: ConversationLockPort
    send_message: SendMessageUseCase
    list_documents: ListDocumentsUseCase
    get_document: GetDocumentUseCase
    list_chats: ListChatsUseCase
    get_chat_messages: GetChatMessagesUseCase
    delete_conversation: DeleteConversationUseCase
    observability: ObservabilityPort
    cache: CachePort
    rate_limit: RateLimitPort
    session: SessionPort | None = None
