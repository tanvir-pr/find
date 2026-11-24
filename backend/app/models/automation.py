"""Autonomous manager action queue + settings."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AgentActionKind, AgentActionMode, AgentActionStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AgentAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_actions"

    kind: Mapped[AgentActionKind] = mapped_column(
        Enum(
            AgentActionKind,
            name="agent_action_kind",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    mode: Mapped[AgentActionMode] = mapped_column(
        Enum(
            AgentActionMode,
            name="agent_action_mode",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    status: Mapped[AgentActionStatus] = mapped_column(
        Enum(
            AgentActionStatus,
            name="agent_action_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AgentActionStatus.pending,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    result: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AutomationSettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Singleton-ish shop automation flags (use the latest row)."""

    __tablename__ = "automation_settings"

    autopilot_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_due_reminders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_daily_sms: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Alerts / reorder always need approve unless flipped on
    auto_low_stock_alerts: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_expiring_alerts: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_reorder_draft: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_phone: Mapped[str | None] = mapped_column(String(30))
