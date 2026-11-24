from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class DailySmsResponse(BaseModel):
    sent: bool
    to_phone: str
    body: str
    sms_log_id: UUID | None = None


class OfferSendRequest(BaseModel):
    area: str | None = None
    message: str = Field(min_length=3, max_length=500)
    only_opt_in: bool = True


class OfferSendResult(BaseModel):
    sent_count: int
    skipped: int
    sample_body: str


class CsvImportLine(BaseModel):
    barcode: str
    qty: Decimal = Field(gt=0)
    cost_price: Decimal = Field(ge=0)
    expiry_date: date | None = None


class CsvImportRequest(BaseModel):
    supplier_id: UUID
    invoice_no: str = Field(min_length=1, max_length=80)
    invoice_date: date
    lines: list[CsvImportLine] = Field(min_length=1)


class OcrInvoiceRequest(BaseModel):
    text: str | None = Field(default=None, max_length=20000)
    image_base64: str | None = None


class OcrInvoiceLine(BaseModel):
    name: str
    qty: Decimal | None = None
    cost_price: Decimal | None = None
    barcode: str | None = None
    expiry_date: date | None = None


class OcrInvoiceResponse(BaseModel):
    provider: str
    lines: list[OcrInvoiceLine]
    raw_notes: str | None = None
