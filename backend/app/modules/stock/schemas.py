from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PurchaseLineCreate(BaseModel):
    variant_id: UUID
    qty: Decimal = Field(gt=0)
    cost_price: Decimal = Field(ge=0)
    expiry_date: date | None = None


class PurchaseCreate(BaseModel):
    supplier_id: UUID
    invoice_no: str = Field(min_length=1, max_length=80)
    invoice_date: date
    lines: list[PurchaseLineCreate] = Field(min_length=1)
    image_path: str | None = None
    branch_id: UUID | None = None


class BatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    variant_id: UUID
    purchase_invoice_id: UUID | None
    initial_qty: Decimal
    cost_price: Decimal
    expiry_date: date | None


class PurchaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supplier_id: UUID
    invoice_no: str
    invoice_date: date
    total_amount: Decimal
    image_path: str | None
    created_by: UUID | None
    branch_id: UUID | None
    created_at: datetime
    batches: list[BatchResponse] = []


class StockAdjustmentCreate(BaseModel):
    variant_id: UUID
    qty_delta: Decimal = Field(description="Positive adds stock, negative removes")
    batch_id: UUID | None = None
    note: str | None = None
    branch_id: UUID | None = None


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    variant_id: UUID
    batch_id: UUID | None
    movement_type: str
    qty: Decimal
    ref_type: str | None
    ref_id: UUID | None
    note: str | None
    created_at: datetime


class VariantStockResponse(BaseModel):
    variant_id: UUID
    current_stock: Decimal


class StockCountLineCreate(BaseModel):
    variant_id: UUID
    counted_qty: Decimal = Field(ge=0)


class StockCountCreate(BaseModel):
    lines: list[StockCountLineCreate] = Field(min_length=1)
    note: str | None = None
    branch_id: UUID | None = None
    apply_adjustments: bool = True


class StockCountLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    variant_id: UUID
    system_qty: Decimal
    counted_qty: Decimal
    difference: Decimal


class StockCountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    branch_id: UUID | None
    counted_by: UUID | None
    note: str | None
    created_at: datetime
    lines: list[StockCountLineResponse] = []
