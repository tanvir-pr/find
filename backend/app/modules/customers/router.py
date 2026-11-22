from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import get_current_user, require_roles
from app.modules.customers import service
from app.modules.customers.schemas import (
    CollectionCreate,
    CustomerCreate,
    CustomerHistoryItem,
    CustomerResponse,
    CustomerUpdate,
    DueReminderResponse,
)

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> CustomerResponse:
    return await service.create_customer(session, body)


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    area: str | None = Query(None),
) -> list[CustomerResponse]:
    return await service.list_customers(session, area=area)


@router.post(
    "/due-reminders/run",
    response_model=list[DueReminderResponse],
)
async def run_due_reminders(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> list[DueReminderResponse]:
    return await service.send_due_reminders(session)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> CustomerResponse:
    return await service.get_customer(session, customer_id)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    body: CustomerUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> CustomerResponse:
    return await service.update_customer(session, customer_id, body)


@router.get("/{customer_id}/history", response_model=list[CustomerHistoryItem])
async def customer_history(
    customer_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[CustomerHistoryItem]:
    return await service.customer_history(session, customer_id)


@router.post("/{customer_id}/collections", response_model=CustomerResponse)
async def collect_due(
    customer_id: UUID,
    body: CollectionCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.staff))],
) -> CustomerResponse:
    return await service.collect_due(session, customer_id, body, user)
