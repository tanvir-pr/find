"""Step 7 E2E: verify seed_demo via API (Swagger-equivalent paths)."""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

from httpx import ASGITransport, AsyncClient

from app.main import app


async def main() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # --- auth ---
        for email, password, role in [
            ("admin@dokan.example", "Admin123!", "admin"),
            ("manager@dokan.example", "Manager123!", "manager"),
            ("staff@dokan.example", "Staff123!", "staff"),
        ]:
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert login.status_code == 200, f"{email}: {login.text}"
            me = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {login.json()['access_token']}"},
            )
            assert me.json()["role"] == role, me.json()
            print(f"ok login {email} -> {role}")

        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@dokan.example", "password": "Admin123!"},
        )
        headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        # --- catalog markers ---
        products = await client.get("/api/v1/products", headers=headers, params={"q": "School Bag"})
        assert products.status_code == 200, products.text
        bags = products.json()["items"]
        assert any(p["name"] == "School Bag" for p in bags), bags
        print(f"ok products search School Bag ({len(bags)})")

        barcode = await client.get(
            "/api/v1/products", headers=headers, params={"q": "SEED-BAG-ORIG"}
        )
        assert barcode.status_code == 200
        assert len(barcode.json()["items"]) >= 1
        print("ok barcode SEED-BAG-ORIG")

        # --- customers / credit due (D2/D7) ---
        customers = await client.get("/api/v1/customers", headers=headers, params={"area": "Mirpur"})
        assert customers.status_code == 200, customers.text
        mirpur = customers.json()
        assert any(c["name"] == "Karim Dealer" for c in mirpur), mirpur
        karim = next(c for c in mirpur if c["name"] == "Karim Dealer")
        assert Decimal(karim["credit_limit"]) == Decimal("50000.00")
        assert Decimal(karim["current_due"]) > 0
        print(f"ok Karim due={karim['current_due']} limit={karim['credit_limit']}")

        history = await client.get(
            f"/api/v1/customers/{karim['id']}/history", headers=headers
        )
        assert history.status_code == 200
        assert len(history.json()) >= 1
        print(f"ok Karim history bills={len(history.json())}")

        # --- reports: expiring (B4/B5) ---
        expiring = await client.get(
            "/api/v1/reports/expiring",
            headers=headers,
            params={"within_days": 30},
        )
        assert expiring.status_code == 200, expiring.text
        exp_items = expiring.json()
        assert any("Glue" in i["product_name"] or "Ink" in i["product_name"] for i in exp_items), exp_items
        print(f"ok expiring items={len(exp_items)}")

        # --- reports: low stock (B6) ---
        low = await client.get("/api/v1/reports/low-stock", headers=headers)
        assert low.status_code == 200, low.text
        low_items = low.json()
        assert any("Pen" in i["product_name"] for i in low_items), low_items
        print(f"ok low-stock items={len(low_items)}")

        # --- reports: sales summary (B7) — year-wide for seasonal seed ---
        today = date.today()
        year_start = date(today.year if today.month >= 2 else today.year - 1, 1, 1)
        summary = await client.get(
            "/api/v1/reports/sales-summary",
            headers=headers,
            params={"from_date": year_start.isoformat(), "to_date": today.isoformat()},
        )
        assert summary.status_code == 200, summary.text
        body = summary.json()
        assert body["bill_count"] >= 5, body
        assert Decimal(body["total_sales"]) > 0
        assert Decimal(body["credit"]) > 0
        print(
            f"ok sales-summary bills={body['bill_count']} "
            f"total={body['total_sales']} credit={body['credit']}"
        )

        # --- suppliers ---
        suppliers = await client.get("/api/v1/suppliers", headers=headers)
        assert suppliers.status_code == 200
        assert any("নবাবপুর" in s["name"] or "Nawabpur" in s["name"] for s in suppliers.json()), (
            suppliers.json()
        )
        print("ok suppliers")

        # --- openapi / swagger surface ---
        openapi = await client.get("/openapi.json")
        assert openapi.status_code == 200
        paths = openapi.json()["paths"]
        required = [
            "/api/v1/auth/login",
            "/api/v1/products",
            "/api/v1/sales",
            "/api/v1/reports/sales-summary",
            "/api/v1/reports/low-stock",
            "/api/v1/reports/expiring",
            "/api/v1/shifts/open",
            "/api/v1/customers",
        ]
        for path in required:
            assert path in paths, f"missing OpenAPI path {path}"
        print(f"ok openapi paths ({len(required)} checked)")

        docs = await client.get("/docs")
        assert docs.status_code == 200
        print("ok /docs")

    print("step7 smoke OK")


if __name__ == "__main__":
    asyncio.run(main())
