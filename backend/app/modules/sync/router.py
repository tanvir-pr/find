from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import require_roles
from app.modules.sync import service
from app.modules.sync.schemas import SyncSalesRequest, SyncSalesResponse

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.post("/sales", response_model=SyncSalesResponse)
async def sync_sales(
    body: SyncSalesRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.staff))],
) -> SyncSalesResponse:
    return await service.sync_offline_sales(session, user, body)
