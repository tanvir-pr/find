from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VariantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    barcode: str | None = Field(default=None, max_length=64)
    retail_price: Decimal = Field(ge=0)
    dealer_price: Decimal = Field(ge=0)
    low_stock_threshold: Decimal = Field(default=Decimal("0"), ge=0)


class VariantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    barcode: str | None = Field(default=None, max_length=64)
    retail_price: Decimal | None = Field(default=None, ge=0)
    dealer_price: Decimal | None = Field(default=None, ge=0)
    low_stock_threshold: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class VariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    name: str
    barcode: str | None
    retail_price: Decimal
    dealer_price: Decimal
    low_stock_threshold: Decimal
    is_active: bool
    current_stock: Decimal = Decimal("0")


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    unit: str = Field(default="pcs", max_length=40)
    tracks_expiry: bool = False
    description: str | None = None
    variants: list[VariantCreate] = Field(min_length=1)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, max_length=40)
    tracks_expiry: bool | None = None
    description: str | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: str | None
    unit: str
    tracks_expiry: bool
    is_active: bool
    description: str | None
    created_at: datetime
    variants: list[VariantResponse] = []


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
