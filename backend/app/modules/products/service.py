from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictError, NotFoundError
from app.models.product import Product, ProductVariant
from app.modules.products.schemas import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    VariantCreate,
    VariantResponse,
    VariantUpdate,
)
from app.modules.stock.helpers import get_variant_stock


async def _variant_response(session: AsyncSession, variant: ProductVariant) -> VariantResponse:
    stock = await get_variant_stock(session, variant.id)
    data = VariantResponse.model_validate(variant)
    return data.model_copy(update={"current_stock": stock})


async def _product_response(session: AsyncSession, product: Product) -> ProductResponse:
    variants = [await _variant_response(session, v) for v in product.variants]
    base = ProductResponse.model_validate(product)
    return base.model_copy(update={"variants": variants})


async def create_product(session: AsyncSession, data: ProductCreate) -> ProductResponse:
    product = Product(
        name=data.name.strip(),
        category=data.category,
        unit=data.unit,
        tracks_expiry=data.tracks_expiry,
        description=data.description,
        is_active=True,
    )
    for v in data.variants:
        product.variants.append(
            ProductVariant(
                name=v.name.strip(),
                barcode=v.barcode.strip() if v.barcode else None,
                retail_price=v.retail_price,
                dealer_price=v.dealer_price,
                low_stock_threshold=v.low_stock_threshold,
                is_active=True,
            )
        )
    session.add(product)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Barcode already exists or variant name duplicated") from exc
    await session.refresh(product, attribute_names=["variants"])
    return await _product_response(session, product)


async def list_products(
    session: AsyncSession,
    *,
    q: str | None,
    category: str | None,
    low_stock: bool | None,
    page: int,
    page_size: int,
) -> ProductListResponse:
    stmt = select(Product).options(selectinload(Product.variants))
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Product.name.ilike(pattern),
                Product.variants.any(ProductVariant.barcode.ilike(pattern)),
                Product.variants.any(ProductVariant.name.ilike(pattern)),
            )
        )
    if category:
        stmt = stmt.where(Product.category == category)

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(await session.scalar(count_stmt) or 0)

    stmt = stmt.order_by(Product.name).offset((page - 1) * page_size).limit(page_size)
    products = (await session.scalars(stmt)).unique().all()

    items: list[ProductResponse] = []
    for product in products:
        resp = await _product_response(session, product)
        if low_stock is True:
            resp = resp.model_copy(
                update={
                    "variants": [
                        v
                        for v in resp.variants
                        if v.current_stock <= v.low_stock_threshold
                    ]
                }
            )
            if not resp.variants:
                continue
        elif low_stock is False:
            pass
        items.append(resp)

    return ProductListResponse(items=items, total=total, page=page, page_size=page_size)


async def get_product(session: AsyncSession, product_id: UUID) -> ProductResponse:
    product = await session.scalar(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.variants))
    )
    if product is None:
        raise NotFoundError("Product not found")
    return await _product_response(session, product)


async def update_product(
    session: AsyncSession, product_id: UUID, data: ProductUpdate
) -> ProductResponse:
    product = await session.scalar(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.variants))
    )
    if product is None:
        raise NotFoundError("Product not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await session.commit()
    await session.refresh(product, attribute_names=["variants"])
    return await _product_response(session, product)


async def deactivate_product(session: AsyncSession, product_id: UUID) -> ProductResponse:
    product = await session.scalar(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.variants))
    )
    if product is None:
        raise NotFoundError("Product not found")
    product.is_active = False
    for variant in product.variants:
        variant.is_active = False
    await session.commit()
    await session.refresh(product, attribute_names=["variants"])
    return await _product_response(session, product)


async def add_variant(
    session: AsyncSession, product_id: UUID, data: VariantCreate
) -> VariantResponse:
    product = await session.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")

    variant = ProductVariant(
        product_id=product_id,
        name=data.name.strip(),
        barcode=data.barcode.strip() if data.barcode else None,
        retail_price=data.retail_price,
        dealer_price=data.dealer_price,
        low_stock_threshold=data.low_stock_threshold,
        is_active=True,
    )
    session.add(variant)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Barcode already exists or variant name duplicated") from exc
    await session.refresh(variant)
    return await _variant_response(session, variant)


async def update_variant(
    session: AsyncSession, variant_id: UUID, data: VariantUpdate
) -> VariantResponse:
    variant = await session.get(ProductVariant, variant_id)
    if variant is None:
        raise NotFoundError("Variant not found")

    payload = data.model_dump(exclude_unset=True)
    if "barcode" in payload and payload["barcode"] is not None:
        payload["barcode"] = payload["barcode"].strip()
    for field, value in payload.items():
        setattr(variant, field, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Barcode already exists or variant name duplicated") from exc
    await session.refresh(variant)
    return await _variant_response(session, variant)


async def get_variant_stock_map(
    session: AsyncSession, variant_ids: list[UUID]
) -> dict[UUID, Decimal]:
    result: dict[UUID, Decimal] = {}
    for vid in variant_ids:
        result[vid] = await get_variant_stock(session, vid)
    return result
