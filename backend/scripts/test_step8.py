"""Step 8 smoke: 7 tools + chat (mock LLM when no API key)."""

from __future__ import annotations

import asyncio
import json

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from app.modules.chat.tool_executors import execute_tool


async def _admin() -> User:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == "admin@dokan.example"))
        assert user is not None, "run seed_users / seed_demo first"
        return user


async def test_tools_direct() -> None:
    admin = await _admin()
    async with AsyncSessionLocal() as session:
        # re-load in this session
        user = await session.get(User, admin.id)
        assert user is not None

        stock = json.loads(await execute_tool(session, user, "check_stock", {"query": "School Bag"}))
        assert stock["count"] >= 1, stock
        print("ok check_stock", stock["count"])

        low = json.loads(await execute_tool(session, user, "low_stock_list", {}))
        assert low["count"] >= 1, low
        print("ok low_stock_list", low["count"])

        exp = json.loads(await execute_tool(session, user, "expiring_items", {"within_days": 30}))
        assert exp["count"] >= 1, exp
        print("ok expiring_items", exp["count"])

        sales = json.loads(
            await execute_tool(session, user, "sales_summary", {"period": "month"})
        )
        assert sales["bill_count"] >= 1, sales
        print("ok sales_summary bills", sales["bill_count"])

        reorder = json.loads(
            await execute_tool(
                session, user, "reorder_suggestion", {"lookback_days": 28, "cover_days": 14}
            )
        )
        assert "suggestions" in reorder, reorder
        print("ok reorder_suggestion", reorder["count"])

        seasonal = json.loads(
            await execute_tool(
                session, user, "seasonal_top_products", {"season": "winter_start"}
            )
        )
        assert seasonal["count"] >= 1, seasonal
        print("ok seasonal_top_products", seasonal["count"], "top=", seasonal["items"][0]["product"])

        due = json.loads(await execute_tool(session, user, "customer_due", {"query": "Karim"}))
        assert due["count"] >= 1, due
        assert float(due["customers"][0]["current_due"]) > 0
        print("ok customer_due", due["customers"][0]["current_due"])

        # staff cannot use customer_due
        staff = await session.scalar(select(User).where(User.role == UserRole.staff))
        assert staff is not None
        try:
            await execute_tool(session, staff, "customer_due", {})
            raise AssertionError("staff should be forbidden from customer_due")
        except Exception as exc:  # ForbiddenError
            assert "permission" in str(exc).lower() or "Forbidden" in type(exc).__name__ or "not allowed" in str(exc).lower()
            print("ok staff blocked from customer_due")


async def test_chat_api() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@dokan.example", "password": "Admin123!"},
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # staff forbidden
        staff_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "staff@dokan.example", "password": "Staff123!"},
        )
        staff_headers = {"Authorization": f"Bearer {staff_login.json()['access_token']}"}
        denied = await client.post(
            "/api/v1/chat",
            headers=staff_headers,
            json={"message": "স্টক কেমন?"},
        )
        assert denied.status_code == 403, denied.text
        print("ok staff chat forbidden")

        probes = [
            ("School Bag স্টক কয়টা আছে?", "check_stock"),
            ("কী কী শেষ হয়ে যাচ্ছে?", "low_stock_list"),
            ("মেয়াদ শেষ হচ্ছে কোনটা?", "expiring_items"),
            ("এই মাসে কত বিক্রি হলো?", "sales_summary"),
            ("কাল কী অর্ডার দেব?", "reorder_suggestion"),
            ("শীতের শুরুতে কী বেশি চলে?", "seasonal_top_products"),
            ("করিম সাহেবের বাকি কত?", "customer_due"),
        ]
        for message, expect_tool in probes:
            resp = await client.post(
                "/api/v1/chat",
                headers=headers,
                json={"message": message, "history": []},
            )
            assert resp.status_code == 200, f"{message}: {resp.text}"
            body = resp.json()
            assert body["reply"], body
            names = [t["name"] for t in body["tools_used"]]
            assert expect_tool in names, (message, names, body["reply"][:200])
            print(f"ok chat -> {expect_tool} ({body['provider']})")

        # multi-turn history accepted
        multi = await client.post(
            "/api/v1/chat",
            headers=headers,
            json={
                "message": "কালকের চেয়ে বেশি?",
                "history": [
                    {"role": "user", "content": "আজ কত বিক্রি হলো?"},
                    {"role": "assistant", "content": "আজকের সারাংশ টুল থেকে এসেছে।"},
                ],
            },
        )
        assert multi.status_code == 200, multi.text
        print("ok multi-turn history")


async def main() -> None:
    await test_tools_direct()
    await test_chat_api()
    print("step8 smoke OK")


if __name__ == "__main__":
    asyncio.run(main())
