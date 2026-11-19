from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import get_current_user, require_roles
from app.modules.sales import service
from app.modules.sales.schemas import (
    ReceiptResponse,
    ReturnCreate,
    ReturnResponse,
    SaleCreate,
    SaleResponse,
)

router = APIRouter(prefix="/api/v1/sales", tags=["sales"])
returns_router = APIRouter(prefix="/api/v1/returns", tags=["returns"])


@router.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(
    body: SaleCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[
        User, Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.staff))
    ],
) -> SaleResponse:
    return await service.create_sale(session, body, user)


@router.get("", response_model=list[SaleResponse])
async def list_sales(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=200),
) -> list[SaleResponse]:
    return await service.list_sales(session, limit=limit)


@router.get("/by-bill/{bill_no}", response_model=SaleResponse)
async def get_sale_by_bill(
    bill_no: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> SaleResponse:
    return await service.get_sale_by_bill(session, bill_no)


@router.post("/by-bill/{bill_no}/receipt", response_model=ReceiptResponse)
async def reprint_receipt(
    bill_no: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ReceiptResponse:
    return await service.reprint_receipt(session, bill_no, user)


@returns_router.post("", response_model=ReturnResponse, status_code=status.HTTP_201_CREATED)
async def create_return(
    body: ReturnCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[
        User, Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.staff))
    ],
) -> ReturnResponse:
    return await service.create_return(session, body, user)
