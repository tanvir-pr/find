from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models.customer import Customer
from app.models.enums import PaymentMethod, PaymentType, StockMovementType
from app.models.product import ProductVariant
from app.models.sales import Payment, Return, Sale, SaleItem
from app.models.stock import StockMovement
from app.models.system import ReceiptLog
from app.models.user import User
from app.modules.customers.service import get_customer_due
from app.modules.sales.schemas import (
    ReceiptResponse,
    ReturnCreate,
    ReturnResponse,
    SaleCreate,
    SaleResponse,
)
from app.modules.stock.helpers import allocate_fifo


def _bill_no() -> str:
    return f"BILL-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"


async def _load_sale(session: AsyncSession, sale_id: UUID) -> Sale:
    sale = await session.scalar(
        select(Sale)
        .where(Sale.id == sale_id)
        .options(selectinload(Sale.items), selectinload(Sale.payments))
    )
    if sale is None:
        raise NotFoundError("Sale not found")
    return sale


def _sale_response(sale: Sale) -> SaleResponse:
    return SaleResponse(
        id=sale.id,
        bill_no=sale.bill_no,
        customer_id=sale.customer_id,
        user_id=sale.user_id,
        shift_id=sale.shift_id,
        branch_id=sale.branch_id,
        device_id=sale.device_id,
        subtotal=sale.subtotal,
        discount=sale.discount,
        total=sale.total,
        created_at=sale.created_at,
        items=sale.items,
        payments=[
            {
                "id": p.id,
                "payment_type": p.payment_type.value,
                "method": p.method,
                "amount": p.amount,
                "txn_id": p.txn_id,
            }
            for p in sale.payments
        ],
    )


async def create_sale(session: AsyncSession, data: SaleCreate, user: User) -> SaleResponse:
    line_rows: list[dict] = []
    subtotal = Decimal("0")

    for item in data.items:
        variant = await session.get(ProductVariant, item.variant_id)
        if variant is None or not variant.is_active:
            raise NotFoundError(f"Variant not found: {item.variant_id}")

        if item.unit_price is not None:
            unit_price = item.unit_price
        elif item.use_dealer_price:
            unit_price = variant.dealer_price
        else:
            unit_price = variant.retail_price

        allocations = await allocate_fifo(session, item.variant_id, item.qty)
        # Distribute line discount proportionally across FIFO splits
        remaining_discount = item.discount
        for idx, (batch_id, alloc_qty) in enumerate(allocations):
            portion = (
                remaining_discount
                if idx == len(allocations) - 1
                else (item.discount * alloc_qty / item.qty).quantize(Decimal("0.01"))
            )
            remaining_discount -= portion
            line_total = unit_price * alloc_qty - portion
            if line_total < 0:
                raise BusinessRuleError("Line discount exceeds line total")
            subtotal += unit_price * alloc_qty
            line_rows.append(
                {
                    "variant_id": item.variant_id,
                    "batch_id": batch_id,
                    "qty": alloc_qty,
                    "unit_price": unit_price,
                    "discount": portion,
                }
            )

    if data.discount > subtotal:
        raise BusinessRuleError("Bill discount exceeds subtotal")
    total = subtotal - data.discount
    paid = sum((p.amount for p in data.payments), Decimal("0"))
    if paid != total:
        raise BusinessRuleError(f"Payments ({paid}) must equal total ({total})")

    credit_amount = sum(
        (p.amount for p in data.payments if p.method == PaymentMethod.credit),
        Decimal("0"),
    )
    if credit_amount > 0:
        assert data.customer_id is not None
        customer = await session.get(Customer, data.customer_id)
        if customer is None:
            raise NotFoundError("Customer not found")
        due = await get_customer_due(session, customer.id)
        if due + credit_amount > customer.credit_limit:
            raise BusinessRuleError(
                f"Credit limit exceeded (due {due}, limit {customer.credit_limit})"
            )

    sale = Sale(
        bill_no=_bill_no(),
        customer_id=data.customer_id,
        user_id=user.id,
        shift_id=data.shift_id,
        branch_id=data.branch_id or user.branch_id,
        device_id=data.device_id,
        subtotal=subtotal,
        discount=data.discount,
        total=total,
    )
    session.add(sale)
    await session.flush()

    for row in line_rows:
        sale_item = SaleItem(sale_id=sale.id, **row)
        session.add(sale_item)
        await session.flush()
        session.add(
            StockMovement(
                variant_id=row["variant_id"],
                batch_id=row["batch_id"],
                movement_type=StockMovementType.sale,
                qty=-row["qty"],
                ref_type="sale",
                ref_id=sale.id,
                user_id=user.id,
                shift_id=data.shift_id,
                branch_id=data.branch_id or user.branch_id,
                device_id=data.device_id,
            )
        )

    for p in data.payments:
        session.add(
            Payment(
                payment_type=PaymentType.sale,
                sale_id=sale.id,
                customer_id=data.customer_id,
                method=p.method,
                amount=p.amount,
                txn_id=p.txn_id,
                user_id=user.id,
            )
        )

    payload = {
        "bill_no": sale.bill_no,
        "total": str(total),
        "discount": str(data.discount),
        "items": [
            {
                "variant_id": str(r["variant_id"]),
                "qty": str(r["qty"]),
                "unit_price": str(r["unit_price"]),
            }
            for r in line_rows
        ],
        "payments": [{"method": p.method.value, "amount": str(p.amount)} for p in data.payments],
    }
    session.add(
        ReceiptLog(sale_id=sale.id, printed_by=user.id, is_copy=False, payload=payload)
    )

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Duplicate transaction id or bill number") from exc

    loaded = await _load_sale(session, sale.id)
    return _sale_response(loaded)


