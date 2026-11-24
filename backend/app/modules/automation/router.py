from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import require_roles
from app.modules.automation import service
from app.modules.automation.schemas import (
    AgentActionResponse,
    AutomationSettingsResponse,
    AutomationSettingsUpdate,
    ScanResponse,
)

router = APIRouter(prefix="/api/v1/automation", tags=["automation"])


@router.get("/settings", response_model=AutomationSettingsResponse)
async def read_settings(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> AutomationSettingsResponse:
    row = await service.get_settings(session)
    return AutomationSettingsResponse.model_validate(row)


@router.patch("/settings", response_model=AutomationSettingsResponse)
async def patch_settings(
    body: AutomationSettingsUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> AutomationSettingsResponse:
    return await service.update_settings(session, body)


@router.get("/actions", response_model=list[AgentActionResponse])
async def actions(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
) -> list[AgentActionResponse]:
    return await service.list_actions(session, status=status, limit=limit)


@router.post("/scan", response_model=ScanResponse)
async def scan(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> ScanResponse:
    return await service.run_scan(session, user)


@router.post("/actions/{action_id}/approve", response_model=AgentActionResponse)
async def approve(
    action_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> AgentActionResponse:
    return await service.approve_action(session, action_id, user)


@router.post("/actions/{action_id}/reject", response_model=AgentActionResponse)
async def reject(
    action_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> AgentActionResponse:
    return await service.reject_action(session, action_id, user)
