from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AutomationSettingsResponse(BaseModel):
    autopilot_enabled: bool
    auto_due_reminders: bool
    auto_daily_sms: bool
    auto_low_stock_alerts: bool
    auto_expiring_alerts: bool
    auto_reorder_draft: bool
    owner_phone: str | None = None

    model_config = {"from_attributes": True}


class AutomationSettingsUpdate(BaseModel):
    autopilot_enabled: bool | None = None
    auto_due_reminders: bool | None = None
    auto_daily_sms: bool | None = None
    auto_low_stock_alerts: bool | None = None
    auto_expiring_alerts: bool | None = None
    auto_reorder_draft: bool | None = None
    owner_phone: str | None = None


class AgentActionResponse(BaseModel):
    id: UUID
    kind: str
    mode: str
    status: str
    title: str
    summary: str
    payload: dict | None = None
    result: dict | None = None
    error_message: str | None = None
    created_at: datetime
    decided_at: datetime | None = None
    executed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ScanResponse(BaseModel):
    created: list[AgentActionResponse] = Field(default_factory=list)
    auto_executed: list[AgentActionResponse] = Field(default_factory=list)
    message: str
