from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.sales.schemas import SaleCreate, SaleResponse


class OfflineSaleItem(BaseModel):
    client_id: UUID
    device_id: str = Field(min_length=1, max_length=80)
    created_at: datetime | None = None
    sale: SaleCreate


class SyncSalesRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    items: list[OfflineSaleItem] = Field(min_length=1)


class SyncSaleResult(BaseModel):
    client_id: UUID
    status: str
    sale: SaleResponse | None = None
    error: str | None = None


class SyncSalesResponse(BaseModel):
    results: list[SyncSaleResult]
