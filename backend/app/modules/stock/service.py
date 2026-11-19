from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import BusinessRuleError, NotFoundError
from app.models.enums import StockMovementType
from app.models.product import Batch, ProductVariant
from app.models.stock import StockCount, StockCountLine, StockMovement
from app.models.supplier import PurchaseInvoice, Supplier
from app.models.user import User
from app.modules.stock.helpers import get_variant_stock
from app.modules.stock.schemas import (
    PurchaseCreate,
    PurchaseResponse,
    StockAdjustmentCreate,
    StockCountCreate,
    StockCountResponse,
    StockMovementResponse,
    VariantStockResponse,
)


async def create_purchase(
    session: AsyncSession, data: PurchaseCreate, user: User
) -> PurchaseResponse:
    supplier = await session.get(Supplier, data.supplier_id)
    if supplier is None:
        raise NotFoundError("Supplier not found")

    variant_ids = {line.variant_id for line in data.lines}
    variants = (
        await session.scalars(select(ProductVariant).where(ProductVariant.id.in_(variant_ids)))
    ).all()
    found = {v.id for v in variants}
    missing = variant_ids - found
    if missing:
        raise NotFoundError(f"Variant not found: {next(iter(missing))}")

    total = sum((line.qty * line.cost_price for line in data.lines), Decimal("0"))
    invoice = PurchaseInvoice(
        supplier_id=data.supplier_id,
        invoice_no=data.invoice_no.strip(),
        invoice_date=data.invoice_date,
        total_amount=total,
        image_path=data.image_path,
        created_by=user.id,
        branch_id=data.branch_id or user.branch_id,
    )
    session.add(invoice)
    await session.flush()

    for line in data.lines:
        batch = Batch(
            variant_id=line.variant_id,
            purchase_invoice_id=invoice.id,
            initial_qty=line.qty,
            cost_price=line.cost_price,
            expiry_date=line.expiry_date,
        )
        session.add(batch)
        await session.flush()

        session.add(
            StockMovement(
                variant_id=line.variant_id,
                batch_id=batch.id,
                movement_type=StockMovementType.purchase,
                qty=line.qty,
                ref_type="purchase_invoice",
                ref_id=invoice.id,
                user_id=user.id,
                branch_id=data.branch_id or user.branch_id,
                note=f"Purchase {invoice.invoice_no}",
            )
        )

    await session.commit()
    loaded = await session.scalar(
        select(PurchaseInvoice)
        .where(PurchaseInvoice.id == invoice.id)
        .options(selectinload(PurchaseInvoice.batches))
    )
    assert loaded is not None
    return PurchaseResponse.model_validate(loaded)


async def list_purchases(session: AsyncSession) -> list[PurchaseResponse]:
    rows = (
        await session.scalars(
            select(PurchaseInvoice)
            .options(selectinload(PurchaseInvoice.batches))
            .order_by(PurchaseInvoice.created_at.desc())
        )
    ).all()
    return [PurchaseResponse.model_validate(r) for r in rows]


async def get_purchase(session: AsyncSession, purchase_id: UUID) -> PurchaseResponse:
    invoice = await session.scalar(
        select(PurchaseInvoice)
        .where(PurchaseInvoice.id == purchase_id)
        .options(selectinload(PurchaseInvoice.batches))
    )
    if invoice is None:
        raise NotFoundError("Purchase invoice not found")
    return PurchaseResponse.model_validate(invoice)


async def adjust_stock(
    session: AsyncSession, data: StockAdjustmentCreate, user: User
) -> StockMovementResponse:
    if data.qty_delta == 0:
        raise BusinessRuleError("qty_delta cannot be zero")

    variant = await session.get(ProductVariant, data.variant_id)
    if variant is None:
        raise NotFoundError("Variant not found")

    if data.batch_id:
        batch = await session.get(Batch, data.batch_id)
        if batch is None or batch.variant_id != data.variant_id:
            raise NotFoundError("Batch not found for this variant")

    current = await get_variant_stock(session, data.variant_id)
    if current + data.qty_delta < 0:
        raise BusinessRuleError(f"স্টকে মাত্র {current} আছে")

    movement = StockMovement(
        variant_id=data.variant_id,
        batch_id=data.batch_id,
        movement_type=StockMovementType.adjustment,
        qty=data.qty_delta,
        ref_type="adjustment",
        user_id=user.id,
        branch_id=data.branch_id or user.branch_id,
        note=data.note,
    )
    session.add(movement)
    await session.commit()
    await session.refresh(movement)
    return StockMovementResponse(
        id=movement.id,
        variant_id=movement.variant_id,
        batch_id=movement.batch_id,
        movement_type=movement.movement_type.value,
        qty=movement.qty,
        ref_type=movement.ref_type,
        ref_id=movement.ref_id,
        note=movement.note,
        created_at=movement.created_at,
    )


async def variant_stock(session: AsyncSession, variant_id: UUID) -> VariantStockResponse:
    variant = await session.get(ProductVariant, variant_id)
    if variant is None:
        raise NotFoundError("Variant not found")
    return VariantStockResponse(
        variant_id=variant_id,
        current_stock=await get_variant_stock(session, variant_id),
    )


async def create_stock_count(
    session: AsyncSession, data: StockCountCreate, user: User
) -> StockCountResponse:
    count = StockCount(
        branch_id=data.branch_id or user.branch_id,
        counted_by=user.id,
        note=data.note,
    )
    session.add(count)
    await session.flush()

    for line in data.lines:
        variant = await session.get(ProductVariant, line.variant_id)
        if variant is None:
            raise NotFoundError(f"Variant not found: {line.variant_id}")
        system_qty = await get_variant_stock(session, line.variant_id)
        diff = line.counted_qty - system_qty
        session.add(
            StockCountLine(
                stock_count_id=count.id,
                variant_id=line.variant_id,
                system_qty=system_qty,
                counted_qty=line.counted_qty,
                difference=diff,
            )
        )
        if data.apply_adjustments and diff != 0:
            session.add(
                StockMovement(
                    variant_id=line.variant_id,
                    movement_type=StockMovementType.adjustment,
                    qty=diff,
                    ref_type="stock_count",
                    ref_id=count.id,
                    user_id=user.id,
                    branch_id=data.branch_id or user.branch_id,
                    note=f"Stock count adjustment ({system_qty} → {line.counted_qty})",
                )
            )

    await session.commit()
    loaded = await session.scalar(
        select(StockCount)
        .where(StockCount.id == count.id)
        .options(selectinload(StockCount.lines))
    )
    assert loaded is not None
    return StockCountResponse.model_validate(loaded)


async def list_stock_counts(session: AsyncSession) -> list[StockCountResponse]:
    rows = (
        await session.scalars(
            select(StockCount)
            .options(selectinload(StockCount.lines))
            .order_by(StockCount.created_at.desc())
        )
    ).all()
    return [StockCountResponse.model_validate(r) for r in rows]
