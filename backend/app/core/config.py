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

    # Database (async for app; sync URL derived for Alembic)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dokan_assistant"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1).replace(
                "postgres+asyncpg://", "postgresql+psycopg://", 1
            )
        )

    # Auth (wired in step 3)
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # LLM / embedding (wired in steps 8–9)
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""
    # gemini | mock — empty key falls back to mock
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_API_KEY: str = ""  # defaults to LLM_API_KEY
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    # Max cosine distance to accept a RAG hit (lower = closer). Mock embeddings are noisier.
    # Cosine distance threshold (0=identical). Mock vectors need a looser cutoff.
    RAG_MAX_DISTANCE: float = 0.72

    # MCP (wired in step 10)
    MCP_API_KEY: str = "change-me-mcp-key"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
