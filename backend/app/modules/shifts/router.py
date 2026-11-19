from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import get_current_user, require_roles
from app.modules.shifts import service
from app.modules.shifts.schemas import (
    CashCloseRequest,
    ShiftOpenRequest,
    ShiftResponse,
    ShiftSummaryResponse,
)

router = APIRouter(prefix="/api/v1/shifts", tags=["shifts"])


@router.post("/open", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
async def open_shift(
    body: ShiftOpenRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[
        User, Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.staff))
    ],
) -> ShiftResponse:
    return await service.open_shift(session, body, user)


@router.get("/mine/open", response_model=ShiftResponse | None)
async def my_open_shift(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ShiftResponse | None:
    return await service.my_open_shift(session, user)


@router.get("/{shift_id}", response_model=ShiftResponse)
async def get_shift(
    shift_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> ShiftResponse:
    return await service.get_shift(session, shift_id)


@router.get("/{shift_id}/summary", response_model=ShiftSummaryResponse)
async def shift_summary(
    shift_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> ShiftSummaryResponse:
    return await service.shift_summary(session, shift_id)


@router.post("/{shift_id}/close", response_model=ShiftResponse)
async def close_shift(
    shift_id: UUID,
    body: CashCloseRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[
        User, Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.staff))
    ],
) -> ShiftResponse:
    return await service.close_shift(session, shift_id, body, user)
