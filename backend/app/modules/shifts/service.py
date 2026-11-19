from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import BusinessRuleError, NotFoundError
from app.models.enums import PaymentMethod, PaymentType
from app.models.sales import Payment, Sale
from app.models.shift import CashClosing, Shift
from app.models.user import User
from app.modules.shifts.schemas import (
    CashCloseRequest,
    ShiftOpenRequest,
    ShiftResponse,
    ShiftSummaryResponse,
)


async def open_shift(session: AsyncSession, data: ShiftOpenRequest, user: User) -> ShiftResponse:
    open_existing = await session.scalar(
        select(Shift).where(Shift.user_id == user.id, Shift.closed_at.is_(None))
    )
    if open_existing:
        raise BusinessRuleError("You already have an open shift")

    shift = Shift(
        user_id=user.id,
        branch_id=data.branch_id or user.branch_id,
        opened_at=datetime.now(UTC),
        opening_cash=data.opening_cash,
    )
    session.add(shift)
    await session.commit()
    loaded = await session.scalar(
        select(Shift).where(Shift.id == shift.id).options(selectinload(Shift.cash_closing))
    )
    assert loaded is not None
    return ShiftResponse.model_validate(loaded)


async def _payment_sum(
    session: AsyncSession, shift_id: UUID, method: PaymentMethod
) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Sale, Payment.sale_id == Sale.id)
        .where(
            Sale.shift_id == shift_id,
            Payment.payment_type == PaymentType.sale,
            Payment.method == method,
        )
    )
    return Decimal(total or 0)


async def shift_summary(session: AsyncSession, shift_id: UUID) -> ShiftSummaryResponse:
    shift = await session.get(Shift, shift_id)
    if shift is None:
        raise NotFoundError("Shift not found")

    cash = await _payment_sum(session, shift_id, PaymentMethod.cash)
    bkash = await _payment_sum(session, shift_id, PaymentMethod.bkash)
    nagad = await _payment_sum(session, shift_id, PaymentMethod.nagad)
    credit = await _payment_sum(session, shift_id, PaymentMethod.credit)
    bill_count = int(
        await session.scalar(
            select(func.count()).select_from(Sale).where(Sale.shift_id == shift_id)
        )
        or 0
    )
    expected = shift.opening_cash + cash
    return ShiftSummaryResponse(
        shift_id=shift.id,
        opening_cash=shift.opening_cash,
        cash_sales=cash,
        bkash_sales=bkash,
        nagad_sales=nagad,
        credit_sales=credit,
        expected_cash=expected,
        bill_count=bill_count,
    )


async def close_shift(
    session: AsyncSession, shift_id: UUID, data: CashCloseRequest, user: User
) -> ShiftResponse:
    shift = await session.scalar(
        select(Shift)
        .where(Shift.id == shift_id)
        .options(selectinload(Shift.cash_closing))
    )
    if shift is None:
        raise NotFoundError("Shift not found")
    if shift.user_id != user.id and user.role.value == "staff":
        raise BusinessRuleError("Cannot close another user's shift")
    if shift.closed_at is not None:
        raise BusinessRuleError("Shift already closed")

    summary = await shift_summary(session, shift_id)
    closing = CashClosing(
        shift_id=shift.id,
        expected_cash=summary.expected_cash,
        counted_cash=data.counted_cash,
        difference=data.counted_cash - summary.expected_cash,
        note=data.note,
    )
    shift.closed_at = datetime.now(UTC)
    shift.cash_closing = closing
    session.add(closing)
    await session.commit()
    await session.refresh(shift, attribute_names=["closed_at", "cash_closing"])
    return ShiftResponse.model_validate(shift)


async def get_shift(session: AsyncSession, shift_id: UUID) -> ShiftResponse:
    shift = await session.scalar(
        select(Shift).where(Shift.id == shift_id).options(selectinload(Shift.cash_closing))
    )
    if shift is None:
        raise NotFoundError("Shift not found")
    return ShiftResponse.model_validate(shift)


async def my_open_shift(session: AsyncSession, user: User) -> ShiftResponse | None:
    shift = await session.scalar(
        select(Shift)
        .where(Shift.user_id == user.id, Shift.closed_at.is_(None))
        .options(selectinload(Shift.cash_closing))
    )
    return ShiftResponse.model_validate(shift) if shift else None
