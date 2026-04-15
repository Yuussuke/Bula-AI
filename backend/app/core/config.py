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

class Settings(MaritacaSettings, DatabaseSettings, SecuritySettings):
    """
    This class combines all application settings, including database and security configurations.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pass

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
