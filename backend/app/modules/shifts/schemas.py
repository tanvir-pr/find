from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ShiftOpenRequest(BaseModel):
    opening_cash: Decimal = Field(default=Decimal("0"), ge=0)
    branch_id: UUID | None = None


class CashCloseRequest(BaseModel):
    counted_cash: Decimal = Field(ge=0)
    note: str | None = None


class CashClosingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shift_id: UUID
    expected_cash: Decimal
    counted_cash: Decimal
    difference: Decimal
    note: str | None
    created_at: datetime


class ShiftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    branch_id: UUID | None
    opened_at: datetime
    closed_at: datetime | None
    opening_cash: Decimal
    cash_closing: CashClosingResponse | None = None


class ShiftSummaryResponse(BaseModel):
    shift_id: UUID
    opening_cash: Decimal
    cash_sales: Decimal
    bkash_sales: Decimal
    nagad_sales: Decimal
    credit_sales: Decimal
    points_discount: Decimal = Decimal("0")
    bill_discount: Decimal = Decimal("0")
    expected_cash: Decimal
    bill_count: int
