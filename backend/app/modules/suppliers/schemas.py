from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = None


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str | None
    address: str | None
    created_at: datetime
    current_due: Decimal = Decimal("0")


class SupplierPaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    purchase_invoice_id: UUID | None = None
    method: str = Field(default="cash")
    txn_id: str | None = None
    note: str | None = None


class SupplierPaymentResponse(BaseModel):
    id: UUID
    supplier_id: UUID
    amount: Decimal
    purchase_invoice_id: UUID | None
    method: str
    txn_id: str | None
    created_at: datetime
