"""End-to-end functional audit: DB + API features."""

from __future__ import annotations

import asyncio
import traceback
from datetime import date
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import AsyncSessionLocal, engine
from app.core.config import settings

BASE = "http://127.0.0.1:8001"
results: list[tuple[str, str, str]] = []


def ok(area: str, detail: str = "") -> None:
    results.append((area, "PASS", detail))


def fail(area: str, detail: str) -> None:
    results.append((area, "FAIL", detail))


def skip(area: str, detail: str) -> None:
    results.append((area, "SKIP", detail))


async def check_db() -> None:
    try:
        async with engine.connect() as conn:
            ver = (await conn.execute(text("select version()"))).scalar()
            db = (await conn.execute(text("select current_database()"))).scalar()
            tables = (
                await conn.execute(
                    text(
                        "select count(*) from information_schema.tables "
                        "where table_schema='public'"
                    )
                )
            ).scalar()
            counts = (
                await conn.execute(
                    text(
                        """
                        select
                          (select count(*) from users) u,
                          (select count(*) from products) p,
                          (select count(*) from product_variants) v,
                          (select count(*) from customers) c,
                          (select count(*) from sales) s,
                          (select count(*) from stock_movements) m,
                          (select count(*) from knowledge_chunks) k
                        """
                    )
                )
            ).one()
        ok(
            "DB connection",
            f"db={db} tables={tables} users={counts[0]} products={counts[1]} "
            f"variants={counts[2]} customers={counts[3]} sales={counts[4]} "
            f"movements={counts[5]} knowledge={counts[6]}",
        )
        ok("DB engine URL host", settings.DATABASE_URL.split("@")[-1])
        if "PostgreSQL" in str(ver):
            ok("Postgres alive", str(ver)[:60])
        if int(counts[1] or 0) == 0:
            fail("Seed data", "No products — run seed_demo.py --force")
        else:
            ok("Seed catalog present", f"{counts[1]} products")
        if int(counts[6] or 0) == 0:
            skip("RAG knowledge chunks", "0 chunks — ingest may not have run")
        else:
            ok("RAG knowledge chunks", f"{counts[6]} chunks")
    except Exception as exc:
        fail("DB connection", f"{exc}")


