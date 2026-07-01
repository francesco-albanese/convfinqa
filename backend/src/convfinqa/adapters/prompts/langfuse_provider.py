import asyncio
from collections.abc import Mapping
from typing import Any, Protocol, cast

from convfinqa.adapters.prompts.local_file import compile_prompt_template
from convfinqa.domain.ports.prompts import CompiledPrompt

DEFAULT_CACHE_TTL_SECONDS = 60


class _LangfuseTextPrompt(Protocol):
    prompt: str
    version: int
    config: dict[str, Any]


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
    ) -> CompiledPrompt:
        def _fetch() -> _LangfuseTextPrompt:
            return self._client.get_prompt(
                name,
                label=label,
                type="text",
                cache_ttl_seconds=self._cache_ttl_seconds,
            )

        prompt = await asyncio.to_thread(_fetch)
        text = compile_prompt_template(prompt.prompt, variables)
        return CompiledPrompt(text=text, version=prompt.version, config=prompt.config)
