from pydantic import Field
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
    system_prompt: str = Field(
        default=(
            "You are ConvFinQA, a financial assistant. "
            "Be concise and cite figures when given."
        )
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
    langfuse_host: str = Field(default="https://cloud.langfuse.com")
    environment: str = Field(default="dev")
    otel_service_name: str = Field(default="convfinqa")
    otel_exporter_otlp_endpoint: str | None = Field(default=None)


SETTINGS = Settings()
