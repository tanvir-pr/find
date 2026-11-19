from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import get_current_user, require_roles
from app.modules.reports import service
from app.modules.reports.schemas import ExpiringItem, LowStockItem, SalesSummaryResponse

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/sales-summary", response_model=SalesSummaryResponse)
async def sales_summary(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
    from_date: date = Query(...),
    to_date: date = Query(...),
    staff_id: UUID | None = None,
) -> SalesSummaryResponse:
    return await service.sales_summary(session, from_date, to_date, user_id=staff_id)


@router.get("/low-stock", response_model=list[LowStockItem])
async def low_stock(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[LowStockItem]:
    return await service.low_stock_report(session)


@router.get("/expiring", response_model=list[ExpiringItem])
async def expiring(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    within_days: int = Query(30, ge=1, le=365),
) -> list[ExpiringItem]:
    return await service.expiring_report(session, within_days=within_days)
