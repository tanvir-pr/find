from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleError
from app.models.product import Batch
from app.models.stock import StockMovement


async def get_variant_stock(session: AsyncSession, variant_id: UUID) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(StockMovement.qty), 0)).where(
            StockMovement.variant_id == variant_id
        )
    )
    return Decimal(total or 0)


async def get_batch_stock(session: AsyncSession, batch_id: UUID) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(StockMovement.qty), 0)).where(
            StockMovement.batch_id == batch_id
        )
    )
    return Decimal(total or 0)


async def allocate_fifo(
    session: AsyncSession, variant_id: UUID, qty: Decimal
) -> list[tuple[UUID | None, Decimal]]:
    """Return list of (batch_id, qty) using earliest expiry first."""
    if qty <= 0:
        raise BusinessRuleError("Quantity must be positive")

    available = await get_variant_stock(session, variant_id)
    if available < qty:
        raise BusinessRuleError(f"স্টকে মাত্র {available} আছে")

    batches = (
        await session.scalars(
            select(Batch)
            .where(Batch.variant_id == variant_id)
            .order_by(Batch.expiry_date.asc().nulls_last(), Batch.created_at.asc())
        )
    ).all()

    remaining = qty
    allocations: list[tuple[UUID | None, Decimal]] = []
    for batch in batches:
        batch_qty = await get_batch_stock(session, batch.id)
        if batch_qty <= 0:
            continue
        take = min(batch_qty, remaining)
        allocations.append((batch.id, take))
        remaining -= take
        if remaining == 0:
            break

    if remaining > 0:
        allocations.append((None, remaining))

    return allocations
