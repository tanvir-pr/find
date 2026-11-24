from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import get_current_user, require_roles
from app.modules.products import service
from app.modules.products.schemas import (
    CategoryListResponse,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    VariantCreate,
    VariantResponse,
    VariantUpdate,
)

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
) -> ProductResponse:
    return await service.create_product(session, body)


@router.get("", response_model=ProductListResponse)
async def list_products(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    q: str | None = None,
    category: str | None = None,
    low_stock: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> ProductListResponse:
    return await service.list_products(
        session, q=q, category=category, low_stock=low_stock, page=page, page_size=page_size
    )


@router.get("/meta/categories", response_model=CategoryListResponse)
async def product_categories(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> CategoryListResponse:
    cats = await service.list_categories(session)
    return CategoryListResponse(categories=cats)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> ProductResponse:
    return await service.get_product(session, product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    body: ProductUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
) -> ProductResponse:
    return await service.update_product(session, product_id, body)


@router.delete("/{product_id}", response_model=ProductResponse)
async def deactivate_product(
    product_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
) -> ProductResponse:
    return await service.deactivate_product(session, product_id)


@router.post(
    "/{product_id}/variants",
    response_model=VariantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_variant(
    product_id: UUID,
    body: VariantCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
) -> VariantResponse:
    return await service.add_variant(session, product_id, body)


@router.patch("/variants/{variant_id}", response_model=VariantResponse)
async def update_variant(
    variant_id: UUID,
    body: VariantUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
) -> VariantResponse:
    return await service.update_variant(session, variant_id, body)
