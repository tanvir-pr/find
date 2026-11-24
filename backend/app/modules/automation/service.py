"""Scan shop signals → queue actions → auto-run or wait for approve."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleError, NotFoundError
from app.models.automation import AgentAction, AutomationSettings
from app.models.enums import AgentActionKind, AgentActionMode, AgentActionStatus
from app.models.user import User
from app.modules.automation.schemas import (
    AgentActionResponse,
    AutomationSettingsResponse,
    AutomationSettingsUpdate,
    ScanResponse,
)
from app.modules.customers import service as customers_service
from app.modules.ops import service as ops_service
from app.modules.reports import service as reports_service


def _to_resp(row: AgentAction) -> AgentActionResponse:
    return AgentActionResponse(
        id=row.id,
        kind=row.kind.value,
        mode=row.mode.value,
        status=row.status.value,
        title=row.title,
        summary=row.summary,
        payload=row.payload,
        result=row.result,
        error_message=row.error_message,
        created_at=row.created_at,
        decided_at=row.decided_at,
        executed_at=row.executed_at,
    )


async def get_settings(session: AsyncSession) -> AutomationSettings:
    row = (
        await session.scalars(select(AutomationSettings).order_by(AutomationSettings.created_at.desc()))
    ).first()
    if row is None:
        row = AutomationSettings(
            autopilot_enabled=False,
            auto_due_reminders=True,
            auto_daily_sms=True,
            auto_low_stock_alerts=False,
            auto_expiring_alerts=False,
            auto_reorder_draft=False,
            owner_phone="01711001100",
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


async def update_settings(
    session: AsyncSession, data: AutomationSettingsUpdate
) -> AutomationSettingsResponse:
    row = await get_settings(session)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await session.commit()
    await session.refresh(row)
    return AutomationSettingsResponse.model_validate(row)


async def list_actions(
    session: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[AgentActionResponse]:
    stmt = select(AgentAction).order_by(AgentAction.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(AgentAction.status == AgentActionStatus(status))
    rows = (await session.scalars(stmt)).all()
    return [_to_resp(r) for r in rows]


def _mode_for(kind: AgentActionKind, settings: AutomationSettings) -> AgentActionMode:
    if not settings.autopilot_enabled:
        return AgentActionMode.approval
    mapping = {
        AgentActionKind.due_reminders: settings.auto_due_reminders,
        AgentActionKind.daily_summary_sms: settings.auto_daily_sms,
        AgentActionKind.low_stock_alert: settings.auto_low_stock_alerts,
        AgentActionKind.expiring_alert: settings.auto_expiring_alerts,
        AgentActionKind.reorder_draft: settings.auto_reorder_draft,
    }
    return AgentActionMode.auto if mapping.get(kind) else AgentActionMode.approval


async def _pending_exists(session: AsyncSession, kind: AgentActionKind) -> bool:
    row = await session.scalar(
        select(AgentAction.id).where(
            AgentAction.kind == kind,
            AgentAction.status == AgentActionStatus.pending,
        ).limit(1)
    )
    return row is not None


async def _create_action(
    session: AsyncSession,
    *,
    user: User,
    kind: AgentActionKind,
    mode: AgentActionMode,
    title: str,
    summary: str,
    payload: dict,
) -> AgentAction:
    action = AgentAction(
        kind=kind,
        mode=mode,
        status=AgentActionStatus.pending,
        title=title,
        summary=summary,
        payload=payload,
        created_by=user.id,
    )
    session.add(action)
    await session.flush()
    return action


async def execute_action(
    session: AsyncSession, action: AgentAction, user: User
) -> AgentAction:
    try:
        if action.kind == AgentActionKind.due_reminders:
            results = await customers_service.send_due_reminders(session)
            action.result = {
                "sent": len(results),
                "items": [r.model_dump(mode="json") for r in results[:20]],
            }
        elif action.kind == AgentActionKind.daily_summary_sms:
            phone = (action.payload or {}).get("to_phone")
            res = await ops_service.send_daily_summary_sms(session, user, phone)
            action.result = res.model_dump(mode="json")
        elif action.kind == AgentActionKind.low_stock_alert:
            # Alert only — store snapshot; no DB mutation beyond the action itself
            action.result = {"acknowledged": True, "items": (action.payload or {}).get("items", [])}
        elif action.kind == AgentActionKind.expiring_alert:
            action.result = {"acknowledged": True, "items": (action.payload or {}).get("items", [])}
        elif action.kind == AgentActionKind.reorder_draft:
            action.result = {
                "draft": True,
                "suggestions": (action.payload or {}).get("suggestions", []),
                "note": "Reorder draft saved — create purchase from Purchases page.",
            }
        else:
            raise BusinessRuleError(f"Unknown action kind: {action.kind}")

        action.status = AgentActionStatus.executed
        action.executed_at = datetime.now(timezone.utc)
        action.error_message = None
    except Exception as exc:  # noqa: BLE001
        action.status = AgentActionStatus.failed
        action.error_message = str(exc)[:500]
        action.executed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(action)
    return action


async def approve_action(
    session: AsyncSession, action_id: UUID, user: User
) -> AgentActionResponse:
    action = await session.get(AgentAction, action_id)
    if action is None:
        raise NotFoundError("Action not found")
    if action.status != AgentActionStatus.pending:
        raise BusinessRuleError("Only pending actions can be approved")
    action.status = AgentActionStatus.approved
    action.decided_by = user.id
    action.decided_at = datetime.now(timezone.utc)
    await session.commit()
    action = await execute_action(session, action, user)
    return _to_resp(action)


async def reject_action(
    session: AsyncSession, action_id: UUID, user: User
) -> AgentActionResponse:
    action = await session.get(AgentAction, action_id)
    if action is None:
        raise NotFoundError("Action not found")
    if action.status != AgentActionStatus.pending:
        raise BusinessRuleError("Only pending actions can be rejected")
    action.status = AgentActionStatus.rejected
    action.decided_by = user.id
    action.decided_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(action)
    return _to_resp(action)


async def run_scan(session: AsyncSession, user: User) -> ScanResponse:
    settings = await get_settings(session)
    created: list[AgentAction] = []
    auto_executed: list[AgentAction] = []

    # 1) Low stock
    low = await reports_service.low_stock_report(session)
    if low and not await _pending_exists(session, AgentActionKind.low_stock_alert):
        items = [
            {
                "product": r.product_name,
                "variant": r.variant_name,
                "stock": str(r.current_stock),
                "threshold": str(r.low_stock_threshold),
            }
            for r in low[:20]
        ]
        mode = _mode_for(AgentActionKind.low_stock_alert, settings)
        action = await _create_action(
            session,
            user=user,
            kind=AgentActionKind.low_stock_alert,
            mode=mode,
            title=f"Low stock · {len(low)} items",
            summary=f"{len(low)} products are at or below threshold. Review and restock.",
            payload={"items": items, "count": len(low)},
        )
        created.append(action)

    # 2) Expiring
    expiring = await reports_service.expiring_report(session, within_days=30)
    if expiring and not await _pending_exists(session, AgentActionKind.expiring_alert):
        items = [
            {
                "product": r.product_name,
                "variant": r.variant_name,
                "expiry_date": str(r.expiry_date) if r.expiry_date else None,
                "qty": str(r.remaining_qty),
            }
            for r in expiring[:20]
        ]
        mode = _mode_for(AgentActionKind.expiring_alert, settings)
        action = await _create_action(
            session,
            user=user,
            kind=AgentActionKind.expiring_alert,
            mode=mode,
            title=f"Expiring soon · {len(expiring)} batches",
            summary=f"{len(expiring)} batches expire within 30 days.",
            payload={"items": items, "count": len(expiring)},
        )
        created.append(action)

    # 3) Reorder draft (from low stock signal)
    if low and not await _pending_exists(session, AgentActionKind.reorder_draft):
        try:
            import json

            from app.modules.chat import tool_executors

            raw = await tool_executors.reorder_suggestion(
                session, user, {"cover_days": 14}
            )
            data = json.loads(raw)
            suggestions = data.get("suggestions") or data.get("items") or []
        except Exception:  # noqa: BLE001
            suggestions = [
                {
                    "product": r.product_name,
                    "variant": r.variant_name,
                    "stock": str(r.current_stock),
                }
                for r in low[:15]
            ]
        if suggestions:
            mode = _mode_for(AgentActionKind.reorder_draft, settings)
            action = await _create_action(
                session,
                user=user,
                kind=AgentActionKind.reorder_draft,
                mode=mode,
                title="Reorder draft",
                summary=f"Draft order list with {len(suggestions)} suggestions.",
                payload={"suggestions": suggestions[:30]},
            )
            created.append(action)

    # 4) Due reminders
    if not await _pending_exists(session, AgentActionKind.due_reminders):
        # Peek dues without sending
        from app.models.customer import Customer

        customers = (await session.scalars(select(Customer))).all()
        due_count = 0
        for c in customers:
            due = await customers_service.get_customer_due(session, c.id)
            if due > 0 and c.phone:
                due_count += 1
        if due_count:
            mode = _mode_for(AgentActionKind.due_reminders, settings)
            action = await _create_action(
                session,
                user=user,
                kind=AgentActionKind.due_reminders,
                mode=mode,
                title=f"Due reminders · {due_count} customers",
                summary=f"Send SMS reminders to {due_count} customers with outstanding dues.",
                payload={"due_customers": due_count},
            )
            created.append(action)

    # 5) Daily SMS (always offer once per pending)
    if not await _pending_exists(session, AgentActionKind.daily_summary_sms):
        today = date.today()
        summary = await reports_service.sales_summary(session, today, today)
        mode = _mode_for(AgentActionKind.daily_summary_sms, settings)
        action = await _create_action(
            session,
            user=user,
            kind=AgentActionKind.daily_summary_sms,
            mode=mode,
            title="Daily sales SMS",
            summary=(
                f"Send owner SMS: sales ৳{summary.total_sales}, "
                f"bills {summary.bill_count}."
            ),
            payload={
                "to_phone": settings.owner_phone or "01711001100",
                "total_sales": str(summary.total_sales),
                "bill_count": summary.bill_count,
            },
        )
        created.append(action)

    await session.commit()
    for a in created:
        await session.refresh(a)

    # Auto-execute where mode=auto
    for action in list(created):
        if action.mode == AgentActionMode.auto and action.status == AgentActionStatus.pending:
            action.status = AgentActionStatus.approved
            action.decided_by = user.id
            action.decided_at = datetime.now(timezone.utc)
            await session.commit()
            executed = await execute_action(session, action, user)
            auto_executed.append(executed)

    msg = (
        f"Scan done · {len(created)} actions queued"
        + (f" · {len(auto_executed)} auto-run" if auto_executed else " · waiting for approve")
    )
    return ScanResponse(
        created=[_to_resp(a) for a in created],
        auto_executed=[_to_resp(a) for a in auto_executed],
        message=msg,
    )
