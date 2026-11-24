from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str = Field(min_length=5, max_length=30)
    email: str = Field(min_length=3, max_length=255)
    area: str | None = Field(default=None, max_length=120)
    credit_limit: Decimal = Field(default=Decimal("0"), ge=0)
    offer_opt_in: bool = False

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        return v.strip()


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, min_length=5, max_length=30)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    area: str | None = Field(default=None, max_length=120)
    credit_limit: Decimal | None = Field(default=None, ge=0)
    offer_opt_in: bool | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        return v.strip().lower() if v else v

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str
    email: str
    area: str | None
    credit_limit: Decimal
    offer_opt_in: bool
    loyalty_points: int = 0
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


# ৳1000 purchase → 5 points; redeem 1 point = ৳1; minimum redeem 100
LOYALTY_POINTS_PER_1000 = 5
LOYALTY_MIN_REDEEM = 100
