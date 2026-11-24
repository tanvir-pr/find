"""Shop demo seed (Step 7). Idempotent — use --force to wipe business data and reseed.

Covers demo scenarios for:
  A7 seasonal/version sales, B4/B5 expiry, B6 low stock,
  D2 credit sales, D7 credit limit customers.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select, text, update

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.branch import Branch
from app.models.customer import Customer
from app.models.enums import PaymentMethod, PaymentType, StockMovementType, UserRole
from app.models.product import Batch, Product, ProductVariant
from app.models.sales import Payment, Sale, SaleItem
from app.models.shift import CashClosing, Shift
from app.models.stock import StockMovement
from app.models.supplier import PurchaseInvoice, Supplier
from app.models.user import User

UTC = ZoneInfo("UTC")
SEED_MARKER = "SEED-BAG-ORIG"

# Business tables only — keep users, branches, knowledge_chunks.
BUSINESS_TABLES = (
    "receipt_logs",
    "sms_logs",
    "sync_logs",
    "commission_entries",
    "deliveries",
    "returns",
    "payments",
    "sale_items",
    "sales",
    "cash_closings",
    "shifts",
    "stock_count_lines",
    "stock_counts",
    "stock_movements",
    "batches",
    "purchase_invoices",
    "product_variants",
    "products",
    "customers",
    "suppliers",
    "vans",
    "commission_rules",
)


async def _wipe_business_data(session) -> None:
    tables = ", ".join(BUSINESS_TABLES)
    await session.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))
    await session.commit()
    print("  wiped business tables (dummy/test rows removed)")


async def _ensure_user(
    session, *, name: str, email: str, password: str, role: UserRole, branch_id
) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    if user:
        user.name = name
        user.role = role
        user.is_active = True
        user.branch_id = branch_id
        await session.flush()
        return user
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        branch_id=branch_id,
    )
    session.add(user)
    await session.flush()
    print(f"  user {email} ({role.value})")
    return user


async def _ensure_branch(session) -> Branch:
    branch = await session.scalar(select(Branch).where(Branch.code == "MAIN"))
    if branch:
        branch.name = "মিরপুর স্টেশনারি শপ"
        branch.address = "Mirpur-10, Dhaka"
        branch.phone = "01711001100"
        branch.is_active = True
        await session.flush()
        return branch
    branch = Branch(
        name="মিরপুর স্টেশনারি শপ",
        code="MAIN",
        address="Mirpur-10, Dhaka",
        phone="01711001100",
        is_active=True,
    )
    session.add(branch)
    await session.flush()
    print("  branch MAIN")
    return branch


def _dt(year: int, month: int, day: int, hour: int = 10) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=UTC)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed realistic shop demo data")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Wipe products/sales/customers/etc. then reseed clean data",
    )
    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        if args.force:
            print("force reseeding…")
            await _wipe_business_data(session)
        else:
            existing = await session.scalar(
                select(ProductVariant).where(ProductVariant.barcode == SEED_MARKER)
            )
            if existing:
                print("seed_demo already applied (SEED-BAG-ORIG exists) — skip")
                print("tip: uv run python scripts/seed_demo.py --force")
                return

        print("seeding shop data…")
        branch = await _ensure_branch(session)
        admin = await _ensure_user(
            session,
            name="দোকান মালিক রফিক",
            email="admin@dokan.example",
            password="Admin123!",
            role=UserRole.admin,
            branch_id=branch.id,
        )
        manager = await _ensure_user(
            session,
            name="ম্যানেজার সালমা",
            email="manager@dokan.example",
            password="Manager123!",
            role=UserRole.manager,
            branch_id=branch.id,
        )
        staff = await _ensure_user(
            session,
            name="ক্যাশিয়ার রহিম",
            email="staff@dokan.example",
            password="Staff123!",
            role=UserRole.staff,
            branch_id=branch.id,
        )
        _ = manager

        # --- suppliers (real Dhaka wholesale areas) ---
        stationery = Supplier(
            name="নবাবপুর স্টেশনারি সাপ্লাই",
            phone="01811112233",
            address="Nawabpur Road, Dhaka",
        )
        adhesives = Supplier(
            name="চকবাজার আঠা ও কালি সেন্টার",
            phone="01822223344",
            address="Chawk Bazar, Dhaka",
        )
        session.add_all([stationery, adhesives])
        await session.flush()
        print("  suppliers")

        # --- catalog ---
        products_spec = [
            {
                "name": "School Bag",
                "category": "bags",
                "tracks_expiry": False,
                "variants": [
                    {
                        "name": "Original",
                        "barcode": SEED_MARKER,
                        "retail": "850.00",
                        "dealer": "700.00",
                        "low": "5",
                    },
                    {
                        "name": "Duplicate",
                        "barcode": "SEED-BAG-DUP",
                        "retail": "450.00",
                        "dealer": "350.00",
                        "low": "8",
                    },
                ],
            },
            {
                "name": "Ball Pen Red",
                "category": "pens",
                "tracks_expiry": False,
                "variants": [
                    {
                        "name": "Original",
                        "barcode": "SEED-PEN-ORIG",
                        "retail": "15.00",
                        "dealer": "10.00",
                        "low": "50",
                    },
                    {
                        "name": "Duplicate",
                        "barcode": "SEED-PEN-DUP",
                        "retail": "8.00",
                        "dealer": "5.00",
                        "low": "80",
                    },
                ],
            },
            {
                "name": "Exercise Book A4",
                "category": "notebooks",
                "tracks_expiry": False,
                "variants": [
                    {
                        "name": "80 pages",
                        "barcode": "SEED-NOTE-80",
                        "retail": "45.00",
                        "dealer": "35.00",
                        "low": "30",
                    },
                ],
            },
            {
                "name": "Glue Stick 20g",
                "category": "adhesives",
                "tracks_expiry": True,
                "variants": [
                    {
                        "name": "20g",
                        "barcode": "SEED-GLUE-20",
                        "retail": "50.00",
                        "dealer": "40.00",
                        "low": "40",
                    },
                ],
            },
            {
                "name": "Fountain Ink Blue",
                "category": "ink",
                "tracks_expiry": True,
                "variants": [
                    {
                        "name": "60ml",
                        "barcode": "SEED-INK-60",
                        "retail": "80.00",
                        "dealer": "60.00",
                        "low": "20",
                    },
                ],
            },
            {
                "name": "Water Bottle 1L",
                "category": "bottles",
                "tracks_expiry": False,
                "variants": [
                    {
                        "name": "Standard",
                        "barcode": "SEED-BOTTLE-1L",
                        "retail": "120.00",
                        "dealer": "90.00",
                        "low": "15",
                    },
                ],
            },
            {
                "name": "Wool Cap",
                "category": "winter",
                "tracks_expiry": False,
                "variants": [
                    {
                        "name": "Adult",
                        "barcode": "SEED-CAP-ADULT",
                        "retail": "200.00",
                        "dealer": "150.00",
                        "low": "10",
                    },
                ],
            },
            {
                "name": "Geometry Box",
                "category": "instruments",
                "tracks_expiry": False,
                "variants": [
                    {
                        "name": "Plastic",
                        "barcode": "SEED-GEO-BOX",
                        "retail": "180.00",
                        "dealer": "140.00",
                        "low": "12",
                    },
                ],
            },
            {
                "name": "Eraser White",
                "category": "stationery",
                "tracks_expiry": False,
                "variants": [
                    {
                        "name": "Standard",
                        "barcode": "SEED-ERASER-01",
                        "retail": "10.00",
                        "dealer": "6.00",
                        "low": "40",
                    },
                ],
            },
        ]

        variant_by_barcode: dict[str, ProductVariant] = {}
        for spec in products_spec:
            product = Product(
                name=spec["name"],
                category=spec["category"],
                unit="pcs",
                tracks_expiry=spec["tracks_expiry"],
                is_active=True,
            )
            session.add(product)
            await session.flush()
            for v in spec["variants"]:
                variant = ProductVariant(
                    product_id=product.id,
                    name=v["name"],
                    barcode=v["barcode"],
                    retail_price=Decimal(v["retail"]),
                    dealer_price=Decimal(v["dealer"]),
                    low_stock_threshold=Decimal(v["low"]),
                    is_active=True,
                )
                session.add(variant)
                await session.flush()
                variant_by_barcode[v["barcode"]] = variant
        print(f"  products/variants ({len(variant_by_barcode)})")

        today = date.today()
        purchase_lines: list[tuple[str, str, Decimal, Decimal, date | None, Supplier]] = [
            (SEED_MARKER, "PUR-BAG-2401", Decimal("40"), Decimal("650.00"), None, stationery),
            ("SEED-BAG-DUP", "PUR-BAG-2401", Decimal("50"), Decimal("320.00"), None, stationery),
            ("SEED-PEN-ORIG", "PUR-PEN-2401", Decimal("200"), Decimal("8.00"), None, stationery),
            ("SEED-PEN-DUP", "PUR-PEN-2401", Decimal("300"), Decimal("4.00"), None, stationery),
            ("SEED-NOTE-80", "PUR-NOTE-2401", Decimal("100"), Decimal("30.00"), None, stationery),
            ("SEED-GEO-BOX", "PUR-NOTE-2401", Decimal("40"), Decimal("120.00"), None, stationery),
            ("SEED-ERASER-01", "PUR-NOTE-2401", Decimal("150"), Decimal("4.00"), None, stationery),
            (
                "SEED-GLUE-20",
                "PUR-GLUE-2401",
                Decimal("60"),
                Decimal("35.00"),
                today + timedelta(days=12),
                adhesives,
            ),
            (
                "SEED-INK-60",
                "PUR-INK-2401",
                Decimal("40"),
                Decimal("50.00"),
                today + timedelta(days=5),
                adhesives,
            ),
            ("SEED-BOTTLE-1L", "PUR-BOT-2401", Decimal("80"), Decimal("70.00"), None, stationery),
            ("SEED-CAP-ADULT", "PUR-CAP-2401", Decimal("30"), Decimal("120.00"), None, stationery),
        ]

        invoices: dict[str, list] = {}
        for row in purchase_lines:
            invoices.setdefault(row[1], []).append(row)

        batch_by_barcode: dict[str, Batch] = {}
        for inv_no, lines in invoices.items():
            supplier = lines[0][5]
            total = sum((qty * cost for _, _, qty, cost, _, _ in lines), Decimal("0"))
            inv = PurchaseInvoice(
                supplier_id=supplier.id,
                invoice_no=inv_no,
                invoice_date=today - timedelta(days=60),
                total_amount=total,
                created_by=admin.id,
                branch_id=branch.id,
            )
            session.add(inv)
            await session.flush()
            for barcode, _, qty, cost, expiry, _ in lines:
                variant = variant_by_barcode[barcode]
                batch = Batch(
                    variant_id=variant.id,
                    purchase_invoice_id=inv.id,
                    initial_qty=qty,
                    cost_price=cost,
                    expiry_date=expiry,
                )
                session.add(batch)
                await session.flush()
                batch_by_barcode[barcode] = batch
                session.add(
                    StockMovement(
                        variant_id=variant.id,
                        batch_id=batch.id,
                        movement_type=StockMovementType.purchase,
                        qty=qty,
                        ref_type="purchase_invoice",
                        ref_id=inv.id,
                        user_id=admin.id,
                        branch_id=branch.id,
                        note="opening stock purchase",
                    )
                )
        print("  purchases/batches")

        karim = Customer(
            name="Karim Dealer",
            phone="01910000001",
            email="karim@example.com",
            area="Mirpur",
            credit_limit=Decimal("50000.00"),
            offer_opt_in=True,
            loyalty_points=120,
        )
        rahima = Customer(
            name="Rahima Retail",
            phone="01910000002",
            email="rahima@example.com",
            area="Dhanmondi",
            credit_limit=Decimal("5000.00"),
            offer_opt_in=False,
            loyalty_points=40,
        )
        walkin = Customer(
            name="Walk-in Banani",
            phone="01910000003",
            email="walkin.banani@example.com",
            area="Banani",
            credit_limit=Decimal("0"),
            offer_opt_in=True,
            loyalty_points=0,
        )
        session.add_all([karim, rahima, walkin])
        await session.flush()
        print("  customers")

        bill_seq = 0

        async def make_sale(
            *,
            when: datetime,
            cashier: User,
            items: list[tuple[str, Decimal, Decimal | None]],
            payments: list[tuple[PaymentMethod, Decimal]],
            customer: Customer | None = None,
            discount: Decimal = Decimal("0"),
            shift_id=None,
            bill_prefix: str = "BILL",
        ) -> Sale:
            nonlocal bill_seq
            bill_seq += 1
            line_rows = []
            subtotal = Decimal("0")
            for barcode, qty, unit_override in items:
                variant = variant_by_barcode[barcode]
                batch = batch_by_barcode[barcode]
                unit = unit_override if unit_override is not None else variant.retail_price
                line_total = unit * qty
                subtotal += line_total
                line_rows.append((variant, batch, qty, unit))
            total = subtotal - discount
            sale = Sale(
                bill_no=f"{bill_prefix}-{when.strftime('%Y%m%d')}-{bill_seq:04d}",
                customer_id=customer.id if customer else None,
                user_id=cashier.id,
                shift_id=shift_id,
                branch_id=branch.id,
                subtotal=subtotal,
                discount=discount,
                total=total,
                created_at=when,
                updated_at=when,
            )
            session.add(sale)
            await session.flush()
            for variant, batch, qty, unit in line_rows:
                session.add(
                    SaleItem(
                        sale_id=sale.id,
                        variant_id=variant.id,
                        batch_id=batch.id,
                        qty=qty,
                        unit_price=unit,
                        discount=Decimal("0"),
                        created_at=when,
                        updated_at=when,
                    )
                )
                session.add(
                    StockMovement(
                        variant_id=variant.id,
                        batch_id=batch.id,
                        movement_type=StockMovementType.sale,
                        qty=-qty,
                        ref_type="sale",
                        ref_id=sale.id,
                        user_id=cashier.id,
                        shift_id=shift_id,
                        branch_id=branch.id,
                        created_at=when,
                        updated_at=when,
                    )
                )
            for method, amount in payments:
                session.add(
                    Payment(
                        payment_type=PaymentType.sale,
                        sale_id=sale.id,
                        customer_id=customer.id if customer else None,
                        method=method,
                        amount=amount,
                        user_id=cashier.id,
                        created_at=when,
                        updated_at=when,
                    )
                )
            return sale

        year = today.year if today.month >= 2 else today.year - 1
        for day, qty_orig, qty_dup in [(8, 3, 1), (15, 4, 1), (22, 5, 2)]:
            await make_sale(
                when=_dt(year, 1, day, 11),
                cashier=staff,
                items=[
                    (SEED_MARKER, Decimal(qty_orig), None),
                    ("SEED-BAG-DUP", Decimal(qty_dup), None),
                    ("SEED-CAP-ADULT", Decimal("2"), None),
                ],
                payments=[(PaymentMethod.cash, Decimal("0"))],
                bill_prefix="WIN",
            )
        for sale in (
            await session.scalars(select(Sale).where(Sale.bill_no.like("WIN-%")))
        ).all():
            await session.execute(
                update(Payment).where(Payment.sale_id == sale.id).values(amount=sale.total)
            )

        for day, qty in [(5, 6), (12, 8), (20, 10)]:
            await make_sale(
                when=_dt(year, 6, day, 14),
                cashier=staff,
                items=[
                    ("SEED-BOTTLE-1L", Decimal(qty), None),
                    ("SEED-PEN-ORIG", Decimal("10"), None),
                ],
                payments=[(PaymentMethod.bkash, Decimal("0"))],
                bill_prefix="SUM",
            )
        for sale in (
            await session.scalars(select(Sale).where(Sale.bill_no.like("SUM-%")))
        ).all():
            await session.execute(
                update(Payment).where(Payment.sale_id == sale.id).values(amount=sale.total)
            )

        shift = Shift(
            user_id=staff.id,
            branch_id=branch.id,
            opened_at=datetime.now(UTC) - timedelta(hours=4),
            opening_cash=Decimal("1000.00"),
        )
        session.add(shift)
        await session.flush()

        glue_retail = variant_by_barcode["SEED-GLUE-20"].retail_price
        discounted = glue_retail * Decimal("0.7")
        await make_sale(
            when=datetime.now(UTC) - timedelta(hours=2),
            cashier=staff,
            items=[("SEED-GLUE-20", Decimal("5"), discounted)],
            payments=[(PaymentMethod.cash, discounted * 5)],
            shift_id=shift.id,
            bill_prefix="TODAY",
        )

        await make_sale(
            when=datetime.now(UTC) - timedelta(hours=1),
            cashier=staff,
            items=[
                ("SEED-NOTE-80", Decimal("4"), None),
                ("SEED-PEN-DUP", Decimal("20"), None),
                ("SEED-ERASER-01", Decimal("5"), None),
            ],
            payments=[
                (PaymentMethod.cash, Decimal("100.00")),
                (PaymentMethod.nagad, Decimal("240.00")),
            ],
            shift_id=shift.id,
            bill_prefix="TODAY",
        )
        today_sales = (
            await session.scalars(
                select(Sale).where(Sale.bill_no.like("TODAY-%")).order_by(Sale.bill_no)
            )
        ).all()
        if len(today_sales) >= 2:
            sale2 = today_sales[1]
            cash_amt = Decimal("100.00")
            nagad_amt = sale2.total - cash_amt
            for p in (
                await session.scalars(select(Payment).where(Payment.sale_id == sale2.id))
            ).all():
                if p.method == PaymentMethod.cash:
                    p.amount = cash_amt
                elif p.method == PaymentMethod.nagad:
                    p.amount = nagad_amt

        await make_sale(
            when=datetime.now(UTC) - timedelta(minutes=30),
            cashier=staff,
            customer=karim,
            items=[
                (SEED_MARKER, Decimal("2"), variant_by_barcode[SEED_MARKER].dealer_price),
                ("SEED-PEN-ORIG", Decimal("50"), variant_by_barcode["SEED-PEN-ORIG"].dealer_price),
            ],
            payments=[(PaymentMethod.credit, Decimal("0"))],
            shift_id=shift.id,
            bill_prefix="CR",
        )
        for sale in (await session.scalars(select(Sale).where(Sale.bill_no.like("CR-%")))).all():
            await session.execute(
                update(Payment)
                .where(Payment.sale_id == sale.id)
                .values(amount=sale.total, customer_id=karim.id)
            )

        session.add(
            Payment(
                payment_type=PaymentType.customer_collection,
                customer_id=karim.id,
                method=PaymentMethod.bkash,
                amount=Decimal("500.00"),
                user_id=admin.id,
                note="partial collection from Karim",
                txn_id="COLLECT-KARIM-001",
            )
        )

        await make_sale(
            when=datetime.now(UTC) - timedelta(minutes=20),
            cashier=staff,
            customer=rahima,
            items=[("SEED-NOTE-80", Decimal("10"), None)],
            payments=[(PaymentMethod.credit, Decimal("0"))],
            shift_id=shift.id,
            bill_prefix="CRR",
        )
        for sale in (await session.scalars(select(Sale).where(Sale.bill_no.like("CRR-%")))).all():
            await session.execute(
                update(Payment)
                .where(Payment.sale_id == sale.id)
                .values(amount=sale.total, customer_id=rahima.id)
            )

        await make_sale(
            when=datetime.now(UTC) - timedelta(minutes=10),
            cashier=staff,
            items=[("SEED-PEN-ORIG", Decimal("120"), None)],
            payments=[(PaymentMethod.cash, Decimal("0"))],
            shift_id=shift.id,
            bill_prefix="LOW",
        )
        for sale in (await session.scalars(select(Sale).where(Sale.bill_no.like("LOW-%")))).all():
            await session.execute(
                update(Payment).where(Payment.sale_id == sale.id).values(amount=sale.total)
            )

        closed_shift = Shift(
            user_id=staff.id,
            branch_id=branch.id,
            opened_at=datetime.now(UTC) - timedelta(days=1, hours=8),
            closed_at=datetime.now(UTC) - timedelta(days=1, hours=1),
            opening_cash=Decimal("500.00"),
        )
        session.add(closed_shift)
        await session.flush()
        session.add(
            CashClosing(
                shift_id=closed_shift.id,
                expected_cash=Decimal("1850.00"),
                counted_cash=Decimal("1840.00"),
                difference=Decimal("-10.00"),
                note="cash short by 10 BDT",
            )
        )

        first_inv = await session.scalar(
            select(PurchaseInvoice).where(PurchaseInvoice.invoice_no == "PUR-BAG-2401")
        )
        session.add(
            Payment(
                payment_type=PaymentType.supplier_payment,
                supplier_id=stationery.id,
                purchase_invoice_id=first_inv.id if first_inv else None,
                method=PaymentMethod.cash,
                amount=Decimal("10000.00"),
                user_id=admin.id,
                note="partial supplier payment",
                txn_id="SUPPAY-NAWABPUR-001",
            )
        )

        await session.commit()
        print("seed_demo done")
        print("logins: admin@dokan.example / Admin123!")
        print("        manager@dokan.example / Manager123!")
        print("        staff@dokan.example / Staff123!")


if __name__ == "__main__":
    asyncio.run(main())
