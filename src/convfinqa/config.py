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

    api_host: str = Field(
        default="127.0.0.1"
    )

    api_port: int = Field(
        description="the port to run the uvicorn server",
        default=8000,
        ge=1,
        le=65535
    )

    api_reload: bool = Field(
        description="whether to automatically reload the server at every file change (dev only)",
        default = False
    )



SETTINGS = Settings()
