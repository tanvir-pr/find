from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class SalesSummaryResponse(BaseModel):
    from_date: date
    to_date: date
    total_sales: Decimal
    total_discount: Decimal
    bill_count: int
    cash: Decimal
    bkash: Decimal
    nagad: Decimal
    credit: Decimal
    estimated_profit: Decimal
    by_staff: list[dict]


class LowStockItem(BaseModel):
    variant_id: UUID
    product_name: str
    variant_name: str
    barcode: str | None
    current_stock: Decimal
    low_stock_threshold: Decimal


class ExpiringItem(BaseModel):
    batch_id: UUID
    variant_id: UUID
    product_name: str
    variant_name: str
    expiry_date: date | None
    remaining_qty: Decimal
