"""Ingest helpers + pgvector similarity search for RAG."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.embedding import get_embedding_client
from app.models.system import KnowledgeChunk
from app.modules.knowledge.chunking import chunk_text, extract_topic

DEFAULT_KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "knowledge"


@dataclass
class SearchHit:
    document_name: str
    chunk_index: int
    chunk_text: str
    topic: str | None
    distance: float


def _content_hash(document_name: str, chunk_index: int, text: str) -> str:
    raw = f"{document_name}|{chunk_index}|{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def ingest_directory(
    session: AsyncSession, knowledge_dir: Path | None = None
) -> dict[str, Any]:
    root = knowledge_dir or DEFAULT_KNOWLEDGE_DIR
    files = sorted(root.glob("*.md"))
    if not files:
        return {"documents": 0, "chunks_upserted": 0, "skipped": 0, "provider": "none"}

    client = get_embedding_client()
    provider = type(client).__name__
    upserted = 0
    skipped = 0

    for path in files:
        text = path.read_text(encoding="utf-8")
        topic = extract_topic(text, fallback=path.stem)
        pieces = chunk_text(text)
        # Replace document chunks atomically for idempotent re-ingest of edits
        existing_hashes = {
            row
            for row in (
                await session.scalars(
                    select(KnowledgeChunk.content_hash).where(
                        KnowledgeChunk.document_name == path.name
                    )
                )
            ).all()
            if row
        }
        new_hashes = [
            _content_hash(path.name, idx, piece) for idx, piece in enumerate(pieces)
        ]
        if existing_hashes and set(new_hashes) == existing_hashes and len(new_hashes) == len(
            existing_hashes
        ):
            skipped += len(pieces)
            continue

        await session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_name == path.name)
        )
        vectors = await client.embed(pieces)
        for idx, (piece, vector) in enumerate(zip(pieces, vectors, strict=True)):
            session.add(
                KnowledgeChunk(
                    document_name=path.name,
                    chunk_index=idx,
                    chunk_text=piece,
                    embedding=vector,
                    meta={"topic": topic, "source_path": str(path.name)},
                    content_hash=_content_hash(path.name, idx, piece),
                )
            )
            upserted += 1

    await session.commit()
    return {
        "documents": len(files),
        "chunks_upserted": upserted,
        "skipped": skipped,
        "provider": provider,
    }


_NOT_FOUND = "এই বিষয়ে দোকানের ডকুমেন্টে কোনো তথ্য পাইনি। মালিকের সাথে কথা বলুন।"


async def _keyword_fallback(
    session: AsyncSession, query: str, *, top_k: int
) -> list[dict[str, Any]]:
    """Simple ILIKE fallback when vector distance is weak (esp. mock embeddings)."""
    tokens = [t for t in query.replace("?", " ").split() if len(t) >= 2][:6]
    if not tokens:
        return []
    stmt = select(KnowledgeChunk)
    for token in tokens:
        stmt = stmt.where(KnowledgeChunk.chunk_text.ilike(f"%{token}%"))
    # If AND is too strict, try OR on distinctive tokens
    rows = (await session.scalars(stmt.limit(top_k))).all()
    if not rows and len(tokens) >= 2:
        from sqlalchemy import or_

        stmt = select(KnowledgeChunk).where(
            or_(*[KnowledgeChunk.chunk_text.ilike(f"%{t}%") for t in tokens])
        )
        rows = (await session.scalars(stmt.limit(top_k))).all()
    return [
        {
            "document_name": r.document_name,
            "chunk_index": r.chunk_index,
            "topic": (r.meta or {}).get("topic"),
            "distance": None,
            "match": "keyword",
            "text": r.chunk_text,
        }
        for r in rows
    ]


async def search_policy(
    session: AsyncSession,
    query: str,
    *,
    top_k: int = 4,
    max_distance: float | None = None,
) -> dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"found": False, "message": _NOT_FOUND, "hits": []}

    client = get_embedding_client()
    vector = (await client.embed([q]))[0]
    threshold = settings.RAG_MAX_DISTANCE if max_distance is None else max_distance

    distance_expr = KnowledgeChunk.embedding.cosine_distance(vector)
    stmt = (
        select(
            KnowledgeChunk.document_name,
            KnowledgeChunk.chunk_index,
            KnowledgeChunk.chunk_text,
            KnowledgeChunk.meta,
            distance_expr.label("distance"),
        )
        .where(KnowledgeChunk.embedding.is_not(None))
        .order_by(distance_expr)
        .limit(top_k)
    )
    rows = (await session.execute(stmt)).all()
    hits: list[dict[str, Any]] = []
    for doc, idx, text, meta, dist in rows:
        if dist is None or float(dist) > threshold:
            continue
        hits.append(
            {
                "document_name": doc,
                "chunk_index": idx,
                "topic": (meta or {}).get("topic"),
                "distance": round(float(dist), 4),
                "match": "vector",
                "text": text,
            }
        )

    if not hits:
        hits = await _keyword_fallback(session, q, top_k=top_k)

    if not hits:
        return {"found": False, "message": _NOT_FOUND, "hits": []}

    return {
        "found": True,
        "message": "নিচের ডকুমেন্ট টুকরো থেকে উত্তর দিন; অনুমান করবেন না।",
        "hits": hits,
    }
