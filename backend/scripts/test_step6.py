"""Step 6 smoke: shift/cash close, stock count, reports, supplier pay, due reminder."""

import asyncio
import uuid
from datetime import date, timedelta
from decimal import Decimal

from httpx import ASGITransport, AsyncClient

from app.main import app


async def main() -> None:
    suffix = uuid.uuid4().hex[:8]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@dokan.example", "password": "Admin123!"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        product = await client.post(
            "/api/v1/products",
            headers=headers,
            json={
                "name": f"Glue Stick {suffix}",
                "category": "stationery",
                "tracks_expiry": True,
                "variants": [
                    {
                        "name": "20g",
                        "barcode": f"GLUE-{suffix}",
                        "retail_price": "50.00",
                        "dealer_price": "40.00",
                        "low_stock_threshold": "100",
                    }
                ],
            },
        )
        assert product.status_code == 201, product.text
        variant_id = product.json()["variants"][0]["id"]

        supplier = await client.post(
            "/api/v1/suppliers",
            headers=headers,
            json={"name": f"Glue Supplier {suffix}"},
        )
        supplier_id = supplier.json()["id"]
        expiry = (date.today() + timedelta(days=10)).isoformat()
        purchase = await client.post(
            "/api/v1/purchases",
            headers=headers,
            json={
                "supplier_id": supplier_id,
                "invoice_no": f"INV-S6-{suffix}",
                "invoice_date": date.today().isoformat(),
                "lines": [
                    {
                        "variant_id": variant_id,
                        "qty": "30",
                        "cost_price": "35.00",
                        "expiry_date": expiry,
                    }
                ],
            },
        )
        assert purchase.status_code == 201, purchase.text

        existing = await client.get("/api/v1/shifts/mine/open", headers=headers)
        if existing.status_code == 200 and existing.json():
            await client.post(
                f"/api/v1/shifts/{existing.json()['id']}/close",
                headers=headers,
                json={"counted_cash": "0", "note": "cleanup"},
            )

        shift = await client.post(
            "/api/v1/shifts/open",
            headers=headers,
            json={"opening_cash": "500.00"},
        )
        assert shift.status_code == 201, shift.text
        shift_id = shift.json()["id"]

        sale = await client.post(
            "/api/v1/sales",
            headers=headers,
            json={
                "shift_id": shift_id,
                "items": [{"variant_id": variant_id, "qty": "2"}],
                "payments": [{"method": "cash", "amount": "100.00"}],
            },
        )
        assert sale.status_code == 201, sale.text

        summary = await client.get(f"/api/v1/shifts/{shift_id}/summary", headers=headers)
        print("summary", summary.json())
        assert Decimal(summary.json()["expected_cash"]) == Decimal("600.00")

        closed = await client.post(
            f"/api/v1/shifts/{shift_id}/close",
            headers=headers,
            json={"counted_cash": "600.00", "note": "ok"},
        )
        assert closed.status_code == 200, closed.text
        assert Decimal(closed.json()["cash_closing"]["difference"]) == Decimal("0")

        count = await client.post(
            "/api/v1/stock/counts",
            headers=headers,
            json={
                "apply_adjustments": True,
                "lines": [{"variant_id": variant_id, "counted_qty": "25"}],
            },
        )
        assert count.status_code == 201, count.text
        stock = await client.get(f"/api/v1/stock/variants/{variant_id}", headers=headers)
        assert Decimal(stock.json()["current_stock"]) == Decimal("25")

        today = date.today().isoformat()
        report = await client.get(
            f"/api/v1/reports/sales-summary?from_date={today}&to_date={today}",
            headers=headers,
        )
        assert report.status_code == 200, report.text
        assert report.json()["bill_count"] >= 1

        low = await client.get("/api/v1/reports/low-stock", headers=headers)
        assert low.status_code == 200
        assert any(i["variant_id"] == variant_id for i in low.json())

        exp = await client.get("/api/v1/reports/expiring?within_days=30", headers=headers)
        assert exp.status_code == 200
        assert any(i["variant_id"] == variant_id for i in exp.json())

        pay = await client.post(
            f"/api/v1/suppliers/{supplier_id}/payments",
            headers=headers,
            json={"amount": "200.00", "method": "cash"},
        )
        assert pay.status_code == 201, pay.text

        customer = await client.post(
            "/api/v1/customers",
            headers=headers,
            json={
                "name": "Due Guy",
                "phone": f"01999{suffix[:6]}",
                "area": "Uttara",
                "credit_limit": "500",
            },
        )
        customer_id = customer.json()["id"]
        credit_sale = await client.post(
            "/api/v1/sales",
            headers=headers,
            json={
                "customer_id": customer_id,
                "items": [{"variant_id": variant_id, "qty": "1"}],
                "payments": [{"method": "credit", "amount": "50.00"}],
            },
        )
        assert credit_sale.status_code == 201, credit_sale.text

        reminders = await client.post("/api/v1/customers/due-reminders/run", headers=headers)
        assert reminders.status_code == 200, reminders.text
        assert any(r["customer_id"] == customer_id for r in reminders.json())

        hist = await client.get(f"/api/v1/customers/{customer_id}/history", headers=headers)
        assert hist.status_code == 200
        assert len(hist.json()) >= 1

        area = await client.get("/api/v1/customers?area=Uttara", headers=headers)
        assert any(c["id"] == customer_id for c in area.json())
        print("step6 smoke OK")


if __name__ == "__main__":
    asyncio.run(main())
