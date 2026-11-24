from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import require_roles
from app.modules.commissions import service
from app.modules.commissions.schemas import (
    CommissionEntryResponse,
    CommissionRuleCreate,
    CommissionRuleResponse,
)

router = APIRouter(prefix="/api/v1/commissions", tags=["commissions"])


@router.get("/rules", response_model=list[CommissionRuleResponse])
async def rules(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> list[CommissionRuleResponse]:
    return await service.list_rules(session)


@router.post("/rules", response_model=CommissionRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    body: CommissionRuleCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
) -> CommissionRuleResponse:
    return await service.create_rule(session, body)


@router.get("/entries", response_model=list[CommissionEntryResponse])
async def entries(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
    user_id: Annotated[UUID | None, Query()] = None,
) -> list[CommissionEntryResponse]:
    return await service.list_entries(session, user_id)
