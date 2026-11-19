from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str = Field(min_length=5, max_length=30)
    area: str | None = Field(default=None, max_length=120)
    credit_limit: Decimal = Field(default=Decimal("0"), ge=0)
    offer_opt_in: bool = False
    email: str | None = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str
    area: str | None
    credit_limit: Decimal
    offer_opt_in: bool
    email: str | None
    created_at: datetime
    current_due: Decimal = Decimal("0")


class CustomerHistoryItem(BaseModel):
    sale_id: UUID
    bill_no: str
    total: Decimal
    created_at: datetime


class CollectionCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    method: str = Field(default="cash")
    txn_id: str | None = None
    note: str | None = None


class DueReminderResponse(BaseModel):
    customer_id: UUID
    phone: str
    due: Decimal
    sms_log_id: UUID
    body: str