async def list_sales(session: AsyncSession, limit: int = 50) -> list[SaleResponse]:
    rows = (
        await session.scalars(
            select(Sale)
            .options(selectinload(Sale.items), selectinload(Sale.payments))
            .order_by(Sale.created_at.desc())
            .limit(limit)
        )
    ).all()
    return [_sale_response(s) for s in rows]


async def get_sale_by_bill(session: AsyncSession, bill_no: str) -> SaleResponse:
    sale = await session.scalar(
        select(Sale)
        .where(Sale.bill_no == bill_no)
        .options(selectinload(Sale.items), selectinload(Sale.payments))
    )
    if sale is None:
        raise NotFoundError("Sale not found")
    return _sale_response(sale)


async def reprint_receipt(
    session: AsyncSession, bill_no: str, user: User
) -> ReceiptResponse:
    sale = await session.scalar(select(Sale).where(Sale.bill_no == bill_no))
    if sale is None:
        raise NotFoundError("Sale not found")

    last = await session.scalar(
        select(ReceiptLog)
        .where(ReceiptLog.sale_id == sale.id)
        .order_by(ReceiptLog.created_at.desc())
        .limit(1)
    )
    payload = last.payload if last else {"bill_no": sale.bill_no, "total": str(sale.total)}
    log = ReceiptLog(sale_id=sale.id, printed_by=user.id, is_copy=True, payload=payload)
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return ReceiptResponse(
        id=log.id,
        sale_id=log.sale_id,
        is_copy=log.is_copy,
        payload=log.payload,
        created_at=log.created_at,
    )


async def create_return(
    session: AsyncSession, data: ReturnCreate, user: User
) -> ReturnResponse:
    sale = await session.scalar(
        select(Sale)
        .where(Sale.bill_no == data.bill_no)
        .options(selectinload(Sale.items))
    )
    if sale is None:
        raise NotFoundError("Sale not found")

    item = next((i for i in sale.items if i.id == data.sale_item_id), None)
    if item is None:
        raise NotFoundError("Sale item not found on this bill")

    already = await session.scalar(
        select(func.coalesce(func.sum(Return.qty), 0)).where(
            Return.sale_item_id == item.id
        )
    )
    already_qty = Decimal(already or 0)
    if data.qty > item.qty - already_qty:
        raise BusinessRuleError(
            f"Cannot return more than sold (remaining {item.qty - already_qty})"
        )

    unit_net = item.unit_price - (item.discount / item.qty if item.qty else Decimal("0"))
    refund = data.refund_amount if data.refund_amount is not None else (unit_net * data.qty)

    ret = Return(
        sale_id=sale.id,
        sale_item_id=item.id,
        variant_id=item.variant_id,
        batch_id=item.batch_id,
        qty=data.qty,
        reason=data.reason,
        is_damaged=data.is_damaged,
        refund_amount=refund,
        user_id=user.id,
    )
    session.add(ret)
    await session.flush()

    # Good stock returns to inventory; damaged goods do not.
    if not data.is_damaged:
        session.add(
            StockMovement(
                variant_id=item.variant_id,
                batch_id=item.batch_id,
                movement_type=StockMovementType.customer_return,
                qty=data.qty,
                ref_type="return",
                ref_id=ret.id,
                user_id=user.id,
                branch_id=sale.branch_id,
            )
        )

    await session.commit()
    await session.refresh(ret)
    return ReturnResponse.model_validate(ret)
