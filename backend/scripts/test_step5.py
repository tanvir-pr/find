"""Step 5 smoke: sale (cash+bkash), credit limit, return restock, receipt copy."""

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
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        product = await client.post(
            "/api/v1/products",
            headers=headers,
            json={
                "name": "Blue Notebook",
                "category": "stationery",
                "variants": [
                    {
                        "name": "A4",
                        "barcode": "NB-BLUE-A4",
                        "retail_price": "100.00",
                        "dealer_price": "80.00",
                        "low_stock_threshold": "5",
                    }
                ],
            },
        )
        assert product.status_code == 201, product.text
        variant_id = product.json()["variants"][0]["id"]

        supplier = await client.post(
            "/api/v1/suppliers",
            headers=headers,
            json={"name": "Paper Co"},
        )
        purchase = await client.post(
            "/api/v1/purchases",
            headers=headers,
            json={
                "supplier_id": supplier.json()["id"],
                "invoice_no": "INV-S5-001",
                "invoice_date": date.today().isoformat(),
                "lines": [
                    {"variant_id": variant_id, "qty": "20", "cost_price": "60.00"}
                ],
            },
        )
        assert purchase.status_code == 201, purchase.text

        # Cash + bKash split sale
        sale = await client.post(
            "/api/v1/sales",
            headers=headers,
            json={
                "items": [{"variant_id": variant_id, "qty": "3", "discount": "0"}],
                "payments": [
                    {"method": "cash", "amount": "200.00"},
                    {"method": "bkash", "amount": "100.00", "txn_id": "BKASH-S5-001"},
                ],
                "discount": "0",
            },
        )
        print("sale", sale.status_code, sale.json().get("bill_no"), sale.json().get("total"))
        assert sale.status_code == 201, sale.text
        bill_no = sale.json()["bill_no"]
        sale_item_id = sale.json()["items"][0]["id"]

        stock = await client.get(f"/api/v1/stock/variants/{variant_id}", headers=headers)
        assert Decimal(stock.json()["current_stock"]) == Decimal("17")

        # Credit customer
        customer = await client.post(
            "/api/v1/customers",
            headers=headers,
            json={
                "name": "Karim",
                "phone": "01811112222",
                "credit_limit": "150.00",
                "area": "Mirpur",
            },
        )
        assert customer.status_code == 201, customer.text
        customer_id = customer.json()["id"]

        credit_ok = await client.post(
            "/api/v1/sales",
            headers=headers,
            json={
                "customer_id": customer_id,
                "items": [{"variant_id": variant_id, "qty": "1"}],
                "payments": [{"method": "credit", "amount": "100.00"}],
            },
        )
        assert credit_ok.status_code == 201, credit_ok.text

        credit_fail = await client.post(
            "/api/v1/sales",
            headers=headers,
            json={
                "customer_id": customer_id,
                "items": [{"variant_id": variant_id, "qty": "1"}],
                "payments": [{"method": "credit", "amount": "100.00"}],
            },
        )
        print("credit_fail", credit_fail.status_code, credit_fail.json())
        assert credit_fail.status_code == 400

        # Good return restocks
        ret = await client.post(
            "/api/v1/returns",
            headers=headers,
            json={
                "bill_no": bill_no,
                "sale_item_id": sale_item_id,
                "qty": "1",
                "reason": "wrong color",
                "is_damaged": False,
            },
        )
        print("return", ret.status_code)
        assert ret.status_code == 201, ret.text

        stock2 = await client.get(f"/api/v1/stock/variants/{variant_id}", headers=headers)
        # 20 - 3 - 1 + 1 return = 17
        assert Decimal(stock2.json()["current_stock"]) == Decimal("17")

        receipt = await client.post(
            f"/api/v1/sales/by-bill/{bill_no}/receipt", headers=headers
        )
        assert receipt.status_code == 200
        assert receipt.json()["is_copy"] is True
        print("step5 smoke OK")


if __name__ == "__main__":
    asyncio.run(main())
