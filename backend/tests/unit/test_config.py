import pytest
from pydantic import ValidationError

from convfinqa.config import Settings


def test_default_model_must_be_in_allowlist() -> None:
    with pytest.raises(ValidationError):
        Settings(
            llm_model="bedrock/not-supported", llm_models=["gemini/gemini-2.5-flash"]
        )


def test_default_settings_have_default_model_in_allowlist() -> None:
    settings = Settings()

    assert settings.llm_model in settings.llm_models


def test_langfuse_host_accepts_langfuse_base_url_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://example.langfuse.test")

    settings = Settings()

    assert settings.langfuse_host == "https://example.langfuse.test"


def test_langfuse_host_prefers_langfuse_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://base.langfuse.test")
    monkeypatch.setenv("LANGFUSE_HOST", "https://host.langfuse.test")

    settings = Settings()

    assert settings.langfuse_host == "https://host.langfuse.test"
