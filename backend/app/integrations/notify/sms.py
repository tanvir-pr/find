"""SMS sender — mock by default; logs every message for demo/audit."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SmsPurpose
from app.models.system import SmsLog


async def send_sms(
    session: AsyncSession,
    *,
    purpose: SmsPurpose,
    to_phone: str,
    body: str,
    customer_id: UUID | None = None,
    meta: dict[str, Any] | None = None,
) -> SmsLog:
    log = SmsLog(
        purpose=purpose,
        to_phone=to_phone,
        body=body,
        provider_status="mock_sent",
        provider_ref="mock-local",
        customer_id=customer_id,
        meta=meta or {},
    )
    session.add(log)
    await session.flush()
    return log
