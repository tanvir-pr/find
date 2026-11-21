"""Step 9 smoke: ingest knowledge + search_policy RAG (+ chat mock)."""

from __future__ import annotations

import asyncio
import json
import os

# Force mock embedding + mock LLM so smoke does not need live Gemini
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["LLM_API_KEY"] = ""
os.environ["LLM_BASE_URL"] = ""
os.environ["LLM_MODEL"] = ""

from app.core import config as config_mod
from app.core.config import get_settings

get_settings.cache_clear()
config_mod.settings = get_settings()

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.system import KnowledgeChunk
from app.models.user import User
from app.modules.chat.tool_executors import execute_tool
from app.modules.knowledge.service import ingest_directory, search_policy


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await ingest_directory(session)
        assert result["documents"] >= 5, result
        print(
            f"ok ingest docs={result['documents']} upserted={result['chunks_upserted']} "
            f"skipped={result['skipped']} provider={result['provider']}"
        )

        # idempotent second run
        again = await ingest_directory(session)
        assert again["chunks_upserted"] == 0, again
        assert again["skipped"] >= 5, again
        print(f"ok ingest idempotent skipped={again['skipped']}")

        count = await session.scalar(select(func.count()).select_from(KnowledgeChunk))
        assert int(count or 0) >= 5, count
        print(f"ok knowledge_chunks={count}")

        hit = await search_policy(session, "ডুপ্লিকেট কলম কি ফেরত নেওয়া যায়?")
        assert hit["found"] is True, hit
        assert any("return" in (h.get("document_name") or "") for h in hit["hits"]) or any(
            "রিটার্ন" in h["text"] or "ফেরত" in h["text"] for h in hit["hits"]
        ), hit
        print("ok search return policy", hit["hits"][0]["document_name"])

        miss = await search_policy(session, "xyzzy quantum moon cheese policy 99999")
        # mock vectors may still match weakly — accept found=False OR weak distance filter
        print("ok search nonsense found=", miss["found"])

        admin = await session.scalar(select(User).where(User.email == "admin@dokan.example"))
        assert admin is not None
        tool = json.loads(
            await execute_tool(
                session,
                admin,
                "search_policy",
                {"query": "ক্যাশ ১০০ টাকা কম হলে কী করব?"},
            )
        )
        assert tool.get("found") is True, tool
        print("ok tool search_policy cash closing")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@dokan.example", "password": "Admin123!"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        chat = await client.post(
            "/api/v1/chat",
            headers=headers,
            json={"message": "ডুপ্লিকেট কলম কি ফেরত নেওয়া যায়?", "history": []},
        )
        assert chat.status_code == 200, chat.text
        body = chat.json()
        names = [t["name"] for t in body["tools_used"]]
        assert "search_policy" in names, body
        print("ok chat -> search_policy")

    print("step9 smoke OK")


if __name__ == "__main__":
    asyncio.run(main())
