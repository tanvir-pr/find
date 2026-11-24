from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DeliveryStatus


class VanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    plate_no: str | None = None
    driver_name: str | None = None
    branch_id: UUID | None = None


class VanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    plate_no: str | None
    driver_name: str | None
    branch_id: UUID | None
    is_active: bool


class DeliveryCreate(BaseModel):
    van_id: UUID
    customer_id: UUID | None = None
    sale_id: UUID | None = None
    destination: str | None = None
    note: str | None = None


class DeliveryUpdate(BaseModel):
    status: DeliveryStatus
    note: str | None = None


class DeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    van_id: UUID
    customer_id: UUID | None
    sale_id: UUID | None
    destination: str | None
    status: DeliveryStatus
    dispatched_at: datetime | None
    delivered_at: datetime | None
    note: str | None
    created_at: datetime
