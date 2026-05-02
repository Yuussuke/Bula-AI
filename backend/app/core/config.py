from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MaritacaSettings(BaseSettings):
    # Optional so the app and CI can boot without a paid API key.
    # Endpoints that require the LLM should validate this at call time.
    maritaca_api_key: str | None = None


class OpenRouterSettings(BaseSettings):
    # Optional so CI/dev can use deterministic heuristic chunking without an API key.
    api_key: str | None = None
    chunk_model: str = "google/gemini-3-flash-preview"
    chunk_fallback_model: str = "deepseek/deepseek-v3"
    require_zdr: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OPENROUTER_",
        extra="ignore",
    )


class ProcessingSettings(BaseSettings):
    chunk_target_tokens: int = 600
    chunk_min_tokens: int = 200
    chunk_max_tokens: int = 850
    chunk_overlap_ratio: float = 0.12
    chunk_max_concurrency: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PROCESSING_",
        extra="ignore",
    )


class DatabaseSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://bulaai:bulaai@postgres:5432/bulaai"
    sql_echo: bool = False


class SecuritySettings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    log_level: str = "INFO"
    json_logs: bool = True  # Set to False in .env for development
    environment: str = "development"  # Set to "development" in .env for development

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("secret_key")
    @classmethod
    def check_secret_key(cls, value: str) -> str:
        if not value or len(value) < 32 or value.lower() == "changeme":
            raise ValueError(
                "SECRET_KEY is invalid or too weak. Configure a strong key in production."
            )
        return value


class Settings(MaritacaSettings, DatabaseSettings, SecuritySettings):
    """
    This class combines all application settings, including database and security configurations.
    """

    FRONTEND_URL: str = "http://localhost:5173"
    max_bula_upload_size_bytes: int = 10 * 1024 * 1024
    backend_cors_origins: list[str] = [
        "http://localhost:3000",
        FRONTEND_URL,
    ]
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
