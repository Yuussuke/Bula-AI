import os


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://bulaai:bulaai@postgres:5432/bulaai",
)

SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"


if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Please configure it in your environment.")