async def api_audit() -> None:
    async with AsyncClient(base_url=BASE, timeout=90.0) as c:
        # health
        try:
            r = await c.get("/health")
            if r.status_code == 200 and r.json().get("status") == "ok":
                ok("API /health", r.json().get("app", ""))
            else:
                fail("API /health", f"{r.status_code} {r.text[:120]}")
                return
        except Exception as exc:
            fail("API reachable", str(exc))
            return

        # login
        try:
            login = await c.post(
                "/api/v1/auth/login",
                json={"email": "admin@dokan.example", "password": "Admin123!"},
            )
            if login.status_code != 200:
                fail("Auth login", login.text[:200])
                return
            token = login.json()["access_token"]
            h = {"Authorization": f"Bearer {token}"}
            me = await c.get("/api/v1/auth/me", headers=h)
            ok("Auth login + /me", f"role={me.json().get('role')}")
        except Exception as exc:
            fail("Auth", str(exc))
            return

        async def hit(name: str, method: str, path: str, **kwargs):
            try:
                fn = getattr(c, method)
                r = await fn(path, headers=h, **kwargs)
                if r.status_code < 400:
                    preview = r.text[:100].replace("\n", " ")
                    ok(name, f"{r.status_code} {preview}")
                    return r
                fail(name, f"{r.status_code} {r.text[:220]}")
                return r
            except Exception as exc:
                fail(name, str(exc))
                return None

        # catalog / reports
        await hit("Products list", "get", "/api/v1/products?page_size=20")
        await hit("Products search", "get", "/api/v1/products?q=School%20Bag")
        await hit("Low stock report", "get", "/api/v1/reports/low-stock")
        await hit("Expiring report", "get", "/api/v1/reports/expiring?within_days=30")
        today = date.today().isoformat()
        await hit(
            "Sales summary",
            "get",
            f"/api/v1/reports/sales-summary?from_date={today}&to_date={today}",
        )
        await hit("Reorder report", "get", "/api/v1/reports/reorder?cover_days=14")
        await hit("Seasonal report", "get", "/api/v1/reports/seasonal?season=winter_start")

        # customers / suppliers
        cust = await hit("Customers list", "get", "/api/v1/customers")
        await hit("Customers area filter", "get", "/api/v1/customers?area=Mirpur")
        sup = await hit("Suppliers list", "get", "/api/v1/suppliers")
        await hit("Purchases list", "get", "/api/v1/purchases")
        await hit("Branches list", "get", "/api/v1/branches")
        await hit("Sales list", "get", "/api/v1/sales?limit=10")

        # shifts
        open_shift = await c.get("/api/v1/shifts/mine/open", headers=h)
        if open_shift.status_code == 200 and open_shift.json():
            sid = open_shift.json()["id"]
            await hit("Shift summary", "get", f"/api/v1/shifts/{sid}/summary")
            ok("Shift open exists", sid[:8])
        else:
            opened = await hit(
                "Shift open",
                "post",
                "/api/v1/shifts/open",
                json={"opening_cash": "500.00"},
            )
            if opened is not None and opened.status_code < 400:
                sid = opened.json()["id"]
                await hit("Shift summary", "get", f"/api/v1/shifts/{sid}/summary")

        # POS sale (cash) — find a variant with stock
        products = (await c.get("/api/v1/products?page_size=50", headers=h)).json()
        variant_id = None
        for p in products.get("items", []):
            for v in p.get("variants", []):
                if Decimal(str(v.get("current_stock") or 0)) > 0:
                    variant_id = v["id"]
                    retail = v["retail_price"]
                    break
            if variant_id:
                break
        if not variant_id:
            fail("POS sale", "No in-stock variant found")
        else:
            sale_body = {
                "items": [{"variant_id": variant_id, "qty": "1"}],
                "payments": [{"method": "cash", "amount": str(retail)}],
                "discount": "0",
            }
            sale_r = await hit("POS create sale", "post", "/api/v1/sales", json=sale_body)
            if sale_r is not None and sale_r.status_code < 400:
                bill = sale_r.json()["bill_no"]
                await hit("Sale by bill", "get", f"/api/v1/sales/by-bill/{bill}")
                await hit(
                    "Receipt reprint",
                    "post",
                    f"/api/v1/sales/by-bill/{bill}/receipt",
                )
                item_id = sale_r.json()["items"][0]["id"]
                await hit(
                    "Return create",
                    "post",
                    "/api/v1/returns",
                    json={
                        "bill_no": bill,
                        "sale_item_id": item_id,
                        "qty": "1",
                        "is_damaged": False,
                        "reason": "audit test",
                    },
                )

        # dual pricing sale
        if variant_id:
            # get dealer price
            for p in products.get("items", []):
                for v in p.get("variants", []):
                    if v["id"] == variant_id:
                        dealer = v["dealer_price"]
                        break
            # may fail if stock 0 after previous sale — try another
            stocked = None
            dealer = "10.00"
            for p in products.get("items", []):
                for v in p.get("variants", []):
                    if Decimal(str(v.get("current_stock") or 0)) > 1:
                        stocked = v
                        dealer = v["dealer_price"]
                        break
                if stocked:
                    break
            if stocked:
                await hit(
                    "Dual price (dealer) sale",
                    "post",
                    "/api/v1/sales",
                    json={
                        "items": [
                            {
                                "variant_id": stocked["id"],
                                "qty": "1",
                                "use_dealer_price": True,
                            }
                        ],
                        "payments": [{"method": "cash", "amount": str(dealer)}],
                    },
                )
            else:
                skip("Dual price sale", "No stock left for second sale")

        # purchase
        if sup is not None and sup.status_code == 200 and sup.json() and variant_id:
            supplier_id = sup.json()[0]["id"]
            await hit(
                "Purchase create",
                "post",
                "/api/v1/purchases",
                json={
                    "supplier_id": supplier_id,
                    "invoice_no": f"AUDIT-{date.today().isoformat()}",
                    "invoice_date": date.today().isoformat(),
                    "lines": [
                        {
                            "variant_id": variant_id,
                            "qty": "2",
                            "cost_price": "5.00",
                        }
                    ],
                },
            )
            import time as _time

            await hit(
                "CSV import purchase",
                "post",
                "/api/v1/ops/purchases/import-csv",
                json={
                    "supplier_id": supplier_id,
                    "invoice_no": f"CSV-AUDIT-{int(_time.time())}",
                    "invoice_date": date.today().isoformat(),
                    "lines": [
                        {
                            "barcode": "SEED-ERASER-01",
                            "qty": "5",
                            "cost_price": "4.00",
                        }
                    ],
                },
            )

        await hit(
            "Invoice OCR",
            "post",
            "/api/v1/ops/invoices/ocr",
            json={"text": "SEED-NOTE-80,3,30"},
        )
        await hit("Daily SMS", "post", "/api/v1/ops/sms/daily-summary")
        await hit(
            "Offer SMS",
            "post",
            "/api/v1/ops/sms/offers",
            json={"area": "Mirpur", "message": "Audit offer test", "only_opt_in": True},
        )
        await hit("Due reminders", "post", "/api/v1/customers/due-reminders/run")

        # logistics
        import time as _time2

        van = await hit(
            "Van create",
            "post",
            "/api/v1/logistics/vans",
            json={"name": f"Audit Van {_time2.time_ns() % 100000}", "plate_no": None},
        )
        if van is not None and van.status_code < 400:
            await hit(
                "Delivery create",
                "post",
                "/api/v1/logistics/deliveries",
                json={"van_id": van.json()["id"], "destination": "Mirpur-10"},
            )
        await hit("Vans list", "get", "/api/v1/logistics/vans")
        await hit("Deliveries list", "get", "/api/v1/logistics/deliveries")

        # commission
        me_id = (await c.get("/api/v1/auth/me", headers=h)).json()["id"]
        await hit(
            "Commission rule",
            "post",
            "/api/v1/commissions/rules",
            json={
                "user_id": me_id,
                "name": "Audit 1%",
                "basis": "percent_of_sale",
                "rate": "1",
            },
        )
        await hit("Commission entries", "get", "/api/v1/commissions/entries")

        # stock count
        if variant_id:
            await hit(
                "Stock count",
                "post",
                "/api/v1/stock/counts",
                json={
                    "apply_adjustments": False,
                    "note": "audit",
                    "lines": [{"variant_id": variant_id, "counted_qty": "1"}],
                },
            )

        # chat
        chat = await hit(
            "AI chat",
            "post",
            "/api/v1/chat",
            json={"message": "কী কী লো স্টক?", "history": []},
        )
        if chat is not None and chat.status_code < 400:
            body = chat.json()
            if body.get("reply"):
                ok("AI chat reply non-empty", f"provider={body.get('provider')} len={len(body['reply'])}")
            else:
                fail("AI chat reply", "empty reply")

        # customer history
        if cust is not None and cust.status_code == 200 and cust.json():
            cid = cust.json()[0]["id"]
            await hit("Customer history", "get", f"/api/v1/customers/{cid}/history")

        # offline sync — endpoint reachable (validation may reject empty)
        try:
            sync_r = await c.post(
                "/api/v1/sync/sales",
                headers=h,
                json={"device_id": "audit-device", "items": []},
            )
            if sync_r.status_code in (200, 422):
                ok("Sync endpoint alive", f"status={sync_r.status_code}")
            else:
                fail("Sync endpoint", f"{sync_r.status_code} {sync_r.text[:160]}")
        except Exception as exc:
            fail("Sync endpoint", str(exc))


async def check_frontend() -> None:
    try:
        async with AsyncClient(timeout=15.0) as c:
            r = await c.get("http://127.0.0.1:3000/login")
            if r.status_code == 200:
                ok("Frontend :3000", "login page loads")
            else:
                fail("Frontend :3000", f"status {r.status_code}")
    except Exception as exc:
        fail("Frontend :3000", str(exc))


async def main() -> None:
    print("DATABASE_URL =", settings.DATABASE_URL)
    print("API_BASE     =", BASE)
    print("---")
    await check_db()
    await api_audit()
    await check_frontend()
    print("\n=== FUNCTIONAL AUDIT ===")
    passed = failed = skipped = 0
    for area, status, detail in results:
        mark = {"PASS": "✓", "FAIL": "✗", "SKIP": "·"}[status]
        print(f"{mark} [{status}] {area}: {detail}")
        if status == "PASS":
            passed += 1
        elif status == "FAIL":
            failed += 1
        else:
            skipped += 1
    print("---")
    print(f"PASS={passed} FAIL={failed} SKIP={skipped}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
