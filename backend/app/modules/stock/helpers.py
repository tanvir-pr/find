from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import StockMovement


async def get_variant_stock(session: AsyncSession, variant_id: UUID) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(StockMovement.qty), 0)).where(
            StockMovement.variant_id == variant_id
        )
    )
    return Decimal(total or 0)
