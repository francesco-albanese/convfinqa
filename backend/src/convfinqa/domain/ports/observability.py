from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol


class ObservabilitySpan(Protocol):
    def set_output(self, output: str) -> None: ...

    def set_error(self) -> None: ...


class ObservabilityPort(Protocol):
    def start_as_current_observation(
        self, as_type: str, name: str, input: dict[str, Any] | None = None
    ) -> AbstractAsyncContextManager["ObservabilitySpan"]: ...

    def propagate_attributes(
        self,
        user_id: str,
        session_id: str,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None: ...

    def update_current_generation(self, **kwargs: Any) -> None: ...

    async def flush(self) -> None: ...
