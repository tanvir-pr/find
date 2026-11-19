from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleError, NotFoundError
from app.models.enums import PaymentMethod, PaymentType
from app.models.sales import Payment
from app.models.supplier import PurchaseInvoice, Supplier
from app.models.user import User
from app.modules.suppliers.schemas import (
    SupplierCreate,
    SupplierPaymentCreate,
    SupplierPaymentResponse,
    SupplierResponse,
)


async def get_supplier_due(session: AsyncSession, supplier_id: UUID) -> Decimal:
    purchased = await session.scalar(
        select(func.coalesce(func.sum(PurchaseInvoice.total_amount), 0)).where(
            PurchaseInvoice.supplier_id == supplier_id
        )
    )
    paid = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.supplier_id == supplier_id,
            Payment.payment_type == PaymentType.supplier_payment,
        )
    )
    return Decimal(purchased or 0) - Decimal(paid or 0)


async def _to_response(session: AsyncSession, supplier: Supplier) -> SupplierResponse:
    due = await get_supplier_due(session, supplier.id)
    base = SupplierResponse.model_validate(supplier)
    return base.model_copy(update={"current_due": due})


async def create_supplier(session: AsyncSession, data: SupplierCreate) -> SupplierResponse:
    supplier = Supplier(name=data.name.strip(), phone=data.phone, address=data.address)
    session.add(supplier)
    await session.commit()
    await session.refresh(supplier)
    return await _to_response(session, supplier)


async def list_suppliers(session: AsyncSession) -> list[SupplierResponse]:
    rows = (await session.scalars(select(Supplier).order_by(Supplier.name))).all()
    return [await _to_response(session, s) for s in rows]


async def pay_supplier(
    session: AsyncSession, supplier_id: UUID, data: SupplierPaymentCreate, user: User
) -> SupplierPaymentResponse:
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFoundError("Supplier not found")
    try:
        method = PaymentMethod(data.method)
    except ValueError as exc:
        raise BusinessRuleError("Invalid payment method") from exc

    payment = Payment(
        payment_type=PaymentType.supplier_payment,
        supplier_id=supplier_id,
        purchase_invoice_id=data.purchase_invoice_id,
        method=method,
        amount=data.amount,
        txn_id=data.txn_id,
        user_id=user.id,
        note=data.note,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return SupplierPaymentResponse(
        id=payment.id,
        supplier_id=supplier_id,
        amount=payment.amount,
        purchase_invoice_id=payment.purchase_invoice_id,
        method=payment.method.value,
        txn_id=payment.txn_id,
        created_at=payment.created_at,
    )
