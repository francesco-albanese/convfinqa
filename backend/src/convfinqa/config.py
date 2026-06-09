from typing import Self

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    llm_model: str = Field(
        default="bedrock/eu.anthropic.claude-haiku-4-5-20251001-v1:0"
    )
    llm_models: list[str] = Field(
        default=[
            "bedrock/eu.anthropic.claude-haiku-4-5-20251001-v1:0",
            "gemini/gemini-3.5-flash",
        ]
    )
    database_url: str = Field(
        default="postgresql+asyncpg://convfinqa:convfinqa@localhost:5432/convfinqa"
    )

    api_host: str = Field(default="127.0.0.1")

    api_port: int = Field(
        description="the port to run the uvicorn server", default=8000, ge=1, le=65535
    )

    api_reload: bool = Field(
        description="whether to automatically reload the server at every file change (dev only)",
        default=False,
    )

    llm_request_timeout_seconds: float = Field(
        description="upper bound on a single LLM streaming call; releases the per-conversation lock if upstream hangs",
        default=60.0,
        gt=0.0,
    )

    llm_max_output_tokens: int = Field(
        description="hard ceiling on tokens the LLM may emit per turn",
        default=1024,
        ge=1,
    )

    cognito_region: str = Field(default="eu-west-1")
    cognito_user_pool_id: str | None = Field(default=None)
    cognito_client_id: str | None = Field(default=None)

    langfuse_enabled: bool = Field(default=True)
    langfuse_public_key: str | None = Field(default=None)
    langfuse_secret_key: str | None = Field(default=None)
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        validation_alias=AliasChoices("LANGFUSE_HOST", "LANGFUSE_BASE_URL"),
    )
    environment: str = Field(default="dev")
    otel_service_name: str = Field(default="convfinqa")
    otel_exporter_otlp_endpoint: str | None = Field(default=None)

    @model_validator(mode="after")
    def _default_model_in_allowlist(self) -> Self:
        if self.llm_model not in self.llm_models:
            raise ValueError(
                f"llm_model {self.llm_model!r} is not in llm_models {self.llm_models!r}"
            )
        return self


SETTINGS = Settings()
