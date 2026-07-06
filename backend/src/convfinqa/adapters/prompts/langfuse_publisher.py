import asyncio
from collections.abc import Sequence
from typing import Any, Protocol, cast

from langfuse.api.commons.errors.not_found_error import NotFoundError


class _LangfuseTextPrompt(Protocol):
    version: int
    config: dict[str, Any]


class _LangfuseClient(Protocol):
    def get_prompt(
        self, name: str, *, label: str, type: str, cache_ttl_seconds: int
    ) -> _LangfuseTextPrompt: ...

    def create_prompt(
        self,
        *,
        name: str,
        prompt: str,
        labels: list[str],
        config: dict[str, Any],
        type: str,
    ) -> _LangfuseTextPrompt: ...


LATEST_LABEL = "latest"


class LangfusePromptPublisher:
    def __init__(self, client: Any) -> None:
        self._client = cast("_LangfuseClient", client)

    async def latest_content_hash(self, name: str) -> str | None:
        def _fetch() -> str | None:
            try:
                prompt = self._client.get_prompt(
                    name, label=LATEST_LABEL, type="text", cache_ttl_seconds=0
                )
            except NotFoundError:
                return None
            return cast("str | None", prompt.config.get("content_hash"))

        return await asyncio.to_thread(_fetch)

    async def publish(
        self, name: str, template: str, content_hash: str, labels: Sequence[str]
    ) -> int:
        def _create() -> int:
            prompt = self._client.create_prompt(
                name=name,
                prompt=template,
                labels=list(labels),
                config={"content_hash": content_hash},
                type="text",
            )
            return prompt.version

        return await asyncio.to_thread(_create)
