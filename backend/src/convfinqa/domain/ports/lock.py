from contextlib import AbstractAsyncContextManager
from typing import Protocol


class ConversationLockPort(Protocol):
    def try_acquire(
        self, conversation_id: str
    ) -> AbstractAsyncContextManager[bool]: ...
