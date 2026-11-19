from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.customer import Customer
from app.models.enums import PaymentMethod, PaymentType
from app.models.sales import Payment
from app.modules.customers.schemas import CustomerCreate, CustomerResponse


async def get_customer_due(session: AsyncSession, customer_id: UUID) -> Decimal:
    credited = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.customer_id == customer_id,
            Payment.payment_type == PaymentType.sale,
            Payment.method == PaymentMethod.credit,
        )
    )
    collected = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.customer_id == customer_id,
            Payment.payment_type == PaymentType.customer_collection,
        )
    )
    return Decimal(credited or 0) - Decimal(collected or 0)


async def _to_response(session: AsyncSession, customer: Customer) -> CustomerResponse:
    due = await get_customer_due(session, customer.id)
    base = CustomerResponse.model_validate(customer)
    return base.model_copy(update={"current_due": due})


async def create_customer(session: AsyncSession, data: CustomerCreate) -> CustomerResponse:
    customer = Customer(
        name=data.name.strip(),
        phone=data.phone.strip(),
        area=data.area,
        credit_limit=data.credit_limit,
        offer_opt_in=data.offer_opt_in,
        email=data.email,
    )
    session.add(customer)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Phone already registered") from exc
    await session.refresh(customer)
    return await _to_response(session, customer)


async def list_customers(session: AsyncSession) -> list[CustomerResponse]:
    rows = (await session.scalars(select(Customer).order_by(Customer.name))).all()
    return [await _to_response(session, c) for c in rows]


async def get_customer(session: AsyncSession, customer_id: UUID) -> CustomerResponse:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found")
    return await _to_response(session, customer)
