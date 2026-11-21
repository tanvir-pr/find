"""Embedding provider integration."""

from app.integrations.embedding.client import (
    GeminiEmbeddingClient,
    MockEmbeddingClient,
    get_embedding_client,
    mock_embed,
)

__all__ = [
    "GeminiEmbeddingClient",
    "MockEmbeddingClient",
    "get_embedding_client",
    "mock_embed",
]
