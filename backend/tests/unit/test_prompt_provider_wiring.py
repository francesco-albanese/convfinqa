from convfinqa.adapters.prompts.langfuse_provider import LangfusePromptProvider
from convfinqa.adapters.prompts.local_file import LocalFilePromptProvider
from convfinqa.config import Settings
from convfinqa.container.factories import build_prompt_provider


def test_uses_local_provider_when_langfuse_disabled() -> None:
    settings = Settings(langfuse_enabled=False)

    provider = build_prompt_provider(settings)

    assert isinstance(provider, LocalFilePromptProvider)


def test_uses_local_provider_when_langfuse_enabled_but_keys_missing() -> None:
    settings = Settings(
        langfuse_enabled=True, langfuse_public_key=None, langfuse_secret_key=None
    )

    provider = build_prompt_provider(settings)

    assert isinstance(provider, LocalFilePromptProvider)


def test_uses_langfuse_provider_when_enabled_with_keys() -> None:
    settings = Settings(
        langfuse_enabled=True,
        langfuse_public_key="pk-test",
        langfuse_secret_key="sk-test",
    )

    provider = build_prompt_provider(settings)

    assert isinstance(provider, LangfusePromptProvider)
