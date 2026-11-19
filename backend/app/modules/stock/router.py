from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import get_current_user, require_roles
from app.modules.stock import service
from app.modules.stock.schemas import (
    PurchaseCreate,
    PurchaseResponse,
    StockAdjustmentCreate,
    StockCountCreate,
    StockCountResponse,
    StockMovementResponse,
    VariantStockResponse,
)

purchases_router = APIRouter(prefix="/api/v1/purchases", tags=["purchases"])
stock_router = APIRouter(prefix="/api/v1/stock", tags=["stock"])


@purchases_router.post("", response_model=PurchaseResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase(
    body: PurchaseCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> PurchaseResponse:
    return await service.create_purchase(session, body, user)


@purchases_router.get("", response_model=list[PurchaseResponse])
async def list_purchases(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[PurchaseResponse]:
    return await service.list_purchases(session)


@purchases_router.get("/{purchase_id}", response_model=PurchaseResponse)
async def get_purchase(
    purchase_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> PurchaseResponse:
    return await service.get_purchase(session, purchase_id)


@stock_router.get("/variants/{variant_id}", response_model=VariantStockResponse)
async def get_variant_stock(
    variant_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> VariantStockResponse:
    return await service.variant_stock(session, variant_id)


@stock_router.post(
    "/adjustments",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_adjustment(
    body: StockAdjustmentCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> StockMovementResponse:
    return await service.adjust_stock(session, body, user)


@stock_router.post(
    "/counts",
    response_model=StockCountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_stock_count(
    body: StockCountCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> StockCountResponse:
    return await service.create_stock_count(session, body, user)


@stock_router.get("/counts", response_model=list[StockCountResponse])
async def list_stock_counts(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[StockCountResponse]:
    return await service.list_stock_counts(session)
