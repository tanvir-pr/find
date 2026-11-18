"""Step 4 smoke: product → supplier → purchase → stock → adjustment."""

import asyncio
from datetime import date
from decimal import Decimal

from httpx import ASGITransport, AsyncClient

from app.main import app


async def main() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@dokan.example", "password": "Admin123!"},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        product = await client.post(
            "/api/v1/products",
            headers=headers,
            json={
                "name": "Red Pen",
                "category": "stationery",
                "unit": "pcs",
                "tracks_expiry": False,
                "variants": [
                    {
                        "name": "Original",
                        "barcode": "PEN-RED-001",
                        "retail_price": "15.00",
                        "dealer_price": "12.00",
                        "low_stock_threshold": "10",
                    }
                ],
            },
        )
        print("product", product.status_code)
        assert product.status_code == 201, product.text
        variant_id = product.json()["variants"][0]["id"]
        assert Decimal(product.json()["variants"][0]["current_stock"]) == 0

        supplier = await client.post(
            "/api/v1/suppliers",
            headers=headers,
            json={"name": "Dhaka Traders", "phone": "01700000000"},
        )
        assert supplier.status_code == 201, supplier.text
        supplier_id = supplier.json()["id"]

        purchase = await client.post(
            "/api/v1/purchases",
            headers=headers,
            json={
                "supplier_id": supplier_id,
                "invoice_no": "INV-STEP4-001",
                "invoice_date": date.today().isoformat(),
                "lines": [
                    {
                        "variant_id": variant_id,
                        "qty": "50",
                        "cost_price": "10.00",
                        "expiry_date": None,
                    }
                ],
            },
        )
        print("purchase", purchase.status_code)
        assert purchase.status_code == 201, purchase.text
        assert len(purchase.json()["batches"]) == 1

        stock = await client.get(f"/api/v1/stock/variants/{variant_id}", headers=headers)
        print("stock", stock.json())
        assert Decimal(stock.json()["current_stock"]) == Decimal("50")

        adj = await client.post(
            "/api/v1/stock/adjustments",
            headers=headers,
            json={"variant_id": variant_id, "qty_delta": "-3", "note": "damaged sample"},
        )
        print("adjust", adj.status_code, adj.json()["qty"])
        assert adj.status_code == 201

        stock2 = await client.get(f"/api/v1/stock/variants/{variant_id}", headers=headers)
        assert Decimal(stock2.json()["current_stock"]) == Decimal("47")

        listed = await client.get("/api/v1/products?q=Red", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["total"] >= 1
        print("step4 smoke OK")


if __name__ == "__main__":
    asyncio.run(main())
