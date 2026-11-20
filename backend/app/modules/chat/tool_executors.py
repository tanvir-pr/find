"""Execute the 7 read-only chat tools against the database."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ForbiddenError
from app.models.customer import Customer
from app.models.enums import PaymentType, UserRole
from app.models.product import Product, ProductVariant
from app.models.sales import Payment, Sale, SaleItem
from app.models.user import User
from app.modules.chat.tool_defs import STAFF_ALLOWED_TOOLS
from app.modules.customers.service import get_customer_due
from app.modules.reports import service as reports_service
from app.modules.stock.helpers import get_variant_stock

UTC = ZoneInfo("UTC")

SEASON_MONTHS: dict[str, list[int]] = {
    "winter_start": [12, 1],
    "winter_end": [1, 2],
    "summer_start": [4, 5],
    "summer_end": [6, 7],
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime, UUID)):
        return str(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _dump(data: Any) -> str:
    return json.dumps(_jsonable(data), ensure_ascii=False)


def _period_bounds(period: str) -> tuple[date, date]:
    today = date.today()
    if period == "today":
        return today, today
    if period == "week":
        return today - timedelta(days=6), today
    if period == "month":
        return today.replace(day=1), today
    raise ValueError("period must be today|week|month")


def _assert_tool_allowed(user: User, name: str) -> None:
    if user.role in (UserRole.admin, UserRole.manager):
        return
    if name not in STAFF_ALLOWED_TOOLS:
        raise ForbiddenError(f"Tool '{name}' is not allowed for role {user.role.value}")


async def check_stock(session: AsyncSession, user: User, args: dict[str, Any]) -> str:
    _assert_tool_allowed(user, "check_stock")
    query = str(args.get("query") or "").strip()
    if not query:
        return _dump({"error": "query required"})
    pattern = f"%{query}%"
    products = (
        await session.scalars(
            select(Product)
            .options(selectinload(Product.variants))
            .where(
                Product.is_active.is_(True),
                or_(
                    Product.name.ilike(pattern),
                    Product.variants.any(ProductVariant.barcode.ilike(pattern)),
                    Product.variants.any(ProductVariant.name.ilike(pattern)),
                ),
            )
            .limit(10)
        )
    ).unique().all()
    items = []
    for p in products:
        for v in p.variants:
            if not v.is_active:
                continue
            stock = await get_variant_stock(session, v.id)
            items.append(
                {
                    "product": p.name,
                    "variant": v.name,
                    "barcode": v.barcode,
                    "current_stock": stock,
                    "retail_price": v.retail_price,
                    "dealer_price": v.dealer_price,
                    "category": p.category,
                }
            )
    return _dump({"query": query, "matches": items, "count": len(items)})


async def low_stock_list(session: AsyncSession, user: User, args: dict[str, Any]) -> str:
    _assert_tool_allowed(user, "low_stock_list")
    category = args.get("category")
    rows = await reports_service.low_stock_report(session)
    if category:
        cat = str(category).lower()
        # filter via product category — report has product_name only; re-query lightly
        variants = (
            await session.scalars(
                select(ProductVariant)
                .join(Product)
                .where(
                    ProductVariant.is_active.is_(True),
                    Product.category.ilike(cat),
                )
                .options(selectinload(ProductVariant.product))
            )
        ).all()
        filtered = []
        for v in variants:
            stock = await get_variant_stock(session, v.id)
            if stock <= v.low_stock_threshold:
                filtered.append(
                    {
                        "product": v.product.name if v.product else "",
                        "variant": v.name,
                        "barcode": v.barcode,
                        "current_stock": stock,
                        "low_stock_threshold": v.low_stock_threshold,
                        "category": v.product.category if v.product else None,
                    }
                )
        return _dump({"items": filtered, "count": len(filtered)})
    return _dump(
        {
            "items": [
                {
                    "product": r.product_name,
                    "variant": r.variant_name,
                    "barcode": r.barcode,
                    "current_stock": r.current_stock,
                    "low_stock_threshold": r.low_stock_threshold,
                }
                for r in rows
            ],
            "count": len(rows),
        }
    )


async def expiring_items(session: AsyncSession, user: User, args: dict[str, Any]) -> str:
    _assert_tool_allowed(user, "expiring_items")
    within = int(args.get("within_days") or 30)
    rows = await reports_service.expiring_report(session, within_days=within)
    return _dump(
        {
            "within_days": within,
            "items": [
                {
                    "product": r.product_name,
                    "variant": r.variant_name,
                    "expiry_date": r.expiry_date,
                    "remaining_qty": r.remaining_qty,
                    "batch_id": r.batch_id,
                }
                for r in rows
            ],
            "count": len(rows),
        }
    )


async def sales_summary(session: AsyncSession, user: User, args: dict[str, Any]) -> str:
    _assert_tool_allowed(user, "sales_summary")
    period = str(args.get("period") or "today")
    from_date, to_date = _period_bounds(period)
    staff_id = None
    staff_name = args.get("staff_name")
    if staff_name:
        staff = await session.scalar(
            select(User).where(User.name.ilike(f"%{str(staff_name).strip()}%"))
        )
        if staff:
            staff_id = staff.id
    summary = await reports_service.sales_summary(
        session, from_date, to_date, user_id=staff_id
    )
    payload = summary.model_dump()
    if user.role == UserRole.staff:
        payload.pop("estimated_profit", None)
    payload["period"] = period
    return _dump(payload)


async def reorder_suggestion(session: AsyncSession, user: User, args: dict[str, Any]) -> str:
    _assert_tool_allowed(user, "reorder_suggestion")
    lookback = int(args.get("lookback_days") or 28)
    cover = int(args.get("cover_days") or 14)
    category = args.get("category")
    start = datetime.combine(date.today() - timedelta(days=lookback), time.min, tzinfo=UTC)

    stmt = (
        select(
            SaleItem.variant_id,
            func.coalesce(func.sum(SaleItem.qty), 0),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .where(Sale.created_at >= start)
        .group_by(SaleItem.variant_id)
    )
    sold_map = {row[0]: Decimal(row[1]) for row in (await session.execute(stmt)).all()}

    v_stmt = (
        select(ProductVariant)
        .join(Product)
        .where(ProductVariant.is_active.is_(True), Product.is_active.is_(True))
        .options(selectinload(ProductVariant.product))
    )
    if category:
        v_stmt = v_stmt.where(Product.category.ilike(str(category)))
    variants = (await session.scalars(v_stmt)).all()

    suggestions = []
    for v in variants:
        sold = sold_map.get(v.id, Decimal("0"))
        avg_daily = sold / Decimal(lookback) if lookback else Decimal("0")
        stock = await get_variant_stock(session, v.id)
        need = avg_daily * Decimal(cover) - stock
        if need <= 0:
            continue
        suggestions.append(
            {
                "product": v.product.name if v.product else "",
                "variant": v.name,
                "barcode": v.barcode,
                "current_stock": stock,
                "sold_in_lookback": sold,
                "avg_daily": round(avg_daily, 3),
                "suggested_qty": round(need, 0),
                "cover_days": cover,
            }
        )
    suggestions.sort(key=lambda x: Decimal(x["suggested_qty"]), reverse=True)
    return _dump(
        {
            "lookback_days": lookback,
            "cover_days": cover,
            "suggestions": suggestions[:20],
            "count": len(suggestions[:20]),
        }
    )


async def seasonal_top_products(session: AsyncSession, user: User, args: dict[str, Any]) -> str:
    _assert_tool_allowed(user, "seasonal_top_products")
    season = args.get("season")
    month = args.get("month")
    category = args.get("category")
    year = args.get("year")

    if season:
        months = SEASON_MONTHS.get(str(season))
        if not months:
            return _dump({"error": f"unknown season {season}"})
    elif month:
        months = [int(month)]
    else:
        months = [date.today().month]

    y = int(year) if year else date.today().year
    # Include previous year for Jan winter when needed
    years = {y, y - 1}

    start = datetime(min(years), 1, 1, tzinfo=UTC)
    end = datetime(max(years) + 1, 1, 1, tzinfo=UTC)

    stmt = (
        select(
            SaleItem.variant_id,
            func.coalesce(func.sum(SaleItem.qty), 0).label("qty"),
            func.coalesce(func.sum(SaleItem.unit_price * SaleItem.qty), 0).label("revenue"),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .where(
            Sale.created_at >= start,
            Sale.created_at < end,
            func.extract("month", Sale.created_at).in_(months),
        )
        .group_by(SaleItem.variant_id)
        .order_by(func.coalesce(func.sum(SaleItem.qty), 0).desc())
        .limit(30)
    )
    rows = (await session.execute(stmt)).all()
    items = []
    for variant_id, qty, revenue in rows:
        variant = await session.get(
            ProductVariant, variant_id, options=[selectinload(ProductVariant.product)]
        )
        if variant is None or variant.product is None:
            continue
        if category and (variant.product.category or "").lower() != str(category).lower():
            continue
        items.append(
            {
                "product": variant.product.name,
                "variant": variant.name,
                "barcode": variant.barcode,
                "category": variant.product.category,
                "qty_sold": qty,
                "revenue": revenue,
            }
        )
    return _dump(
        {
            "season": season,
            "months": months,
            "years": sorted(years),
            "items": items[:15],
            "count": len(items[:15]),
        }
    )


async def customer_due(session: AsyncSession, user: User, args: dict[str, Any]) -> str:
    _assert_tool_allowed(user, "customer_due")
    query = str(args.get("query") or "").strip()
    stmt = select(Customer)
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(or_(Customer.name.ilike(pattern), Customer.phone.ilike(pattern)))
    customers = (await session.scalars(stmt.order_by(Customer.name).limit(30))).all()

    results = []
    for c in customers:
        due = await get_customer_due(session, c.id)
        if query == "" and due <= 0:
            continue
        last_pay = await session.scalar(
            select(func.max(Payment.created_at)).where(
                Payment.customer_id == c.id,
                Payment.payment_type == PaymentType.customer_collection,
            )
        )
        results.append(
            {
                "customer_id": c.id,
                "name": c.name,
                "phone": c.phone,
                "area": c.area,
                "credit_limit": c.credit_limit,
                "current_due": due,
                "last_collection_at": last_pay,
            }
        )
    results.sort(key=lambda r: Decimal(r["current_due"]), reverse=True)
    return _dump({"customers": results, "count": len(results)})


EXECUTORS = {
    "check_stock": check_stock,
    "low_stock_list": low_stock_list,
    "expiring_items": expiring_items,
    "sales_summary": sales_summary,
    "reorder_suggestion": reorder_suggestion,
    "seasonal_top_products": seasonal_top_products,
    "customer_due": customer_due,
}


async def execute_tool(
    session: AsyncSession, user: User, name: str, arguments: dict[str, Any]
) -> str:
    fn = EXECUTORS.get(name)
    if fn is None:
        return _dump({"error": f"unknown tool: {name}"})
    try:
        return await fn(session, user, arguments or {})
    except ForbiddenError:
        raise
    except Exception as exc:  # noqa: BLE001 — tool errors become model-visible JSON
        return _dump({"error": str(exc)})
