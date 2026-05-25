from convfinqa.config import Settings


def test_langfuse_host_accepts_langfuse_base_url_alias(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://example.langfuse.test")

    settings = Settings()

    assert settings.langfuse_host == "https://example.langfuse.test"


def test_langfuse_host_prefers_langfuse_host(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://base.langfuse.test")
    monkeypatch.setenv("LANGFUSE_HOST", "https://host.langfuse.test")

    settings = Settings()

    assert settings.langfuse_host == "https://host.langfuse.test"
