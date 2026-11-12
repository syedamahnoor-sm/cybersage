from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "CyberSage"
    APP_ENV: str = "development"
    DEBUG: bool = False
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: SecretStr | None = None
    POSTGRES_DB: str | None = None
    RETRIEVAL_MIN_SIMILARITY: float = Field(default=0.2, ge=-1, le=1, allow_inf_nan=False)
    GROQ_API_KEY: SecretStr | None = None
    GROQ_MODEL: str = Field(default="openai/gpt-oss-120b", min_length=1, max_length=200)
    GROQ_TEMPERATURE: float = Field(default=0.0, ge=0, le=1, allow_inf_nan=False)
    GROQ_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0, le=120, allow_inf_nan=False)
    GROQ_MAX_OUTPUT_TOKENS: int = Field(default=2048, ge=128, le=8192)
    RAG_MAX_RETRIEVED_CHUNKS: int = Field(default=8, ge=1, le=20)
    RAG_MAX_CONTEXT_CHARS: int = Field(default=8000, ge=256, le=50000)
    RAG_MAX_PROMPT_CHARS: int = Field(default=24000, ge=1000, le=100000)

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parents[3] / ".env",
            Path(__file__).resolve().parents[2] / ".env",
        ),
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
