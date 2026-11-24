from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commission import CommissionEntry, CommissionRule
from app.models.enums import CommissionBasis
from app.models.sales import Sale
from app.models.user import User
from app.modules.commissions.schemas import (
    CommissionEntryResponse,
    CommissionRuleCreate,
    CommissionRuleResponse,
)


async def list_rules(session: AsyncSession) -> list[CommissionRuleResponse]:
    rows = (await session.scalars(select(CommissionRule).order_by(CommissionRule.created_at.desc()))).all()
    return [CommissionRuleResponse.model_validate(r) for r in rows]


async def create_rule(session: AsyncSession, data: CommissionRuleCreate) -> CommissionRuleResponse:
    user = await session.get(User, data.user_id)
    if user is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("User not found")
    rule = CommissionRule(
        user_id=data.user_id,
        name=data.name.strip(),
        basis=data.basis,
        rate=data.rate,
        is_active=True,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return CommissionRuleResponse.model_validate(rule)


async def list_entries(session: AsyncSession, user_id: UUID | None = None) -> list[CommissionEntryResponse]:
    stmt = select(CommissionEntry).order_by(CommissionEntry.created_at.desc()).limit(100)
    if user_id:
        stmt = stmt.where(CommissionEntry.user_id == user_id)
    rows = (await session.scalars(stmt)).all()
    return [CommissionEntryResponse.model_validate(e) for e in rows]


async def apply_commission_for_sale(session: AsyncSession, sale: Sale) -> None:
    rules = (
        await session.scalars(
            select(CommissionRule).where(
                CommissionRule.user_id == sale.user_id,
                CommissionRule.is_active.is_(True),
            )
        )
    ).all()
    for rule in rules:
        if rule.basis == CommissionBasis.percent_of_sale:
            amount = (sale.total * rule.rate / Decimal("100")).quantize(Decimal("0.01"))
        else:
            amount = rule.rate
        session.add(
            CommissionEntry(
                rule_id=rule.id,
                user_id=sale.user_id,
                sale_id=sale.id,
                amount=amount,
            )
        )
