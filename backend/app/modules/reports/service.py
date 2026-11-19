from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import PaymentMethod, PaymentType
from app.models.product import Batch, ProductVariant
from app.models.sales import Payment, Sale
from app.models.user import User
from app.modules.reports.schemas import ExpiringItem, LowStockItem, SalesSummaryResponse
from app.modules.stock.helpers import get_batch_stock, get_variant_stock

UTC = ZoneInfo("UTC")


def _day_bounds(from_date: date, to_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(from_date, time.min, tzinfo=UTC)
    end = datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=UTC)
    return start, end


async def sales_summary(
    session: AsyncSession, from_date: date, to_date: date, user_id: UUID | None = None
) -> SalesSummaryResponse:
    start, end = _day_bounds(from_date, to_date)
    sale_filter = [Sale.created_at >= start, Sale.created_at < end]
    if user_id:
        sale_filter.append(Sale.user_id == user_id)

    total_sales = Decimal(
        await session.scalar(
            select(func.coalesce(func.sum(Sale.total), 0)).where(*sale_filter)
        )
        or 0
    )
    total_discount = Decimal(
        await session.scalar(
            select(func.coalesce(func.sum(Sale.discount), 0)).where(*sale_filter)
        )
        or 0
    )
    bill_count = int(
        await session.scalar(select(func.count()).select_from(Sale).where(*sale_filter)) or 0
    )

    async def pay_sum(method: PaymentMethod) -> Decimal:
        q = (
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Sale, Payment.sale_id == Sale.id)
            .where(
                *sale_filter,
                Payment.payment_type == PaymentType.sale,
                Payment.method == method,
            )
        )
        return Decimal(await session.scalar(q) or 0)

    # Estimated profit: sale line net - cost from batch
    profit = Decimal("0")
    sales = (
        await session.scalars(
            select(Sale)
            .where(*sale_filter)
            .options(selectinload(Sale.items))
        )
    ).all()
    for sale in sales:
        for item in sale.items:
            cost = Decimal("0")
            if item.batch_id:
                batch = await session.get(Batch, item.batch_id)
                if batch:
                    cost = batch.cost_price * item.qty
            revenue = item.unit_price * item.qty - item.discount
            profit += revenue - cost

    staff_rows = (
        await session.execute(
            select(Sale.user_id, User.name, func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0))
            .join(User, User.id == Sale.user_id)
            .where(*sale_filter)
            .group_by(Sale.user_id, User.name)
        )
    ).all()
    by_staff = [
        {
            "user_id": str(row[0]),
            "name": row[1],
            "bill_count": int(row[2]),
            "total": str(row[3]),
        }
        for row in staff_rows
    ]

    return SalesSummaryResponse(
        from_date=from_date,
        to_date=to_date,
        total_sales=total_sales,
        total_discount=total_discount,
        bill_count=bill_count,
        cash=await pay_sum(PaymentMethod.cash),
        bkash=await pay_sum(PaymentMethod.bkash),
        nagad=await pay_sum(PaymentMethod.nagad),
        credit=await pay_sum(PaymentMethod.credit),
        estimated_profit=profit,
        by_staff=by_staff,
    )


async def low_stock_report(session: AsyncSession) -> list[LowStockItem]:
    variants = (
        await session.scalars(
            select(ProductVariant)
            .where(ProductVariant.is_active.is_(True))
            .options(selectinload(ProductVariant.product))
        )
    ).all()
    items: list[LowStockItem] = []
    for v in variants:
        stock = await get_variant_stock(session, v.id)
        if stock <= v.low_stock_threshold:
            items.append(
                LowStockItem(
                    variant_id=v.id,
                    product_name=v.product.name if v.product else "",
                    variant_name=v.name,
                    barcode=v.barcode,
                    current_stock=stock,
                    low_stock_threshold=v.low_stock_threshold,
                )
            )
    return items


async def expiring_report(session: AsyncSession, within_days: int = 30) -> list[ExpiringItem]:
    cutoff = date.today() + timedelta(days=within_days)
    batches = (
        await session.scalars(
            select(Batch)
            .where(Batch.expiry_date.is_not(None), Batch.expiry_date <= cutoff)
            .options(selectinload(Batch.variant).selectinload(ProductVariant.product))
        )
    ).all()
    items: list[ExpiringItem] = []
    for b in batches:
        remaining = await get_batch_stock(session, b.id)
        if remaining <= 0:
            continue
        variant = b.variant
        items.append(
            ExpiringItem(
                batch_id=b.id,
                variant_id=b.variant_id,
                product_name=variant.product.name if variant and variant.product else "",
                variant_name=variant.name if variant else "",
                expiry_date=b.expiry_date,
                remaining_qty=remaining,
            )
        )
    return items
