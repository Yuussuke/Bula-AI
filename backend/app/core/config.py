from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    database_url: str = "postgresql+asyncpg://bulaai:bulaai@postgres:5432/bulaai"
    sql_echo: bool = False 

    secret_key: str 
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore" 
    )

settings = Settings()