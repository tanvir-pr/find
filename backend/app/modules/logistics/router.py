from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import require_roles
from app.modules.logistics import service
from app.modules.logistics.schemas import (
    DeliveryCreate,
    DeliveryResponse,
    DeliveryUpdate,
    VanCreate,
    VanResponse,
)

router = APIRouter(prefix="/api/v1/logistics", tags=["logistics"])


@router.get("/vans", response_model=list[VanResponse])
async def vans(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.staff))],
) -> list[VanResponse]:
    return await service.list_vans(session)


@router.post("/vans", response_model=VanResponse, status_code=status.HTTP_201_CREATED)
async def create_van(
    body: VanCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> VanResponse:
    return await service.create_van(session, body)


@router.get("/deliveries", response_model=list[DeliveryResponse])
async def deliveries(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.staff))],
) -> list[DeliveryResponse]:
    return await service.list_deliveries(session)


@router.post("/deliveries", response_model=DeliveryResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery(
    body: DeliveryCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.staff))],
) -> DeliveryResponse:
    return await service.create_delivery(session, body)


@router.patch("/deliveries/{delivery_id}", response_model=DeliveryResponse)
async def update_delivery(
    delivery_id: UUID,
    body: DeliveryUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.staff))],
) -> DeliveryResponse:
    return await service.update_delivery(session, delivery_id, body)
