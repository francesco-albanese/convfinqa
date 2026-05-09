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


SETTINGS = Settings()
