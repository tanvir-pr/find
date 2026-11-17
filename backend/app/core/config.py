from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Dokan Assistant"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database (async)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dokan_assistant"

    # Auth (wired in step 3)
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # LLM / embedding (wired in steps 8–9)
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""
    EMBEDDING_BASE_URL: str = "http://localhost:8080"

    # MCP (wired in step 10)
    MCP_API_KEY: str = "change-me-mcp-key"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
