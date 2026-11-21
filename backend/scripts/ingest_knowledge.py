"""Ingest knowledge/*.md into knowledge_chunks (idempotent)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow `uv run python scripts/ingest_knowledge.py`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import AsyncSessionLocal
from app.modules.knowledge.service import DEFAULT_KNOWLEDGE_DIR, ingest_directory


async def main() -> None:
    print(f"knowledge dir: {DEFAULT_KNOWLEDGE_DIR}")
    async with AsyncSessionLocal() as session:
        result = await ingest_directory(session)
    print(
        f"ingest done documents={result['documents']} "
        f"upserted={result['chunks_upserted']} skipped={result['skipped']} "
        f"provider={result['provider']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
