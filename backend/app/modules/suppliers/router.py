from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import get_current_user, require_roles
from app.modules.suppliers import service
from app.modules.suppliers.schemas import (
    SupplierCreate,
    SupplierPaymentCreate,
    SupplierPaymentResponse,
    SupplierResponse,
)

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    body: SupplierCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> SupplierResponse:
    return await service.create_supplier(session, body)


@router.get("", response_model=list[SupplierResponse])
async def list_suppliers(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[SupplierResponse]:
    return await service.list_suppliers(session)


@router.post(
    "/{supplier_id}/payments",
    response_model=SupplierPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def pay_supplier(
    supplier_id: UUID,
    body: SupplierPaymentCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> SupplierPaymentResponse:
    return await service.pay_supplier(session, supplier_id, body, user)
