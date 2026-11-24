from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import PaymentMethod


class SaleItemCreate(BaseModel):
    variant_id: UUID
    qty: Decimal = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    use_dealer_price: bool = False


class PaymentCreate(BaseModel):
    method: PaymentMethod
    amount: Decimal = Field(gt=0)
    txn_id: str | None = Field(default=None, max_length=120)


class SaleCreate(BaseModel):
    items: list[SaleItemCreate] = Field(min_length=1)
    payments: list[PaymentCreate] = Field(min_length=1)
    customer_id: UUID | None = None
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    shift_id: UUID | None = None
    branch_id: UUID | None = None
    device_id: str | None = None
    # Contact lookup / invoice — phone or email finds the same customer
    invoice_phone: str | None = Field(default=None, max_length=30)
    invoice_email: str | None = Field(default=None, max_length=255)
    customer_name: str | None = Field(default=None, max_length=160)
    points_to_redeem: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def credit_needs_customer(self) -> "SaleCreate":
        credit = any(p.method == PaymentMethod.credit for p in self.payments)
        if credit and self.customer_id is None and not (
            self.invoice_phone or self.invoice_email
        ):
            raise ValueError("credit sale needs customer phone or email")
        for p in self.payments:
            if p.method in (PaymentMethod.bkash, PaymentMethod.nagad) and not p.txn_id:
                raise ValueError(f"txn_id required for {p.method.value}")
        return self


class InvoiceDelivery(BaseModel):
    sms_sent: bool = False
    email_sent: bool = False
    phone: str | None = None
    email: str | None = None
    detail: str | None = None


class SaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    variant_id: UUID
    batch_id: UUID | None
    qty: Decimal
    unit_price: Decimal
    discount: Decimal


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_type: str
    method: PaymentMethod
    amount: Decimal
    txn_id: str | None


class LoyaltySaleInfo(BaseModel):
    points_redeemed: int = 0
    points_earned: int = 0
    points_balance: int = 0
    points_discount: Decimal = Decimal("0")


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bill_no: str
    customer_id: UUID | None
    user_id: UUID
    shift_id: UUID | None
    branch_id: UUID | None
    device_id: str | None
    subtotal: Decimal
    discount: Decimal
    points_discount: Decimal = Decimal("0")
    points_redeemed: int = 0
    total: Decimal
    created_at: datetime
    items: list[SaleItemResponse] = []
    payments: list[PaymentResponse] = []
    invoice_delivery: InvoiceDelivery | None = None
    loyalty: LoyaltySaleInfo | None = None


class ReturnCreate(BaseModel):
    bill_no: str
    sale_item_id: UUID
    qty: Decimal = Field(gt=0)
    reason: str | None = None
    is_damaged: bool = False
    refund_amount: Decimal | None = Field(default=None, ge=0)


class ReturnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sale_id: UUID
    sale_item_id: UUID
    variant_id: UUID
    batch_id: UUID | None
    qty: Decimal
    reason: str | None
    is_damaged: bool
    refund_amount: Decimal
    created_at: datetime


class ReceiptResponse(BaseModel):
    id: UUID
    sale_id: UUID
    is_copy: bool
    payload: dict | None
    created_at: datetime
