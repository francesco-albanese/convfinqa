import asyncio
from collections.abc import Mapping
from typing import Any, Protocol, cast

from convfinqa.adapters.prompts.local_file import compile_prompt_template

DEFAULT_CACHE_TTL_SECONDS = 60


class _LangfuseTextPrompt(Protocol):
    prompt: str


class _LangfuseClient(Protocol):
    def get_prompt(
        self,
        name: str,
        *,
        label: str,
        type: str,
        cache_ttl_seconds: int,
    ) -> _LangfuseTextPrompt: ...


class LangfusePromptProvider:
    def __init__(
        self, client: Any, cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
    ) -> None:
        self._client = cast("_LangfuseClient", client)
        self._cache_ttl_seconds = cache_ttl_seconds

    async def compile(
        self, name: str, label: str, variables: Mapping[str, object]
    ) -> str:
        def _fetch() -> str:
            prompt = self._client.get_prompt(
                name,
                label=label,
                type="text",
                cache_ttl_seconds=self._cache_ttl_seconds,
            )
            return prompt.prompt

        template = await asyncio.to_thread(_fetch)
        return compile_prompt_template(template, variables)
