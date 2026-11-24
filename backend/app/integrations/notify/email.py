"""Email sender — mock by default; logs every message for demo/audit."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import EmailLog


async def send_email(
    session: AsyncSession,
    *,
    to_email: str,
    subject: str,
    body: str,
    customer_id: UUID | None = None,
    meta: dict[str, Any] | None = None,
) -> EmailLog:
    log = EmailLog(
        to_email=to_email.strip().lower(),
        subject=subject,
        body=body,
        provider_status="mock_sent",
        provider_ref="mock-local",
        customer_id=customer_id,
        meta=meta or {},
    )
    session.add(log)
    await session.flush()
    return log
