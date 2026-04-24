from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class MaritacaSettings(BaseSettings):
    # Optional so the app and CI can boot without a paid API key.
    # Endpoints that require the LLM should validate this at call time.
    maritaca_api_key: str | None = None


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
    backend_cors_origins: list[str] = [FRONTEND_URL]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pass


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
