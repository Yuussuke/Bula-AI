from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class MaritacaSettings(BaseSettings):
    maritaca_api_key: str


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


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()