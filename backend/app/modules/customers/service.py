from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models.customer import Customer
from app.models.enums import PaymentMethod, PaymentType, SmsPurpose
from app.models.sales import Payment, Sale
from app.models.system import SmsLog
from app.models.user import User
from app.modules.customers.schemas import (
    CollectionCreate,
    CustomerCreate,
    CustomerHistoryItem,
    CustomerResponse,
    DueReminderResponse,
)


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


async def list_customers(
    session: AsyncSession, area: str | None = None
) -> list[CustomerResponse]:
    stmt = select(Customer).order_by(Customer.name)
    if area:
        stmt = stmt.where(Customer.area == area)
    rows = (await session.scalars(stmt)).all()
    return [await _to_response(session, c) for c in rows]


async def get_customer(session: AsyncSession, customer_id: UUID) -> CustomerResponse:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found")
    return await _to_response(session, customer)


async def customer_history(
    session: AsyncSession, customer_id: UUID
) -> list[CustomerHistoryItem]:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found")
    sales = (
        await session.scalars(
            select(Sale)
            .where(Sale.customer_id == customer_id)
            .order_by(Sale.created_at.desc())
        )
    ).all()
    return [
        CustomerHistoryItem(
            sale_id=s.id,
            bill_no=s.bill_no,
            total=s.total,
            created_at=s.created_at,
        )
        for s in sales
    ]


async def collect_due(
    session: AsyncSession, customer_id: UUID, data: CollectionCreate, user: User
) -> CustomerResponse:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found")
    due = await get_customer_due(session, customer_id)
    if data.amount > due:
        raise BusinessRuleError(f"Collection exceeds due ({due})")
    try:
        method = PaymentMethod(data.method)
    except ValueError as exc:
        raise BusinessRuleError("Invalid payment method") from exc
    if method == PaymentMethod.credit:
        raise BusinessRuleError("Collection cannot use credit method")

    session.add(
        Payment(
            payment_type=PaymentType.customer_collection,
            customer_id=customer_id,
            method=method,
            amount=data.amount,
            txn_id=data.txn_id,
            user_id=user.id,
            note=data.note,
        )
    )
    await session.commit()
    return await _to_response(session, customer)


async def send_due_reminders(session: AsyncSession) -> list[DueReminderResponse]:
    customers = (await session.scalars(select(Customer))).all()
    results: list[DueReminderResponse] = []
    for customer in customers:
        due = await get_customer_due(session, customer.id)
        if due <= 0:
            continue
        body = (
            f"প্রিয় {customer.name}, আপনার বাকি টাকা {due} টাকা। "
            f"অনুগ্রহ করে দোকানে পরিশোধ করুন।"
        )
        log = SmsLog(
            purpose=SmsPurpose.due_reminder,
            to_phone=customer.phone,
            body=body,
            provider_status="mock_queued",
            provider_ref="mock",
            customer_id=customer.id,
            meta={"due": str(due)},
        )
        session.add(log)
        await session.flush()
        results.append(
            DueReminderResponse(
                customer_id=customer.id,
                phone=customer.phone,
                due=due,
                sms_log_id=log.id,
                body=body,
            )
        )
    await session.commit()
    return results
