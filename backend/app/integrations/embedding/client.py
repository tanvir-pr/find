"""Embedding client — Gemini (768-d) or deterministic mock for offline/tests."""

from __future__ import annotations

import hashlib
import math
import struct
from typing import Sequence

import httpx

from app.core.config import settings
from app.core.errors import AppError
from app.models.system import EMBEDDING_DIM


class EmbeddingError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=502, code="embedding_error")


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def mock_embed(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Hashing + character n-grams → stable unit vector (good enough for smoke RAG)."""
    vec = [0.0] * dim
    lowered = (text or "").lower()
    tokens = lowered.replace("\n", " ").split()
    grams = tokens[:]
    # char trigrams help Bangla matching without a real model
    compact = "".join(ch for ch in lowered if not ch.isspace())
    for i in range(max(0, len(compact) - 2)):
        grams.append(compact[i : i + 3])
    for token in grams:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for j in range(0, len(digest) - 3, 4):
            idx = struct.unpack_from(">I", digest, j)[0] % dim
            sign = 1.0 if digest[j] % 2 == 0 else -1.0
            vec[idx] += sign
    return _l2_normalize(vec)


class GeminiEmbeddingClient:
    """Google Generative Language embedContent API (text-embedding-004 → 768)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = (api_key or settings.EMBEDDING_API_KEY or settings.LLM_API_KEY).strip()
        self.model = (model or settings.EMBEDDING_MODEL).strip() or "gemini-embedding-001"
        base = (settings.EMBEDDING_BASE_URL or "").strip()
        if not base or "embedding:" in base or "localhost:8080" in base:
            base = "https://generativelanguage.googleapis.com/v1beta"
        self.base_url = base.rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not self.configured:
            raise EmbeddingError("Embedding API key missing")
        out: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for text in texts:
                url = (
                    f"{self.base_url}/models/{self.model}:embedContent"
                    f"?key={self.api_key}"
                )
                payload = {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": text}]},
                    # Match knowledge_chunks Vector(768)
                    "outputDimensionality": EMBEDDING_DIM,
                }
                try:
                    resp = await client.post(url, json=payload)
                except httpx.HTTPError as exc:
                    raise EmbeddingError(f"Embedding transport error: {exc}") from exc
                if resp.status_code >= 400:
                    raise EmbeddingError(
                        f"Embedding error {resp.status_code}: {resp.text[:300]}"
                    )
                data = resp.json()
                values = (data.get("embedding") or {}).get("values")
                if not values or len(values) != EMBEDDING_DIM:
                    raise EmbeddingError(
                        f"Expected {EMBEDDING_DIM}-d embedding, got "
                        f"{0 if not values else len(values)}"
                    )
                out.append([float(x) for x in values])
        return out


class MockEmbeddingClient:
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [mock_embed(t) for t in texts]


def get_embedding_client() -> GeminiEmbeddingClient | MockEmbeddingClient:
    """Prefer Gemini when key present; otherwise mock (ingest/tests still work)."""
    if settings.EMBEDDING_PROVIDER.strip().lower() == "mock":
        return MockEmbeddingClient()
    gemini = GeminiEmbeddingClient()
    if gemini.configured:
        return gemini
    return MockEmbeddingClient()
