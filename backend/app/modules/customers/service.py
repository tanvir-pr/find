from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models.customer import Customer
from app.models.enums import PaymentMethod, PaymentType, SmsPurpose
from app.models.sales import Payment, Sale
from app.models.user import User
from app.modules.customers.schemas import (
    LOYALTY_MIN_REDEEM,
    LOYALTY_POINTS_PER_1000,
    CollectionCreate,
    CustomerCreate,
    CustomerHistoryItem,
    CustomerResponse,
    CustomerUpdate,
    DueReminderResponse,
)


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    cleaned = phone.strip()
    return cleaned or None


def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    cleaned = email.strip().lower()
    return cleaned or None


def points_earned_for_amount(amount: Decimal) -> int:
    """৳1000 → 5 points (proportional, floored)."""
    if amount <= 0:
        return 0
    return int((amount * LOYALTY_POINTS_PER_1000) / Decimal("1000"))


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
        phone=normalize_phone(data.phone) or data.phone.strip(),
        email=normalize_email(data.email) or data.email.strip().lower(),
        area=data.area,
        credit_limit=data.credit_limit,
        offer_opt_in=data.offer_opt_in,
        loyalty_points=0,
    )
    session.add(customer)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Phone or email already registered") from exc
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


async def _find_by_contacts(
    session: AsyncSession,
    *,
    phone: str | None,
    email: str | None,
) -> Customer | None:
    phone = normalize_phone(phone)
    email = normalize_email(email)
    if not phone and not email:
        return None

    by_phone = (
        await session.scalar(select(Customer).where(Customer.phone == phone))
        if phone
        else None
    )
    by_email = (
        await session.scalar(select(Customer).where(Customer.email == email))
        if email
        else None
    )

    if by_phone and by_email and by_phone.id != by_email.id:
        raise ConflictError(
            "Phone and email belong to different customers — use one contact to look up"
        )
    return by_phone or by_email


async def _attach_contacts(
    session: AsyncSession,
    customer: Customer,
    *,
    phone: str | None,
    email: str | None,
) -> None:
    phone = normalize_phone(phone)
    email = normalize_email(email)
    if phone and customer.phone != phone:
        taken = await session.scalar(
            select(Customer.id).where(Customer.phone == phone, Customer.id != customer.id)
        )
        if taken:
            raise ConflictError("That phone belongs to another customer")
        customer.phone = phone
    if email and customer.email != email:
        taken = await session.scalar(
            select(Customer.id).where(Customer.email == email, Customer.id != customer.id)
        )
        if taken:
            raise ConflictError("That email belongs to another customer")
        customer.email = email


async def lookup_customer(
    session: AsyncSession,
    *,
    phone: str | None = None,
    email: str | None = None,
) -> CustomerResponse | None:
    """Find by phone or email. Merges the other contact onto the same row when free."""
    customer = await _find_by_contacts(session, phone=phone, email=email)
    if customer is None:
        return None
    await _attach_contacts(session, customer, phone=phone, email=email)
    await session.commit()
    await session.refresh(customer)
    return await _to_response(session, customer)


async def resolve_customer_for_sale(
    session: AsyncSession,
    *,
    customer_id: UUID | None,
    phone: str | None,
    email: str | None,
    name: str | None = None,
) -> Customer | None:
    """
    Attach sale to one customer.
    Lookup by id / phone / email; create only when both phone + email are present.
    """
    phone = normalize_phone(phone)
    email = normalize_email(email)

    if customer_id is not None:
        customer = await session.get(Customer, customer_id)
        if customer is None:
            raise NotFoundError("Customer not found")
        await _attach_contacts(session, customer, phone=phone, email=email)
        await session.flush()
        return customer

    if not phone and not email:
        return None

    customer = await _find_by_contacts(session, phone=phone, email=email)
    if customer is not None:
        await _attach_contacts(session, customer, phone=phone, email=email)
        await session.flush()
        return customer

    # New customer — both contacts required so phone+email never become two users
    if not phone or not email:
        return None

    display = (name or "").strip() or f"Customer {phone}"
    customer = Customer(
        name=display,
        phone=phone,
        email=email,
        credit_limit=Decimal("0"),
        offer_opt_in=False,
        loyalty_points=0,
    )
    session.add(customer)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError("Phone or email already registered") from exc
    return customer


async def update_customer(
    session: AsyncSession, customer_id: UUID, data: CustomerUpdate
) -> CustomerResponse:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found")
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(customer, key, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Phone or email already registered") from exc
    await session.refresh(customer)
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


async def apply_loyalty(
    customer: Customer,
    *,
    points_to_redeem: int,
    purchase_total_before_points: Decimal,
) -> tuple[int, int, Decimal]:
    """
    Returns (redeemed, earned, points_discount_taka).
    Redeem min 100; 1 point = ৳1. Earn after redeem on remaining payable.
    """
    redeem = max(0, int(points_to_redeem or 0))
    if redeem and redeem < LOYALTY_MIN_REDEEM:
        raise BusinessRuleError(f"Minimum redeem is {LOYALTY_MIN_REDEEM} points")
    if redeem > customer.loyalty_points:
        raise BusinessRuleError(
            f"Not enough points (have {customer.loyalty_points}, need {redeem})"
        )
    max_by_bill = int(purchase_total_before_points)
    if redeem > max_by_bill:
        raise BusinessRuleError("Cannot redeem more points than bill total")

    discount = Decimal(redeem)
    payable = purchase_total_before_points - discount
    earned = points_earned_for_amount(payable)

    customer.loyalty_points = customer.loyalty_points - redeem + earned
    return redeem, earned, discount


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
        from app.integrations.notify import send_sms

        log = await send_sms(
            session,
            purpose=SmsPurpose.due_reminder,
            to_phone=customer.phone,
            body=body,
            customer_id=customer.id,
            meta={"due": str(due)},
        )
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
